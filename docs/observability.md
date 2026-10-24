# Observability Plan

**Service:** HealthQueue patient scheduling API
**Status:** this is a **plan**. Only part of it exists today, and no monitoring stack is deployed. The table below separates what is real from what is intended.
**Last reviewed:** 2026-10-24

## Goal

Answer three questions quickly: *Is the service meeting its SLOs? (metrics) What went wrong for this request? (logs) Where did the time go? (traces)* Each signal is chosen for the question it answers best.

## Where we are today

| Signal | Today | Planned |
|---|---|---|
| Metrics | None from the app. Kubernetes probes check `/health` only. | `/metrics` endpoint with request count and duration |
| Logs | **Yes.** One JSON line per request (method, path, status) to stderr, readable with `kubectl logs`. | Collected and searchable, with a request ID |
| Traces | None | Deferred (see rationale) |
| Alerts | Rules written in `observability/alerts.yml`, **not deployed** | Deployed with the metrics stack |
| Dashboards | None | Planned list below |

## Metrics

**What:** the "RED" signals for every route: **R**ate (requests per second), **E**rrors (5xx ratio), **D**uration (latency histogram).

**Why:** the SLIs in `docs/slo.md` are ratios of these counters, so metrics are the only signal that can answer "are we within budget?" They are cheap to store, aggregate well, and are the right input for alerts.

**Planned metrics** (the names used by `observability/alerts.yml`):

- `http_requests_total{route, code}`
- `http_request_duration_seconds_bucket{route, le}` (with `_count` and `_sum`)

**Rules:**

- Label by **route template** (`/appointments/{id}`) and status code only. Never label by patient, provider, or appointment ID: it explodes storage cost and leaks identifiers.
- Include a bucket boundary at exactly 0.3 seconds so the latency SLI can be read directly.
- Also use infrastructure metrics from Kubernetes (replica availability, restarts, CPU, memory) for the "service down" and "crash loop" alerts.

## Logs

**What:** structured JSON, one object per request. Already in place: `method`, `path` (query string removed), `status`.

**Why:** metrics say *that* something is wrong; logs say *what* happened. They are the only place to see an individual failure, a stack trace from a crash, or an audit trail.

**Planned additions:** a request ID on every line and in the response header, and the error text for failed requests.

**Privacy rules (health data):**

- Never log request bodies or query strings.
- Log only opaque IDs. No names, dates of birth, or contact details, and no patient or provider IDs unless there is a specific, reviewed need.
- Do not record client IP addresses in application logs.
- Retain logs for 30 days unless a compliance requirement says otherwise. Whether any regulation applies to this data must be confirmed with legal counsel. Nothing in this repository claims compliance with any health data law.

## Traces

**What:** a record of one request's path through the system, with timing for each step (OpenTelemetry is the standard).

**Why we are deferring them:** today there is one service with no database and no outbound calls, so a trace would show a single step. That is poor value for the setup and maintenance cost. Traces become valuable when the API gains a database, a notification service, or other dependencies, because they show which hop is slow.

**Trigger to adopt:** the first time a request crosses a process boundary (for example, the shared database). Sample about 10% of requests, and keep the same privacy rules as logs.

## Tooling

An open-source stack fits the existing Kubernetes and GitOps setup and avoids a vendor decision before launch:

| Need | Choice | Why |
|---|---|---|
| Metrics and alert rules | Prometheus (rules already written) | Standard for Kubernetes, rules are plain files in Git |
| Dashboards | Grafana | Reads Prometheus and logs together |
| Logs | Loki | Cheap, label-based, pairs with Grafana |
| Traces (later) | Tempo plus OpenTelemetry | Same Grafana experience |

The alternative is a managed service, which removes operating cost but adds per-volume fees and sends health-adjacent data to a third party. That is a decision for leadership once the data-handling rules are settled.

## Dashboards (planned)

1. **SLO overview:** availability and latency over 30 days, error budget remaining, current burn rate.
2. **Service health:** request rate, error ratio, latency percentiles, by route.
3. **Platform:** replicas available, restarts, CPU and memory against limits.

## Alerts and response

Alerts follow the burn-rate method from `docs/slo.md`, defined in `observability/alerts.yml`. Each alert links to a runbook:

| Alert | Severity | Runbook |
|---|---|---|
| Error budget burning fast or slow | Page | `docs/runbooks/high-error-rate.md` |
| Error budget burning steadily | Ticket | `docs/runbooks/high-error-rate.md` |
| Latency budget burning | Ticket | `docs/runbooks/high-latency.md` |
| No replicas available | Page | `docs/runbooks/service-down.md` |
| Pod restarting repeatedly | Ticket | `docs/runbooks/service-down.md` |

## Rollout order

1. Add `/metrics` to the app (request count and duration).
2. Move bookings to a shared database, otherwise the SLIs are misleading.
3. Deploy Prometheus and load the rules.
4. Add log collection and the request ID.
5. Add an external synthetic probe for the blind spot described in `docs/slo.md`.
6. Add tracing when the first dependency appears.

## Not in scope

No monitoring stack is deployed in this repository, and the alert rules have never fired against real traffic. This plan documents the design and the reasoning.
