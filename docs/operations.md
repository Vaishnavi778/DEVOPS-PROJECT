# Security and recovery runbook

## Security controls included

- Pull-request CI runs unit/API tests, Ruff, dependency audit, and Trivy filesystem checks for dependencies, IaC/container configuration, and secrets.
- Inventory CRUD endpoints require a high-entropy API key in `X-API-Key`; comparisons use constant-time comparison. Liveness remains unauthenticated for kubelet probes, while readiness fails if the key is missing or too short.
- Container uses a slim Python base image and runs as an unprivileged user. Kubernetes application and migration containers disable privilege escalation, drop Linux capabilities, use a read-only root filesystem, and set RuntimeDefault seccomp.
- API input models enforce SKU format, non-negative quantity/price, and bounded request fields. Database uniqueness is enforced by PostgreSQL.
- GitHub Actions use read-only permissions by default; image publication has the narrow package-write permission. Deployment is manual and gated by a protected GitHub Environment.
- Secrets are injected at runtime and excluded from source control. The local Compose password is explicitly for local development only.

Review action versions, base images, container scan findings, and Terraform plans regularly. Protect the default branch and require passing CI before merge.

## Recovery

1. **Canary failure:** use `kubectl argo rollouts get rollout inventory-api -n inventory` to inspect AnalysisRuns and pod health. Argo aborts a failed analysis and retains the prior ReplicaSet; verify `/health/ready`, then roll back to the last known-good image by redeploying its SHA.
2. **API regression:** dispatch the approved deployment workflow with the previous successful image SHA. Do not edit the live ReplicaSet manually as the permanent fix.
3. **Database outage:** inspect `kubectl describe pod` and logs for `inventory-db`; verify PVC and secret references. Restore production data from the managed database's latest verified backup according to the provider-specific runbook.
4. **Schema rollback:** take/verify a database backup before destructive schema changes. The sample migration has a downgrade for initial setup only; production schema changes should use backward-compatible expand/migrate/contract steps and a reviewed recovery plan.
5. **AWS resources:** preserve Terraform state and use a reviewed plan for repair. Never delete or recreate the state file to resolve drift.

The included StatefulSet PVC is not a backup strategy. Configure encrypted automated snapshots, retention, restore drills, and ownership objectives for any production database.
