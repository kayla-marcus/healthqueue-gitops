# Service Level Objectives (SLOs)

**Service:** HealthQueue patient scheduling API (`patient-scheduling-api`)
**Status:** proposed launch targets. There is no production traffic yet, so nothing below has been measured. Review the targets after 30 days of real data.
**Last reviewed:** 2026-10-24

## Why these exist

Patients use this API to book appointments. When it is down or slow, someone may not get care on time. An SLO turns "reliable enough" into a number the team can measure and defend, and the error budget turns that number into a decision rule: how much unreliability we can afford before we stop shipping features.

## Service level indicators (SLIs)

An SLI is a ratio: **good events / valid events**.

| SLI | Good event | Valid events | Measured at |
|---|---|---|---|
| **Availability** | A request to `/appointments` or `/appointments/{id}` that returns any status below 500 | All requests to those routes | The application (server side) |
| **Latency** | A request to those routes answered in **under 300 ms** | All requests to those routes | The application (server side) |

Decisions behind these definitions:

- **4xx responses count as good.** A `409` for a double booking or a `400` for a bad request means the API did its job. Only server failures (5xx) hurt the patient's experience of the service.
- **Health probes are excluded.** Kubernetes calls `/health` every few seconds, so including it would flatter the numbers. The SLIs cover real patient traffic only.

## The objectives

| SLO | Target | Window |
|---|---|---|
| Availability | **99.9%** of requests succeed | Rolling 30 days |
| Latency | **95%** of requests complete in under 300 ms | Rolling 30 days |

## Error budget

The error budget is the amount of failure the SLO allows: **error budget = 1 − SLO target**.

**Availability, 99.9% over 30 days**

- Budget = 1 − 0.999 = **0.1%** of requests.
- As time: 30 days × 24 h × 60 min = 43,200 minutes. 43,200 × 0.001 = **43.2 minutes** of full outage.
- As requests: this needs a traffic assumption. Assuming **50,000 requests per day** (a planning figure, not a measurement), that is 1,500,000 requests per 30 days, so the budget is **1,500 failed requests**.

**Latency, 95% under 300 ms**

- Budget = 5% of requests. At the same assumed traffic, **75,000 requests** may be slower than 300 ms in 30 days.

**How a budget is spent (worked example).** If 600 requests fail in the first 10 days, 600 / 1,500 = **40%** of the availability budget is gone, and **900** failed requests remain for the other 20 days.

**What other targets would mean** (same 30-day window and traffic assumption):

| Availability SLO | Allowed outage | Failed requests allowed |
|---|---|---|
| 99.5% | 216 min | 7,500 |
| **99.9% (chosen)** | **43.2 min** | **1,500** |
| 99.95% | 21.6 min | 750 |
| 99.99% | 4.32 min | 150 |

### Burn rate

Burn rate is how fast the budget is being spent: 1x uses exactly the whole budget over the window, 10x uses it ten times too fast. These are the thresholds the alerts use (see `observability/alerts.yml`).

| Burn rate | Over | Budget consumed | Budget gone in | Response |
|---|---|---|---|---|
| 14.4x | 1 hour | 2% | about 2 days | Page now |
| 6x | 6 hours | 5% | 5 days | Page |
| 1x | 3 days | 10% | 30 days | Ticket |

## Error budget policy

| Budget remaining | Action |
|---|---|
| More than 50% | Normal work. Ship features. |
| 25% to 50% | Review recent incidents. Prefer small, low-risk changes. |
| Under 25% | Reliability work comes first. Only fixes and safety changes ship. |
| Exhausted (0%) | Feature freeze until the budget recovers. Write a post-incident review. |

## Why these numbers

- **99.9%, not 99.99%.** Each extra nine costs far more engineering effort. At 99.99% the budget is 4.3 minutes a month, less than one slow rollout. 99.9% is demanding but reachable for a new service, and we can raise it later.
- **300 ms.** A booking request does a small amount of in-memory work, so 300 ms leaves room for a real database later while still feeling instant to a person.
- **30-day rolling window.** Long enough to smooth out one bad afternoon, short enough that last quarter's outage doesn't hide this week's trend.

## Known limitations

These affect whether the numbers can be trusted. Resolve them before relying on the SLOs for launch decisions.

1. **No metrics exist yet.** The app does not expose `/metrics`, so none of these SLIs can be computed today. See `docs/observability.md`.
2. **Storage is per-pod memory.** The Deployment runs two replicas and each has its own bookings. A valid booking can return `404` from the other replica, and a `404` counts as "good" here, so the availability SLI would overstate real quality. A shared database is needed before launch.
3. **Crashes may not appear as 5xx.** Python's built-in server drops the connection when a handler throws, instead of sending a `500`. Those failures would be missed by a status-code SLI, so logs must also be watched for tracebacks.
4. **Server-side measurement has blind spots.** If the cluster or network is down, no request reaches the app and nothing is recorded. A synthetic probe from outside the cluster would close this gap.
5. **The current environment is a single local cluster.** A 99.9% target describes the planned production deployment, not the laptop demo.
6. **Traffic and thresholds are assumptions.** Revisit them after launch.
