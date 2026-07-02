"""Path constants for the object detection module.

Everything is derived from this file's location, so the module works
from any working directory. Generic AI-wide paths (AI_ROOT,
PROJECT_ROOT) live in ai/shared/utils/paths.py.
"""
from pathlib import Path

MODULE_ROOT: Path = Path(__file__).resolve().parent

CONFIGS_DIR: Path = MODULE_ROOT / "configs"

DATASETS_DIR: Path = MODULE_ROOT / "datasets"
RAW_DATA_DIR: Path = DATASETS_DIR / "raw"
PROCESSED_DATA_DIR: Path = DATASETS_DIR / "processed"
EXTERNAL_DATA_DIR: Path = DATASETS_DIR / "external"
MERGED_DATA_DIR: Path = DATASETS_DIR / "merged"
REPORTS_DIR: Path = DATASETS_DIR / "reports"

DOCS_DIR: Path = MODULE_ROOT / "docs"

MODELS_DIR: Path = MODULE_ROOT / "models"
CHECKPOINTS_DIR: Path = MODELS_DIR / "checkpoints"
EXPORTS_DIR: Path = MODELS_DIR / "exports"
