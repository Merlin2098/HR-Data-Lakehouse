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


def test_transformations_config_declares_bronze_to_silver_pipeline() -> None:
    config = load_yaml_file(resolve_project_path("src/configs/transformations.yaml"))
    assert config["defaults"]["execution_mode"] == "local"
    assert config["defaults"]["engines"] == {"local": "duckdb", "aws": "glue_spark"}
    pipeline = config["pipelines"]["bronze_to_silver"]

    assert pipeline["source"]["local_uri"] == "data/HR-Employee-Attrition.csv"
    assert pipeline["source"]["source_uri"] == "s3://{data_lake_bucket}/bronze/hr_attrition/raw/"
    assert pipeline["target"]["format"] == "parquet"
    assert pipeline["target"]["layout"] == "dataset"
    assert pipeline["target"]["write_mode"] == "overwrite_full"
    assert pipeline["artifacts"]["query_path"] == "src/queries/bronze_to_silver.sql"
    assert pipeline["artifacts"]["query_uri"] == "s3://{scripts_bucket}/queries/bronze_to_silver.sql"
    assert pipeline["artifacts"]["contract_path"] == "src/configs/contracts.yaml"
    assert pipeline["artifacts"]["config_uri"] == "s3://{scripts_bucket}/configs/transformations.yaml"
    assert pipeline["target"]["local_uri"] == "data/output/silver/hr_employees"
    assert pipeline["target"]["target_uri"] == "s3://{data_lake_bucket}/silver/hr_employees/"


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


def test_transformations_config_declares_landing_to_bronze_pipeline() -> None:
    config = load_yaml_file(resolve_project_path("src/configs/transformations.yaml"))
    pipeline = config["pipelines"]["landing_to_bronze"]

    assert pipeline["source"]["local_uri"] == "data/HR-Employee-Attrition.csv"
    assert pipeline["source"]["source_uri"] == "s3://{data_lake_bucket}/bronze/hr_attrition/landing/"
    assert pipeline["target"]["target_uri"] == "s3://{data_lake_bucket}/bronze/hr_attrition/raw/"
    assert pipeline["target"]["write_mode"] == "immutable"


def test_contract_matches_expected_silver_columns() -> None:
    contract = load_yaml_file(resolve_project_path("src/configs/contracts.yaml"))

    assert expected_columns(contract, "silver_hr_employees") == EXPECTED_COLUMNS


def test_contract_matches_expected_gold_columns() -> None:
    contract = load_yaml_file(resolve_project_path("src/configs/contracts.yaml"))

    assert expected_columns(contract, "gold_hr_attrition_fact") == EXPECTED_GOLD_COLUMNS


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


def test_data_lake_defines_medallion_prefix_placeholders() -> None:
    s3_tf = Path(resolve_project_path("infra/modules/s3/main.tf")).read_text(encoding="utf-8")
    resource_loader = Path(resolve_project_path("src/common/resource_loader.py")).read_text(encoding="utf-8")

    assert 'resource "aws_s3_object" "data_lake_prefix_placeholders"' in s3_tf
    assert 'bronze/hr_attrition/landing/.keep' in s3_tf
    assert 'bronze/hr_attrition/raw/.keep' in s3_tf
    assert 'silver/hr_employees/.keep' in s3_tf
    assert 'gold/hr_attrition/.keep' in s3_tf
    assert "_is_placeholder_key" in resource_loader
    assert 'if _is_placeholder_key(key):' in resource_loader
