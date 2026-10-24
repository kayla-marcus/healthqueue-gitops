# 0007. Set 99.9% and 300 ms targets and alert on burn rate

Status: Accepted
Date: 2026-10-24

## Context

"Reliable" needs a number the team can measure and defend. When a patient cannot book an appointment, they may not get care on time, but each extra nine of availability costs far more effort.

## Decision

- **Availability SLO:** 99.9% of requests to `/appointments` return a status below 500, over a rolling 30 days. The error budget is 0.1%, or 43.2 minutes of full outage per window.
- **Latency SLO:** 95% of those requests complete in under 300 ms.
- **Alerts** use burn rate instead of raw thresholds: page at 14.4x over an hour or 6x over six hours, ticket at 1x over three days.
- Observability is a **plan**. The alert rules are written and syntax-checked, but no monitoring stack is deployed and the app exposes no metrics yet.

## Consequences

**Good**

- A shared definition of "good enough", and a rule for when to stop shipping features (the error budget policy).
- Burn-rate alerts page for real budget loss and stay quiet for brief blips.

**Costs and limits**

- The targets are proposals. No production traffic exists, and the traffic assumption (50,000 requests a day) is a planning figure.
- The SLIs cannot be computed until the app exposes metrics, and are misleading until bookings move to a shared database (ADR 0006).
- Server-side measurement misses outages where requests never reach the app.
- Crashes in Python's built-in server drop connections instead of returning 500s, so logs must be watched alongside status codes.

## Alternatives considered

- **99.99%:** a 4.3-minute monthly budget is smaller than one slow rollout.
- **99%:** allows over seven hours of outage a month, too weak for a booking service.
- **Fixed error-rate thresholds:** simple, but noisy and blind to slow, steady budget loss.

See [`docs/slo.md`](../slo.md) and [`docs/observability.md`](../observability.md).
