# Evidence

Terminal output, links, and screenshots that show each requirement works. Add files here as each step is completed, and note the date.

## CI/CD and supply chain
- [ ] Link to a green `publish` run on `main`
- [ ] Output of the verify step (`cosign verify` and `gh attestation verify`)
- [ ] The `sbom-cyclonedx` artifact (downloaded from the run)
- [ ] Link to a PR run where `test` or `build` failed on purpose, then passed

## GitOps
- [ ] Links to both PRs from the GitOps demo
- [ ] `kubectl get application`, revision, `initiatedBy`, and image output
- [ ] `/health` response showing the new version
- [ ] Self-heal demo output

## Infrastructure as Code
- [ ] `tofu plan` and `tofu apply` output
- [ ] State locking evidence
- [ ] Drift detection output and how it was resolved

## Observability and DORA
- [ ] Generated DORA report (clearly labeled synthetic)
