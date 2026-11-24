# Optional AWS EKS infrastructure

This Terraform configuration provisions an AWS VPC, NAT gateway, private EKS control-plane endpoint, managed node group, and EKS control-plane audit logs. It is an optional cloud deployment path; the local kind workflow does not require AWS.

## Before applying

- Review AWS pricing for EKS, EC2, NAT Gateway, and CloudWatch Logs in your region.
- Use an AWS identity with least-privilege permissions and MFA. Do not put credentials in `.tf` files or `terraform.tfvars`.
- The EKS endpoint is private-only. Provision approved VPN, Direct Connect, or a controlled in-VPC runner before attempting `kubectl` access.
- Configure remote state with encryption, versioning, and locking before team use. The example deliberately does not create or configure a backend.
- Confirm the selected EKS/Kubernetes version is supported in the chosen region.

## Plan and provision

```powershell
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform fmt -check
terraform -chdir=infra/terraform validate
terraform -chdir=infra/terraform plan
```

Only after reviewing the plan and cost/security implications:

```powershell
terraform -chdir=infra/terraform apply
```

Destroy the environment after evaluation if it is no longer needed:

```powershell
terraform -chdir=infra/terraform destroy
```

State files and plans may contain sensitive infrastructure details and are excluded from Git.
