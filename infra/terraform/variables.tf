variable "aws_region" {
  description = "AWS region for the EKS cluster and VPC."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment label applied to provisioned resources."
  type        = string
  default     = "capstone"
}

variable "cluster_name" {
  description = "Name of the EKS cluster."
  type        = string
  default     = "inventory-capstone"
}

variable "cluster_version" {
  description = "Kubernetes version supported by the selected EKS region."
  type        = string
  default     = "1.36"
}

variable "vpc_cidr" {
  description = "CIDR block for the cluster VPC."
  type        = string
  default     = "10.40.0.0/16"
}
