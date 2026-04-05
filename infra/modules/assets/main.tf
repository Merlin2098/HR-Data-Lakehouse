locals {
  glue_runtime_files = {
    "src/__init__.py"                = "${path.module}/../../../src/__init__.py"
    "src/common/__init__.py"         = "${path.module}/../../../src/common/__init__.py"
    "src/common/config_loader.py"    = "${path.module}/../../../src/common/config_loader.py"
    "src/common/contract_loader.py"  = "${path.module}/../../../src/common/contract_loader.py"
    "src/common/pipeline_runtime.py" = "${path.module}/../../../src/common/pipeline_runtime.py"
    "src/common/project_paths.py"    = "${path.module}/../../../src/common/project_paths.py"
    "src/common/query_loader.py"     = "${path.module}/../../../src/common/query_loader.py"
    "src/common/resource_loader.py"  = "${path.module}/../../../src/common/resource_loader.py"
    "src/common/s3_utils.py"         = "${path.module}/../../../src/common/s3_utils.py"
  }

  assets = {
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

data "archive_file" "glue_runtime" {
  type        = "zip"
  output_path = "${path.root}/.terraform/glue_runtime.zip"

  dynamic "source" {
    for_each = local.glue_runtime_files

    content {
      filename = source.key
      content  = file(source.value)
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

resource "aws_s3_object" "glue_runtime_package" {
  bucket = var.scripts_bucket_name
  key    = "runtime/glue_runtime.zip"
  source = data.archive_file.glue_runtime.output_path
  etag   = data.archive_file.glue_runtime.output_md5
}
