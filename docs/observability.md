# Monitoring and logging

## Metrics and health

The API exposes `/metrics` using Prometheus format. Kubernetes liveness and readiness probes use `/health/live` and `/health/ready`; readiness checks the database connection. `deploy/kubernetes/service-monitor.yaml` configures a Prometheus Operator ServiceMonitor and a stable `job` label. The Argo Rollouts AnalysisTemplate evaluates the inventory API request success rate while excluding health probes.

Install a pinned Prometheus/Grafana stack into `monitoring`:

```powershell
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update prometheus-community
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack `
  --namespace monitoring --create-namespace --version 69.3.1 --wait
kubectl apply -f deploy/kubernetes/service-monitor.yaml
```

The chart's Grafana dashboards and default cluster alerts provide the starting point. Add an application dashboard with request rate, non-2xx/5xx ratio, latency percentiles, process/container resource use, and PostgreSQL availability. Configure alert routing to a real on-call destination before production.

## Structured logs

The API writes one JSON request record to stdout with method, path, status, and latency. It intentionally excludes request bodies, credentials, and query values. Kubernetes retains container logs according to cluster policy; install a log collector and retention policy for centralized querying.

For a small single-cluster evaluation, the repository includes Loki and Alloy Helm values:

```powershell
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update grafana
helm upgrade --install loki grafana/loki --namespace monitoring `
  --version 6.24.0 --values deploy/observability/loki-values.yaml --wait
helm upgrade --install alloy grafana/alloy --namespace monitoring `
  --version 0.12.2 --values deploy/observability/alloy-values.yaml --wait
```

These settings are for a single-node evaluation, not a production log-retention design. Review chart compatibility and configure durable storage, retention, access control, and resource limits before handling production logs. Alloy collects Kubernetes pod logs and sends them to Loki; restrict its RBAC to required namespaces. The capstone uses stdout/stderr as the application logging contract so the collector can be changed without modifying application code.

Example LogQL after Alloy is configured:

```logql
{namespace="inventory", app_kubernetes_io_name="inventory-api"} | json | status_code >= 500
```

## Operational SLI starting points

- Availability: successful API requests divided by all API requests, excluding health probes.
- Latency: p95 request duration below the service objective agreed with users.
- Saturation: CPU, memory, connection pool, and PostgreSQL storage utilization.
- Canary gate: success-rate analysis must pass at each rollout checkpoint. Tune the query, minimum sample size, and alert thresholds against observed traffic before production.
