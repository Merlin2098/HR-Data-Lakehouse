from __future__ import annotations

import json
from pathlib import Path

from src.common.config_loader import load_yaml_file
from src.common.project_paths import resolve_project_path


def read_text(path: str) -> str:
    return Path(resolve_project_path(path)).read_text(encoding="utf-8")


def test_pipeline_doc_reflects_trigger_only_landing_flow() -> None:
    pipeline_doc = read_text("docs/pipeline.md")

    assert "Landing -> Silver -> Gold" in pipeline_doc
    assert "Physical copy to `raw`: removed from the current design" in pipeline_doc
    assert "Bronze -> raw ingestion" not in pipeline_doc
    assert "raw.csv" not in pipeline_doc
    assert "ingestion_year" not in pipeline_doc
    assert "ingestion_month" not in pipeline_doc


def test_overview_doc_matches_current_pipeline_shape() -> None:
    overview_doc = read_text("docs/etl_architecture_overview.md")

    assert "Landing -> Silver -> Gold" in overview_doc
    assert "landing_to_bronze" not in overview_doc
    assert "reads the CSV from the exact `landing` object" in overview_doc
    assert "event-driven ingestion from `landing`" in overview_doc


def test_implementation_doc_describes_current_validation_status() -> None:
    implementation_doc = read_text("docs/implementation.md")

    assert "landing -> silver -> gold" in implementation_doc
    assert "validated functionally" in implementation_doc
    assert "AWS execution has not been validated yet" not in implementation_doc
    assert "IMPLEMENTED IN CODE, NOT VALIDATED IN AWS" not in implementation_doc


def test_docs_describe_quicksight_direct_query_over_bi_view() -> None:
    terraform_usage = read_text("docs/terraform_usage.md")
    overview_doc = read_text("docs/etl_architecture_overview.md")

    assert "QuickSight in `direct query` mode over Athena" in terraform_usage
    assert "`vw_quicksight_hr_attrition`" in terraform_usage
    assert "not using the CSV files under `athena-results` as an analytical layer" in terraform_usage
    assert "QuickSight should connect to the stable view `vw_quicksight_hr_attrition`" in overview_doc
    assert "without a manual SPICE refresh" in overview_doc


def test_tinker_project_metadata_and_context_graph_reflect_repo_layout() -> None:
    metadata = load_yaml_file(resolve_project_path(".tinker/project_metadata.yaml"))
    context_graph = json.loads(read_text(".tinker/context_graph.json"))
    dependencies_graph = json.loads(read_text(".tinker/dependencies_graph.json"))

    assert metadata["structure"]["has_tests"] is True
    assert metadata["structure"]["has_ci"] is True
    assert metadata["structure"]["has_terraform"] is True

    context_paths = {node["path"] for node in context_graph["nodes"] if "path" in node}
    assert "infra/main.tf" in context_paths
    assert "infra/provider.tf" in context_paths
    assert "main.tf" not in context_paths
    assert "provider.tf" not in context_paths

    dependency_ids = {node["id"] for node in dependencies_graph["nodes"]}
    assert "module:src.glue.bronze_to_silver" in dependency_ids
    assert "module:src.glue.silver_to_gold" in dependency_ids
    assert "module:src.glue.retry_state_machine" in dependency_ids
    assert "module:src.glue.landing_to_bronze" not in dependency_ids
