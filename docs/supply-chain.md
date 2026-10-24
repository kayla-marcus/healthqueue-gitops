# Supply Chain Security Summary

**Audience:** HealthQueue engineering leadership.
**Scope:** how the `patient-scheduling-api` container image is built, checked, signed, and recorded.
**Last reviewed:** 2026-10-23

## In one paragraph

Every change to `main` is tested, built, scanned for vulnerabilities, and published by a GitHub Actions pipeline. The published image is signed, and it carries a signed record of how it was built (provenance) and what is inside it (an SBOM). We claim **SLSA v1.0 Build Level 2**. We do **not** claim Level 3, and the cluster does not yet verify any of this before running an image (see [Known gaps](#known-gaps)).

## Controls at a glance

| Control | Tool | Where in `.github/workflows/ci.yml` | What it gives us | What it does not give us |
|---|---|---|---|---|
| Automated tests | `unittest` | `test` job | Code behaves as specified before anything is built | Does not test the container or the cluster |
| Vulnerability scan | Trivy | `build` job (early feedback) and `publish` job (the exact digest we sign) | Fails the pipeline on fixable HIGH or CRITICAL vulnerabilities | Ignores vulnerabilities with no fix yet. A point-in-time result: new vulnerabilities appear later. |
| SBOM | Trivy (CycloneDX format) | `publish` job | An inventory of the packages inside the image, stored as a run artifact and as a signed attestation | Only as complete as the scanner's detection. Not proof the contents are safe. |
| Image signature | cosign, keyless | `publish` job | Proof the image digest was signed by this repository's workflow | Does not describe how the image was built or what it contains |
| Build provenance | `actions/attest` | `publish` job | A signed record linking the image digest to the commit and workflow that built it | Not enforced anywhere until something verifies it |
| Self-verification | `cosign verify`, `gh attestation verify` | last step of `publish` | The pipeline checks its own signature and provenance right after creating them | Proves the pipeline is consistent, not that anyone downstream checks |

Each control answers a different question, and none replaces another. A clean scan says nothing about who built the image. A signature says nothing about what is inside it.

## SLSA alignment

SLSA ("Supply-chain Levels for Software Artifacts") grades how trustworthy a build's provenance is. We target and claim **Build Level 2**.

**Why we can claim Level 2:** the image is built on GitHub-hosted runners, not on a developer laptop, and the pipeline produces signed provenance tied to the exact image digest. GitHub's documentation states that artifact attestations on their own provide SLSA v1.0 Build Level 2 (see [GitHub: using artifact attestations to establish provenance for builds](https://docs.github.com/en/actions/security-guides/using-artifact-attestations-to-establish-provenance-for-builds)).

**Why we do not claim Level 3:** per GitHub's guidance, Level 3 needs the build isolated from the calling workflow, using audited reusable workflows with a verification policy that requires them. Our build and signing steps live in the same workflow file as the triggering logic, so we do not meet that isolation.

**What a signature does and does not mean:** signing the image does not by itself establish a SLSA level. The level comes from how the provenance is produced and protected. The cosign signature and the provenance attestation are separate artifacts that answer separate questions.

SLSA also defines requirements about source code handling. We do not claim anything beyond the Build level. Branch rules require pull requests, but there are no required reviewers (single maintainer).

## Known gaps

These are deliberate scope decisions or open items, not hidden problems.

1. **Nothing verifies signatures before deploy.** Argo CD and Kubernetes will run any image named in `k8s/deployment.yaml`. Enforcing signatures would need an admission policy (for example Kyverno or Sigstore's policy-controller). Not implemented.
2. **The deployment pins a tag, not a digest.** Tags of the form `sha-<commit>` are unique by convention, but the registry does not enforce immutability. Pinning the digest in the manifest would close this.
3. **The first image (`v1.0.0`) was pushed by hand** from a developer machine and is unsigned. The image deployed after the GitOps demo comes from the pipeline.
4. **Third-party action pinning is incomplete.** The Trivy action is pinned to an exact commit. `sigstore/cosign-installer` is currently pinned to a version tag, and GitHub's own actions to major version tags. A moved tag could change what runs in the pipeline.
5. **The base image is not pinned by digest.** `python:3.12-slim` can change between builds, which helps patching but reduces reproducibility.
6. **No required reviewers.** A single maintainer can merge their own pull requests.
7. **Scan scope is limited.** Fixable HIGH and CRITICAL findings only, and only the container's operating system and installed packages. Application code is not analyzed for flaws.
8. **Public transparency log.** Keyless signing records the repository identity in Sigstore's public log. That is expected for a public repository.
9. **Infrastructure pipeline tooling.** The OpenTofu binary is pinned and checksum-verified. The LocalStack image is pinned by tag, not digest, and is an unmaintained release that runs only inside a temporary CI job or on a developer machine. The pipeline targets an emulator with dummy credentials. A real cloud target would need OIDC short-lived credentials, a least-privilege role, and an approval step.

## Why third-party actions are pinned by commit

The Trivy GitHub Action's own release notes describe a recent supply chain attack and a migration of its tags. A tag such as `@v1` can be moved to different code. A full commit hash cannot. For this reason we pin the actions that matter most to an exact commit and track the rest as a known gap above.

## How to verify a published image

Take the digest from the `publish` job summary on GitHub (the line beginning "Published").

```
cosign verify ghcr.io/kayla-marcus/patient-scheduling-api@sha256:<digest> --certificate-identity https://github.com/kayla-marcus/healthqueue-gitops/.github/workflows/ci.yml@refs/heads/main --certificate-oidc-issuer https://token.actions.githubusercontent.com

gh attestation verify oci://ghcr.io/kayla-marcus/patient-scheduling-api@sha256:<digest> --repo kayla-marcus/healthqueue-gitops
```

The SBOM is attached to each `publish` run as the `sbom-cyclonedx` artifact.

## Recommended next steps (not required for Level 2)

- Pin `cosign-installer` to a full commit hash, and let Dependabot keep action pins current.
- Deploy by digest instead of tag.
- Add an admission policy that rejects unsigned images.
- Move build and signing into a reusable workflow to work toward Level 3.
