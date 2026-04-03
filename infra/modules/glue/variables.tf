variable "job_name" {
  description = "Glue job name."
  type        = string
}

variable "role_arn" {
  description = "ARN of the Glue execution role."
  type        = string
}

variable "script_bucket" {
  description = "Bucket that will store Glue scripts and config assets."
  type        = string
}

variable "script_key" {
  description = "S3 key for the Glue script."
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

variable "query_key" {
  description = "S3 key for the SQL transformation file."
  type        = string
}

variable "bronze_bucket" {
  description = "Bronze bucket name."
  type        = string
}

variable "silver_bucket" {
  description = "Silver bucket name."
  type        = string
}

variable "common_tags" {
  description = "Tags applied to the Glue job."
  type        = map(string)
  default     = {}
}
