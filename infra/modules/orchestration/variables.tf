variable "state_machine_name" {
  description = "Step Functions state machine name."
  type        = string
}

variable "event_rule_name" {
  description = "EventBridge rule name for S3 object created events."
  type        = string
}

variable "event_target_id" {
  description = "EventBridge target identifier for the Step Functions trigger."
  type        = string
}

variable "step_functions_role_arn" {
  description = "Execution role ARN for Step Functions."
  type        = string
}

variable "landing_to_bronze_job_name" {
  description = "Landing-to-bronze Glue job name."
  type        = string
}

variable "bronze_to_silver_job_name" {
  description = "Bronze-to-silver Glue job name."
  type        = string
}

variable "silver_to_gold_job_name" {
  description = "Silver-to-gold Glue job name."
  type        = string
}

variable "athena_workgroup_name" {
  description = "Athena workgroup name."
  type        = string
}

variable "athena_database_name" {
  description = "Athena database name."
  type        = string
}

variable "gold_table_name" {
  description = "Gold table name used for validation."
  type        = string
}

variable "bronze_bucket_name" {
  description = "Bronze bucket name."
  type        = string
}

variable "landing_prefix" {
  description = "Landing key prefix monitored for new objects."
  type        = string
}

variable "landing_suffix" {
  description = "Landing file suffix monitored for new objects."
  type        = string
}

variable "step_functions_log_group_name" {
  description = "CloudWatch log group name for the state machine."
  type        = string
}

variable "athena_results_bucket_name" {
  description = "Athena results bucket name."
  type        = string
}

variable "kms_key_arn" {
  description = "KMS key ARN for state machine logs."
  type        = string
}

variable "common_tags" {
  description = "Tags applied to orchestration resources."
  type        = map(string)
  default     = {}
}
