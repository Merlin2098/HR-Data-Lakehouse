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

from src.common.pipeline_runtime import parse_ingestion_date
from src.common.resource_loader import copy_resource, resolve_resource_reference, resource_exists
from src.common.s3_utils import build_s3_uri, is_s3_uri, split_s3_uri


DEFAULT_CONFIG_PATH = "src/configs/transformations.yaml"
DEFAULT_PIPELINE_NAME = "landing_to_bronze"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promote the daily landing file into the bronze raw layer.")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Pipeline config reference for parity with other jobs.")
    parser.add_argument("--pipeline", default=DEFAULT_PIPELINE_NAME, help="Pipeline name for logging purposes.")
    parser.add_argument("--source", help="Landing source path or URI.")
    parser.add_argument("--target", help="Bronze raw root path or URI.")
    parser.add_argument("--source-uri", dest="source_uri", help="Alias for --source in AWS.")
    parser.add_argument("--target-uri", dest="target_uri", help="Alias for --target in AWS.")
    parser.add_argument("--business-date", help="Optional business date in ISO format.")
    parser.add_argument("--source-filename", help="Optional filename override for the promoted raw object.")
    return parser.parse_args()


def build_bronze_raw_target(target_root: str, business_date_value: str | None, source_filename: str) -> str:
    business_date = parse_ingestion_date(business_date_value).isoformat()

    if is_s3_uri(target_root):
        bucket, key_prefix = split_s3_uri(target_root)
        normalized_prefix = key_prefix.rstrip("/")
        return build_s3_uri(bucket, f"{normalized_prefix}/ingestion_date={business_date}/{source_filename}")

    return str(Path(resolve_resource_reference(target_root)) / f"ingestion_date={business_date}" / source_filename)


def resolve_source_filename(source_uri: str, source_filename: str | None = None) -> str:
    candidate = (source_filename or source_uri).rstrip("/")
    if is_s3_uri(candidate):
        _, key = split_s3_uri(candidate)
        return key.rsplit("/", 1)[-1]
    return Path(candidate).name


def run_pipeline(
    *,
    source_uri: str,
    target_uri: str,
    business_date_value: str | None = None,
    source_filename: str | None = None,
) -> dict[str, str]:
    resolved_source = resolve_resource_reference(source_uri)
    if not resource_exists(resolved_source):
        raise FileNotFoundError(f"Landing source was not found: {resolved_source}")

    effective_source_filename = resolve_source_filename(str(resolved_source), source_filename)
    final_target_uri = build_bronze_raw_target(target_uri, business_date_value, effective_source_filename)

    if not resource_exists(final_target_uri):
        copy_resource(resolved_source, final_target_uri)

    return {
        "pipeline_name": DEFAULT_PIPELINE_NAME,
        "source_uri": resolved_source,
        "target_uri": final_target_uri,
        "business_date": parse_ingestion_date(business_date_value).isoformat(),
        "source_file": effective_source_filename,
    }


def main() -> None:
    args = parse_args()
    result = run_pipeline(
        source_uri=args.source_uri or args.source,
        target_uri=args.target_uri or args.target,
        business_date_value=args.business_date,
        source_filename=args.source_filename,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
