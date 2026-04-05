variable "aws_region" {
  description = "AWS region where the lakehouse resources will be created."
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "Optional AWS shared credentials profile for local Terraform execution."
  type        = string
  default     = null
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

variable "athena_database_name" {
  description = "Glue Catalog database and Athena database name."
  type        = string
  default     = "hr_attrition_lakehouse"
}

variable "athena_workgroup_name" {
  description = "Dedicated Athena workgroup for the project."
  type        = string
  default     = "hr-attrition-analytics"
}

variable "monthly_budget_limit_usd" {
  description = "Monthly AWS Budget threshold for the selected environment."
  type        = number
}

variable "budget_name_override" {
  description = "Optional override for the AWS Budget name."
  type        = string
  default     = null
}

variable "alert_email_endpoints" {
  description = "Email endpoints subscribed to the shared SNS alerts topic."
  type        = list(string)
  default     = []
}

variable "scripts_bucket_reader_arns" {
  description = "Additional IAM principal ARNs granted read-only inspection access to the scripts bucket."
  type        = list(string)
  default     = []
}

variable "quicksight_principal_arns" {
  description = "QuickSight IAM principal ARNs granted access to the curated gold dataset and Athena query-results prefix."
  type        = list(string)
  default     = []
}

variable "landing_prefix" {
  description = "S3 prefix monitored for landing file arrivals."
  type        = string
  default     = "bronze/hr_attrition/landing/"
}

variable "landing_suffix" {
  description = "Filename suffix accepted for landing file arrivals."
  type        = string
  default     = ".csv"
}

variable "year_projection_range" {
  description = "Year range exposed through Athena partition projection."
  type        = string
  default     = "2024,2035"
}

variable "common_tags" {
  description = "Additional tags applied to every lakehouse resource."
  type        = map(string)
  default     = {}
}
