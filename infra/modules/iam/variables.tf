variable "name_prefix" {
  description = "Prefix used to compose IAM resource names."
  type        = string
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
}

variable "region" {
  description = "AWS region where the resources are deployed."
  type        = string
}

variable "account_id" {
  description = "AWS account ID used for scoped IAM permissions."
  type        = string
}

variable "data_lake_bucket_arn" {
  description = "ARN of the shared data lake bucket."
  type        = string
}

variable "scripts_bucket_arn" {
  description = "ARN of the scripts bucket."
  type        = string
}

variable "athena_results_bucket_arn" {
  description = "ARN of the Athena results bucket."
  type        = string
}

variable "kms_key_arn" {
  description = "KMS key ARN used across the lakehouse resources."
  type        = string
}

variable "athena_workgroup_name" {
  description = "Athena workgroup name accessed by Step Functions."
  type        = string
}

variable "common_tags" {
  description = "Tags applied to IAM resources that support them."
  type        = map(string)
  default     = {}
}
