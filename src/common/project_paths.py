from __future__ import annotations

import sys
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SRC_ROOT.parent


def resolve_project_path(path_value: str | Path) -> Path:
    """Resolve a project-relative path into an absolute path."""
    path = Path(path_value)
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / path).resolve()


def ensure_parent_dir(path_value: str | Path) -> Path:
    """Create the parent directory for a local output path when needed."""
    path = Path(path_value)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def ensure_src_package_importable(script_path: str | Path) -> None:
    """Ensure local script execution can import the top-level src package."""
    current_path = Path(script_path).resolve()
    for candidate in (current_path.parent, *current_path.parents):
        if (candidate / "src" / "__init__.py").exists():
            candidate_str = str(candidate)
            if candidate_str not in sys.path:
                sys.path.append(candidate_str)
            return
