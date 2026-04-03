variable "name_prefix" {
  description = "Bucket-safe prefix used to compose resource names."
  type        = string
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
}

variable "region" {
  description = "AWS region used in bucket naming."
  type        = string
}

variable "account_id" {
  description = "AWS account ID used to guarantee global bucket uniqueness."
  type        = string
}

variable "common_tags" {
  description = "Tags applied to every bucket."
  type        = map(string)
  default     = {}
}
