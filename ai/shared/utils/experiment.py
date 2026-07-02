"""Experiment naming and checkpoint discovery, shared by all AI modules.

Training runs live in <checkpoints_dir>/<experiment>-<timestamp>/,
following the Ultralytics layout: weights/best.pt and weights/last.pt
inside each run directory. Each module passes its own checkpoints
directory (e.g. ai/object_detection/paths.py: CHECKPOINTS_DIR).
"""
from datetime import datetime
from pathlib import Path

_TIMESTAMP_FORMAT = "%Y%m%d-%H%M%S"


def make_run_name(experiment_name: str, now: datetime | None = None) -> str:
    """Build a unique run directory name for an experiment.

    Args:
        experiment_name: Base name from training.yaml.
        now: Timestamp to use; defaults to the current time.

    Returns:
        '<experiment_name>-<YYYYmmdd-HHMMSS>'.
    """
    stamp = (now or datetime.now()).strftime(_TIMESTAMP_FORMAT)
    return f"{experiment_name}-{stamp}"


def list_runs(checkpoints_dir: Path) -> list[Path]:
    """Return all run directories, newest first (by name, i.e. timestamp).

    Args:
        checkpoints_dir: Directory containing run subdirectories.

    Returns:
        Run directories sorted descending; empty list if none exist.
    """
    if not checkpoints_dir.is_dir():
        return []
    return sorted((p for p in checkpoints_dir.iterdir() if p.is_dir()), reverse=True)


def find_weights(kind: str, checkpoints_dir: Path) -> Path | None:
    """Locate the newest saved weights file across all runs.

    Args:
        kind: 'best' or 'last'.
        checkpoints_dir: Directory containing run subdirectories.

    Returns:
        Path to '<run>/weights/<kind>.pt' from the newest run that has
        one, or None if no run has saved weights yet.

    Raises:
        ValueError: If kind is not 'best' or 'last'.
    """
    if kind not in ("best", "last"):
        raise ValueError(f"kind must be 'best' or 'last', got '{kind}'")
    for run in list_runs(checkpoints_dir):
        candidate = run / "weights" / f"{kind}.pt"
        if candidate.is_file():
            return candidate
    return None
