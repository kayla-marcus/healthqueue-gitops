# 0008. Use clearly labeled synthetic data for DORA metrics

Status: Accepted
Date: 2026-10-24

## Context

DORA metrics (deployment frequency, lead time, change failure rate, and failed deployment recovery time) describe real delivery history. This project has only a short history and no production, so real figures would be small and unrepresentative.

## Decision

`dora/dora_synthetic.py` generates 90 days of invented deployments for a hypothetical first quarter after launch, using documented assumptions and a fixed random seed. It calculates the four metrics, compares them with DORA's 2024 performance levels, and derives toil-reduction recommendations from the results. Every output carries a visible "SYNTHETIC" label: file names, a data column, and banners in the report.

## Consequences

**Good**

- Demonstrates the method end to end, reproducibly, and is covered by tests.
- Recommendations cite numbers from the data instead of opinion.

**Costs and risks**

- **The results follow from invented assumptions.** They say nothing about real performance and must never be quoted as if they did. The report and this record both say so.
- Small numbers of failures make the failure rate and recovery results fragile, and the report flags this.
- Benchmarks come from DORA's 2024 report, which should be checked against dora.dev before citing.

## Next step

Measure the real thing: deployment events from Git and GitHub Actions, and failures from incident records, then compare real figures with these synthetic ones.

See [`dora/output/report_SYNTHETIC.md`](../../dora/output/report_SYNTHETIC.md).
