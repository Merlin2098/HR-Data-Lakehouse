from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_yaml_file(path_value: str | Path) -> dict[str, Any]:
    """Load a YAML file into a dictionary."""
    path = Path(path_value)
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}

    if not isinstance(loaded, dict):
        raise ValueError(f"Expected a mapping in {path}, got {type(loaded).__name__}.")

    return loaded
