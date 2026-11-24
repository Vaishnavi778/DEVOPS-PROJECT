output "cluster_name" {
  description = "EKS cluster name."
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "Private EKS API endpoint. Access requires network connectivity to the VPC."
  value       = module.eks.cluster_endpoint
}

output "vpc_id" {
  description = "VPC hosting the EKS cluster."
  value       = module.vpc.vpc_id
}
