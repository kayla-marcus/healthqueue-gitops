# 0003. Tag images with the commit hash

Status: Accepted
Date: 2026-10-24

## Context

Argo CD only redeploys when something in Git changes. A tag like `latest` never changes in Git, so a new image would not roll out, and nobody could tell which code a running pod contains.

## Decision

The `publish` job tags each image `sha-<first 7 characters of the commit>` (for example `sha-d143c2b`). A deployment is a pull request that sets that tag in `k8s/deployment.yaml`. The first image, `v1.0.0`, was pushed by hand before the pipeline existed and is the only exception.

## Consequences

**Good**

- Any running pod traces to one commit, one build, and one signed digest.
- The tag changes with every build, so Git always shows what changed.

**Costs and risks**

- **Immutability is a convention.** The registry does not stop someone pushing a different image under an existing tag. Signing and provenance apply to the digest, so deploying by digest would close this gap. It is listed as a next step in `docs/supply-chain.md`.
- **Copying the tag is manual.** A mistyped tag causes an `ImagePullBackOff`. In the synthetic DORA scenario this is the most common failure cause, and automating the tag pull request is the top toil recommendation.
- Tags are less readable than version numbers. The app reports its own version at `/health`.

## Alternatives considered

- **Semantic version tags** (`v1.2.0`): readable, but depend on someone remembering to bump them and are easier to reuse by mistake.
- **`latest`:** rejected, see the context.
- **Digest pinning in the manifest:** the strongest option, deferred because it makes the manual step harder until the tag pull request is automated.
