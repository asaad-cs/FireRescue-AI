"""Train the FireRescue AI object detector (Ultralytics YOLO).

Entry point:
    python -m ai.object_detection.training.train

Loads and validates the three configs in ai/object_detection/configs/,
seeds all RNGs, resolves the compute device, writes a resolved dataset
yaml, and starts transfer learning from the official pretrained YOLO
checkpoint.

Importing this module never starts training — only direct execution does.
"""
from dataclasses import dataclass
from pathlib import Path

import yaml

from ai.object_detection.config import (
    ConfigError,
    DatasetConfig,
    ModelConfig,
    TrainingConfig,
    load_dataset_config,
    load_model_config,
    load_training_config,
)
from ai.shared.utils.device import select_device
from ai.shared.utils.experiment import make_run_name
from ai.shared.utils.logger import get_logger
from ai.object_detection.paths import CHECKPOINTS_DIR
from ai.shared.utils.paths import ensure_dir
from ai.shared.utils.seed import seed_everything

logger = get_logger("training.train")


@dataclass(frozen=True)
class TrainingSession:
    """Everything needed to launch one training run."""

    model: ModelConfig
    run_name: str
    run_dir: Path
    data_yaml: Path
    tensorboard_dir: Path
    device: str
    train_kwargs: dict


def load_yolo_class() -> type:
    """Import and return the Ultralytics YOLO class.

    Imported lazily so config handling and tests never require the ML
    stack to be installed.

    Returns:
        The ultralytics.YOLO class.

    Raises:
        RuntimeError: If ultralytics is not installed.
    """
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise RuntimeError(
            "ultralytics is not installed. Run: pip install -r ai/requirements.txt"
        ) from exc
    return YOLO


def write_resolved_dataset_yaml(dataset: DatasetConfig, run_dir: Path) -> Path:
    """Write an Ultralytics data yaml with the root resolved to absolute.

    The committed dataset.yaml keeps relative paths; Ultralytics needs
    an absolute 'path' to work from any working directory, so each run
    gets its own resolved copy.

    Args:
        dataset: Validated dataset configuration.
        run_dir: Run directory to write into (created if missing).

    Returns:
        Path to the written data.yaml.
    """
    data = {
        "path": str(dataset.root_dir),
        "train": dataset.train,
        "val": dataset.val,
        "test": dataset.test,
        "nc": dataset.nc,
        "names": dataset.names,
    }
    ensure_dir(run_dir)
    out = run_dir / "data.yaml"
    out.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return out


def missing_split_dirs(dataset: DatasetConfig) -> list[Path]:
    """Return the dataset split directories that do not exist on disk.

    Args:
        dataset: Validated dataset configuration.

    Returns:
        Missing directories among train/val/test; empty when complete.
    """
    expected = (
        dataset.root_dir / dataset.train,
        dataset.root_dir / dataset.val,
        dataset.root_dir / dataset.test,
    )
    return [p for p in expected if not p.is_dir()]


def prepare_session(
    training: TrainingConfig | None = None,
    dataset: DatasetConfig | None = None,
    model: ModelConfig | None = None,
    checkpoints_dir: Path = CHECKPOINTS_DIR,
    require_data: bool = True,
) -> TrainingSession:
    """Validate configuration and assemble a ready-to-launch session.

    Args:
        training: Training config; loaded from ai/object_detection/configs/ when None.
        dataset: Dataset config; loaded from ai/object_detection/configs/ when None.
        model: Model config; loaded from ai/object_detection/configs/ when None.
        checkpoints_dir: Root directory for run output.
        require_data: When True, fail if dataset split dirs are missing.

    Returns:
        A TrainingSession with resolved paths, device, and the exact
        keyword arguments for YOLO.train().

    Raises:
        ConfigError: If any config is invalid or the dataset is missing.
    """
    training = training or load_training_config()
    dataset = dataset or load_dataset_config()
    model = model or load_model_config()

    if require_data:
        missing = missing_split_dirs(dataset)
        if missing:
            listing = ", ".join(str(p) for p in missing)
            raise ConfigError(
                f"Dataset split directories missing: {listing}. "
                "Populate ai/object_detection/datasets/ before training "
                "(see ai/README.md)."
            )

    seed = seed_everything(training.seed)
    device = select_device(model.device)
    run_name = make_run_name(training.experiment_name)
    run_dir = checkpoints_dir / run_name
    data_yaml = write_resolved_dataset_yaml(dataset, run_dir)
    tensorboard_dir = ensure_dir(run_dir / training.tensorboard_dir)

    train_kwargs = {
        "data": str(data_yaml),
        "epochs": model.epochs,
        "imgsz": model.image_size,
        "batch": model.batch_size,
        "device": device,
        "optimizer": model.optimizer,
        "lr0": model.learning_rate,
        "seed": seed,
        "workers": training.workers,
        "amp": training.mixed_precision,
        # Ultralytics disables early stopping when patience is 0.
        "patience": training.early_stopping_patience,
        "save_period": training.checkpoint_frequency,
        "project": str(checkpoints_dir),
        "name": run_name,
        "exist_ok": True,
        "resume": training.resume,
    }

    logger.info(
        "Training session prepared | run=%s device=%s model=%s epochs=%d",
        run_name, device, model.pretrained_weights, model.epochs,
    )
    return TrainingSession(
        model=model,
        run_name=run_name,
        run_dir=run_dir,
        data_yaml=data_yaml,
        tensorboard_dir=tensorboard_dir,
        device=device,
        train_kwargs=train_kwargs,
    )


def build_model(model: ModelConfig):
    """Instantiate a pretrained YOLO model for transfer learning.

    Args:
        model: Validated model configuration.

    Returns:
        An ultralytics.YOLO instance loaded with pretrained weights.
    """
    yolo_class = load_yolo_class()
    logger.info("Loading pretrained weights | %s", model.pretrained_weights)
    return yolo_class(model.pretrained_weights)


def main() -> None:
    """Prepare the session and run training to completion."""
    session = prepare_session()
    model = build_model(session.model)
    logger.info("Starting training | run=%s", session.run_name)
    model.train(**session.train_kwargs)
    logger.info(
        "Training finished | weights=%s", session.run_dir / "weights" / "best.pt"
    )


if __name__ == "__main__":
    main()
