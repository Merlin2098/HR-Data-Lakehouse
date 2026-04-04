variable "environment" {
  description = "Deployment environment name."
  type        = string
}

variable "landing_to_bronze_job_name" {
  description = "Glue Python Shell job name for landing to bronze promotion."
  type        = string
}

variable "bronze_to_silver_job_name" {
  description = "Glue ETL job name for bronze to silver."
  type        = string
}

variable "silver_to_gold_job_name" {
  description = "Glue ETL job name for silver to gold."
  type        = string
}

variable "role_arn" {
  description = "ARN of the Glue execution role."
  type        = string
}

variable "script_bucket" {
  description = "Bucket that stores Glue scripts and config assets."
  type        = string
}

variable "data_lake_bucket" {
  description = "Shared data lake bucket name."
  type        = string
}

variable "config_key" {
  description = "S3 key for the pipeline configuration file."
  type        = string
}

variable "contract_key" {
  description = "S3 key for the data contract file."
  type        = string
}

variable "landing_script_key" {
  description = "S3 key for the landing-to-bronze script."
  type        = string
}

variable "bronze_to_silver_script_key" {
  description = "S3 key for the bronze-to-silver script."
  type        = string
}

variable "silver_to_gold_script_key" {
  description = "S3 key for the silver-to-gold script."
  type        = string
}

variable "bronze_to_silver_query_key" {
  description = "S3 key for the bronze-to-silver SQL query."
  type        = string
}

variable "silver_to_gold_query_key" {
  description = "S3 key for the silver-to-gold SQL query."
  type        = string
}

variable "landing_log_group_name" {
  description = "CloudWatch log group name for the landing job."
  type        = string
}

variable "bronze_to_silver_log_group_name" {
  description = "CloudWatch log group name for the bronze-to-silver job."
  type        = string
}

variable "silver_to_gold_log_group_name" {
  description = "CloudWatch log group name for the silver-to-gold job."
  type        = string
}

variable "kms_key_arn" {
  description = "KMS key ARN used for job log groups."
  type        = string
}

variable "common_tags" {
  description = "Tags applied to the Glue jobs and log groups."
  type        = map(string)
  default     = {}
}
