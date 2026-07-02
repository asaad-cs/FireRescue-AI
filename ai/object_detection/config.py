"""Typed loading and validation of the object detection config YAMLs.

Each file in ai/object_detection/configs/ maps to a frozen dataclass.
Loading validates eagerly and raises ConfigError with a message naming
the file and field, so a bad config fails before any heavy library is
imported. The generic YAML machinery lives in ai/shared/utils/config.py.
"""
from dataclasses import dataclass, field
from pathlib import Path

from ai.object_detection.paths import CONFIGS_DIR, MODULE_ROOT
from ai.shared.utils.config import ConfigError, load_yaml, require as _require

VALID_MODEL_SIZES = ("n", "s", "m", "l", "x")
VALID_OPTIMIZERS = ("auto", "SGD", "Adam", "AdamW")


@dataclass(frozen=True)
class DatasetConfig:
    """Parsed ai/object_detection/configs/dataset.yaml."""

    root: str
    train: str
    val: str
    test: str
    nc: int
    names: list[str] = field(default_factory=list)

    @property
    def root_dir(self) -> Path:
        """Dataset root resolved to an absolute path under this module."""
        return MODULE_ROOT / self.root

    def validate(self) -> None:
        """Check internal consistency.

        Raises:
            ConfigError: If any field is invalid.
        """
        for name, value in (("root", self.root), ("train", self.train),
                            ("val", self.val), ("test", self.test)):
            # Reject drive-qualified paths and rooted paths like '/data':
            # on Windows the latter are not 'absolute' but are not
            # relative either.
            p = Path(value)
            if p.is_absolute() or p.drive or p.root:
                raise ConfigError(
                    f"dataset.yaml: '{name}' must be a relative path, got '{value}'"
                )
        if self.nc < 1:
            raise ConfigError(f"dataset.yaml: 'nc' must be >= 1, got {self.nc}")
        if len(self.names) != self.nc:
            raise ConfigError(
                f"dataset.yaml: 'nc' is {self.nc} but 'names' has "
                f"{len(self.names)} entries"
            )


@dataclass(frozen=True)
class ModelConfig:
    """Parsed ai/object_detection/configs/model.yaml."""

    size: str
    epochs: int
    image_size: int
    batch_size: int
    device: str
    optimizer: str
    learning_rate: float
    confidence_threshold: float
    iou_threshold: float
    export_format: str

    @property
    def pretrained_weights(self) -> str:
        """Ultralytics pretrained checkpoint name for transfer learning."""
        return f"yolov8{self.size}.pt"

    def validate(self) -> None:
        """Check internal consistency.

        Raises:
            ConfigError: If any field is invalid.
        """
        if self.size not in VALID_MODEL_SIZES:
            raise ConfigError(
                f"model.yaml: 'size' must be one of {VALID_MODEL_SIZES}, "
                f"got '{self.size}'"
            )
        if self.epochs < 1:
            raise ConfigError(f"model.yaml: 'epochs' must be >= 1, got {self.epochs}")
        if self.image_size < 32:
            raise ConfigError(
                f"model.yaml: 'image_size' must be >= 32, got {self.image_size}"
            )
        if self.batch_size == 0 or self.batch_size < -1:
            raise ConfigError(
                f"model.yaml: 'batch_size' must be positive or -1 (auto), "
                f"got {self.batch_size}"
            )
        if self.optimizer not in VALID_OPTIMIZERS:
            raise ConfigError(
                f"model.yaml: 'optimizer' must be one of {VALID_OPTIMIZERS}, "
                f"got '{self.optimizer}'"
            )
        if self.learning_rate <= 0:
            raise ConfigError(
                f"model.yaml: 'learning_rate' must be > 0, got {self.learning_rate}"
            )
        for name, value in (("confidence_threshold", self.confidence_threshold),
                            ("iou_threshold", self.iou_threshold)):
            if not 0.0 < value < 1.0:
                raise ConfigError(
                    f"model.yaml: '{name}' must be between 0 and 1, got {value}"
                )


@dataclass(frozen=True)
class TrainingConfig:
    """Parsed ai/object_detection/configs/training.yaml."""

    seed: int
    workers: int
    mixed_precision: bool
    early_stopping_patience: int
    checkpoint_frequency: int
    experiment_name: str
    tensorboard_dir: str
    resume: bool

    def validate(self) -> None:
        """Check internal consistency.

        Raises:
            ConfigError: If any field is invalid.
        """
        if self.workers < 0:
            raise ConfigError(
                f"training.yaml: 'workers' must be >= 0, got {self.workers}"
            )
        if self.early_stopping_patience < 0:
            raise ConfigError(
                f"training.yaml: 'early_stopping_patience' must be >= 0, "
                f"got {self.early_stopping_patience}"
            )
        if self.checkpoint_frequency == 0 or self.checkpoint_frequency < -1:
            raise ConfigError(
                f"training.yaml: 'checkpoint_frequency' must be positive or -1, "
                f"got {self.checkpoint_frequency}"
            )
        if not self.experiment_name.strip():
            raise ConfigError("training.yaml: 'experiment_name' must not be empty")


def load_dataset_config(path: Path = CONFIGS_DIR / "dataset.yaml") -> DatasetConfig:
    """Load and validate the dataset configuration.

    Args:
        path: YAML file to read; defaults to ai/object_detection/configs/dataset.yaml.

    Returns:
        A validated DatasetConfig.

    Raises:
        ConfigError: If the file is missing, malformed, or inconsistent.
    """
    data = load_yaml(path)
    src = path.name
    cfg = DatasetConfig(
        root=str(_require(data, "root", src)),
        train=str(_require(data, "train", src)),
        val=str(_require(data, "val", src)),
        test=str(_require(data, "test", src)),
        nc=int(_require(data, "nc", src)),
        names=list(_require(data, "names", src)),
    )
    cfg.validate()
    return cfg


def load_model_config(path: Path = CONFIGS_DIR / "model.yaml") -> ModelConfig:
    """Load and validate the model configuration.

    Args:
        path: YAML file to read; defaults to ai/object_detection/configs/model.yaml.

    Returns:
        A validated ModelConfig.

    Raises:
        ConfigError: If the file is missing, malformed, or inconsistent.
    """
    data = load_yaml(path)
    src = path.name
    model = _require(data, "model", src)
    train = _require(data, "train", src)
    inference = _require(data, "inference", src)
    export = _require(data, "export", src)
    cfg = ModelConfig(
        size=str(_require(model, "size", f"{src}:model")),
        epochs=int(_require(train, "epochs", f"{src}:train")),
        image_size=int(_require(train, "image_size", f"{src}:train")),
        batch_size=int(_require(train, "batch_size", f"{src}:train")),
        device=str(_require(train, "device", f"{src}:train")),
        optimizer=str(_require(train, "optimizer", f"{src}:train")),
        learning_rate=float(_require(train, "learning_rate", f"{src}:train")),
        confidence_threshold=float(
            _require(inference, "confidence_threshold", f"{src}:inference")
        ),
        iou_threshold=float(_require(inference, "iou_threshold", f"{src}:inference")),
        export_format=str(_require(export, "format", f"{src}:export")),
    )
    cfg.validate()
    return cfg


def load_training_config(path: Path = CONFIGS_DIR / "training.yaml") -> TrainingConfig:
    """Load and validate the training configuration.

    Args:
        path: YAML file to read; defaults to ai/object_detection/configs/training.yaml.

    Returns:
        A validated TrainingConfig.

    Raises:
        ConfigError: If the file is missing, malformed, or inconsistent.
    """
    data = load_yaml(path)
    src = path.name
    cfg = TrainingConfig(
        seed=int(_require(data, "seed", src)),
        workers=int(_require(data, "workers", src)),
        mixed_precision=bool(_require(data, "mixed_precision", src)),
        early_stopping_patience=int(_require(data, "early_stopping_patience", src)),
        checkpoint_frequency=int(_require(data, "checkpoint_frequency", src)),
        experiment_name=str(_require(data, "experiment_name", src)),
        tensorboard_dir=str(_require(data, "tensorboard_dir", src)),
        resume=bool(_require(data, "resume", src)),
    )
    cfg.validate()
    return cfg
