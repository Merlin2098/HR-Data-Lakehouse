from __future__ import annotations

from pathlib import Path
from typing import Any

from src.common.resource_loader import load_yaml_resource


def load_yaml_file(path_value: str | Path) -> dict[str, Any]:
    """Load a YAML file into a dictionary."""
    return load_yaml_resource(path_value)
