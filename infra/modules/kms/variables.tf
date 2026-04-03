variable "name_prefix" {
  description = "Prefix used to compose KMS resource names."
  type        = string
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
}

variable "common_tags" {
  description = "Tags applied to KMS resources."
  type        = map(string)
  default     = {}
}
