from __future__ import annotations

from pathlib import Path

from src.common.config_loader import load_yaml_file


def load_contract(path_value: str | Path) -> dict[str, object]:
    """Load the project contract file."""
    return load_yaml_file(path_value)


def expected_columns(contract: dict[str, object], dataset_name: str) -> list[str]:
    """Return the ordered column list for a declared dataset contract."""
    datasets = contract.get("datasets", {})
    if not isinstance(datasets, dict):
        raise ValueError("contracts.yaml must define a 'datasets' mapping.")

    dataset = datasets.get(dataset_name)
    if not isinstance(dataset, dict):
        raise ValueError(f"Dataset '{dataset_name}' was not found in the contract.")

    columns = dataset.get("columns", [])
    if not isinstance(columns, list):
        raise ValueError(f"Dataset '{dataset_name}' columns must be a list.")

    ordered_names: list[str] = []
    for column in columns:
        if not isinstance(column, dict) or "name" not in column:
            raise ValueError(f"Dataset '{dataset_name}' contains an invalid column entry.")
        ordered_names.append(str(column["name"]))

    return ordered_names
