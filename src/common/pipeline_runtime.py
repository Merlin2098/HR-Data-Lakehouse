from __future__ import annotations

import re
import shutil
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
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
    target_layout: str
    partition_style: str


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
    write_mode = str(target_config.get("write_mode", "overwrite_full"))
    target_layout = str(target_config.get("layout", "file"))
    partition_style = str(target_config.get("partition_style", "hive"))

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
        target_layout=target_layout,
        partition_style=partition_style,
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


def default_run_id() -> str:
    return uuid.uuid4().hex


def default_processed_at_utc() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0).isoformat(sep=" ")


def source_file_name(source_uri: str) -> str:
    if is_s3_uri(source_uri):
        return source_uri.rstrip("/").rsplit("/", 1)[-1]
    return Path(source_uri).name


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


def sql_string_literal(value: str) -> str:
    return f"'{escape_sql_string(value)}'"


def run_csv_to_parquet_pipeline(
    context: PipelineContext,
    *,
    sql_variables: dict[str, Any] | None = None,
    quality_context: dict[str, Any] | None = None,
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
            f"SELECT * FROM read_csv_auto('{source_path}', HEADER=TRUE, ALL_VARCHAR=TRUE);"
        )
        result_view_name = f"{context.pipeline_name}_result"
        connection.execute(f"CREATE OR REPLACE TEMP VIEW {result_view_name} AS {sql_text}")
        actual_columns = [row[0] for row in connection.execute(f"DESCRIBE {result_view_name}").fetchall()]
        validate_output_columns(actual_columns, required_columns)
        validate_quality_checks(
            connection,
            result_view_name,
            context.target_dataset_name,
            actual_columns,
            quality_context or {},
        )
        written_target = materialize_parquet_result(
            connection,
            result_view_name,
            context,
            partition_by=[],
            partition_values={},
        )
        ensure_materialized_output(
            context,
            partition_by=[],
            partition_values={},
        )
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
    }


def run_parquet_to_parquet_pipeline(
    context: PipelineContext,
    *,
    sql_variables: dict[str, Any] | None = None,
    partition_by: list[str] | None = None,
    partition_values: dict[str, Any] | None = None,
    quality_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if is_s3_uri(context.source_uri) or is_s3_uri(context.target_uri):
        raise RuntimeError("Local DuckDB execution only supports filesystem paths.")

    sql_text = load_rendered_sql(context.query_path, sql_variables)
    required_columns = expected_dataset_columns(context.contract_path, context.target_dataset_name)
    connection = duckdb.connect()
    try:
        source_relation = connection.read_parquet(
            parquet_input_paths(context.source_uri),
            hive_partitioning=context.partition_style == "hive",
        )
        source_relation.create_view(context.source_view_name, replace=True)
        result_view_name = f"{context.pipeline_name}_result"
        connection.execute(f"CREATE OR REPLACE TEMP VIEW {result_view_name} AS {sql_text}")
        actual_columns = [row[0] for row in connection.execute(f"DESCRIBE {result_view_name}").fetchall()]
        validate_output_columns(actual_columns, required_columns)
        normalized_partition_by = partition_by or []
        normalized_partition_values = partition_values or {}
        validate_quality_checks(
            connection,
            result_view_name,
            context.target_dataset_name,
            actual_columns,
            quality_context or {},
        )
        written_target = materialize_parquet_result(
            connection,
            result_view_name,
            context,
            partition_by=normalized_partition_by,
            partition_values=normalized_partition_values,
        )
        ensure_materialized_output(
            context,
            partition_by=normalized_partition_by,
            partition_values=normalized_partition_values,
        )
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
        "partition_by": normalized_partition_by,
    }


def parquet_input_paths(path_value: str | Path) -> str | list[str]:
    path = resolve_project_path(path_value)
    if path.is_dir():
        parquet_files = sorted(path.rglob("*.parquet"))
        if not parquet_files:
            raise FileNotFoundError(f"No Parquet files were found under {path}.")
        return [str(parquet_file) for parquet_file in parquet_files]
    return str(path)


def prepare_dataset_output_root(path_value: str | Path) -> Path:
    path = resolve_project_path(path_value)
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def prepare_partition_output_root(
    path_value: str | Path,
    *,
    write_mode: str,
    partition_by: list[str],
    partition_values: dict[str, Any],
    partition_style: str,
) -> Path:
    path = resolve_project_path(path_value)

    if write_mode == "overwrite_full":
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    if write_mode != "overwrite_partition":
        raise ValueError(f"Unsupported partitioned write mode '{write_mode}'.")

    path.mkdir(parents=True, exist_ok=True)
    partition_dir = build_partition_path(path, partition_by, partition_values, partition_style)
    if partition_dir.exists():
        shutil.rmtree(partition_dir)
    return path


def escape_sql_string(value: str) -> str:
    return value.replace("'", "''")


def materialize_parquet_result(
    connection: duckdb.DuckDBPyConnection,
    result_view_name: str,
    context: PipelineContext,
    *,
    partition_by: list[str],
    partition_values: dict[str, Any],
) -> str:
    if partition_by:
        return materialize_partitioned_parquet_result(
            connection,
            result_view_name,
            context,
            partition_by=partition_by,
            partition_values=partition_values,
        )

    if context.target_layout == "dataset":
        target_root = prepare_dataset_output_root(context.target_uri)
        target_file = target_root / "data_0.parquet"
        target_sql = escape_sql_string(str(target_file))
        connection.execute(
            "COPY "
            f"(SELECT * FROM {result_view_name}) "
            f"TO '{target_sql}' "
            f"(FORMAT PARQUET, COMPRESSION '{context.output_compression}');"
        )
        return str(target_root)

    target_file = ensure_parent_dir(context.target_uri)
    if target_file.exists():
        target_file.unlink()
    target_sql = escape_sql_string(str(target_file))
    connection.execute(
        "COPY "
        f"(SELECT * FROM {result_view_name}) "
        f"TO '{target_sql}' "
        f"(FORMAT PARQUET, COMPRESSION '{context.output_compression}');"
    )
    return str(target_file)


def materialize_partitioned_parquet_result(
    connection: duckdb.DuckDBPyConnection,
    result_view_name: str,
    context: PipelineContext,
    *,
    partition_by: list[str],
    partition_values: dict[str, Any],
) -> str:
    partition_spec = ", ".join(partition_by)

    if context.write_mode == "overwrite_full":
        target_root = prepare_partition_output_root(
            context.target_uri,
            write_mode=context.write_mode,
            partition_by=partition_by,
            partition_values=partition_values,
            partition_style=context.partition_style,
        )
        target_sql = escape_sql_string(str(target_root))
        connection.execute(
            "COPY "
            f"(SELECT * FROM {result_view_name}) "
            f"TO '{target_sql}' "
            f"(FORMAT PARQUET, PARTITION_BY ({partition_spec}), COMPRESSION '{context.output_compression}');"
        )
        return str(target_root)

    if context.write_mode != "overwrite_partition":
        raise ValueError(f"Unsupported partitioned write mode '{context.write_mode}'.")

    target_root = resolve_project_path(context.target_uri)
    target_root.mkdir(parents=True, exist_ok=True)
    staging_root = target_root / f"_stage_{uuid.uuid4().hex[:8]}"
    staging_root.mkdir(parents=True, exist_ok=True)

    try:
        target_sql = escape_sql_string(str(staging_root))
        connection.execute(
            "COPY "
            f"(SELECT * FROM {result_view_name}) "
            f"TO '{target_sql}' "
            f"(FORMAT PARQUET, PARTITION_BY ({partition_spec}), COMPRESSION '{context.output_compression}');"
        )

        staged_partition_path = build_partition_path(staging_root, partition_by, partition_values, context.partition_style)
        final_partition_path = build_partition_path(target_root, partition_by, partition_values, context.partition_style)
        if final_partition_path.exists():
            shutil.rmtree(final_partition_path)
        final_partition_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staged_partition_path), str(final_partition_path))
    finally:
        if staging_root.exists():
            shutil.rmtree(staging_root)

    return str(target_root)


def build_partition_path(
    root: Path,
    partition_by: list[str],
    partition_values: dict[str, Any],
    partition_style: str,
) -> Path:
    current_path = root
    for partition_name in partition_by:
        if partition_name not in partition_values:
            raise ValueError(f"Missing partition value for '{partition_name}'.")
        partition_value = str(partition_values[partition_name])
        if partition_style == "hive":
            current_path = current_path / f"{partition_name}={partition_value}"
        elif partition_style == "numeric":
            current_path = current_path / partition_value
        else:
            raise ValueError(f"Unsupported partition style '{partition_style}'.")
    return current_path


def ensure_materialized_output(
    context: PipelineContext,
    *,
    partition_by: list[str],
    partition_values: dict[str, Any],
) -> None:
    target_path = resolve_project_path(context.target_uri)
    if partition_by:
        parquet_dir = build_partition_path(target_path, partition_by, partition_values, context.partition_style)
        if not parquet_dir.exists():
            raise FileNotFoundError(f"Expected partition directory was not created: {parquet_dir}")
        if not list(parquet_dir.glob("*.parquet")):
            raise FileNotFoundError(f"No Parquet files were written under partition {parquet_dir}")
        return

    if context.target_layout == "dataset":
        if not target_path.exists():
            raise FileNotFoundError(f"Expected dataset directory was not created: {target_path}")
        if not list(target_path.glob("*.parquet")):
            raise FileNotFoundError(f"No Parquet files were written under dataset {target_path}")
        return

    if not target_path.exists():
        raise FileNotFoundError(f"Expected output file was not created: {target_path}")


def validate_quality_checks(
    connection: duckdb.DuckDBPyConnection,
    view_name: str,
    dataset_name: str,
    actual_columns: list[str],
    quality_context: dict[str, Any],
) -> None:
    column_set = set(actual_columns)

    if dataset_name == "silver_hr_employees":
        validate_non_null_columns(connection, view_name, ["employee_number", "source_file", "run_id", "processed_at_utc"], column_set)
        validate_numeric_ranges(
            connection,
            view_name,
            [
                "job_satisfaction",
                "environment_satisfaction",
                "relationship_satisfaction",
                "work_life_balance",
            ],
            1,
            4,
            column_set,
        )
        return

    if dataset_name == "gold_hr_attrition_fact":
        validate_non_null_columns(
            connection,
            view_name,
            ["employee_id", "ingestion_date", "source_file", "run_id", "processed_at_utc"],
            column_set,
        )
        validate_numeric_ranges(
            connection,
            view_name,
            [
                "job_satisfaction_score",
                "environment_satisfaction_score",
                "relationship_satisfaction_score",
                "work_life_balance_score",
            ],
            1,
            4,
            column_set,
        )
        validate_allowed_domain(
            connection,
            view_name,
            [
                "job_satisfaction_label",
                "environment_satisfaction_label",
                "relationship_satisfaction_label",
                "work_life_balance_label",
            ],
            {"low", "medium", "high", "very_high"},
            column_set,
        )
        validate_partition_consistency(connection, view_name, quality_context, column_set)


def validate_non_null_columns(
    connection: duckdb.DuckDBPyConnection,
    view_name: str,
    column_names: list[str],
    available_columns: set[str],
) -> None:
    for column_name in column_names:
        if column_name not in available_columns:
            continue
        null_count = connection.execute(
            f"SELECT COUNT(*) FROM {view_name} WHERE {column_name} IS NULL"
        ).fetchone()[0]
        if null_count:
            raise ValueError(f"Column '{column_name}' contains {null_count} null values in {view_name}.")


def validate_numeric_ranges(
    connection: duckdb.DuckDBPyConnection,
    view_name: str,
    column_names: list[str],
    minimum_value: int,
    maximum_value: int,
    available_columns: set[str],
) -> None:
    for column_name in column_names:
        if column_name not in available_columns:
            continue
        invalid_count = connection.execute(
            "SELECT COUNT(*) "
            f"FROM {view_name} "
            f"WHERE {column_name} IS NULL OR {column_name} < {minimum_value} OR {column_name} > {maximum_value}"
        ).fetchone()[0]
        if invalid_count:
            raise ValueError(
                f"Column '{column_name}' contains {invalid_count} values outside the range "
                f"[{minimum_value}, {maximum_value}] in {view_name}."
            )


def validate_allowed_domain(
    connection: duckdb.DuckDBPyConnection,
    view_name: str,
    column_names: list[str],
    allowed_values: set[str],
    available_columns: set[str],
) -> None:
    allowed_literal = ", ".join(sql_string_literal(value) for value in sorted(allowed_values))
    for column_name in column_names:
        if column_name not in available_columns:
            continue
        invalid_count = connection.execute(
            "SELECT COUNT(*) "
            f"FROM {view_name} "
            f"WHERE {column_name} IS NULL OR {column_name} NOT IN ({allowed_literal})"
        ).fetchone()[0]
        if invalid_count:
            raise ValueError(
                f"Column '{column_name}' contains {invalid_count} values outside the allowed label domain in {view_name}."
            )


def validate_partition_consistency(
    connection: duckdb.DuckDBPyConnection,
    view_name: str,
    quality_context: dict[str, Any],
    available_columns: set[str],
) -> None:
    expected_year = quality_context.get("year")
    expected_month = quality_context.get("month")
    expected_day = quality_context.get("day")
    expected_ingestion_date = quality_context.get("ingestion_date")

    predicates: list[str] = []
    if expected_year is not None and "year" in available_columns:
        predicates.append(f"year <> {int(expected_year)}")
    if expected_month is not None and "month" in available_columns:
        predicates.append(f"month <> {int(expected_month)}")
    if expected_day is not None and "day" in available_columns:
        predicates.append(f"day <> {int(expected_day)}")
    if expected_ingestion_date is not None and "ingestion_date" in available_columns:
        predicates.append(
            f"CAST(ingestion_date AS DATE) <> CAST({sql_string_literal(str(expected_ingestion_date))} AS DATE)"
        )

    if not predicates:
        return

    invalid_count = connection.execute(
        "SELECT COUNT(*) "
        f"FROM {view_name} "
        f"WHERE {' OR '.join(predicates)}"
    ).fetchone()[0]
    if invalid_count:
        raise ValueError(f"Partition columns are not coherent with the configured ingestion date in {view_name}.")
