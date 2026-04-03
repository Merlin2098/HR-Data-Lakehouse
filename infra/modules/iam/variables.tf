variable "name_prefix" {
  description = "Prefix used to compose IAM resource names."
  type        = string
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
}

variable "bronze_bucket_arn" {
  description = "ARN of the bronze bucket."
  type        = string
}

variable "silver_bucket_arn" {
  description = "ARN of the silver bucket."
  type        = string
}

variable "scripts_bucket_arn" {
  description = "ARN of the scripts bucket."
  type        = string
}

variable "common_tags" {
  description = "Tags applied to IAM resources that support them."
  type        = map(string)
  default     = {}
}
