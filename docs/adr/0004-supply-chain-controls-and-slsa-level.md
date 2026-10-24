# 0004. Scan, SBOM, sign, and attest; target SLSA Build Level 2

Status: Accepted
Date: 2026-10-24

## Context

The service will handle appointment data for patients, so customers and auditors will ask what is inside the container and who built it. A vulnerability scan, a software bill of materials (SBOM), a signature, and a build record each answer a different question, and none replaces another.

## Decision

On every merge, `publish`:

1. Scans the pushed image digest with Trivy and fails on fixable HIGH or CRITICAL vulnerabilities.
2. Generates a CycloneDX SBOM and attaches it to the image as a signed attestation.
3. Signs the image digest with cosign, using keyless signing tied to the workflow's identity.
4. Attests build provenance with GitHub's `actions/attest`.
5. Verifies its own signature and provenance.

We target and claim **SLSA v1.0 Build Level 2**, and do not claim Level 3. The third-party Trivy action is pinned to an exact commit, because its project reported a supply chain attack and a tag migration. Pinning the remaining actions is tracked as an open item.

## Consequences

**Good**

- Anyone can verify an image with `cosign verify` and `gh attestation verify`.
- The scan and the signature apply to the same digest.

**Costs and limits**

- A signature does not establish a SLSA level by itself, and a scan does not replace an SBOM. The summary says what each control proves.
- **Nothing verifies signatures at deploy time.** An unsigned image could still be named in a manifest. An admission policy would enforce it.
- The scan covers only fixable operating-system and package vulnerabilities, at one point in time.
- Keyless signing records the repository identity in a public transparency log.

## Alternatives considered

- **Level 3 through isolated reusable workflows:** more isolation, more complexity. Not needed to meet the target.
- **Long-lived signing keys:** a key must be stored and rotated. Keyless avoids this.
- **Scan only:** cheapest, but proves nothing about origin.

Details and the full list of gaps are in [`docs/supply-chain.md`](../supply-chain.md).
