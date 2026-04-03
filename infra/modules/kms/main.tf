locals {
  alias_name = "alias/${var.name_prefix}-${var.environment}-lakehouse"
}

resource "aws_kms_key" "lakehouse" {
  description             = "KMS key for the HR lakehouse data plane and operational logs."
  enable_key_rotation     = true
  deletion_window_in_days = 7
  tags                    = var.common_tags
}

resource "aws_kms_alias" "lakehouse" {
  name          = local.alias_name
  target_key_id = aws_kms_key.lakehouse.key_id
}
