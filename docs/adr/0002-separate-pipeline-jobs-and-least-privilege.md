# 0002. Separate test, build, and publish jobs; only publish can write

Status: Accepted
Date: 2026-10-24

## Context

The pipeline must check every pull request, but only merged code should produce a published, signed image. Publishing needs powerful permissions: writing packages, minting signing identities, and storing attestations.

## Decision

`.github/workflows/ci.yml` has three jobs:

- `test` and `build` run on pull requests and on `main`. They are read-only and never push.
- `publish` runs only on merges to `main`, after `test` and `build` pass. It is the only job with write permissions.

Workflow-level permissions default to read-only, and `publish` raises only what it needs.

## Consequences

**Good**

- **Least privilege.** A pull request cannot publish an image or sign anything.
- **Observability.** Each job reports its own status and duration, so a failure names its stage, and the per-job timings feed lead-time analysis.
- **Independent required checks.** Branch rules can require `test` and `build` separately.

**Costs**

- Each job starts a fresh runner and checks out the code again, which adds a little time to every pull request.
- Jobs do not share files, so `publish` rebuilds the image rather than reusing the one `build` scanned. To close that gap, `publish` rescans the exact digest it signs.
- Checks run twice for each change: once on the pull request and once after the merge. This also catches differences between the pull request and the merged result.

## Alternatives considered

- **One combined job:** simpler, and slightly faster, but a pull request run would hold write permissions, and the status list would show one combined check. We judged the isolation and visibility worth the extra seconds.
- **Reusing the scanned image through an artifact:** avoids the rebuild but adds moving parts. Rescanning the digest is simpler.
