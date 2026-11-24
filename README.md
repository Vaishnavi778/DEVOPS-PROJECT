# Inventory Platform: end-to-end DevOps capstone

A reproducible delivery platform for a small inventory-management API. It includes a tested FastAPI service, PostgreSQL, container builds, GitHub Actions CI, Kubernetes deployment with an Argo Rollouts canary, Terraform for an optional AWS EKS environment, and operational/security guidance.

## Architecture

```text
Git commit / pull request
        |
        v
GitHub Actions: lint -> tests -> dependency/security checks -> container build
        | (push to main)
        v
GHCR image tagged with commit SHA
        | (manually approved deployment workflow)
        v
Kubernetes -> migration Job -> Argo Rollouts canary -> inventory API -> PostgreSQL
                             |                           |
                             +---- Prometheus metrics ---+---- structured stdout logs
                                      |                            |
                                  Grafana                  Grafana Alloy -> Loki
```

The local path uses Docker Compose or kind. `infra/terraform/` is an optional AWS EKS starting point; applying it creates billable AWS resources. Production deployments should use a managed database, TLS ingress, restricted cluster access, external secret management, backups, and a configured GitHub `production` environment.

## Requirements

- Python 3.12+
- Docker Desktop (or Docker Engine) and Docker Compose
- For Kubernetes: `kubectl`, `kind`, and Helm
- For optional AWS: Terraform 1.6+, AWS CLI credentials, and a reviewed cost estimate

## Run locally with Compose

From the repository root:

```powershell
$env:POSTGRES_USER = "inventory"
$env:POSTGRES_PASSWORD = Read-Host "Choose a local database password"
$env:API_KEY = [guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")
docker compose up --build
```

Compose starts PostgreSQL and the API; the API container runs the Alembic migration before serving requests.

```powershell
Invoke-RestMethod http://localhost:8000/health/live
Invoke-RestMethod http://localhost:8000/health/ready
$headers = @{ "X-API-Key" = $env:API_KEY }
Invoke-RestMethod -Headers $headers http://localhost:8000/items
```

Create an item:

```powershell
$item = @{ sku = "CHAIR-001"; name = "Desk chair"; quantity = 12; unit_price = "89.99" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8000/items -Headers $headers -ContentType "application/json" -Body $item
```

Load the sample records from [samples/inventory-items.json](samples/inventory-items.json):

```powershell
Get-Content .\samples\inventory-items.json -Raw | ConvertFrom-Json | ForEach-Object {
  Invoke-RestMethod -Method Post -Uri http://localhost:8000/items `
    -Headers $headers -ContentType "application/json" -Body ($_ | ConvertTo-Json)
}
```

OpenAPI docs: <http://localhost:8000/docs>. Stop the services with `docker compose down`; add `-v` only when intentionally deleting local database data.

## Test and lint

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
```

Tests use an isolated in-memory SQLite database and do not require Docker or PostgreSQL.

## Local Kubernetes (kind)

1. Create a cluster: `kind create cluster --name inventory --config deploy/kind/kind-config.yaml`.
2. Install Argo Rollouts and Prometheus/Grafana (see [Kubernetes deployment](docs/kubernetes.md) and [observability setup](docs/observability.md)); canary analysis requires Prometheus.
3. Build and load the local image:

   ```powershell
   docker build -t ghcr.io/vaishnavi778/devops-project:latest .
   kind load docker-image ghcr.io/vaishnavi778/devops-project:latest --name inventory
   ```

4. Create the namespace and database credential Secret (choose your own local password):

   ```powershell
   kubectl apply -f deploy/kubernetes/namespace.yaml
   $env:LOCAL_DB_PASSWORD = Read-Host "Choose a local database password"
   $env:LOCAL_API_KEY = [guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")
   kubectl create secret generic inventory-db -n inventory `
     --from-literal=POSTGRES_USER=inventory `
     --from-literal="POSTGRES_PASSWORD=$($env:LOCAL_DB_PASSWORD)" `
     --from-literal=DB_USER=inventory `
     --from-literal="DB_PASSWORD=$($env:LOCAL_DB_PASSWORD)" `
     --from-literal="API_KEY=$($env:LOCAL_API_KEY)"
   ```

   Apply local database connection settings:

   ```powershell
   kubectl apply -f deploy/kubernetes/configmap-local.yaml
   ```

5. Apply PostgreSQL and wait for readiness; apply the migration Job and wait for completion; then apply the API resources. Exact commands and rollout verification are in [docs/kubernetes.md](docs/kubernetes.md).
6. The kind host port is `8080`; API checks use `http://localhost:8080`.

Business API requests require an `X-API-Key` header. The key must be at least 32 printable ASCII characters and is provisioned only in the Kubernetes Secret. The Kubernetes manifests are deliberately not populated with usable credentials. Never commit Secrets, kubeconfigs, cloud credentials, or production connection strings.

## CI/CD and release flow

- Pull requests and pushes run formatting/lint, unit/API tests, dependency audit, and IaC/container configuration checks.
- A push to `main` builds and publishes a SHA-tagged container to GitHub Container Registry (GHCR).
- `.github/workflows/deploy.yml` is a manually dispatched, approval-gated production deployment. Configure a GitHub Environment named `production`, required reviewers, and its `KUBE_CONFIG` secret as base64-encoded kubeconfig. A protected self-hosted runner in the private cluster network is required. The cluster must already have a managed database connection ConfigMap/Secret, Argo Rollouts, and monitoring prerequisites.
- Canary progression is controlled by Argo Rollouts and Prometheus analysis; a failed health analysis aborts the rollout. See [docs/kubernetes.md](docs/kubernetes.md).

## Infrastructure, monitoring, security, and recovery

- Optional AWS EKS Terraform: [infra/terraform/README.md](infra/terraform/README.md). Review the plan and configure private network access before apply.
- Sample inventory records: [samples/inventory-items.json](samples/inventory-items.json).
- Monitoring/logging installation, dashboards, alerts, and example queries: [docs/observability.md](docs/observability.md).
- Security controls and operational recovery runbook: [docs/operations.md](docs/operations.md).
- Full capstone report (ready to export/upload to ZOSIMA): [docs/capstone-report.md](docs/capstone-report.md).

## Repository layout

```text
src/inventory_api/        API, persistence and validation
tests/                    focused API and health checks
alembic/                  versioned PostgreSQL schema migrations
deploy/kubernetes/        namespace, database, migration Job and canary rollout
deploy/kind/              local kind port mapping
infra/terraform/          optional AWS VPC and EKS
.github/workflows/        CI, image publication and approved deployment
docs/                     architecture, operations and capstone report
```

## Important limitations

This capstone is a reproducible reference implementation, not a claim that an AWS cluster has been provisioned or a public production release has been executed. Faculty evaluation should use the CI run, local API tests, kind rollout, and monitoring evidence produced by following the runbooks. Production readiness still depends on environment-specific access control, TLS, managed data services, backup retention, incident ownership, and cost/security review.
