from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import duckdb

from src.common.config_loader import load_yaml_file
from src.common.contract_loader import expected_columns, load_contract
from src.common.project_paths import ensure_parent_dir, resolve_project_path
from src.common.query_loader import load_sql_file
from src.common.s3_utils import is_s3_uri


TEMPLATE_PATTERN = re.compile(r"\{\{\s*(\w+)\s*\}\}")


@dataclass(frozen=True)
class PipelineContext:
    pipeline_name: str
    config_path: Path
    pipeline_definition: dict[str, Any]
    query_path: Path
    contract_path: Path
    source_uri: str
    target_uri: str
    source_view_name: str
    target_dataset_name: str
    output_compression: str
    write_mode: str


def load_pipeline_context(
    config_path: str | Path,
    pipeline_name: str,
    *,
    source_override: str | Path | None = None,
    target_override: str | Path | None = None,
    query_override: str | Path | None = None,
    contract_override: str | Path | None = None,
) -> PipelineContext:
    resolved_config_path = resolve_project_path(config_path)
    config = load_yaml_file(resolved_config_path)
    pipelines = config.get("pipelines", {})
    if not isinstance(pipelines, dict):
        raise ValueError("transformations.yaml must define a 'pipelines' mapping.")

    pipeline_definition = pipelines.get(pipeline_name)
    if not isinstance(pipeline_definition, dict):
        raise ValueError(f"Pipeline '{pipeline_name}' was not found in {resolved_config_path}.")

    artifacts = pipeline_definition.get("artifacts", {})
    source_config = pipeline_definition.get("source", {})
    target_config = pipeline_definition.get("target", {})

    if not isinstance(artifacts, dict) or not isinstance(source_config, dict) or not isinstance(target_config, dict):
        raise ValueError("Pipeline source, target, and artifacts definitions must be mappings.")

    query_path = query_override or artifacts.get("query_path")
    contract_path = contract_override or artifacts.get("contract_path")
    source_uri = source_override or source_config.get("local_path")
    target_uri = target_override or target_config.get("local_path")
    source_view_name = str(source_config.get("view_name", source_config.get("dataset_name", "pipeline_source")))
    target_dataset_name = str(target_config.get("dataset_name", pipeline_name))
    output_compression = str(target_config.get("compression", "snappy"))
    write_mode = str(target_config.get("write_mode", "overwrite"))

    if not query_path or not contract_path or not source_uri or not target_uri:
        raise ValueError("Pipeline definition is missing query, contract, source, or target settings.")

    return PipelineContext(
        pipeline_name=pipeline_name,
        config_path=resolved_config_path,
        pipeline_definition=pipeline_definition,
        query_path=resolve_project_path(query_path),
        contract_path=resolve_project_path(contract_path),
        source_uri=resolve_local_or_remote(source_uri),
        target_uri=resolve_local_or_remote(target_uri),
        source_view_name=source_view_name,
        target_dataset_name=target_dataset_name,
        output_compression=output_compression,
        write_mode=write_mode,
    )


def resolve_local_or_remote(value: str | Path) -> str:
    text_value = str(value)
    if is_s3_uri(text_value):
        return text_value
    return str(resolve_project_path(text_value))


def parse_ingestion_date(ingestion_date_value: str | None) -> date:
    if not ingestion_date_value:
        return datetime.now().date()
    return date.fromisoformat(ingestion_date_value)


def expected_dataset_columns(contract_path: str | Path, dataset_name: str) -> list[str]:
    contract = load_contract(resolve_project_path(contract_path))
    return expected_columns(contract, dataset_name)


def load_rendered_sql(query_path: str | Path, variables: dict[str, Any] | None = None) -> str:
    sql_text = load_sql_file(resolve_project_path(query_path))
    return render_sql_template(sql_text, variables or {})


def render_sql_template(sql_text: str, variables: dict[str, Any]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in variables:
            raise ValueError(f"Missing SQL template variable '{key}'.")
        return str(variables[key])

    return TEMPLATE_PATTERN.sub(replace, sql_text)


def validate_output_columns(actual_columns: list[str], required_columns: list[str]) -> None:
    if actual_columns != required_columns:
        raise ValueError(
            "The transformed dataset does not match the declared contract. "
            f"Expected {required_columns}, got {actual_columns}."
        )


def run_csv_to_parquet_pipeline(
    context: PipelineContext,
    *,
    sql_variables: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if is_s3_uri(context.source_uri) or is_s3_uri(context.target_uri):
        raise RuntimeError("Local DuckDB execution only supports filesystem paths.")

    sql_text = load_rendered_sql(context.query_path, sql_variables)
    required_columns = expected_dataset_columns(context.contract_path, context.target_dataset_name)
    source_path = escape_sql_string(context.source_uri)
    target_path = prepare_file_output_path(context.target_uri)

    connection = duckdb.connect()
    try:
        connection.execute(
            f"CREATE OR REPLACE VIEW {context.source_view_name} AS "
            f"SELECT * FROM read_csv_auto('{source_path}', HEADER=TRUE, ALL_VARCHAR=TRUE);"
        )
        relation = connection.sql(sql_text)
        actual_columns = list(relation.columns)
        validate_output_columns(actual_columns, required_columns)
        relation.write_parquet(str(target_path), compression=context.output_compression)
    finally:
        connection.close()

    return {
        "pipeline_name": context.pipeline_name,
        "config_path": str(context.config_path),
        "query_path": str(context.query_path),
        "contract_path": str(context.contract_path),
        "source_uri": context.source_uri,
        "target_uri": str(target_path),
        "engine": "duckdb",
        "columns": actual_columns,
    }


def run_parquet_to_parquet_pipeline(
    context: PipelineContext,
    *,
    sql_variables: dict[str, Any] | None = None,
    partition_by: list[str] | None = None,
) -> dict[str, Any]:
    if is_s3_uri(context.source_uri) or is_s3_uri(context.target_uri):
        raise RuntimeError("Local DuckDB execution only supports filesystem paths.")

    sql_text = load_rendered_sql(context.query_path, sql_variables)
    required_columns = expected_dataset_columns(context.contract_path, context.target_dataset_name)
    source_path = escape_sql_string(context.source_uri)

    connection = duckdb.connect()
    try:
        connection.execute(
            f"CREATE OR REPLACE VIEW {context.source_view_name} AS "
            f"SELECT * FROM read_parquet('{source_path}');"
        )
        result_view_name = f"{context.pipeline_name}_result"
        connection.execute(f"CREATE OR REPLACE TEMP VIEW {result_view_name} AS {sql_text}")
        actual_columns = [
            row[0]
            for row in connection.execute(f"DESCRIBE {result_view_name}").fetchall()
        ]
        validate_output_columns(actual_columns, required_columns)

        if partition_by:
            final_target_dir = resolve_project_path(context.target_uri)
            target_dir = prepare_directory_output_path(context.target_uri)
            partition_spec = ", ".join(partition_by)
            target_sql = escape_sql_string(str(target_dir))
            connection.execute(
                "COPY "
                f"(SELECT * FROM {result_view_name}) "
                f"TO '{target_sql}' "
                f"(FORMAT PARQUET, PARTITION_BY ({partition_spec}), COMPRESSION '{context.output_compression}');"
            )
            normalize_partition_layout(target_dir, partition_by)
            written_target = str(target_dir)
        else:
            target_file = prepare_file_output_path(context.target_uri)
            target_sql = escape_sql_string(str(target_file))
            connection.execute(
                "COPY "
                f"(SELECT * FROM {result_view_name}) "
                f"TO '{target_sql}' "
                f"(FORMAT PARQUET, COMPRESSION '{context.output_compression}');"
            )
            written_target = str(target_file)
    finally:
        connection.close()

    return {
        "pipeline_name": context.pipeline_name,
        "config_path": str(context.config_path),
        "query_path": str(context.query_path),
        "contract_path": str(context.contract_path),
        "source_uri": context.source_uri,
        "target_uri": written_target,
        "engine": "duckdb",
        "columns": actual_columns,
        "partition_by": partition_by or [],
    }


def prepare_file_output_path(path_value: str | Path) -> Path:
    path = ensure_parent_dir(path_value)
    if path.exists():
        path.unlink()
    return path


def prepare_directory_output_path(path_value: str | Path) -> Path:
    path = resolve_project_path(path_value)
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def escape_sql_string(value: str) -> str:
    return value.replace("'", "''")


def normalize_partition_layout(root: Path, partition_by: list[str]) -> None:
    current_level_dirs = [root]

    for partition_name in partition_by:
        next_level_dirs: list[Path] = []
        prefix = f"{partition_name}="

        for parent in current_level_dirs:
            for child in sorted(parent.iterdir()):
                if not child.is_dir():
                    continue

                normalized_child = child
                if child.name.startswith(prefix):
                    normalized_child = child.with_name(child.name.removeprefix(prefix))
                    child.rename(normalized_child)

                next_level_dirs.append(normalized_child)

        current_level_dirs = next_level_dirs
