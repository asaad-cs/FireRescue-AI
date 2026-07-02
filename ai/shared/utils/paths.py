"""Canonical path resolution shared by all AI modules.

Every path is derived from this file's location on disk, so the module
works from any working directory and no path is ever hardcoded.
Module-specific paths (e.g. object detection datasets and checkpoints)
live in the owning module, such as ai/object_detection/paths.py.
"""
from pathlib import Path

AI_ROOT: Path = Path(__file__).resolve().parents[2]
PROJECT_ROOT: Path = AI_ROOT.parent

NOTEBOOKS_DIR: Path = AI_ROOT / "notebooks"


def ensure_dir(path: Path) -> Path:
    """Create a directory (and parents) if missing and return it.

    Args:
        path: Directory to create.

    Returns:
        The same path, guaranteed to exist as a directory.
    """
    path.mkdir(parents=True, exist_ok=True)
    return path
