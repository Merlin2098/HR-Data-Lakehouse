output "bronze_bucket_name" {
  description = "Phase-1 bronze bucket name."
  value       = module.s3.bronze_bucket_name
}

output "silver_bucket_name" {
  description = "Phase-1 silver bucket name."
  value       = module.s3.silver_bucket_name
}

output "scripts_bucket_name" {
  description = "Phase-1 scripts bucket name."
  value       = module.s3.scripts_bucket_name
}

output "glue_role_arn" {
  description = "Glue execution role ARN."
  value       = module.iam.glue_role_arn
}

output "glue_job_name" {
  description = "Name of the bronze-to-silver Glue job."
  value       = module.glue.job_name
}

output "glue_script_location" {
  description = "Expected S3 location of the bronze-to-silver Glue script."
  value       = module.glue.script_location
}
