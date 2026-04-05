locals {
  bucket_names = {
    data_lake      = lower("${var.name_prefix}-${var.environment}-${var.account_id}-${var.region}-data-lake")
    scripts        = lower("${var.name_prefix}-${var.environment}-${var.account_id}-${var.region}-scripts")
    athena_results = lower("${var.name_prefix}-${var.environment}-${var.account_id}-${var.region}-athena-results")
  }

  medallion_prefix_placeholders = {
    bronze_landing = "bronze/hr_attrition/landing/.keep"
    silver_dataset = "silver/hr_employees/.keep"
    gold_dataset   = "gold/hr_attrition/.keep"
    bi_snapshot    = "bi/hr_attrition_snapshot/.keep"
  }
}

data "aws_iam_policy_document" "scripts_bucket_readers" {
  statement {
    sid    = "AllowScriptsBucketInspection"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = var.scripts_bucket_reader_arns
    }

    actions = [
      "s3:ListBucket",
      "s3:GetBucketLocation",
    ]
    resources = [aws_s3_bucket.scripts.arn]
  }

  statement {
    sid    = "AllowScriptsObjectReads"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = var.scripts_bucket_reader_arns
    }

    actions = [
      "s3:GetObject",
      "s3:GetObjectVersion",
    ]
    resources = ["${aws_s3_bucket.scripts.arn}/*"]
  }
}

resource "aws_s3_bucket" "data_lake" {
  bucket = local.bucket_names.data_lake
  tags   = merge(var.common_tags, { Layer = "data-lake" })
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
    data_lake      = aws_s3_bucket.data_lake.id
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
    data_lake      = aws_s3_bucket.data_lake.id
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
    data_lake      = aws_s3_bucket.data_lake.id
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

resource "aws_s3_bucket_server_side_encryption_configuration" "scripts" {
  bucket = aws_s3_bucket.scripts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_notification" "data_lake_eventbridge" {
  bucket      = aws_s3_bucket.data_lake.id
  eventbridge = true
}

resource "aws_s3_object" "data_lake_prefix_placeholders" {
  for_each = local.medallion_prefix_placeholders

  bucket  = aws_s3_bucket.data_lake.id
  key     = each.value
  content = ""
}

resource "aws_s3_bucket_policy" "scripts" {
  bucket = aws_s3_bucket.scripts.id
  policy = data.aws_iam_policy_document.scripts_bucket_readers.json
}

resource "aws_s3_bucket_lifecycle_configuration" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id

  rule {
    id     = "expire-athena-results"
    status = "Enabled"

    filter {}

    expiration {
      days = 30
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}
