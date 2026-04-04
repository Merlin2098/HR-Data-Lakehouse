variable "account_id" {
  description = "AWS account ID that owns the budget."
  type        = string
}

variable "name_prefix" {
  description = "Prefix used to compose the budget name."
  type        = string
}

variable "project_name" {
  description = "Logical project name used for naming and documentation."
  type        = string
}

variable "environment" {
  description = "Environment associated with the budget."
  type        = string
}

variable "monthly_budget_limit_usd" {
  description = "Monthly spend threshold in USD for the environment budget."
  type        = number
}

variable "sns_topic_arn" {
  description = "SNS topic ARN that receives budget threshold alerts."
  type        = string
}

variable "budget_name_override" {
  description = "Optional override for the generated budget name."
  type        = string
  default     = null
}

variable "common_tags" {
  description = "Tags propagated from the root module for documentation symmetry."
  type        = map(string)
  default     = {}
}
