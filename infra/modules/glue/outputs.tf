output "landing_to_bronze_job_name" {
  description = "Glue job name for landing-to-bronze promotion."
  value       = aws_glue_job.landing_to_bronze.name
}

output "bronze_to_silver_job_name" {
  description = "Glue job name for bronze-to-silver transformation."
  value       = aws_glue_job.bronze_to_silver.name
}

output "silver_to_gold_job_name" {
  description = "Glue job name for silver-to-gold transformation."
  value       = aws_glue_job.silver_to_gold.name
}

output "job_names" {
  description = "Ordered list of Glue job names."
  value = [
    aws_glue_job.landing_to_bronze.name,
    aws_glue_job.bronze_to_silver.name,
    aws_glue_job.silver_to_gold.name,
  ]
}
