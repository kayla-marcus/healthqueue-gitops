# Architecture Decision Records

Each record explains one decision: the situation, what we chose, what it costs, and what we rejected. Records are not edited after the fact. If a decision changes, a new record supersedes the old one.

| # | Decision | Status |
|---|---|---|
| [0001](0001-gitops-with-argo-cd.md) | Deploy with Argo CD from Git, with auto-sync, self-heal, and prune | Accepted |
| [0002](0002-separate-pipeline-jobs-and-least-privilege.md) | Separate test, build, and publish jobs; only publish can write | Accepted |
| [0003](0003-immutable-sha-image-tags.md) | Tag images with the commit hash | Accepted |
| [0004](0004-supply-chain-controls-and-slsa-level.md) | Scan, SBOM, sign, and attest; target SLSA Build Level 2 | Accepted |
| [0005](0005-localstack-for-infrastructure.md) | Use a pinned LocalStack emulator for infrastructure as code | Accepted |
| [0006](0006-in-memory-storage-is-a-prelaunch-limitation.md) | Keep bookings in memory until launch work begins | Accepted, temporary |
| [0007](0007-slo-targets-and-burn-rate-alerting.md) | Set 99.9% and 300 ms targets and alert on burn rate | Accepted |
| [0008](0008-synthetic-dora-data.md) | Use clearly labeled synthetic data for DORA metrics | Accepted |

## Template

```
# NNNN. Title
Status: Proposed | Accepted | Superseded by NNNN
Date: YYYY-MM-DD

## Context
## Decision
## Consequences
## Alternatives considered
```
