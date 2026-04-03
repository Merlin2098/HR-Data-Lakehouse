variable "scripts_bucket_name" {
  description = "Bucket that stores scripts, SQL, and config assets."
  type        = string
}

variable "common_tags" {
  description = "Tags applied to uploaded S3 objects when supported."
  type        = map(string)
  default     = {}
}
