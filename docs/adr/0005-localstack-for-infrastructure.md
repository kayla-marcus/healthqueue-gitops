# 0005. Use a pinned LocalStack emulator for infrastructure as code

Status: Accepted
Date: 2026-10-24

## Context

The project needs OpenTofu to provision cloud resources with remote state and locking, without a paid cloud account. The current LocalStack images require an account and auth token, which adds sign-up and secret handling.

## Decision

- Use LocalStack **4.4.0**, an older community release that needs no token, bound to localhost.
- Provision an S3 bucket (with versioning) and an SNS topic, with state in a separate S3 bucket and S3 native lock files for locking. If the emulator cannot support lock files, the runbook describes a DynamoDB fallback.
- Create the state bucket by hand once, because OpenTofu cannot store state in a bucket that does not exist yet.
- In CI, start a **fresh emulator on every run**. The plan job first applies the base branch so the pull request comment shows only what this change alters.
- Pin the OpenTofu binary and verify its checksum.

## Consequences

**Good**

- No cloud account, cost, or secret. The pipeline holds only dummy credentials.
- Infrastructure changes are reviewed through a plan comment, then applied from Git.

**Costs and risks**

- **An emulator is not AWS.** Behavior can differ, and the pinned image is unmaintained and gets no security fixes. It runs only on a developer machine or in a temporary CI job.
- **State is lost when the emulator restarts.** Real cloud storage would not behave this way.
- **The CI environment is temporary.** GitHub's servers cannot reach a laptop, and a self-hosted runner on a public repository would be a security risk. CI proves the code builds the infrastructure from scratch, but the laptop copy can drift. A manual drift drill demonstrates detection and repair.
- A real cloud target would need short-lived credentials (OIDC), a least-privilege role, and an approval step before apply.

## Alternatives considered

- **Current LocalStack with a token:** works, but needs an account and secret handling.
- **A real cloud free tier:** closest to production, but adds account, credential, and cost risk.
- **A self-hosted runner on the laptop:** would let CI update the laptop copy, but is unsafe for a public repository.
