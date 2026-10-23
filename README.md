# HealthQueue Patient Scheduling API

The patient-facing appointment scheduling API for HealthQueue, a health-tech startup preparing to launch. It is a small Python service (standard library only), deployed to Kubernetes with Argo CD (GitOps).

> **Status: pre-launch reference implementation.** Appointment data is held in memory, there is no authentication, and no real patient data should be used. See [Known limitations](#known-limitations).

## API

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check. Returns `{"status":"ok","version":"1.0.0"}` |
| POST | `/appointments` | Book an appointment. Body: `patient_id`, `provider_id`, `slot` (ISO 8601 with timezone). Returns `201` with the appointment, `400` for invalid input, `409` if the provider is already booked at that slot |
| GET | `/appointments` | List appointments |
| GET | `/appointments/{id}` | Get one appointment, or `404` |

Any other path returns a 404 JSON error. Patients and providers are identified by opaque IDs only; the API stores no names or other personal details.

## Known limitations

- **In-memory storage.** Appointments are lost when a pod restarts. The Deployment runs 2 replicas and each keeps its own copy, so a booking made through one pod may not appear when a request reaches the other. A shared database is required before launch.
- **No authentication, authorization, or TLS.**
- **Not for real patient data.** Use synthetic IDs only.
- **Logging.** Each request writes one JSON line (method, path, status) to stderr. It deliberately omits client IPs and query strings.

## How it works

1. Code and manifests live in this one repo.
2. The image is built and pushed by hand to GitHub Container Registry (GHCR).
3. `argocd/application.yaml` tells Argo CD to watch the `k8s/` folder on `main`.
4. Every change to `k8s/` goes through a pull request. Argo CD applies it automatically. No `kubectl apply`, no manual Sync.

| Path | Purpose |
|---|---|
| `app/main.py` | The API |
| `app/Dockerfile` | Multi-stage build, non-root user, HEALTHCHECK |
| `k8s/deployment.yaml` | What runs: image tag, replicas, probes, resources, security |
| `k8s/service.yaml` | Stable internal address for the pods |
| `argocd/application.yaml` | What Argo CD watches (auto-sync, self-heal, prune) |

## CI pipeline

`.github/workflows/ci.yml` runs on every pull request and on every merge to `main`.

| Job | Runs on | What it does |
|---|---|---|
| `test` | Pull requests and `main` | Runs the unit tests |
| `build` | Pull requests and `main` | Builds the image, scans it for vulnerabilities, and smoke-tests it. Never pushes. |
| `publish` | Merges to `main` only | Pushes the image, rescans the pushed digest, generates an SBOM, signs the image, and attests provenance and the SBOM |

### Why `test` and `build` are separate jobs

**Why:**

- **Observability.** Each job reports its own status on the pull request, so you can see at a glance whether the code or the container failed without opening a log. Each job also records its own duration, which shows where pipeline time goes and gives real timing data for lead-time analysis.
- **Independent required checks.** Branch rules can require `test` and `build` individually, and a failure names the stage that broke.
- **Different needs.** `test` needs only Python. `build` needs Docker.
- **Ordering is explicit.** `build` declares `needs: test`, so a failing test stops the build.

**Trade-offs we accepted:**

- Each job starts a fresh runner and checks out the code again, which adds a little time to every pull request. We judged that small compared with the clarity it buys. The per-job durations in the Actions tab show the actual cost.
- Jobs don't share files. `publish` rebuilds the image rather than reusing the one `build` scanned, so it rescans the exact digest it signs. The scan in `build` is early feedback; the scan in `publish` is the one that gates signing.

`publish` is separate for a different reason: it is the only job with write permissions (packages, signing, attestations) and it never runs on pull requests.

## Prune policy trade-off

`argocd/application.yaml` sets `prune: true`. Pruning means Argo CD **deletes** a cluster resource when its file is removed from `k8s/`.

- **Benefit:** the cluster always matches Git exactly. Nothing is left behind as an orphan.
- **Risk:** deleting or renaming a manifest in a merged pull request deletes the live resource. For example, removing `k8s/service.yaml` removes the Service. Check any deleted or renamed files closely when reviewing a pull request.
- **Why it's acceptable here:** the app is two small resources, and Argo CD only prunes resources it created and tracks.
- **Default behavior:** automated sync does not prune unless you turn it on, as a safety measure. See the Argo CD docs on [Automatic Pruning](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/#automatic-pruning).

## Build and push an image

```
docker build -t ghcr.io/kayla-marcus/patient-scheduling-api:v1.0.0 app
docker login ghcr.io -u kayla-marcus      # paste your token at the prompt, in your own terminal only
docker push ghcr.io/kayla-marcus/patient-scheduling-api:v1.0.0
```

Then make the package public in GitHub (Packages > package settings > Change visibility).

## One-time Argo CD setup

```
kubectl apply -f argocd/application.yaml
```

## Verify the deployment

```
kubectl get application patient-scheduling-api -n argocd
kubectl get pods -n healthqueue
kubectl port-forward -n healthqueue svc/patient-scheduling-api 8080:80
curl.exe -i http://localhost:8080/health
```

In a second PowerShell window, book and list an appointment:

```
$body = @{ patient_id = "p-1001"; provider_id = "dr-42"; slot = "2026-11-02T15:00:00Z" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8080/appointments -ContentType "application/json" -Body $body
Invoke-RestMethod -Uri http://localhost:8080/appointments
```

Booking the same provider and slot again returns `409`. Because storage is per pod, a list request may not show the booking if it reaches the other replica (see [Known limitations](#known-limitations)).

## Change workflow (GitOps demo)

1. Edit `app/main.py` (for example, add a field to the appointment response) and bump `VERSION`, then build and push `v1.1.0`.
2. Create a branch, change only the image tag in `k8s/deployment.yaml`, open a pull request, and merge it.
3. Do not click Sync and do not run `kubectl apply`. Watch: `kubectl get pods -n healthqueue -w`
4. Prove it was automatic (Argo CD checks Git about every 3 minutes):

```
git pull
git log -1 --oneline
kubectl get application patient-scheduling-api -n argocd -o 'jsonpath={.status.sync.revision}'
kubectl get application patient-scheduling-api -n argocd -o 'jsonpath={.status.operationState.operation.initiatedBy}'
kubectl get deployment patient-scheduling-api -n healthqueue -o 'jsonpath={.spec.template.spec.containers[0].image}'
```

The revision should start with your merge commit ID, `initiatedBy` should show `{"automated":true}`, and the image should be the new tag.

## Optional self-heal demo

```
kubectl scale deployment patient-scheduling-api -n healthqueue --replicas=5
kubectl get pods -n healthqueue -w
```

Argo CD should return the Deployment to 2 replicas.
