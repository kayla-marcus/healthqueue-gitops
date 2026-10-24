# Runbook: High latency

**Alert:** `LatencyBudgetBurn` (ticket)
**Service:** `patient-scheduling-api`, namespace `healthqueue`
**Related:** `docs/slo.md`

## What it means

More than 30% of requests have taken longer than 300 ms over the last 6 hours, using up the latency budget at six times the sustainable rate. Requests are succeeding, but slowly. This is a ticket, not a page, unless users are timing out.

## First 5 minutes

1. **Is it all routes or one?** Compare request duration by route on the service dashboard, or scan recent log lines.
2. **Is the service starved of CPU?**
   ```
   kubectl top pods -n healthqueue
   kubectl describe pod -n healthqueue <pod>
   ```
   The CPU limit is 200m, so sustained load causes throttling and slow responses.
3. **Did a release change behavior?** Check recent merged pull requests and the image tag.
4. **Is the cluster itself slow?** `kubectl get nodes` and `kubectl get events -n healthqueue --sort-by=.lastTimestamp`.

## Common causes and fixes

| Cause | Sign | Fix |
|---|---|---|
| CPU throttling under load | CPU near its limit | Raise the CPU limit or replica count in `k8s/deployment.yaml` through a pull request |
| Large booking list | Slow `GET /appointments` as bookings grow (it returns everything) | Add pagination, or move to a database |
| Slow release | Latency rose right after a deployment | Revert the pull request |
| Node pressure | Slow events, high node load | Investigate the cluster |

Make changes through Git (a pull request), not directly in the cluster. Argo CD's self-heal reverts manual changes.

## Confirm recovery

The slow-request ratio falls below 30% and the alert resolves. Confirm with a health check and a sample booking request.

## After the incident

Record what was slow, why, and how much latency budget was used. Add a follow-up to prevent a repeat.
