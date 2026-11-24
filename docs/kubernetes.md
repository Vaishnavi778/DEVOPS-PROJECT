# Kubernetes deployment runbook

## Cluster prerequisites

- A Kubernetes cluster with a default `ReadWriteOnce` StorageClass.
- `kubectl`, Helm, and the Argo Rollouts controller plus its `kubectl-argo-rollouts` plugin.
- Prometheus Operator and the `kube-prometheus-stack` release in namespace `monitoring` before canary analysis is enabled.
- A ConfigMap named `inventory-api-config` containing `DB_HOST`, `DB_PORT`, and `DB_NAME`, and a Secret named `inventory-db` containing `DB_USER`, `DB_PASSWORD`, and a random `API_KEY` of at least 32 printable ASCII characters. `configmap-local.yaml` is only for local kind PostgreSQL; set the production ConfigMap to the managed database endpoint.
- An image registry the cluster can pull from. Make the GHCR package public for a public capstone repo, or provision an `imagePullSecret` in namespace `inventory` with read-only package credentials.
- Create the `inventory-db` Secret before starting the local PostgreSQL StatefulSet. Use unique credentials for each environment.

The manifests include a single-node PostgreSQL StatefulSet for local demonstrations. Use a managed database with encryption, high availability, and automated backups for production.

## kind quick path

```powershell
kind create cluster --name inventory --config deploy/kind/kind-config.yaml
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update argo
helm upgrade --install argo-rollouts argo/argo-rollouts --namespace argo-rollouts --create-namespace --wait
```

Install the matching Argo Rollouts kubectl plugin from the [official release instructions](https://argoproj.github.io/rollouts/installation/#kubectl-plugin-installation). Build and load the image tag referenced by `rollout.yaml` and `migration-job.yaml`:

```powershell
docker build -t ghcr.io/vaishnavi778/devops-project:latest .
kind load docker-image ghcr.io/vaishnavi778/devops-project:latest --name inventory
```

The manifests use `imagePullPolicy: IfNotPresent` to allow a locally loaded kind image.

After creating the namespace Secret using the README instructions:

```powershell
kubectl apply -f deploy/kubernetes/configmap-local.yaml
kubectl apply -f deploy/kubernetes/database.yaml
kubectl rollout status statefulset/inventory-db -n inventory --timeout=180s
kubectl apply -f deploy/kubernetes/migration-job.yaml
kubectl wait --for=condition=complete job/inventory-migrate -n inventory --timeout=240s
kubectl apply -f deploy/kubernetes/analysis-template.yaml
kubectl apply -f deploy/kubernetes/rollout.yaml
kubectl argo rollouts status inventory-api -n inventory --timeout 10m
kubectl get pods,svc,rollouts -n inventory
```

If running the ServiceMonitor manifest, first install the Prometheus Operator CRDs. The `AnalysisTemplate` expects Prometheus at `kube-prometheus-stack-prometheus.monitoring.svc:9090`; update the address if the Helm release differs.

Verify the service and API:

```powershell
Invoke-RestMethod http://localhost:8080/health/ready
Invoke-RestMethod http://localhost:8080/metrics
```

## Canary behavior

Argo Rollouts replaces the standard Kubernetes Deployment. It gradually shifts replica capacity at 20%, then 50%, then 100%, with pauses and Prometheus analysis between steps. The analysis checks the aggregate non-5xx HTTP success rate and aborts the rollout on a failed measurement. In a low-traffic evaluation, generate repeatable requests during the analysis windows; otherwise the metric may not represent a meaningful production SLI.

Because this reference configuration uses replica-based canary weighting, distribution is approximate and depends on the number of replicas and request volume. For precise per-request traffic weights, add an ingress/service-mesh traffic router and configure Argo Rollouts traffic routing before production.

Inspect, promote, or abort a rollout:

```powershell
kubectl argo rollouts get rollout inventory-api -n inventory
kubectl argo rollouts promote inventory-api -n inventory
kubectl argo rollouts abort inventory-api -n inventory
```

## GitHub deployment workflow

The manual workflow requires:

1. A GitHub Environment named `production` with required reviewers.
2. The `KUBE_CONFIG` environment secret containing base64-encoded kubeconfig for the private/approved cluster.
3. A protected Linux self-hosted runner labelled `inventory-deploy` inside the private cluster network, with `kubectl`, Helm, and `curl` installed.
4. The managed database connection ConfigMap and Secret (database credentials and API key), monitoring stack, Argo analysis prerequisites, and package pull access provisioned out of band. Do not deploy the local PostgreSQL StatefulSet to production.
5. A successful CI run that published the desired 40-character commit SHA to GHCR.
6. Dispatch `.github/workflows/deploy.yml` with that SHA. The workflow runs the migration Job before updating the Rollout and waits for rollout health.

The kubeconfig should use a short-lived, least-privilege identity scoped to the target namespace. Do not use a cluster-admin kubeconfig for routine delivery.
