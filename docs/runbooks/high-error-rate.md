# Runbook: High error rate

**Alerts:** `ErrorBudgetBurnFast` (page), `ErrorBudgetBurnSlow` (page), `ErrorBudgetBurnSteady` (ticket)
**Service:** `patient-scheduling-api`, namespace `healthqueue`
**Related:** `docs/slo.md` (what the numbers mean), `docs/observability.md`

## What it means

The API is returning 5xx responses faster than the 99.9% availability SLO allows. Patients may be unable to book or view appointments. The faster the burn, the faster to act: a page means the monthly error budget is draining in hours or days.

## First 5 minutes

1. **Is the service up and what is running?**
   ```
   kubectl get pods -n healthqueue
   kubectl get application patient-scheduling-api -n argocd
   kubectl get deployment patient-scheduling-api -n healthqueue -o 'jsonpath={.spec.template.spec.containers[0].image}'
   ```
   Note the image tag and the Application's `revision`.
2. **Look at recent errors.** Logs are one JSON line per request:
   ```
   kubectl logs -n healthqueue deploy/patient-scheduling-api --tail=200 | Select-String '"status":5'
   ```
   Also look for Python tracebacks. A crashing handler may drop the connection instead of returning a 500, so it will not show up as a status code.
3. **Did something change recently?** Check the most recent merged pull requests and the last `publish` run. A new image tag in `k8s/deployment.yaml` is the most common cause.
4. **Resource pressure?** `kubectl describe pod -n healthqueue <pod>` and look for `OOMKilled` (the memory limit is 128Mi) or repeated restarts.

## Common causes and fixes

| Cause | Sign | Fix |
|---|---|---|
| Bad release | Errors began right after a deployment PR merged | Revert that pull request (see below) |
| Out of memory | `OOMKilled`, restarts climbing | Raise the limit in `k8s/deployment.yaml` through a pull request |
| Crashing handler | Tracebacks in logs, dropped connections | Fix the code, or revert the release |
| Bad input pattern | Errors on one route only | Fix the handler. Consider blocking the caller. |

## Fix through Git, not the cluster

Argo CD's self-heal reverts manual changes, so edits made with `kubectl edit`, `kubectl scale`, or `kubectl rollout undo` will be undone within minutes.

1. Revert the merge commit of the bad deployment pull request, and open a pull request for the revert.
2. Merge it. Argo CD checks Git about every 3 minutes. In an emergency an authorized engineer may trigger a sync in the Argo CD UI; record that in the incident notes.
3. To restart a stuck pod, delete the pod (`kubectl delete pod -n healthqueue <pod>`). Do **not** use `kubectl rollout restart`, which edits the Deployment and will be reverted.

> **Warning:** bookings are held in pod memory today. Restarting or deleting a pod **loses the bookings it holds.** Tell the on-call lead before restarting, and record how many patients may be affected.

## Confirm recovery

- `kubectl get pods -n healthqueue` shows all pods `Running` and ready.
- Health check passes through a port-forward: `curl.exe http://localhost:8080/health`.
- The 5xx ratio returns below the threshold and the alert resolves.

## Escalation

If errors continue 15 minutes after a revert, escalate to the engineering lead (the service owner). Replace this line with the real on-call contact before launch.

## After the incident

- Record the start and end times, the cause, patient impact, and how much error budget was used (see the policy in `docs/slo.md`).
- Open follow-up issues. Apply the error budget policy if less than 25% remains.
