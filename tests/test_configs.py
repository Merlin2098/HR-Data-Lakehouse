from __future__ import annotations

from pathlib import Path

from src.common.config_loader import load_yaml_file
from src.common.contract_loader import dataset_contract, expected_columns
from src.common.project_paths import resolve_project_path


EXPECTED_COLUMNS = [
    "employee_number",
    "department",
    "job_role",
    "job_level",
    "over_time",
    "monthly_income",
    "percent_salary_hike",
    "years_at_company",
    "years_since_last_promotion",
    "total_working_years",
    "job_satisfaction",
    "environment_satisfaction",
    "relationship_satisfaction",
    "work_life_balance",
    "attrition",
    "source_file",
    "run_id",
    "processed_at_utc",
]

EXPECTED_GOLD_COLUMNS = [
    "employee_id",
    "ingestion_date",
    "year",
    "month",
    "day",
    "department",
    "job_role",
    "job_level",
    "attrition",
    "monthly_income",
    "percent_salary_hike",
    "years_at_company",
    "years_since_last_promotion",
    "total_working_years",
    "over_time",
    "job_satisfaction_score",
    "environment_satisfaction_score",
    "relationship_satisfaction_score",
    "work_life_balance_score",
    "job_satisfaction_label",
    "environment_satisfaction_label",
    "relationship_satisfaction_label",
    "work_life_balance_label",
    "source_file",
    "run_id",
    "processed_at_utc",
]

EXPECTED_BI_COLUMNS = EXPECTED_GOLD_COLUMNS.copy()


def test_transformations_config_declares_bronze_to_silver_pipeline() -> None:
    config = load_yaml_file(resolve_project_path("src/configs/transformations.yaml"))
    assert config["defaults"]["execution_mode"] == "local"
    assert config["defaults"]["engines"] == {"local": "duckdb", "aws": "glue_spark"}
    pipeline = config["pipelines"]["bronze_to_silver"]

    assert pipeline["source"]["local_uri"] == "data/HR-Employee-Attrition3.csv"
    assert pipeline["source"]["source_uri"] == "s3://{data_lake_bucket}/bronze/hr_attrition/landing/"
    assert pipeline["target"]["format"] == "parquet"
    assert pipeline["target"]["layout"] == "dataset"
    assert pipeline["target"]["write_mode"] == "overwrite_full"
    assert pipeline["artifacts"]["query_path"] == "src/queries/bronze_to_silver.sql"
    assert pipeline["artifacts"]["query_uri"] == "s3://{scripts_bucket}/queries/bronze_to_silver.sql"
    assert pipeline["artifacts"]["contract_path"] == "src/configs/contracts.yaml"
    assert pipeline["artifacts"]["config_uri"] == "s3://{scripts_bucket}/configs/transformations.yaml"
    assert pipeline["target"]["local_uri"] == "data/output/silver/hr_employees"
    assert pipeline["target"]["target_uri"] == "s3://{data_lake_bucket}/silver/hr_employees/"
    assert "landing_to_bronze" not in config["pipelines"]


def test_transformations_config_declares_silver_to_gold_pipeline() -> None:
    config = load_yaml_file(resolve_project_path("src/configs/transformations.yaml"))
    pipeline = config["pipelines"]["silver_to_gold"]

    assert pipeline["source"]["local_uri"] == "data/output/silver/hr_employees"
    assert pipeline["source"]["source_uri"] == "s3://{data_lake_bucket}/silver/hr_employees/"
    assert pipeline["target"]["local_uri"] == "data/output/gold/hr_attrition"
    assert pipeline["target"]["target_uri"] == "s3://{data_lake_bucket}/gold/hr_attrition/"
    assert pipeline["target"]["layout"] == "dataset"
    assert pipeline["target"]["write_mode"] == "overwrite_partition"
    assert pipeline["target"]["partition_style"] == "hive"
    assert pipeline["target"]["partition_by"] == ["year", "month", "day"]
    assert pipeline["artifacts"]["query_path"] == "src/queries/silver_to_gold.sql"


def test_transformations_config_declares_gold_to_bi_export_pipeline() -> None:
    config = load_yaml_file(resolve_project_path("src/configs/transformations.yaml"))
    pipeline = config["pipelines"]["gold_to_bi_export"]

    assert pipeline["source"]["local_uri"] == "data/output/gold/hr_attrition"
    assert pipeline["source"]["source_uri"] == "s3://{data_lake_bucket}/gold/hr_attrition/"
    assert pipeline["source"]["view_name"] == "gold_hr_attrition_fact"
    assert pipeline["target"]["local_uri"] == "data/output/bi/hr_attrition_snapshot.parquet"
    assert pipeline["target"]["target_uri"] == "s3://{data_lake_bucket}/bi/hr_attrition_snapshot/hr_attrition_snapshot.parquet"
    assert pipeline["target"]["layout"] == "file"
    assert pipeline["target"]["write_mode"] == "overwrite_full"
    assert pipeline["artifacts"]["query_path"] == "src/queries/gold_to_bi_export.sql"
    assert pipeline["artifacts"]["glue_script_path"] == "src/glue/gold_to_bi_export.py"


def test_contract_matches_expected_silver_columns() -> None:
    contract = load_yaml_file(resolve_project_path("src/configs/contracts.yaml"))

    assert expected_columns(contract, "silver_hr_employees") == EXPECTED_COLUMNS


def test_contract_matches_expected_gold_columns() -> None:
    contract = load_yaml_file(resolve_project_path("src/configs/contracts.yaml"))

    assert expected_columns(contract, "gold_hr_attrition_fact") == EXPECTED_GOLD_COLUMNS


def test_contract_matches_expected_bi_snapshot_columns() -> None:
    contract = load_yaml_file(resolve_project_path("src/configs/contracts.yaml"))

    assert expected_columns(contract, "bi_hr_attrition_snapshot") == EXPECTED_BI_COLUMNS


def test_contract_declares_quality_metadata_for_aws_style_execution() -> None:
    contract = load_yaml_file(resolve_project_path("src/configs/contracts.yaml"))
    silver_contract = dataset_contract(contract, "silver_hr_employees")
    gold_contract = dataset_contract(contract, "gold_hr_attrition_fact")

    assert silver_contract["primary_key"] == ["employee_number"]
    assert gold_contract["primary_key"] == ["employee_id"]
    assert gold_contract["partition_columns"] == ["year", "month", "day"]


def test_event_driven_orchestration_replaces_scheduler_resources() -> None:
    orchestration_tf = Path(resolve_project_path("infra/modules/orchestration/main.tf")).read_text(encoding="utf-8")

    assert "aws_scheduler_schedule" not in orchestration_tf
    assert '"detail-type" = ["Object Created"]' in orchestration_tf
    assert 'wildcard = local.landing_object_pattern' in orchestration_tf
    assert 'states:StartExecution' in orchestration_tf


def test_data_lake_bucket_forwards_events_to_eventbridge() -> None:
    s3_tf = Path(resolve_project_path("infra/modules/s3/main.tf")).read_text(encoding="utf-8")

    assert 'resource "aws_s3_bucket_notification" "data_lake_eventbridge"' in s3_tf
    assert "eventbridge = true" in s3_tf


def test_budgets_module_defines_monthly_cost_budget_with_sns_alerts() -> None:
    budgets_tf = Path(resolve_project_path("infra/modules/budgets/main.tf")).read_text(encoding="utf-8")

    assert 'resource "aws_budgets_budget" "monthly_cost"' in budgets_tf
    assert 'budget_type  = "COST"' in budgets_tf
    assert 'time_unit    = "MONTHLY"' in budgets_tf
    assert 'format("user:Environment$%s", var.environment)' in budgets_tf
    assert 'subscriber_sns_topic_arns = [var.sns_topic_arn]' in budgets_tf
    assert budgets_tf.count('threshold                 = 80') == 2
    assert budgets_tf.count('threshold                 = 100') == 2
    assert budgets_tf.count('notification_type         = "ACTUAL"') == 2
    assert budgets_tf.count('notification_type         = "FORECASTED"') == 2


def test_root_module_wires_budgets_to_observability_topic() -> None:
    root_tf = Path(resolve_project_path("infra/main.tf")).read_text(encoding="utf-8")

    assert 'module "budgets"' in root_tf
    assert 'sns_topic_arn            = module.observability.alerts_topic_arn' in root_tf
    assert 'monthly_budget_limit_usd = var.monthly_budget_limit_usd' in root_tf


def test_observability_topic_accepts_budgets_and_supports_email_subscriptions() -> None:
    observability_tf = Path(resolve_project_path("infra/modules/observability/main.tf")).read_text(encoding="utf-8")
    kms_tf = Path(resolve_project_path("infra/modules/kms/main.tf")).read_text(encoding="utf-8")

    assert 'resource "aws_sns_topic_policy" "alerts"' in observability_tf
    assert 'identifiers = ["budgets.amazonaws.com"]' in observability_tf
    assert 'actions   = ["SNS:Publish"]' in observability_tf
    assert 'resource "aws_sns_topic_subscription" "email"' in observability_tf
    assert 'for_each = toset(var.alert_email_endpoints)' in observability_tf
    assert 'identifiers = ["sns.amazonaws.com"]' in kms_tf
    assert 'variable = "aws:SourceAccount"' in kms_tf


def test_step_functions_role_can_run_athena_validation_against_curated_data_lake_prefixes() -> None:
    iam_tf = Path(resolve_project_path("infra/modules/iam/main.tf")).read_text(encoding="utf-8")

    assert 'sid    = "AthenaDataLakeRead"' in iam_tf
    assert 'sid    = "AthenaCuratedObjectRead"' in iam_tf
    assert 'var.data_lake_bucket_arn' in iam_tf
    assert '"s3:ListBucket"' in iam_tf
    assert '"s3:GetBucketLocation"' in iam_tf
    assert '"s3:GetObject"' in iam_tf
    assert '"${var.data_lake_bucket_arn}/silver/*"' in iam_tf
    assert '"${var.data_lake_bucket_arn}/gold/*"' in iam_tf


def test_github_actions_workflow_runs_on_main_and_targets_dev() -> None:
    workflow = Path(resolve_project_path(".github/workflows/terraform.yml")).read_text(encoding="utf-8")

    assert "push:" in workflow
    assert '      - "main"' in workflow
    assert 'terraform plan -var-file="env/dev.tfvars" -input=false' in workflow
    assert "Terraform CI Summary" in workflow
    assert "prod automation: manual only" in workflow


def test_scripts_bucket_uses_aes256_and_explicit_reader_policy() -> None:
    s3_tf = Path(resolve_project_path("infra/modules/s3/main.tf")).read_text(encoding="utf-8")
    root_tf = Path(resolve_project_path("infra/main.tf")).read_text(encoding="utf-8")
    dev_tfvars = Path(resolve_project_path("infra/env/dev.tfvars")).read_text(encoding="utf-8")

    assert 'resource "aws_s3_bucket_server_side_encryption_configuration" "scripts"' in s3_tf
    assert 'sse_algorithm = "AES256"' in s3_tf
    assert 'kms_master_key_id = var.kms_key_arn' in s3_tf
    assert 'resource "aws_s3_bucket_policy" "scripts"' in s3_tf
    assert '"s3:GetObject"' in s3_tf
    assert '"s3:GetObjectVersion"' in s3_tf
    assert '"s3:ListBucket"' in s3_tf
    assert '["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]' in root_tf
    assert "scripts_bucket_reader_arns" in root_tf
    assert '"arn:aws:iam::184670914470:user/admin2"' in dev_tfvars


def test_catalog_exposes_only_curated_tables_and_not_quicksight_view() -> None:
    catalog_tf = Path(resolve_project_path("infra/modules/catalog/main.tf")).read_text(encoding="utf-8")
    catalog_outputs = Path(resolve_project_path("infra/modules/catalog/outputs.tf")).read_text(encoding="utf-8")
    root_outputs = Path(resolve_project_path("infra/outputs.tf")).read_text(encoding="utf-8")

    assert 'resource "aws_glue_catalog_table" "silver"' in catalog_tf
    assert 'resource "aws_glue_catalog_table" "gold"' in catalog_tf
    assert 'resource "aws_glue_catalog_table" "quicksight"' not in catalog_tf
    assert 'output "quicksight_view_name"' not in catalog_outputs
    assert 'module.catalog.quicksight_view_name' not in root_outputs
    assert 'output "bi_snapshot_s3_uri"' in root_outputs


def test_s3_module_defines_bi_placeholder_and_no_active_quicksight_policies() -> None:
    s3_tf = Path(resolve_project_path("infra/modules/s3/main.tf")).read_text(encoding="utf-8")
    s3_vars = Path(resolve_project_path("infra/modules/s3/variables.tf")).read_text(encoding="utf-8")
    root_tf = Path(resolve_project_path("infra/main.tf")).read_text(encoding="utf-8")
    root_vars = Path(resolve_project_path("infra/variables.tf")).read_text(encoding="utf-8")
    dev_tfvars = Path(resolve_project_path("infra/env/dev.tfvars")).read_text(encoding="utf-8")

    assert 'variable "quicksight_principal_arns"' not in s3_vars
    assert 'variable "quicksight_principal_arns"' not in root_vars
    assert 'quicksight_principal_arns = var.quicksight_principal_arns' not in root_tf
    assert 'resource "aws_s3_bucket_policy" "data_lake_quicksight"' not in s3_tf
    assert 'resource "aws_s3_bucket_policy" "athena_results_quicksight"' not in s3_tf
    assert 'bi/hr_attrition_snapshot/.keep' in s3_tf
    assert 'quicksight_principal_arns' not in dev_tfvars


def test_data_lake_defines_medallion_prefix_placeholders() -> None:
    s3_tf = Path(resolve_project_path("infra/modules/s3/main.tf")).read_text(encoding="utf-8")
    resource_loader = Path(resolve_project_path("src/common/resource_loader.py")).read_text(encoding="utf-8")

    assert 'resource "aws_s3_object" "data_lake_prefix_placeholders"' in s3_tf
    assert 'bronze/hr_attrition/landing/.keep' in s3_tf
    assert 'bronze/hr_attrition/raw/.keep' not in s3_tf
    assert 'silver/hr_employees/.keep' in s3_tf
    assert 'gold/hr_attrition/.keep' in s3_tf
    assert 'bi/hr_attrition_snapshot/.keep' in s3_tf
    assert "_is_placeholder_key" in resource_loader
    assert 'if _is_placeholder_key(key):' in resource_loader


def test_glue_runtime_is_packaged_minimally_and_attached_to_jobs() -> None:
    provider_tf = Path(resolve_project_path("infra/provider.tf")).read_text(encoding="utf-8")
    assets_tf = Path(resolve_project_path("infra/modules/assets/main.tf")).read_text(encoding="utf-8")
    assets_outputs = Path(resolve_project_path("infra/modules/assets/outputs.tf")).read_text(encoding="utf-8")
    glue_tf = Path(resolve_project_path("infra/modules/glue/main.tf")).read_text(encoding="utf-8")
    glue_vars = Path(resolve_project_path("infra/modules/glue/variables.tf")).read_text(encoding="utf-8")
    root_tf = Path(resolve_project_path("infra/main.tf")).read_text(encoding="utf-8")

    assert 'source  = "hashicorp/archive"' in provider_tf
    assert 'data "archive_file" "glue_runtime"' in assets_tf
    assert '"src/common/pipeline_runtime.py"' in assets_tf
    assert '"src/common/resource_loader.py"' in assets_tf
    assert 'landing_to_bronze_script' not in assets_tf
    assert 'key    = "runtime/glue_runtime.zip"' in assets_tf
    assert 'output "glue_runtime_package_key"' in assets_outputs
    assert 'variable "glue_runtime_package_key"' in glue_vars
    assert 'glue_runtime_package_uri = "s3://${var.script_bucket}/${var.glue_runtime_package_key}"' in glue_tf
    assert 'module.assets.glue_runtime_package_key' in root_tf
    assert glue_tf.count('"--extra-py-files"') == 3


def test_assets_and_glue_module_publish_bi_export_stage() -> None:
    assets_tf = Path(resolve_project_path("infra/modules/assets/main.tf")).read_text(encoding="utf-8")
    assets_outputs = Path(resolve_project_path("infra/modules/assets/outputs.tf")).read_text(encoding="utf-8")
    glue_tf = Path(resolve_project_path("infra/modules/glue/main.tf")).read_text(encoding="utf-8")
    glue_outputs = Path(resolve_project_path("infra/modules/glue/outputs.tf")).read_text(encoding="utf-8")
    root_tf = Path(resolve_project_path("infra/main.tf")).read_text(encoding="utf-8")

    assert 'gold_to_bi_export_script' in assets_tf
    assert 'glue/gold_to_bi_export.py' in assets_tf
    assert 'queries/gold_to_bi_export.sql' in assets_tf
    assert 'output "gold_to_bi_export_script_key"' in assets_outputs
    assert 'output "gold_to_bi_export_query_key"' in assets_outputs
    assert 'resource "aws_glue_job" "gold_to_bi_export"' in glue_tf
    assert '"--target-uri"' in glue_tf
    assert 'local.bi_export_uri' in glue_tf
    assert 'output "gold_to_bi_export_job_name"' in glue_outputs
    assert 'gold_to_bi_export_job_name' in root_tf
    assert 'local.gold_to_bi_export_job_name' in root_tf


def test_pipeline_runtime_loads_duckdb_lazily_for_local_only() -> None:
    runtime_py = Path(resolve_project_path("src/common/pipeline_runtime.py")).read_text(encoding="utf-8")

    assert "import duckdb" not in runtime_py.splitlines()[:20]
    assert "def get_duckdb_module():" in runtime_py
    assert "duckdb = get_duckdb_module()" in runtime_py


def test_glue_entrypoints_use_safe_bootstrap_helper() -> None:
    bronze_script = Path(resolve_project_path("src/glue/bronze_to_silver.py")).read_text(encoding="utf-8")
    gold_script = Path(resolve_project_path("src/glue/silver_to_gold.py")).read_text(encoding="utf-8")
    bi_script = Path(resolve_project_path("src/glue/gold_to_bi_export.py")).read_text(encoding="utf-8")
    project_paths = Path(resolve_project_path("src/common/project_paths.py")).read_text(encoding="utf-8")

    assert "def ensure_src_package_importable" in project_paths
    for script in (bronze_script, gold_script, bi_script):
        assert "parents[2]" not in script
        assert "ensure_src_package_importable(__file__)" in script
        assert "candidate / \"src\" / \"__init__.py\"" in script


def test_glue_entrypoints_tolerate_unknown_glue_arguments() -> None:
    bronze_script = Path(resolve_project_path("src/glue/bronze_to_silver.py")).read_text(encoding="utf-8")
    gold_script = Path(resolve_project_path("src/glue/silver_to_gold.py")).read_text(encoding="utf-8")
    bi_script = Path(resolve_project_path("src/glue/gold_to_bi_export.py")).read_text(encoding="utf-8")

    for script in (bronze_script, gold_script, bi_script):
        assert "parse_known_args()" in script
        assert "return parser.parse_args()" not in script


def test_state_machine_uses_last_key_segment_for_source_filename_and_exposes_manual_retry_shape() -> None:
    orchestration_tf = Path(resolve_project_path("infra/modules/orchestration/main.tf")).read_text(encoding="utf-8")
    outputs_tf = Path(resolve_project_path("infra/outputs.tf")).read_text(encoding="utf-8")

    assert 'States.ArrayLength(States.StringSplit($.detail.object.key, \'/\'))' in orchestration_tf
    assert 'States.MathAdd(States.ArrayLength(States.StringSplit($.detail.object.key, \'/\')), -1)' in orchestration_tf
    assert 'States.ArrayGetItem(States.StringSplit($.detail.object.key, \'/\'), 2)' not in orchestration_tf
    assert '"source_filename.$" = "$.source_filename"' in orchestration_tf
    assert 'output "state_machine_name"' in outputs_tf


def test_state_machine_preserves_normalized_context_between_glue_tasks() -> None:
    orchestration_tf = Path(resolve_project_path("infra/modules/orchestration/main.tf")).read_text(encoding="utf-8")

    assert 'ResultPath = "$.bronze_to_silver_result"' in orchestration_tf
    assert 'ResultPath = "$.silver_to_gold_result"' in orchestration_tf
    assert 'ResultPath = "$.gold_to_bi_export_result"' in orchestration_tf
    assert 'PromoteLandingToBronze' not in orchestration_tf
    assert 'JobName = var.landing_to_bronze_job_name' not in orchestration_tf
    assert 'GoldToBiExport' in orchestration_tf
    assert 'JobName = var.gold_to_bi_export_job_name' in orchestration_tf
    assert '"--source-uri.$"      = "$.source_uri"' in orchestration_tf
    assert '"--business-date.$"   = "$.business_date"' in orchestration_tf
    assert '"--run-id.$"          = "$.run_id"' in orchestration_tf
    assert '"--source-filename.$" = "$.source_filename"' in orchestration_tf


def test_manual_retry_helper_starts_step_functions_execution_from_existing_landing_object() -> None:
    retry_helper = Path(resolve_project_path("src/glue/retry_state_machine.py")).read_text(encoding="utf-8")

    assert 'boto3.client("stepfunctions")' in retry_helper
    assert "start_execution" in retry_helper
    assert "--source-uri" in retry_helper
    assert "--bucket" in retry_helper
    assert "--object-key" in retry_helper
    assert "--state-machine-arn" in retry_helper
    assert "--state-machine-name" in retry_helper
    assert '"source_filename": source_filename' in retry_helper
    assert '"bucket_name": bucket_name' in retry_helper
    assert '"object_key": object_key' in retry_helper


def test_glue_runtime_supports_cloudwatch_metrics_and_s3_partition_validation() -> None:
    iam_tf = Path(resolve_project_path("infra/modules/iam/main.tf")).read_text(encoding="utf-8")
    runtime_py = Path(resolve_project_path("src/common/pipeline_runtime.py")).read_text(encoding="utf-8")
    resource_loader = Path(resolve_project_path("src/common/resource_loader.py")).read_text(encoding="utf-8")

    assert '"cloudwatch:PutMetricData"' in iam_tf
    assert "treat_as_prefix=s3_partition_prefix" in runtime_py
    assert "def resource_exists(value: str | Path, *, treat_as_prefix: bool = False)" in resource_loader
    assert "def list_resource_objects(value: str | Path, *, treat_as_prefix: bool = False)" in resource_loader
