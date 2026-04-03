variable "database_name" {
  description = "Glue Catalog database name."
  type        = string
}

variable "silver_bucket_name" {
  description = "Silver bucket name."
  type        = string
}

variable "gold_bucket_name" {
  description = "Gold bucket name."
  type        = string
}

variable "year_projection_range" {
  description = "Projected year range for the gold table."
  type        = string
}

variable "common_tags" {
  description = "Tags applied to Glue Catalog resources."
  type        = map(string)
  default     = {}
}
