locals {
  bucket_names = {
    bronze         = lower("${var.name_prefix}-${var.environment}-${var.account_id}-${var.region}-bronze")
    silver         = lower("${var.name_prefix}-${var.environment}-${var.account_id}-${var.region}-silver")
    gold           = lower("${var.name_prefix}-${var.environment}-${var.account_id}-${var.region}-gold")
    scripts        = lower("${var.name_prefix}-${var.environment}-${var.account_id}-${var.region}-scripts")
    athena_results = lower("${var.name_prefix}-${var.environment}-${var.account_id}-${var.region}-athena-results")
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

resource "aws_s3_bucket" "gold" {
  bucket = local.bucket_names.gold
  tags   = merge(var.common_tags, { Layer = "gold" })
}

resource "aws_s3_bucket" "scripts" {
  bucket = local.bucket_names.scripts
  tags   = merge(var.common_tags, { Layer = "scripts" })
}

resource "aws_s3_bucket" "athena_results" {
  bucket = local.bucket_names.athena_results
  tags   = merge(var.common_tags, { Layer = "athena-results" })
}

resource "aws_s3_bucket_versioning" "buckets" {
  for_each = {
    bronze         = aws_s3_bucket.bronze.id
    silver         = aws_s3_bucket.silver.id
    gold           = aws_s3_bucket.gold.id
    scripts        = aws_s3_bucket.scripts.id
    athena_results = aws_s3_bucket.athena_results.id
  }

  bucket = each.value

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "buckets" {
  for_each = {
    bronze         = aws_s3_bucket.bronze.id
    silver         = aws_s3_bucket.silver.id
    gold           = aws_s3_bucket.gold.id
    scripts        = aws_s3_bucket.scripts.id
    athena_results = aws_s3_bucket.athena_results.id
  }

  bucket                  = each.value
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "buckets" {
  for_each = {
    bronze         = aws_s3_bucket.bronze.id
    silver         = aws_s3_bucket.silver.id
    gold           = aws_s3_bucket.gold.id
    scripts        = aws_s3_bucket.scripts.id
    athena_results = aws_s3_bucket.athena_results.id
  }

  bucket = each.value

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.kms_key_arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id

  rule {
    id     = "expire-athena-results"
    status = "Enabled"

    expiration {
      days = 30
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}
