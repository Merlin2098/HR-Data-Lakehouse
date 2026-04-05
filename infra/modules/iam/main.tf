locals {
  glue_role_name           = "${var.name_prefix}-${var.environment}-glue-role"
  glue_policy_name         = "${var.name_prefix}-${var.environment}-glue-runtime"
  step_functions_role_name = "${var.name_prefix}-${var.environment}-sfn-role"
  step_functions_policy    = "${var.name_prefix}-${var.environment}-sfn-runtime"

  s3_resource_arns = [
    var.data_lake_bucket_arn,
    "${var.data_lake_bucket_arn}/*",
    var.scripts_bucket_arn,
    "${var.scripts_bucket_arn}/*",
    var.athena_results_bucket_arn,
    "${var.athena_results_bucket_arn}/*",
  ]

  glue_job_arn_pattern = "arn:aws:glue:${var.region}:${var.account_id}:job/${var.name_prefix}-${var.environment}-*"
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
      "logs:AssociateKmsKey",
    ]
    resources = ["*"]
  }

  statement {
    sid       = "CloudWatchMetrics"
    effect    = "Allow"
    actions   = ["cloudwatch:PutMetricData"]
    resources = ["*"]
  }

  statement {
    sid    = "KmsLakehouseAccess"
    effect = "Allow"
    actions = [
      "kms:Decrypt",
      "kms:Encrypt",
      "kms:GenerateDataKey",
      "kms:DescribeKey",
    ]
    resources = [var.kms_key_arn]
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

data "aws_iam_policy_document" "step_functions_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

data "aws_iam_policy_document" "step_functions_runtime" {
  statement {
    sid    = "GlueJobExecution"
    effect = "Allow"
    actions = [
      "glue:StartJobRun",
      "glue:GetJobRun",
      "glue:GetJobRuns",
      "glue:BatchStopJobRun",
    ]
    resources = [local.glue_job_arn_pattern]
  }

  statement {
    sid    = "AthenaQueryExecution"
    effect = "Allow"
    actions = [
      "athena:StartQueryExecution",
      "athena:GetQueryExecution",
      "athena:GetQueryResults",
      "athena:StopQueryExecution",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "GlueCatalogRead"
    effect = "Allow"
    actions = [
      "glue:GetDatabase",
      "glue:GetDatabases",
      "glue:GetTable",
      "glue:GetTables",
      "glue:GetPartition",
      "glue:GetPartitions",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "AthenaResultsAccess"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket",
      "s3:GetBucketLocation",
    ]
    resources = [
      var.athena_results_bucket_arn,
      "${var.athena_results_bucket_arn}/*",
    ]
  }

  statement {
    sid    = "AthenaDataLakeRead"
    effect = "Allow"
    actions = [
      "s3:ListBucket",
      "s3:GetBucketLocation",
    ]
    resources = [var.data_lake_bucket_arn]
  }

  statement {
    sid    = "AthenaCuratedObjectRead"
    effect = "Allow"
    actions = [
      "s3:GetObject",
    ]
    resources = [
      "${var.data_lake_bucket_arn}/silver/*",
      "${var.data_lake_bucket_arn}/gold/*",
    ]
  }

  statement {
    sid    = "StepFunctionsLoggingAndKms"
    effect = "Allow"
    actions = [
      "logs:CreateLogDelivery",
      "logs:GetLogDelivery",
      "logs:UpdateLogDelivery",
      "logs:DeleteLogDelivery",
      "logs:ListLogDeliveries",
      "logs:PutResourcePolicy",
      "logs:DescribeResourcePolicies",
      "logs:DescribeLogGroups",
      "kms:Decrypt",
      "kms:Encrypt",
      "kms:GenerateDataKey",
      "kms:DescribeKey",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role" "step_functions" {
  name               = local.step_functions_role_name
  assume_role_policy = data.aws_iam_policy_document.step_functions_assume_role.json
  tags               = var.common_tags
}

resource "aws_iam_policy" "step_functions_runtime" {
  name   = local.step_functions_policy
  policy = data.aws_iam_policy_document.step_functions_runtime.json
  tags   = var.common_tags
}

resource "aws_iam_role_policy_attachment" "step_functions_runtime" {
  role       = aws_iam_role.step_functions.name
  policy_arn = aws_iam_policy.step_functions_runtime.arn
}
