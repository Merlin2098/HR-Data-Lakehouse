locals {
  landing_object_pattern = "${var.landing_prefix}*${var.landing_suffix}"

  event_pattern = jsonencode({
    source        = ["aws.s3"]
    "detail-type" = ["Object Created"]
    detail = {
      bucket = {
        name = [var.bronze_bucket_name]
      }
      object = {
        key = [
          {
            wildcard = local.landing_object_pattern
          }
        ]
      }
    }
  })

  state_machine_definition = jsonencode({
    Comment = "Event-driven HR lakehouse medallion pipeline"
    StartAt = "DetectInputShape"
    States = {
      DetectInputShape = {
        Type = "Choice"
        Choices = [
          {
            Variable  = "$.detail.bucket.name"
            IsPresent = true
            Next      = "NormalizeS3Event"
          },
          {
            Variable  = "$.bucket_name"
            IsPresent = true
            Next      = "NormalizeManualInput"
          },
        ]
        Default = "InvalidInput"
      }
      NormalizeS3Event = {
        Type = "Pass"
        Parameters = {
          "bucket_name.$"     = "$.detail.bucket.name"
          "object_key.$"      = "$.detail.object.key"
          "event_time.$"      = "$.time"
          "business_date.$"   = "States.ArrayGetItem(States.StringSplit($.time, 'T'), 0)"
          "run_id.$"          = "$.id"
          "source_uri.$"      = "States.Format('s3://{}/{}', $.detail.bucket.name, $.detail.object.key)"
          "source_filename.$" = "States.ArrayGetItem(States.StringSplit($.detail.object.key, '/'), 2)"
        }
        ResultPath = "$"
        Next       = "PromoteLandingToBronze"
      }
      NormalizeManualInput = {
        Type = "Pass"
        Parameters = {
          "bucket_name.$"     = "$.bucket_name"
          "object_key.$"      = "$.object_key"
          "source_uri.$"      = "$.source_uri"
          "source_filename.$" = "$.source_filename"
          "business_date.$"   = "$.business_date"
          "run_id.$"          = "$.run_id"
          "event_time.$"      = "$.event_time"
        }
        ResultPath = "$"
        Next       = "PromoteLandingToBronze"
      }
      InvalidInput = {
        Type  = "Fail"
        Error = "InvalidPipelineInput"
        Cause = "Expected either an S3 EventBridge payload or a normalized manual execution payload."
      }
      PromoteLandingToBronze = {
        Type     = "Task"
        Resource = "arn:aws:states:::glue:startJobRun.sync"
        Parameters = {
          JobName = var.landing_to_bronze_job_name
          Arguments = {
            "--business-date.$"   = "$.business_date"
            "--source-uri.$"      = "$.source_uri"
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
            "--business-date.$"   = "$.business_date"
            "--run-id.$"          = "$.run_id"
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
          WorkGroup   = var.athena_workgroup_name
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

data "aws_iam_policy_document" "eventbridge_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

data "aws_iam_policy_document" "eventbridge_start_execution" {
  statement {
    effect = "Allow"
    actions = [
      "states:StartExecution",
    ]
    resources = [aws_sfn_state_machine.daily_medallion.arn]
  }
}

resource "aws_iam_role" "eventbridge_trigger" {
  name               = "${var.event_rule_name}-role"
  assume_role_policy = data.aws_iam_policy_document.eventbridge_assume_role.json
  tags               = var.common_tags
}

resource "aws_iam_role_policy" "eventbridge_start_execution" {
  name   = "${var.event_rule_name}-start-execution"
  role   = aws_iam_role.eventbridge_trigger.id
  policy = data.aws_iam_policy_document.eventbridge_start_execution.json
}

resource "aws_cloudwatch_event_rule" "landing_object_created" {
  name          = var.event_rule_name
  event_pattern = local.event_pattern
  tags          = var.common_tags
}

resource "aws_cloudwatch_event_target" "start_state_machine" {
  rule      = aws_cloudwatch_event_rule.landing_object_created.name
  target_id = var.event_target_id
  arn       = aws_sfn_state_machine.daily_medallion.arn
  role_arn  = aws_iam_role.eventbridge_trigger.arn
}
