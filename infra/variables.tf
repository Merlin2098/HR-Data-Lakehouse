variable "aws_region" {
  description = "AWS region where the phase-1 lakehouse resources will be created."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Logical project name used for tagging and naming conventions."
  type        = string
  default     = "hr-data-lakehouse"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "dev"
}

variable "name_prefix" {
  description = "Bucket-safe prefix used to compose resource names."
  type        = string
  default     = "hr-lakehouse"
}

variable "common_tags" {
  description = "Additional tags applied to every phase-1 resource."
  type        = map(string)
  default     = {}
}
