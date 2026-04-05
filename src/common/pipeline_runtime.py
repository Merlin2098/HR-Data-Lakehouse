from __future__ import annotations

import re
import shutil
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from string import Formatter
from typing import Any

from src.common.config_loader import load_yaml_file
from src.common.contract_loader import column_definitions, dataset_contract, expected_columns, load_contract
from src.common.project_paths import ensure_parent_dir, resolve_project_path
from src.common.query_loader import load_sql_file
from src.common.resource_loader import list_resource_objects, resolve_resource_reference, resource_exists
from src.common.s3_utils import build_s3_uri, is_s3_uri


TEMPLATE_PATTERN = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def get_duckdb_module():
    try:
        import duckdb
    except ImportError as exc:
        raise RuntimeError("duckdb is required for local duckdb execution.") from exc
    return duckdb


@dataclass(frozen=True)
class PipelineContext:
    pipeline_name: str
    config_ref: str
    pipeline_definition: dict[str, Any]
    query_ref: str
    contract_ref: str
    source_uri: str
    target_uri: str
    source_format: str
    source_view_name: str
    target_dataset_name: str
    output_compression: str
    write_mode: str
    target_layout: str
    partition_style: str
    execution_mode: str
    engine: str


def load_pipeline_context(
    config_path: str | Path,
    pipeline_name: str,
    *,
    execution_mode: str | None = None,
    engine: str | None = None,
    source_override: str | Path | None = None,
    target_override: str | Path | None = None,
    query_override: str | Path | None = None,
    contract_override: str | Path | None = None,
    runtime_variables: dict[str, Any] | None = None,
) -> PipelineContext:
    resolved_config_ref = resolve_resource_reference(config_path)
    config = load_yaml_file(resolved_config_ref)
    pipelines = config.get("pipelines", {})
    if not isinstance(pipelines, dict):
        raise ValueError("transformations.yaml must define a 'pipelines' mapping.")

    pipeline_definition = pipelines.get(pipeline_name)
    if not isinstance(pipeline_definition, dict):
        raise ValueError(f"Pipeline '{pipeline_name}' was not found in {resolved_config_ref}.")

    defaults = config.get("defaults", {})
    if not isinstance(defaults, dict):
        defaults = {}

    resolved_execution_mode = str(execution_mode or defaults.get("execution_mode", "local"))
    engines = defaults.get("engines", {})
    if not isinstance(engines, dict):
        engines = {}

    resolved_engine = str(
        engine
        or engines.get(resolved_execution_mode)
        or ("duckdb" if resolved_execution_mode == "local" else "glue_spark")
    )

    runtime_values = collect_runtime_values(defaults, runtime_variables)
    artifacts = _ensure_mapping(pipeline_definition.get("artifacts"), "Pipeline artifacts")
    source_config = _ensure_mapping(pipeline_definition.get("source"), "Pipeline source")
    target_config = _ensure_mapping(pipeline_definition.get("target"), "Pipeline target")

    query_ref = render_reference(
        query_override or choose_mode_value(artifacts, resolved_execution_mode, "query"),
        runtime_values,
    )
    contract_ref = render_reference(
        contract_override or choose_mode_value(artifacts, resolved_execution_mode, "contract"),
        runtime_values,
    )
    source_uri = render_reference(
        source_override or choose_mode_value(source_config, resolved_execution_mode, "source"),
        runtime_values,
    )
    target_uri = render_reference(
        target_override or choose_mode_value(target_config, resolved_execution_mode, "target"),
        runtime_values,
    )

    if not query_ref or not contract_ref or not source_uri or not target_uri:
        raise ValueError("Pipeline definition is missing query, contract, source, or target settings.")

    return PipelineContext(
        pipeline_name=pipeline_name,
        config_ref=resolved_config_ref,
        pipeline_definition=pipeline_definition,
        query_ref=resolve_resource_reference(query_ref),
        contract_ref=resolve_resource_reference(contract_ref),
        source_uri=resolve_resource_reference(source_uri),
        target_uri=resolve_resource_reference(target_uri),
        source_format=str(source_config.get("format", "parquet")),
        source_view_name=str(source_config.get("view_name", source_config.get("dataset_name", "pipeline_source"))),
        target_dataset_name=str(target_config.get("dataset_name", pipeline_name)),
        output_compression=str(target_config.get("compression", "snappy")),
        write_mode=str(target_config.get("write_mode", "overwrite_full")),
        target_layout=str(target_config.get("layout", "dataset")),
        partition_style=str(target_config.get("partition_style", "hive")),
        execution_mode=resolved_execution_mode,
        engine=resolved_engine,
    )


def _ensure_mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a mapping.")
    return value


def collect_runtime_values(defaults: dict[str, Any], overrides: dict[str, Any] | None) -> dict[str, Any]:
    runtime_values = defaults.get("runtime_variables", {})
    if not isinstance(runtime_values, dict):
        runtime_values = {}
    merged = {key: str(value) for key, value in runtime_values.items()}
    if overrides:
        merged.update({key: str(value) for key, value in overrides.items() if value is not None})
    return merged


def choose_mode_value(config: dict[str, Any], execution_mode: str, value_kind: str) -> str:
    mode_fields = {
        "local": {
            "source": ["local_uri", "local_path"],
            "target": ["local_uri", "local_path"],
            "query": ["query_path"],
            "contract": ["contract_path"],
        },
        "aws": {
            "source": ["source_uri", "s3_uri"],
            "target": ["target_uri", "s3_uri"],
            "query": ["query_uri"],
            "contract": ["contract_uri"],
        },
    }

    candidates = mode_fields.get(execution_mode, {}).get(value_kind, [])
    for candidate in candidates:
        if candidate in config and config[candidate]:
            return str(config[candidate])

    for candidate in ("uri", "path"):
        if candidate in config and config[candidate]:
            return str(config[candidate])

    raise ValueError(f"No '{value_kind}' reference was defined for execution mode '{execution_mode}'.")


def render_reference(value: str | Path, runtime_values: dict[str, Any]) -> str:
    text_value = str(value)
    if not runtime_values or "{" not in text_value:
        return text_value

    formatter = Formatter()
    field_names = [field_name for _, field_name, _, _ in formatter.parse(text_value) if field_name]
    if not field_names:
        return text_value

    missing = [field_name for field_name in field_names if field_name not in runtime_values]
    if missing:
        raise ValueError(f"Missing runtime values for placeholders: {', '.join(sorted(set(missing)))}")
    return text_value.format_map(runtime_values)


def parse_ingestion_date(ingestion_date_value: str | None) -> date:
    if not ingestion_date_value:
        return datetime.now().date()

    normalized = ingestion_date_value.strip()
    if "T" in normalized:
        normalized = normalized.split("T", 1)[0]
    elif " " in normalized:
        normalized = normalized.split(" ", 1)[0]
    return date.fromisoformat(normalized)


def default_run_id() -> str:
    return uuid.uuid4().hex


def default_processed_at_utc() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0).isoformat(sep=" ")


def source_file_name(source_uri: str) -> str:
    if is_s3_uri(source_uri):
        normalized_source = source_uri.rstrip("/")
        return normalized_source.rsplit("/", 1)[-1]
    return Path(source_uri).name


def expected_dataset_columns(contract_ref: str | Path, dataset_name: str) -> list[str]:
    contract = load_contract(contract_ref)
    return expected_columns(contract, dataset_name)


def load_rendered_sql(query_ref: str | Path, variables: dict[str, Any] | None = None) -> str:
    sql_text = load_sql_file(query_ref)
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
    return run_pipeline(
        context,
        source_format="csv",
        sql_variables=sql_variables,
        partition_by=[],
        partition_values={},
        quality_context=quality_context,
    )


def run_parquet_to_parquet_pipeline(
    context: PipelineContext,
    *,
    sql_variables: dict[str, Any] | None = None,
    partition_by: list[str] | None = None,
    partition_values: dict[str, Any] | None = None,
    quality_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_partition_by = partition_by or []
    normalized_partition_values = partition_values or {}
    return run_pipeline(
        context,
        source_format="parquet",
        sql_variables=sql_variables,
        partition_by=normalized_partition_by,
        partition_values=normalized_partition_values,
        quality_context=quality_context,
    )


def run_pipeline(
    context: PipelineContext,
    *,
    source_format: str,
    sql_variables: dict[str, Any] | None,
    partition_by: list[str],
    partition_values: dict[str, Any],
    quality_context: dict[str, Any] | None,
) -> dict[str, Any]:
    quality_metadata = quality_context or {}
    if context.engine == "duckdb":
        actual_columns, written_target = run_duckdb_pipeline(
            context,
            source_format=source_format,
            sql_variables=sql_variables,
            partition_by=partition_by,
            partition_values=partition_values,
            quality_context=quality_metadata,
        )
    elif context.engine == "glue_spark":
        actual_columns, written_target = run_spark_pipeline(
            context,
            source_format=source_format,
            sql_variables=sql_variables,
            partition_by=partition_by,
            quality_context=quality_metadata,
        )
    else:
        raise ValueError(f"Unsupported execution engine '{context.engine}'.")

    return {
        "pipeline_name": context.pipeline_name,
        "config_ref": context.config_ref,
        "query_ref": context.query_ref,
        "contract_ref": context.contract_ref,
        "source_uri": context.source_uri,
        "target_uri": written_target,
        "engine": context.engine,
        "execution_mode": context.execution_mode,
        "columns": actual_columns,
        "partition_by": partition_by,
    }


def run_duckdb_pipeline(
    context: PipelineContext,
    *,
    source_format: str,
    sql_variables: dict[str, Any] | None,
    partition_by: list[str],
    partition_values: dict[str, Any],
    quality_context: dict[str, Any],
) -> tuple[list[str], str]:
    duckdb = get_duckdb_module()
    if is_s3_uri(context.source_uri) or is_s3_uri(context.target_uri):
        raise RuntimeError("DuckDB local execution only supports filesystem paths.")

    sql_text = load_rendered_sql(context.query_ref, sql_variables)
    contract = load_contract(context.contract_ref)
    required_columns = expected_columns(contract, context.target_dataset_name)
    dataset_meta = dataset_contract(contract, context.target_dataset_name)

    connection = duckdb.connect()
    try:
        if source_format == "csv":
            source_path = escape_sql_string(context.source_uri)
            connection.execute(
                f"CREATE OR REPLACE VIEW {context.source_view_name} AS "
                f"SELECT * FROM read_csv_auto('{source_path}', HEADER=TRUE, ALL_VARCHAR=TRUE);"
            )
        else:
            source_relation = connection.read_parquet(
                parquet_input_paths(context.source_uri),
                hive_partitioning=context.partition_style == "hive",
            )
            source_relation.create_view(context.source_view_name, replace=True)

        result_view_name = f"{context.pipeline_name}_result"
        connection.execute(f"CREATE OR REPLACE TEMP VIEW {result_view_name} AS {sql_text}")
        actual_columns = [row[0] for row in connection.execute(f"DESCRIBE {result_view_name}").fetchall()]
        validate_output_columns(actual_columns, required_columns)
        validate_quality_checks_duckdb(connection, result_view_name, dataset_meta, actual_columns, quality_context)
        written_target = materialize_duckdb_result(
            connection,
            result_view_name,
            context,
            partition_by=partition_by,
            partition_values=partition_values,
        )
        ensure_materialized_output(
            context,
            partition_by=partition_by,
            partition_values=partition_values,
        )
    finally:
        connection.close()

    return actual_columns, written_target


def run_spark_pipeline(
    context: PipelineContext,
    *,
    source_format: str,
    sql_variables: dict[str, Any] | None,
    partition_by: list[str],
    quality_context: dict[str, Any],
) -> tuple[list[str], str]:
    sql_text = load_rendered_sql(context.query_ref, sql_variables)
    contract = load_contract(context.contract_ref)
    required_columns = expected_columns(contract, context.target_dataset_name)
    dataset_meta = dataset_contract(contract, context.target_dataset_name)
    spark = get_spark_session(context.pipeline_name)

    if source_format == "csv":
        source_df = (
            spark.read.option("header", "true")
            .option("inferSchema", "false")
            .csv(context.source_uri)
        )
    else:
        source_df = spark.read.parquet(context.source_uri)

    source_df.createOrReplaceTempView(context.source_view_name)
    result_df = spark.sql(sql_text)
    actual_columns = result_df.columns
    validate_output_columns(actual_columns, required_columns)
    validate_quality_checks_spark(result_df, dataset_meta, quality_context)
    written_target = materialize_spark_result(result_df, context, partition_by=partition_by)
    ensure_materialized_output(context, partition_by=partition_by, partition_values=quality_context)
    return actual_columns, written_target


def get_spark_session(app_name: str):  # pragma: no cover - exercised in AWS runtime
    try:
        from pyspark.sql import SparkSession
    except ImportError as exc:
        raise RuntimeError("pyspark is required for glue_spark execution.") from exc

    spark = SparkSession.builder.appName(app_name).getOrCreate()
    spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")
    return spark


def parquet_input_paths(path_value: str | Path) -> str | list[str]:
    path = resolve_project_path(path_value)
    if path.is_dir():
        parquet_files = sorted(path.rglob("*.parquet"))
        if not parquet_files:
            raise FileNotFoundError(f"No Parquet files were found under {path}.")
        return [str(parquet_file) for parquet_file in parquet_files]
    return str(path)


def materialize_duckdb_result(
    connection: duckdb.DuckDBPyConnection,
    result_view_name: str,
    context: PipelineContext,
    *,
    partition_by: list[str],
    partition_values: dict[str, Any],
) -> str:
    if partition_by:
        return materialize_duckdb_partitioned_result(
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


def materialize_duckdb_partitioned_result(
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
        staged_partition_path = build_partition_location(staging_root, partition_by, partition_values, context.partition_style)
        final_partition_path = build_partition_location(target_root, partition_by, partition_values, context.partition_style)
        if final_partition_path.exists():
            shutil.rmtree(final_partition_path)
        final_partition_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staged_partition_path), str(final_partition_path))
    finally:
        if staging_root.exists():
            shutil.rmtree(staging_root)
    return str(target_root)


def materialize_spark_result(result_df, context: PipelineContext, *, partition_by: list[str]) -> str:  # pragma: no cover - exercised in AWS runtime
    writer = result_df.write.mode("overwrite").option("compression", context.output_compression)
    if partition_by:
        writer.partitionBy(*partition_by).parquet(context.target_uri)
    else:
        writer.parquet(context.target_uri)
    return context.target_uri


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
    partition_dir = build_partition_location(path, partition_by, partition_values, partition_style)
    if partition_dir.exists():
        shutil.rmtree(partition_dir)
    return path


def build_partition_location(
    root: str | Path,
    partition_by: list[str],
    partition_values: dict[str, Any],
    partition_style: str,
) -> Any:
    current_value: Any = root
    for partition_name in partition_by:
        if partition_name not in partition_values:
            raise ValueError(f"Missing partition value for '{partition_name}'.")
        partition_value = str(partition_values[partition_name])

        if isinstance(current_value, Path):
            if partition_style == "hive":
                current_value = current_value / f"{partition_name}={partition_value}"
            elif partition_style == "numeric":
                current_value = current_value / partition_value
            else:
                raise ValueError(f"Unsupported partition style '{partition_style}'.")
            continue

        current_text = str(current_value).rstrip("/")
        next_segment = f"{partition_name}={partition_value}" if partition_style == "hive" else partition_value
        current_value = f"{current_text}/{next_segment}"

    return current_value


def escape_sql_string(value: str) -> str:
    return value.replace("'", "''")


def ensure_materialized_output(
    context: PipelineContext,
    *,
    partition_by: list[str],
    partition_values: dict[str, Any],
) -> None:
    if partition_by:
        partition_location = build_partition_location(context.target_uri, partition_by, partition_values, context.partition_style)
        s3_partition_prefix = is_s3_uri(str(partition_location))
        if not resource_exists(partition_location, treat_as_prefix=s3_partition_prefix):
            raise FileNotFoundError(f"Expected partition output was not created: {partition_location}")
        if not list_resource_objects(partition_location, treat_as_prefix=s3_partition_prefix):
            raise FileNotFoundError(f"No materialized files were found under {partition_location}")
        return

    if not resource_exists(context.target_uri):
        raise FileNotFoundError(f"Expected output was not created: {context.target_uri}")

    materialized_files = list_resource_objects(context.target_uri)
    if not materialized_files:
        raise FileNotFoundError(f"No materialized files were found under {context.target_uri}")


def validate_quality_checks_duckdb(
    connection: duckdb.DuckDBPyConnection,
    view_name: str,
    dataset_meta: dict[str, Any],
    actual_columns: list[str],
    quality_context: dict[str, Any],
) -> None:
    available_columns = set(actual_columns)
    validate_contract_quality(
        available_columns,
        dataset_meta,
        non_null_check=lambda column_name: count_duckdb_rows(connection, view_name, f"{column_name} IS NULL"),
        duplicate_check=lambda key_columns: count_duckdb_duplicates(connection, view_name, key_columns),
        domain_check=lambda column_name, allowed_values: count_duckdb_domain_violations(connection, view_name, column_name, allowed_values),
        range_check=lambda column_name, minimum_value, maximum_value: count_duckdb_range_violations(connection, view_name, column_name, minimum_value, maximum_value),
    )
    validate_partition_consistency_duckdb(connection, view_name, available_columns, quality_context)


def count_duckdb_rows(connection: duckdb.DuckDBPyConnection, view_name: str, predicate: str) -> int:
    return int(connection.execute(f"SELECT COUNT(*) FROM {view_name} WHERE {predicate}").fetchone()[0])


def count_duckdb_duplicates(connection: duckdb.DuckDBPyConnection, view_name: str, key_columns: list[str]) -> int:
    group_by = ", ".join(key_columns)
    predicate = " AND ".join(f"{column_name} IS NOT NULL" for column_name in key_columns)
    query = (
        "SELECT COUNT(*) FROM ("
        f"SELECT {group_by}, COUNT(*) AS row_count "
        f"FROM {view_name} WHERE {predicate} GROUP BY {group_by} HAVING COUNT(*) > 1"
        ") duplicate_rows"
    )
    return int(connection.execute(query).fetchone()[0])


def count_duckdb_domain_violations(
    connection: duckdb.DuckDBPyConnection,
    view_name: str,
    column_name: str,
    allowed_values: list[Any],
) -> int:
    allowed_literal = ", ".join(sql_string_literal(str(value)) for value in allowed_values)
    query = (
        "SELECT COUNT(*) "
        f"FROM {view_name} "
        f"WHERE {column_name} IS NOT NULL AND CAST({column_name} AS VARCHAR) NOT IN ({allowed_literal})"
    )
    return int(connection.execute(query).fetchone()[0])


def count_duckdb_range_violations(
    connection: duckdb.DuckDBPyConnection,
    view_name: str,
    column_name: str,
    minimum_value: Any | None,
    maximum_value: Any | None,
) -> int:
    predicates: list[str] = []
    if minimum_value is not None:
        predicates.append(f"{column_name} < {minimum_value}")
    if maximum_value is not None:
        predicates.append(f"{column_name} > {maximum_value}")
    if not predicates:
        return 0

    query = (
        "SELECT COUNT(*) "
        f"FROM {view_name} "
        f"WHERE {column_name} IS NOT NULL AND ({' OR '.join(predicates)})"
    )
    return int(connection.execute(query).fetchone()[0])


def validate_quality_checks_spark(result_df, dataset_meta: dict[str, Any], quality_context: dict[str, Any]) -> None:  # pragma: no cover - exercised in AWS runtime
    from pyspark.sql import functions as F

    available_columns = set(result_df.columns)
    validate_contract_quality(
        available_columns,
        dataset_meta,
        non_null_check=lambda column_name: int(result_df.filter(F.col(column_name).isNull()).count()),
        duplicate_check=lambda key_columns: int(
            result_df.where(" AND ".join(f"{column_name} IS NOT NULL" for column_name in key_columns))
            .groupBy(*key_columns)
            .count()
            .filter(F.col("count") > 1)
            .count()
        ),
        domain_check=lambda column_name, allowed_values: int(
            result_df.filter(
                F.col(column_name).isNotNull() & (~F.col(column_name).cast("string").isin([str(value) for value in allowed_values]))
            ).count()
        ),
        range_check=lambda column_name, minimum_value, maximum_value: int(
            result_df.filter(
                F.col(column_name).isNotNull()
                & (
                    ((F.col(column_name) < minimum_value) if minimum_value is not None else F.lit(False))
                    | ((F.col(column_name) > maximum_value) if maximum_value is not None else F.lit(False))
                )
            ).count()
        ),
    )

    if "ingestion_date" in available_columns and quality_context.get("ingestion_date"):
        invalid_count = result_df.filter(
            F.col("ingestion_date").cast("string") != F.lit(str(quality_context["ingestion_date"]))
        ).count()
        if invalid_count:
            raise ValueError("Partition columns are not coherent with the configured ingestion date.")

    for partition_name in dataset_meta.get("partition_columns", []):
        if partition_name not in available_columns or partition_name not in quality_context:
            continue
        invalid_count = result_df.filter(F.col(partition_name) != F.lit(int(quality_context[partition_name]))).count()
        if invalid_count:
            raise ValueError(f"Partition column '{partition_name}' is not coherent with the configured business date.")


def validate_contract_quality(
    available_columns: set[str],
    dataset_meta: dict[str, Any],
    *,
    non_null_check,
    duplicate_check,
    domain_check,
    range_check,
) -> None:
    primary_key = dataset_meta.get("primary_key", [])
    if isinstance(primary_key, list) and primary_key:
        if duplicate_check(primary_key):
            raise ValueError(f"Primary key violation detected for columns {primary_key}.")

    for column_meta in column_definitions({"datasets": {"current": dataset_meta}}, "current"):
        column_name = str(column_meta.get("name"))
        if column_name not in available_columns:
            continue

        nullable = bool(column_meta.get("nullable", True))
        if not nullable and non_null_check(column_name):
            raise ValueError(f"Column '{column_name}' contains null values.")

        allowed_values = column_meta.get("allowed_values")
        if isinstance(allowed_values, list) and domain_check(column_name, allowed_values):
            raise ValueError(f"Column '{column_name}' contains values outside the allowed domain.")

        minimum_value = column_meta.get("min_value")
        maximum_value = column_meta.get("max_value")
        if (minimum_value is not None or maximum_value is not None) and range_check(column_name, minimum_value, maximum_value):
            raise ValueError(f"Column '{column_name}' contains values outside the configured range.")


def validate_partition_consistency_duckdb(
    connection: duckdb.DuckDBPyConnection,
    view_name: str,
    available_columns: set[str],
    quality_context: dict[str, Any],
) -> None:
    predicates: list[str] = []
    if "ingestion_date" in available_columns and quality_context.get("ingestion_date"):
        predicates.append(
            f"CAST(ingestion_date AS DATE) <> CAST({sql_string_literal(str(quality_context['ingestion_date']))} AS DATE)"
        )

    for partition_name in ("year", "month", "day"):
        if partition_name in available_columns and partition_name in quality_context:
            predicates.append(f"{partition_name} <> {int(quality_context[partition_name])}")

    if not predicates:
        return

    invalid_count = count_duckdb_rows(connection, view_name, " OR ".join(predicates))
    if invalid_count:
        raise ValueError("Partition columns are not coherent with the configured ingestion date.")


def build_runtime_variables(
    *,
    business_date: date | None = None,
    run_id: str | None = None,
    processed_at_utc: str | None = None,
    source_file: str | None = None,
    source_filename: str | None = None,
    extra_variables: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_run_id = run_id or default_run_id()
    resolved_processed_at_utc = processed_at_utc or default_processed_at_utc()
    runtime_variables: dict[str, Any] = {
        "run_id": resolved_run_id,
        "processed_at_utc": resolved_processed_at_utc,
    }

    if business_date is not None:
        runtime_variables.update(
            {
                "business_date": business_date.isoformat(),
                "ingestion_date": business_date.isoformat(),
                "year": business_date.year,
                "month": business_date.month,
                "day": business_date.day,
            }
        )

    if source_file is not None:
        runtime_variables["source_file"] = source_file
    if source_filename is not None:
        runtime_variables["source_filename"] = source_filename
    if extra_variables:
        runtime_variables.update({key: value for key, value in extra_variables.items() if value is not None})
    return runtime_variables


def build_quality_context(runtime_variables: dict[str, Any]) -> dict[str, Any]:
    return {
        key: runtime_variables[key]
        for key in ("ingestion_date", "year", "month", "day", "source_file", "run_id", "processed_at_utc")
        if key in runtime_variables
    }


def build_s3_dataset_uri(bucket: str, key_prefix: str) -> str:
    normalized_prefix = key_prefix.strip("/")
    return build_s3_uri(bucket, f"{normalized_prefix}/")
