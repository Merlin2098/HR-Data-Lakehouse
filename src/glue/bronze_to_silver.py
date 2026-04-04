from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _bootstrap_src_package() -> None:
    bootstrap_script_path = Path(__file__).resolve()
    for candidate in (bootstrap_script_path.parent, *bootstrap_script_path.parents):
        if (candidate / "src" / "__init__.py").exists():
            candidate_str = str(candidate)
            if candidate_str not in sys.path:
                sys.path.append(candidate_str)
            return


try:
    from src.common.project_paths import ensure_src_package_importable
except ModuleNotFoundError:
    _bootstrap_src_package()
    from src.common.project_paths import ensure_src_package_importable

ensure_src_package_importable(__file__)

from src.common.pipeline_runtime import (
    build_quality_context,
    build_runtime_variables,
    default_processed_at_utc,
    default_run_id,
    load_pipeline_context,
    parse_ingestion_date,
    run_csv_to_parquet_pipeline,
    source_file_name,
    sql_string_literal,
)
from src.common.s3_utils import build_s3_uri, is_s3_uri


DEFAULT_CONFIG_PATH = "src/configs/transformations.yaml"
DEFAULT_PIPELINE_NAME = "bronze_to_silver"


def normalize_source_filename(value: str) -> str:
    return Path(str(value).rstrip("/")).name


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the bronze-to-silver HR pipeline.")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Local path or S3 URI to the pipeline YAML file.")
    parser.add_argument("--pipeline", default=DEFAULT_PIPELINE_NAME, help="Pipeline name inside the YAML config.")
    parser.add_argument("--query", help="Optional override for the SQL file path or URI.")
    parser.add_argument("--contract", help="Optional override for the contract YAML path or URI.")
    parser.add_argument("--source", help="Optional override for the source CSV path or URI.")
    parser.add_argument("--target", help="Optional override for the target parquet path or URI.")
    parser.add_argument("--config-uri", dest="config_uri", help="Alias for --config when running in AWS.")
    parser.add_argument("--query-uri", dest="query_uri", help="Alias for --query when running in AWS.")
    parser.add_argument("--contracts-uri", dest="contract_uri", help="Alias for --contract when running in AWS.")
    parser.add_argument("--source-uri", dest="source_uri", help="Alias for --source when running in AWS.")
    parser.add_argument("--target-uri", dest="target_uri", help="Alias for --target when running in AWS.")
    parser.add_argument("--execution-mode", choices=["local", "aws"], help="Execution mode override.")
    parser.add_argument("--engine", choices=["duckdb", "glue_spark"], help="Execution engine override.")
    parser.add_argument("--business-date", help="Optional business date in ISO format. Used by AWS raw bronze paths.")
    parser.add_argument("--source-filename", help="Expected raw source filename for AWS bronze ingestion.")
    parser.add_argument("--run-id", help="Explicit run identifier.")
    parser.add_argument("--processed-at-utc", help="Explicit UTC processing timestamp.")
    return parser.parse_args()


def resolve_bronze_source_uri(source_uri: str, ingestion_date_value: str | None, source_filename: str) -> str:
    if not source_uri.endswith("/"):
        return source_uri

    ingestion_date = parse_ingestion_date(ingestion_date_value).isoformat()
    if is_s3_uri(source_uri):
        without_suffix = source_uri.rstrip("/")
        bucket_and_prefix = without_suffix.removeprefix("s3://")
        bucket, _, prefix = bucket_and_prefix.partition("/")
        return build_s3_uri(bucket, f"{prefix}/ingestion_date={ingestion_date}/{source_filename}")

    return str(Path(source_uri) / f"ingestion_date={ingestion_date}" / source_filename)


def run_pipeline(
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    pipeline_name: str = DEFAULT_PIPELINE_NAME,
    source_override: str | Path | None = None,
    target_override: str | Path | None = None,
    query_override: str | Path | None = None,
    contract_override: str | Path | None = None,
    execution_mode: str | None = None,
    engine: str | None = None,
    business_date_value: str | None = None,
    source_filename: str | None = None,
    run_id: str | None = None,
    processed_at_utc: str | None = None,
) -> dict[str, object]:
    runtime_variables = build_runtime_variables(
        business_date=parse_ingestion_date(business_date_value) if business_date_value else None,
        run_id=run_id,
        processed_at_utc=processed_at_utc or default_processed_at_utc(),
        source_filename=source_filename,
    )
    context = load_pipeline_context(
        config_path,
        pipeline_name,
        execution_mode=execution_mode,
        engine=engine,
        source_override=source_override,
        target_override=target_override,
        query_override=query_override,
        contract_override=contract_override,
        runtime_variables=runtime_variables,
    )

    resolved_source_filename = normalize_source_filename(
        str(source_filename or runtime_variables.get("source_filename") or source_file_name(context.source_uri))
    )
    resolved_source_uri = resolve_bronze_source_uri(context.source_uri, business_date_value, resolved_source_filename)

    if resolved_source_uri != context.source_uri:
        context = load_pipeline_context(
            config_path,
            pipeline_name,
            execution_mode=execution_mode,
            engine=engine,
            source_override=resolved_source_uri,
            target_override=target_override,
            query_override=query_override,
            contract_override=contract_override,
            runtime_variables=runtime_variables,
        )

    resolved_run_id = str(runtime_variables.get("run_id") or run_id or default_run_id())
    resolved_processed_at_utc = str(runtime_variables.get("processed_at_utc") or processed_at_utc or default_processed_at_utc())
    resolved_source_file = resolved_source_filename if context.execution_mode == "aws" else source_file_name(context.source_uri)

    execution_variables = build_runtime_variables(
        business_date=parse_ingestion_date(business_date_value) if business_date_value else None,
        run_id=resolved_run_id,
        processed_at_utc=resolved_processed_at_utc,
        source_file=resolved_source_file,
        source_filename=resolved_source_filename,
    )

    result = run_csv_to_parquet_pipeline(
        context,
        sql_variables={
            "source_file": sql_string_literal(resolved_source_file),
            "run_id": sql_string_literal(resolved_run_id),
            "processed_at_utc": sql_string_literal(resolved_processed_at_utc),
        },
        quality_context=build_quality_context(execution_variables),
    )
    result["source_file"] = resolved_source_file
    return result


def main() -> None:
    args = parse_args()
    result = run_pipeline(
        config_path=args.config_uri or args.config,
        pipeline_name=args.pipeline,
        source_override=args.source_uri or args.source,
        target_override=args.target_uri or args.target,
        query_override=args.query_uri or args.query,
        contract_override=args.contract_uri or args.contract,
        execution_mode=args.execution_mode,
        engine=args.engine,
        business_date_value=args.business_date,
        source_filename=args.source_filename,
        run_id=args.run_id,
        processed_at_utc=args.processed_at_utc,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
