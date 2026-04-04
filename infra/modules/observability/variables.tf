variable "kms_key_arn" {
  description = "KMS key ARN used for SNS encryption."
  type        = string
}

variable "account_id" {
  description = "AWS account ID that owns the SNS topic."
  type        = string
}

variable "glue_job_names" {
  description = "List of Glue job names to monitor."
  type        = list(string)
}

variable "state_machine_name" {
  description = "State machine name to monitor."
  type        = string
}

variable "state_machine_arn" {
  description = "State machine ARN to monitor."
  type        = string
}

variable "alert_email_endpoints" {
  description = "Email recipients subscribed to the shared alerts SNS topic."
  type        = list(string)
  default     = []
}

variable "common_tags" {
  description = "Tags applied to observability resources."
  type        = map(string)
  default     = {}
}
