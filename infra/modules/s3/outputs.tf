output "bronze_bucket_name" {
  description = "Bronze bucket name."
  value       = aws_s3_bucket.bronze.bucket
}

output "silver_bucket_name" {
  description = "Silver bucket name."
  value       = aws_s3_bucket.silver.bucket
}

output "gold_bucket_name" {
  description = "Gold bucket name."
  value       = aws_s3_bucket.gold.bucket
}

output "scripts_bucket_name" {
  description = "Scripts bucket name."
  value       = aws_s3_bucket.scripts.bucket
}

output "athena_results_bucket_name" {
  description = "Athena results bucket name."
  value       = aws_s3_bucket.athena_results.bucket
}

output "bronze_bucket_arn" {
  description = "Bronze bucket ARN."
  value       = aws_s3_bucket.bronze.arn
}

output "silver_bucket_arn" {
  description = "Silver bucket ARN."
  value       = aws_s3_bucket.silver.arn
}

output "gold_bucket_arn" {
  description = "Gold bucket ARN."
  value       = aws_s3_bucket.gold.arn
}

output "scripts_bucket_arn" {
  description = "Scripts bucket ARN."
  value       = aws_s3_bucket.scripts.arn
}

output "athena_results_bucket_arn" {
  description = "Athena results bucket ARN."
  value       = aws_s3_bucket.athena_results.arn
}
