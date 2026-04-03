locals {
  silver_table_name = "silver_hr_employees"
  gold_table_name   = "gold_hr_attrition_fact"
}

resource "aws_glue_catalog_database" "lakehouse" {
  name = var.database_name
}

resource "aws_glue_catalog_table" "silver" {
  name          = local.silver_table_name
  database_name = aws_glue_catalog_database.lakehouse.name
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    classification = "parquet"
    EXTERNAL       = "TRUE"
  }

  storage_descriptor {
    location      = "s3://${var.silver_bucket_name}/hr_attrition/silver/hr_employees/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "parquet-serde"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "employee_number"
      type = "int"
    }
    columns {
      name = "department"
      type = "string"
    }
    columns {
      name = "job_role"
      type = "string"
    }
    columns {
      name = "job_level"
      type = "int"
    }
    columns {
      name = "over_time"
      type = "boolean"
    }
    columns {
      name = "monthly_income"
      type = "decimal(12,2)"
    }
    columns {
      name = "percent_salary_hike"
      type = "int"
    }
    columns {
      name = "years_at_company"
      type = "int"
    }
    columns {
      name = "years_since_last_promotion"
      type = "int"
    }
    columns {
      name = "total_working_years"
      type = "int"
    }
    columns {
      name = "job_satisfaction"
      type = "int"
    }
    columns {
      name = "environment_satisfaction"
      type = "int"
    }
    columns {
      name = "relationship_satisfaction"
      type = "int"
    }
    columns {
      name = "work_life_balance"
      type = "int"
    }
    columns {
      name = "attrition"
      type = "boolean"
    }
    columns {
      name = "source_file"
      type = "string"
    }
    columns {
      name = "run_id"
      type = "string"
    }
    columns {
      name = "processed_at_utc"
      type = "timestamp"
    }
  }
}

resource "aws_glue_catalog_table" "gold" {
  name          = local.gold_table_name
  database_name = aws_glue_catalog_database.lakehouse.name
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    classification              = "parquet"
    EXTERNAL                    = "TRUE"
    "projection.enabled"        = "true"
    "projection.year.type"      = "integer"
    "projection.year.range"     = var.year_projection_range
    "projection.month.type"     = "integer"
    "projection.month.range"    = "1,12"
    "projection.day.type"       = "integer"
    "projection.day.range"      = "1,31"
    "storage.location.template" = "s3://${var.gold_bucket_name}/hr_attrition/gold/hr_attrition/year=$${year}/month=$${month}/day=$${day}/"
  }

  partition_keys {
    name = "year"
    type = "int"
  }
  partition_keys {
    name = "month"
    type = "int"
  }
  partition_keys {
    name = "day"
    type = "int"
  }

  storage_descriptor {
    location      = "s3://${var.gold_bucket_name}/hr_attrition/gold/hr_attrition/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "parquet-serde"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "employee_id"
      type = "int"
    }
    columns {
      name = "ingestion_date"
      type = "date"
    }
    columns {
      name = "department"
      type = "string"
    }
    columns {
      name = "job_role"
      type = "string"
    }
    columns {
      name = "job_level"
      type = "int"
    }
    columns {
      name = "attrition"
      type = "boolean"
    }
    columns {
      name = "monthly_income"
      type = "decimal(12,2)"
    }
    columns {
      name = "percent_salary_hike"
      type = "int"
    }
    columns {
      name = "years_at_company"
      type = "int"
    }
    columns {
      name = "years_since_last_promotion"
      type = "int"
    }
    columns {
      name = "total_working_years"
      type = "int"
    }
    columns {
      name = "over_time"
      type = "boolean"
    }
    columns {
      name = "job_satisfaction_score"
      type = "int"
    }
    columns {
      name = "environment_satisfaction_score"
      type = "int"
    }
    columns {
      name = "relationship_satisfaction_score"
      type = "int"
    }
    columns {
      name = "work_life_balance_score"
      type = "int"
    }
    columns {
      name = "job_satisfaction_label"
      type = "string"
    }
    columns {
      name = "environment_satisfaction_label"
      type = "string"
    }
    columns {
      name = "relationship_satisfaction_label"
      type = "string"
    }
    columns {
      name = "work_life_balance_label"
      type = "string"
    }
    columns {
      name = "source_file"
      type = "string"
    }
    columns {
      name = "run_id"
      type = "string"
    }
    columns {
      name = "processed_at_utc"
      type = "timestamp"
    }
  }
}
