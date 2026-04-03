variable "workgroup_name" {
  description = "Athena workgroup name."
  type        = string
}

variable "athena_results_bucket" {
  description = "Athena results bucket name."
  type        = string
}

variable "kms_key_arn" {
  description = "KMS key ARN for Athena result encryption."
  type        = string
}

variable "common_tags" {
  description = "Tags applied to Athena resources."
  type        = map(string)
  default     = {}
}
