# Infrastructure (OpenTofu + LocalStack)

OpenTofu provisions two cloud resources, with remote state and state locking, against **LocalStack, a local AWS emulator**. Nothing here runs on real AWS. The emulator was chosen to avoid cloud cost and account setup; the OpenTofu code is the same shape it would be against real AWS (only the endpoints and dummy credentials differ).

| Resource | Purpose |
|---|---|
| `aws_s3_bucket.supply_chain_artifacts` (+ versioning) | Archive for SBOMs and scan reports |
| `aws_sns_topic.alerts` | Destination for operational alerts (see the observability plan) |
| State bucket `healthqueue-tofu-state` | Remote state (created in step 2, outside OpenTofu) |

## Prerequisites

- Docker Desktop running
- OpenTofu **1.10 or newer** (`tofu version`). Install with `winget install --id=OpenTofu.Tofu -e`, or see opentofu.org.
- Access to the `localstack/localstack:4.4.0` image. Check with `docker pull localstack/localstack:4.4.0`. No account or token is needed for this older community release.

## 1. Start LocalStack

If an old `localstack` container exists from an earlier attempt, remove it first: `docker rm -f localstack`.

```
cd infra
docker compose up -d
curl.exe http://localhost:4566/_localstack/health
```

LocalStack can take 10 to 30 seconds to become ready.

## 2. Create the state bucket (one-time bootstrap)

OpenTofu cannot store its state in a bucket that does not exist yet, so this one bucket is created by hand.

```
docker exec localstack awslocal s3 mb s3://healthqueue-tofu-state
docker exec localstack awslocal s3api put-bucket-versioning --bucket healthqueue-tofu-state --versioning-configuration Status=Enabled
```

## 3. Plan and apply

Save the output as evidence (run from `infra/`).

```
tofu init
tofu plan -no-color | Tee-Object ..\docs\evidence\tofu-plan.txt
tofu apply -no-color | Tee-Object ..\docs\evidence\tofu-apply.txt
tofu output
```

## 4. Show state locking

1. In window A, run `tofu apply` and **do not answer the prompt**. The run is now holding the lock.
2. In window B, run `tofu plan`. It should fail with "Error acquiring the state lock".
3. In window A, type `no` to cancel. Save the error from window B as `docs/evidence/tofu-lock.txt`.

## 5. Show and fix drift

Change a resource outside of OpenTofu:

```
docker exec localstack awslocal s3api put-bucket-versioning --bucket healthqueue-supply-chain-artifacts --versioning-configuration Status=Suspended
```

Detect it:

```
tofu plan -no-color | Tee-Object ..\docs\evidence\tofu-drift-plan.txt
```

The plan should show versioning changing from `Suspended` back to `Enabled`. Git is the source of truth, so we resolve the drift by applying:

```
tofu apply -no-color | Tee-Object ..\docs\evidence\tofu-drift-fix.txt
```

(`tofu plan -refresh-only` records the drift in state without changing anything. Use it when the out-of-band change should be investigated before it is overwritten.)

## Things to know

- **The emulator is a pinned, unmaintained release.** Current LocalStack images require an account and token, so this project pins an older community tag (`4.4.0`) that needs neither. It gets no security fixes, so it runs only on your machine, bound to localhost, and is never deployed or exposed. A newer community tag (4.12 is reported to be the last one) may behave closer to real AWS; change the tag in `docker-compose.yml` if you hit a missing feature.
- **Restarting LocalStack erases everything**, including the state bucket, unless persistence is configured. If that happens, repeat steps 2 and 3. This is an emulator limitation, not how real cloud storage behaves.
- **If locking does not work on LocalStack** (step 4 shows no error), the emulator may not support S3 conditional writes. Fall back to a DynamoDB lock table:
  ```
  docker exec localstack awslocal dynamodb create-table --table-name healthqueue-tofu-locks --attribute-definitions AttributeName=LockID,AttributeType=S --key-schema AttributeName=LockID,KeyType=HASH --billing-mode PAY_PER_REQUEST
  ```
  Then in `backend.tf`, replace `use_lockfile = true` with `dynamodb_table = "healthqueue-tofu-locks"` and add `dynamodb = "http://localhost:4566"` to `endpoints`. Run `tofu init -reconfigure`.
- **Dummy credentials** (`test` / `test`) are LocalStack defaults, not secrets. Real AWS credentials must never go in these files.
- **Commit** `.terraform.lock.hcl`. **Never commit** `.terraform/` or any `*.tfstate` file (both are in `.gitignore`).
- The commands in this README are for your own machine. Pull requests and merges also run through the pipeline below, against a separate, temporary LocalStack.

## The infrastructure pipeline (GitHub Actions)

| Trigger | Workflow job | What happens |
|---|---|---|
| Pull request touching `infra/` | `validate` | Formatting check and `tofu validate` |
| Pull request touching `infra/` | `plan` | Builds a baseline from the base branch, plans this PR against it, and posts the plan as a PR comment |
| Merge to `main` | `apply` | Plans, applies the saved plan, then re-plans to confirm nothing is left to change |
| Manual run of "Infrastructure drift drill" | `drift-drill` | Applies, changes a resource by hand, detects the drift with `plan`, reconciles with `apply` |

**How Git stays the source of truth here**

- Infrastructure reaches the pipeline's environment only through a merged pull request. Direct pushes to `main` are blocked by the branch ruleset.
- Reviewers see the plan before merging, and the merge applies the saved plan, not a fresh guess.
- The OpenTofu binary is pinned to an exact version and verified against a checksum. Each job has the minimum permissions it needs, and only `plan` can write (PR comments).
- The target is an emulator with dummy credentials, so the pipeline holds no cloud secrets.

**What this does not guarantee**

- **The pipeline's environment is temporary.** Every run starts a fresh LocalStack, so "apply" proves the code builds the infrastructure from scratch; it does not update a long-lived environment. GitHub's servers cannot reach the LocalStack on your laptop (and a self-hosted runner on a public repository would be a security risk), so the laptop copy is for development and demos and can drift. The drift drill shows how drift would be caught.
- **The PR plan needs a baseline.** Because the emulator starts empty, the `plan` job first applies the base branch so the comment shows only this PR's changes.
- **Nothing here replaces access control on real cloud accounts.** A real target would use short-lived credentials (OIDC) for a least-privilege role, plus an approval step before apply.
- **Required checks and path filters conflict.** These workflows run only when infrastructure files change, so they are deliberately not required status checks. A required check that never runs would block every unrelated pull request.

## Clean up

```
tofu destroy
docker compose down
```
