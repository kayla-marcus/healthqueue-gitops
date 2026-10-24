# 0001. Deploy with Argo CD from Git, with auto-sync, self-heal, and prune

Status: Accepted
Date: 2026-10-24

## Context

A patient-facing service needs deployments that are reviewable, repeatable, and easy to undo. Hand-run `kubectl apply` commands leave no audit trail and let the cluster drift from what anyone reviewed.

## Decision

Git is the source of truth. Argo CD, running inside the cluster, watches the `k8s/` folder on `main` and applies it. The Application (`argocd/application.yaml`) enables:

- **Auto-sync:** merged changes deploy without a manual Sync.
- **Self-heal:** manual changes to the cluster are reverted.
- **Prune:** a resource whose manifest is deleted from Git is deleted from the cluster.

Every change goes through a pull request. To deploy a new version, a pull request changes the image tag in `k8s/deployment.yaml`.

## Consequences

**Good**

- Every production change has a pull request, a reviewer, and a commit.
- Rollback is reverting a pull request.
- Manual edits do not survive, so the cluster cannot quietly diverge.
- No cluster credentials are stored in GitHub, because Argo CD pulls from a public repository.

**Costs and risks**

- **Prune can delete things.** Removing or renaming a manifest in a merged pull request deletes the live resource. Reviewers must check deleted and renamed files.
- **Delay.** Argo CD checks Git about every 3 minutes, so a deployment is not instant.
- **Self-heal fights emergency fixes.** Edits with `kubectl edit`, `scale`, or `rollout undo` are reverted. The runbooks say to fix things through Git.
- **A second pull request per release.** Changing the image tag by hand is slow and error-prone. See ADR 0003 and the DORA recommendations.

## Alternatives considered

- **Push from CI** (`kubectl apply` in GitHub Actions): needs cluster credentials stored in CI, and a local cluster is not reachable from GitHub's servers.
- **Flux:** a comparable GitOps tool. Argo CD was already installed and its UI shows sync state clearly.
- **Manual deploys:** rejected for the reasons in the context.
