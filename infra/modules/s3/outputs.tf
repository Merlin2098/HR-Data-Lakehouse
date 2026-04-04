output "data_lake_bucket_name" {
  description = "Shared data lake bucket name."
  value       = aws_s3_bucket.data_lake.bucket
}

output "scripts_bucket_name" {
  description = "Scripts bucket name."
  value       = aws_s3_bucket.scripts.bucket
}

output "athena_results_bucket_name" {
  description = "Athena results bucket name."
  value       = aws_s3_bucket.athena_results.bucket
}

output "data_lake_bucket_arn" {
  description = "Shared data lake bucket ARN."
  value       = aws_s3_bucket.data_lake.arn
}

output "scripts_bucket_arn" {
  description = "Scripts bucket ARN."
  value       = aws_s3_bucket.scripts.arn
}

output "athena_results_bucket_arn" {
  description = "Athena results bucket ARN."
  value       = aws_s3_bucket.athena_results.arn
}
