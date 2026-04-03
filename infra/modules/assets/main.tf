locals {
  assets = {
    landing_to_bronze_script = {
      key    = "glue/landing_to_bronze.py"
      source = "${path.module}/../../../src/glue/landing_to_bronze.py"
    }
    bronze_to_silver_script = {
      key    = "glue/bronze_to_silver.py"
      source = "${path.module}/../../../src/glue/bronze_to_silver.py"
    }
    silver_to_gold_script = {
      key    = "glue/silver_to_gold.py"
      source = "${path.module}/../../../src/glue/silver_to_gold.py"
    }
    transformations = {
      key    = "configs/transformations.yaml"
      source = "${path.module}/../../../src/configs/transformations.yaml"
    }
    contracts = {
      key    = "configs/contracts.yaml"
      source = "${path.module}/../../../src/configs/contracts.yaml"
    }
    bronze_to_silver_query = {
      key    = "queries/bronze_to_silver.sql"
      source = "${path.module}/../../../src/queries/bronze_to_silver.sql"
    }
    silver_to_gold_query = {
      key    = "queries/silver_to_gold.sql"
      source = "${path.module}/../../../src/queries/silver_to_gold.sql"
    }
  }
}

resource "aws_s3_object" "assets" {
  for_each = local.assets

  bucket = var.scripts_bucket_name
  key    = each.value.key
  source = each.value.source
  etag   = filemd5(each.value.source)
}
