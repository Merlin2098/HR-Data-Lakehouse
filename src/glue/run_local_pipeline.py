from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from uuid import uuid4

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.common.pipeline_runtime import default_processed_at_utc
from src.glue.bronze_to_silver import run_pipeline as run_bronze_to_silver
from src.glue.gold_to_bi_export import run_pipeline as run_gold_to_bi_export
from src.glue.silver_to_gold import run_pipeline as run_silver_to_gold


DEFAULT_CONFIG_PATH = "src/configs/transformations.yaml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the full local HR pipeline from bronze through the BI export.")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to the pipeline YAML file.")
    parser.add_argument("--source", help="Optional override for the bronze CSV path.")
    parser.add_argument("--silver-target", help="Optional override for the silver parquet path.")
    parser.add_argument("--gold-target", help="Optional override for the gold output base directory.")
    parser.add_argument("--bi-target", help="Optional override for the BI export parquet snapshot path.")
    parser.add_argument("--silver-query", help="Optional override for the bronze-to-silver SQL file.")
    parser.add_argument("--gold-query", help="Optional override for the silver-to-gold SQL file.")
    parser.add_argument("--bi-query", help="Optional override for the gold-to-BI SQL file.")
    parser.add_argument("--contract", help="Optional override for the shared contract YAML path.")
    parser.add_argument(
        "--ingestion-date",
        help="Optional ingestion date in ISO format (YYYY-MM-DD). Defaults to the current local date.",
    )
    return parser.parse_args()


def run_pipeline(
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    *,
    source_override: str | Path | None = None,
    silver_target_override: str | Path | None = None,
    gold_target_override: str | Path | None = None,
    bi_target_override: str | Path | None = None,
    silver_query_override: str | Path | None = None,
    gold_query_override: str | Path | None = None,
    bi_query_override: str | Path | None = None,
    contract_override: str | Path | None = None,
    ingestion_date_value: str | None = None,
) -> dict[str, object]:
    run_id = uuid4().hex
    processed_at_utc = default_processed_at_utc()
    silver_result = run_bronze_to_silver(
        config_path=config_path,
        source_override=source_override,
        target_override=silver_target_override,
        query_override=silver_query_override,
        contract_override=contract_override,
        run_id=run_id,
        processed_at_utc=processed_at_utc,
    )
    gold_result = run_silver_to_gold(
        config_path=config_path,
        source_override=silver_result["target_uri"],
        target_override=gold_target_override,
        query_override=gold_query_override,
        contract_override=contract_override,
        ingestion_date_value=ingestion_date_value,
        run_id=run_id,
        processed_at_utc=processed_at_utc,
    )
    bi_export_result = run_gold_to_bi_export(
        config_path=config_path,
        source_override=gold_result["target_uri"],
        target_override=bi_target_override,
        query_override=bi_query_override,
        contract_override=contract_override,
        business_date_value=ingestion_date_value,
        run_id=run_id,
        processed_at_utc=processed_at_utc,
    )

    return {
        "engine": "duckdb",
        "silver": silver_result,
        "gold": gold_result,
        "bi_export": bi_export_result,
    }


def main() -> None:
    args = parse_args()
    result = run_pipeline(
        config_path=args.config,
        source_override=args.source,
        silver_target_override=args.silver_target,
        gold_target_override=args.gold_target,
        bi_target_override=args.bi_target,
        silver_query_override=args.silver_query,
        gold_query_override=args.gold_query,
        bi_query_override=args.bi_query,
        contract_override=args.contract,
        ingestion_date_value=args.ingestion_date,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
