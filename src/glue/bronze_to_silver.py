from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.common.config_loader import load_yaml_file
from src.common.contract_loader import expected_columns, load_contract
from src.common.project_paths import ensure_parent_dir, resolve_project_path
from src.common.query_loader import load_sql_file
from src.common.s3_utils import is_s3_uri


DEFAULT_CONFIG_PATH = "src/configs/transformations.yaml"
DEFAULT_PIPELINE_NAME = "bronze_to_silver"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the bronze-to-silver HR pipeline.")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to the pipeline YAML file.")
    parser.add_argument("--pipeline", default=DEFAULT_PIPELINE_NAME, help="Pipeline name inside the YAML config.")
    parser.add_argument("--query", help="Optional override for the SQL file path.")
    parser.add_argument("--contract", help="Optional override for the contract YAML path.")
    parser.add_argument("--source", help="Optional override for the source CSV path or S3 URI.")
    parser.add_argument("--target", help="Optional override for the target Parquet path or S3 URI.")
    return parser.parse_args()


def load_pipeline_definition(config_path: str | Path, pipeline_name: str) -> tuple[dict[str, Any], Path]:
    resolved_config_path = resolve_project_path(config_path)
    config = load_yaml_file(resolved_config_path)
    pipelines = config.get("pipelines", {})
    if not isinstance(pipelines, dict):
        raise ValueError("transformations.yaml must define a 'pipelines' mapping.")

    pipeline = pipelines.get(pipeline_name)
    if not isinstance(pipeline, dict):
        raise ValueError(f"Pipeline '{pipeline_name}' was not found in {resolved_config_path}.")

    return pipeline, resolved_config_path


def resolve_local_or_remote(value: str | Path) -> str:
    text_value = str(value)
    if is_s3_uri(text_value):
        return text_value
    return str(resolve_project_path(text_value))


def validate_output_columns(actual_columns: list[str], required_columns: list[str]) -> None:
    if actual_columns != required_columns:
        raise ValueError(
            "The transformed dataset does not match the declared contract. "
            f"Expected {required_columns}, got {actual_columns}."
        )


def run_with_duckdb(source_uri: str, sql_text: str, target_uri: str) -> list[str]:
    if is_s3_uri(source_uri) or is_s3_uri(target_uri):
        raise RuntimeError("DuckDB local mode only supports local filesystem paths.")

    import duckdb

    target_path = ensure_parent_dir(target_uri)
    safe_source_uri = source_uri.replace("'", "''")

    connection = duckdb.connect()
    try:
        connection.execute(
            "CREATE OR REPLACE VIEW bronze_hr_attrition AS "
            f"SELECT * FROM read_csv_auto('{safe_source_uri}', HEADER=TRUE);",
        )
        relation = connection.sql(sql_text)
        relation.write_parquet(str(target_path), compression="zstd")
        return list(relation.columns)
    finally:
        connection.close()


def run_with_spark(source_uri: str, sql_text: str, target_uri: str) -> list[str]:
    from pyspark.sql import SparkSession

    spark = SparkSession.builder.appName("hr-bronze-to-silver").getOrCreate()
    try:
        dataframe = (
            spark.read.option("header", True)
            .option("inferSchema", True)
            .csv(source_uri)
        )
        dataframe.createOrReplaceTempView("bronze_hr_attrition")
        result = spark.sql(sql_text)
        result.write.mode("overwrite").parquet(target_uri)
        return list(result.columns)
    finally:
        spark.stop()


def run_pipeline(
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    pipeline_name: str = DEFAULT_PIPELINE_NAME,
    source_override: str | Path | None = None,
    target_override: str | Path | None = None,
    query_override: str | Path | None = None,
    contract_override: str | Path | None = None,
) -> dict[str, Any]:
    pipeline, resolved_config_path = load_pipeline_definition(config_path, pipeline_name)

    artifacts = pipeline.get("artifacts", {})
    source_config = pipeline.get("source", {})
    target_config = pipeline.get("target", {})
    dataset_name = str(target_config.get("dataset_name", "silver_hr_attrition"))

    if not isinstance(artifacts, dict) or not isinstance(source_config, dict) or not isinstance(target_config, dict):
        raise ValueError("Pipeline source, target, and artifacts definitions must be mappings.")

    query_path = query_override or artifacts.get("query_path")
    contract_path = contract_override or artifacts.get("contract_path")
    source_uri = source_override or source_config.get("local_path")
    target_uri = target_override or target_config.get("local_path")

    if not query_path or not contract_path or not source_uri or not target_uri:
        raise ValueError("Pipeline definition is missing query, contract, source, or target settings.")

    resolved_query_path = resolve_project_path(query_path)
    resolved_contract_path = resolve_project_path(contract_path)
    resolved_source_uri = resolve_local_or_remote(source_uri)
    resolved_target_uri = resolve_local_or_remote(target_uri)

    sql_text = load_sql_file(resolved_query_path)
    contract = load_contract(resolved_contract_path)
    required_columns = expected_columns(contract, dataset_name)

    try:
        import pyspark  # noqa: F401
    except ImportError:
        engine = "duckdb"
        actual_columns = run_with_duckdb(resolved_source_uri, sql_text, resolved_target_uri)
    else:
        engine = "spark"
        actual_columns = run_with_spark(resolved_source_uri, sql_text, resolved_target_uri)

    validate_output_columns(actual_columns, required_columns)

    return {
        "config_path": str(resolved_config_path),
        "query_path": str(resolved_query_path),
        "contract_path": str(resolved_contract_path),
        "source_uri": resolved_source_uri,
        "target_uri": resolved_target_uri,
        "engine": engine,
        "columns": actual_columns,
    }


def main() -> None:
    args = parse_args()
    result = run_pipeline(
        config_path=args.config,
        pipeline_name=args.pipeline,
        source_override=args.source,
        target_override=args.target,
        query_override=args.query,
        contract_override=args.contract,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
