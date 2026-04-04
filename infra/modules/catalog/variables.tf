variable "database_name" {
  description = "Glue Catalog database name."
  type        = string
}

variable "data_lake_bucket_name" {
  description = "Shared data lake bucket name."
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
