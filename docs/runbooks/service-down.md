# Runbook: Service down or crash-looping

**Alerts:** `NoReplicasAvailable` (page), `PodRestartingRepeatedly` (ticket)
**Service:** `patient-scheduling-api`, namespace `healthqueue`
**Related:** `docs/slo.md`

## What it means

No pods are ready to serve traffic, or a pod keeps restarting. If no replicas are available, **patients cannot book appointments** and the availability budget is draining at its fastest.

## First 5 minutes

1. **See what state the pods are in:**
   ```
   kubectl get pods -n healthqueue
   kubectl describe pod -n healthqueue <pod>
   kubectl get events -n healthqueue --sort-by=.lastTimestamp
   ```
2. **Read the status:**

   | Status | Meaning | Next step |
   |---|---|---|
   | `ImagePullBackOff` / `ErrImagePull` | The image tag is wrong, missing, or the package is private | Check the tag in `k8s/deployment.yaml` against the `publish` run. Fix or revert by pull request. |
   | `CrashLoopBackOff` | The container starts and exits | `kubectl logs -n healthqueue <pod> --previous` for the error |
   | `OOMKilled` | The 128Mi memory limit was exceeded | Raise the limit by pull request |
   | `Pending` | No node can run the pod | `kubectl describe pod` shows why (resources or scheduling) |
   | Readiness failing | `/health` is not answering | Check the logs and the probe settings |

3. **Check the GitOps layer.**
   ```
   kubectl get application patient-scheduling-api -n argocd
   ```
   `OutOfSync` or `Degraded` points to a bad manifest. A rejected change should be reverted in Git.

## Fix through Git, not the cluster

Revert the pull request that introduced the problem, merge the revert, and let Argo CD apply it (about 3 minutes, or a manual sync by an authorized engineer, recorded in the incident notes). Manual cluster edits are reverted by self-heal.

If the cluster itself is unreachable, restore it first: confirm Docker Desktop and the kind cluster are running, and check `kubectl get nodes`.

> **Warning:** bookings are held in pod memory today. When pods restart, **the bookings in them are lost.** Record the time of the outage and tell the on-call lead so affected patients can be contacted.

## Confirm recovery

- All pods `Running` and ready.
- `kubectl get application patient-scheduling-api -n argocd` shows `Synced` and `Healthy`.
- A health check passes through a port-forward, and a test booking works.

## Escalation

If the service is still down 15 minutes after a revert, escalate to the engineering lead. Replace this line with the real on-call contact before launch.

## After the incident

Record the outage window and patient impact, and subtract it from the error budget. A full outage of 43.2 minutes uses the whole 30-day availability budget. Write a post-incident review.
