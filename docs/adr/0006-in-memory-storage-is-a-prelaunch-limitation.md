# 0006. Keep bookings in memory until launch work begins

Status: Accepted, temporary
Date: 2026-10-24

## Context

The API needs to demonstrate scheduling behavior, deployment, and reliability practices. Adding a database would add a new dependency, credentials, and operational work before the delivery pipeline was proven.

## Decision

Appointments live in process memory. Patient and provider identifiers are opaque IDs, and no names or other personal details are stored. The Deployment keeps two replicas so that rolling updates have no downtime.

## Consequences

**Costs and risks (this is a launch blocker)**

- **Two replicas, two copies.** A booking made through one pod can return `404` from the other.
- **Restarts lose data.** Any pod restart, rollout, or crash discards the bookings it held, and the runbooks warn about this.
- **SLOs are unreliable.** The availability SLI counts a `404` as a good response, so it would overstate quality. See `docs/slo.md`.
- Not suitable for real patient data. The README says so.

**Good**

- A small, dependency-free service that is easy to build, scan, and explain.

## Required before launch

A shared database, with a decision on hosting, backups, access control, and data protection requirements. That choice needs leadership input and should get its own record. Until then, no real patient data should be used.

## Alternatives considered

- **One replica:** consistent, but every rollout still loses data and removes availability headroom.
- **SQLite on a volume:** simple, but awkward with multiple replicas and rollouts.
- **Managed database now:** the right end state, deferred to keep the first milestone focused.
