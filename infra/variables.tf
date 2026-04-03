variable "aws_region" {
  description = "AWS region where the lakehouse resources will be created."
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

variable "schedule_expression" {
  description = "EventBridge Scheduler cron expression for the daily pipeline."
  type        = string
  default     = "cron(0 11 * * ? *)"
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

variable "dataset_source_filename" {
  description = "Expected filename for the daily HR attrition dataset."
  type        = string
  default     = "HR-Employee-Attrition.csv"
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
