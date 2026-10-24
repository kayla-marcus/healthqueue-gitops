# Design Decisions and Trade-offs

**For:** Maya Chen, CTO
**Subject:** HealthQueue patient scheduling API: what we built, why, and what is still open
**Last reviewed:** 2026-10-24

## The short version

- We built a **delivery system you can trust**. Every change is reviewed, tested, scanned, signed, and deployed from Git. Nobody runs commands against the cluster, and any change can be undone by reverting a pull request.
- The **API itself is not ready for patients**. Bookings are stored in memory, so they disappear on restart and can differ between the two running copies. A shared database is a launch blocker.
- **Several pieces are designed but not deployed**: monitoring, signature enforcement, and real cloud infrastructure. They are marked as such throughout.
- **Five decisions need you**, listed near the end.

## What we built

| What leadership cares about | What exists | Where to look |
|---|---|---|
| Changes are safe and reviewable | Pull requests only; automated tests; Git is the single path to production | [ADR 0001](adr/0001-gitops-with-argo-cd.md) |
| We know what is inside our software | Vulnerability scan, software bill of materials, signed image, signed build record | [Supply chain summary](supply-chain.md) |
| Infrastructure is reproducible | Infrastructure as code with remote state, locking, a plan on every pull request, and a drift drill | [Infrastructure guide](../infra/README.md) |
| We know when it is broken | Targets, error budget, alert rules, and runbooks (a design, not a running system) | [SLOs](slo.md), [Observability plan](observability.md) |
| We can measure delivery speed | A method for the four DORA metrics, demonstrated on **synthetic** data | [DORA report](../dora/output/report_SYNTHETIC.md) |

## The decisions that matter, and what they cost

**1. Deploy from Git, automatically (Argo CD).** Every release is a reviewed pull request, and manual changes to the cluster are reverted. *Cost:* a deployment takes up to about three minutes to start, deleting a file deletes the live resource, and emergency fixes must also go through Git. ([ADR 0001](adr/0001-gitops-with-argo-cd.md))

**2. Only merged code can publish.** The jobs that test and build cannot publish or sign anything. Only the publish job can, and only after a merge. *Cost:* a little extra pipeline time, and checks run twice for every change. ([ADR 0002](adr/0002-separate-pipeline-jobs-and-least-privilege.md))

**3. Aim for SLSA Build Level 2, not Level 3.** We scan, produce an inventory, sign, and record how each image was built. Level 3 needs more isolation in the build system than we judged worthwhile for a first release. *Cost:* the stronger guarantee is not claimed, and nothing yet checks signatures before running an image. ([ADR 0004](adr/0004-supply-chain-controls-and-slsa-level.md))

**4. Use an emulator for cloud infrastructure.** This avoids cloud accounts, spend, and secrets while we prove the process. *Cost:* an emulator is not the real cloud, the pinned version gets no security updates, and its data is lost on restart. ([ADR 0005](adr/0005-localstack-for-infrastructure.md))

**5. Targets of 99.9% availability and 300 ms.** Each extra nine costs far more, and 99.99% would leave about four minutes of failure a month. 99.9% allows 43.2 minutes. *Cost:* these are proposals, because no traffic has been measured. ([ADR 0007](adr/0007-slo-targets-and-burn-rate-alerting.md))

**6. Be honest about the gaps.** We kept bookings in memory to prove the delivery system first, and documented the consequences instead of hiding them. *Cost:* it blocks launch. ([ADR 0006](adr/0006-in-memory-storage-is-a-prelaunch-limitation.md))

## What the synthetic delivery analysis suggests

These figures come from an **invented scenario** and are not HealthQueue's real performance. They show the method, which would rank real bottlenecks the same way once real data exists.

- In the scenario, the largest avoidable cost is the **manual second pull request to change the image tag**: 3.4 hours on average per release, and 5 of 7 failures traced to a hand-edited manifest. The top recommendation is to automate that step while keeping human review.
- The second is **review wait** (4.2 hours on average).
- Recovery is dominated by people opening and approving the rollback, which a pre-approved rollback path would shorten.

## What is not ready for launch

1. **Shared database.** Blocker. Bookings must survive restarts and be consistent across copies.
2. **Authentication, authorization, and encryption in transit.** The API has none.
3. **Monitoring.** The app exposes no metrics, and no monitoring stack runs, so the SLOs cannot be measured yet.
4. **Signature enforcement.** Images are signed, but the cluster does not check.
5. **A production cluster and real cloud infrastructure.** Today's cluster is a local one.
6. **A data-handling review.** The data will relate to health. Nothing here claims compliance with any regulation, and what applies must be confirmed with legal counsel.

## Decisions we need from you

1. **Database and hosting.** Which database, where it runs, and what data protection and retention requirements apply.
2. **Production platform and budget.** Which cloud and cluster, and what we may spend.
3. **Monitoring approach.** Run open-source tools ourselves, or pay for a managed service (which sends operational data to a third party).
4. **Policy choices.** Whether the cluster must reject unsigned images, and whether a rollback may merge without a second approver.
5. **On-call ownership.** Who is paged and who is the escalation contact. The runbooks currently contain placeholders.

## How to check what we claim

- Pipeline runs, pull requests, and plan comments: the repository's Actions and Pull requests tabs.
- Saved terminal output and links: [`docs/evidence/`](evidence/README.md).
- Every decision above has a record in [`docs/adr/`](adr/README.md), including what we rejected.
