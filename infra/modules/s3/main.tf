locals {
  bucket_names = {
    bronze  = lower("${var.name_prefix}-${var.environment}-${var.account_id}-${var.region}-bronze")
    silver  = lower("${var.name_prefix}-${var.environment}-${var.account_id}-${var.region}-silver")
    scripts = lower("${var.name_prefix}-${var.environment}-${var.account_id}-${var.region}-scripts")
  }
}

resource "aws_s3_bucket" "bronze" {
  bucket = local.bucket_names.bronze
  tags   = merge(var.common_tags, { Layer = "bronze" })
}

resource "aws_s3_bucket" "silver" {
  bucket = local.bucket_names.silver
  tags   = merge(var.common_tags, { Layer = "silver" })
}

resource "aws_s3_bucket" "scripts" {
  bucket = local.bucket_names.scripts
  tags   = merge(var.common_tags, { Layer = "scripts" })
}
