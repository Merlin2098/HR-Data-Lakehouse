output "job_name" {
  description = "Glue job name."
  value       = aws_glue_job.bronze_to_silver.name
}

output "script_location" {
  description = "Expected S3 location for the Glue script."
  value       = aws_glue_job.bronze_to_silver.command[0].script_location
}
