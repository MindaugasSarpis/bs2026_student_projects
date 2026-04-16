variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "eu-west-1"
}

variable "environment" {
  description = "Deployment environment (staging | production)"
  type        = string
  default     = "staging"
}

variable "app_name" {
  description = "Application name prefix"
  type        = string
  default     = "repops"
}

variable "ec2_instance_type" {
  description = "EC2 instance type — t3.medium recommended (Playwright + Elasticsearch + all services)"
  type        = string
  default     = "t3.medium"
}

variable "ec2_key_pair" {
  description = "Name of an existing EC2 Key Pair for SSH access"
  type        = string
}

variable "allowed_ssh_cidr" {
  description = "CIDR allowed to SSH into the instance — restrict to your IP for security"
  type        = string
  default     = "0.0.0.0/0"
}

variable "s3_evidence_bucket" {
  description = "S3 bucket name for evidence storage (must be globally unique)"
  type        = string
}
