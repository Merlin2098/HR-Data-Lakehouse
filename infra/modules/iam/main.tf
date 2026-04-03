locals {
  glue_role_name   = "${var.name_prefix}-${var.environment}-glue-role"
  glue_policy_name = "${var.name_prefix}-${var.environment}-glue-runtime"

  s3_resource_arns = [
    var.bronze_bucket_arn,
    "${var.bronze_bucket_arn}/*",
    var.silver_bucket_arn,
    "${var.silver_bucket_arn}/*",
    var.scripts_bucket_arn,
    "${var.scripts_bucket_arn}/*",
  ]
}

data "aws_iam_policy_document" "glue_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["glue.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

data "aws_iam_policy_document" "glue_runtime" {
  statement {
    sid    = "S3LakehouseAccess"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket",
      "s3:GetBucketLocation",
    ]
    resources = local.s3_resource_arns
  }

  statement {
    sid    = "CloudWatchLogging"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role" "glue" {
  name               = local.glue_role_name
  assume_role_policy = data.aws_iam_policy_document.glue_assume_role.json
  tags               = var.common_tags
}

resource "aws_iam_policy" "glue_runtime" {
  name   = local.glue_policy_name
  policy = data.aws_iam_policy_document.glue_runtime.json
  tags   = var.common_tags
}

resource "aws_iam_role_policy_attachment" "glue_runtime" {
  role       = aws_iam_role.glue.name
  policy_arn = aws_iam_policy.glue_runtime.arn
}
