locals {
  scheduler_input = {
    business_date   = "<aws.scheduler.scheduled-time>"
    run_id          = "<aws.scheduler.execution-id>"
    source_uri      = "s3://${var.bronze_bucket_name}/hr_attrition/landing/${var.dataset_source_filename}"
    source_filename = var.dataset_source_filename
  }

  state_machine_definition = jsonencode({
    Comment = "Daily HR lakehouse medallion pipeline"
    StartAt = "PromoteLandingToBronze"
    States = {
      PromoteLandingToBronze = {
        Type     = "Task"
        Resource = "arn:aws:states:::glue:startJobRun.sync"
        Parameters = {
          JobName = var.landing_to_bronze_job_name
          Arguments = {
            "--business-date.$" = "$.business_date"
            "--run-id.$"        = "$.run_id"
            "--source-uri.$"    = "$.source_uri"
            "--source-filename.$" = "$.source_filename"
          }
        }
        Next = "BronzeToSilver"
      }
      BronzeToSilver = {
        Type     = "Task"
        Resource = "arn:aws:states:::glue:startJobRun.sync"
        Parameters = {
          JobName = var.bronze_to_silver_job_name
          Arguments = {
            "--business-date.$" = "$.business_date"
            "--run-id.$"        = "$.run_id"
            "--source-filename.$" = "$.source_filename"
          }
        }
        Next = "SilverToGold"
      }
      SilverToGold = {
        Type     = "Task"
        Resource = "arn:aws:states:::glue:startJobRun.sync"
        Parameters = {
          JobName = var.silver_to_gold_job_name
          Arguments = {
            "--business-date.$" = "$.business_date"
            "--run-id.$"        = "$.run_id"
          }
        }
        Next = "ValidateCatalog"
      }
      ValidateCatalog = {
        Type     = "Task"
        Resource = "arn:aws:states:::athena:startQueryExecution.sync"
        Parameters = {
          WorkGroup = var.athena_workgroup_name
          QueryString = "SELECT COUNT(*) AS row_count FROM \"${var.athena_database_name}\".\"${var.gold_table_name}\""
          QueryExecutionContext = {
            Database = var.athena_database_name
          }
          ResultConfiguration = {
            OutputLocation = "s3://${var.athena_results_bucket_name}/query-results/"
          }
        }
        End = true
      }
    }
  })
}

resource "aws_cloudwatch_log_group" "step_functions" {
  name              = var.step_functions_log_group_name
  retention_in_days = 30
  kms_key_id        = var.kms_key_arn
  tags              = var.common_tags
}

resource "aws_sfn_state_machine" "daily_medallion" {
  name       = var.state_machine_name
  role_arn   = var.step_functions_role_arn
  definition = local.state_machine_definition
  type       = "STANDARD"
  tags       = var.common_tags

  logging_configuration {
    include_execution_data = true
    level                  = "ALL"
    log_destination        = "${aws_cloudwatch_log_group.step_functions.arn}:*"
  }
}

data "aws_iam_policy_document" "scheduler_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

data "aws_iam_policy_document" "scheduler_start_execution" {
  statement {
    effect = "Allow"
    actions = [
      "states:StartExecution",
    ]
    resources = [aws_sfn_state_machine.daily_medallion.arn]
  }
}

resource "aws_iam_role" "scheduler" {
  name               = "${var.scheduler_name}-role"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume_role.json
  tags               = var.common_tags
}

resource "aws_iam_role_policy" "scheduler_start_execution" {
  name   = "${var.scheduler_name}-start-execution"
  role   = aws_iam_role.scheduler.id
  policy = data.aws_iam_policy_document.scheduler_start_execution.json
}

resource "aws_scheduler_schedule" "daily_pipeline" {
  name                = var.scheduler_name
  schedule_expression = var.schedule_expression
  state               = "ENABLED"
  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_sfn_state_machine.daily_medallion.arn
    role_arn = aws_iam_role.scheduler.arn
    input    = jsonencode(local.scheduler_input)
  }
}
