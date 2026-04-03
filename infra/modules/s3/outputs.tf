output "bronze_bucket_name" {
  description = "Bronze bucket name."
  value       = aws_s3_bucket.bronze.bucket
}

output "silver_bucket_name" {
  description = "Silver bucket name."
  value       = aws_s3_bucket.silver.bucket
}

output "scripts_bucket_name" {
  description = "Scripts bucket name."
  value       = aws_s3_bucket.scripts.bucket
}

output "bronze_bucket_arn" {
  description = "Bronze bucket ARN."
  value       = aws_s3_bucket.bronze.arn
}

output "silver_bucket_arn" {
  description = "Silver bucket ARN."
  value       = aws_s3_bucket.silver.arn
}

output "scripts_bucket_arn" {
  description = "Scripts bucket ARN."
  value       = aws_s3_bucket.scripts.arn
}
