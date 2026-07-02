"""Tests: ai.object_detection.config — YAML loading and validation of all three configs."""
import tempfile
import unittest
from pathlib import Path

from ai.object_detection.config import (
    ConfigError,
    DatasetConfig,
    ModelConfig,
    TrainingConfig,
    load_dataset_config,
    load_model_config,
    load_training_config,
    load_yaml,
)
from ai.object_detection.paths import MODULE_ROOT


def _valid_dataset(**overrides) -> DatasetConfig:
    kwargs = dict(
        root="datasets/processed", train="images/train", val="images/val",
        test="images/test", nc=3, names=["fire", "smoke", "person"],
    )
    kwargs.update(overrides)
    return DatasetConfig(**kwargs)


def _valid_model(**overrides) -> ModelConfig:
    kwargs = dict(
        size="n", epochs=50, image_size=640, batch_size=16, device="auto",
        optimizer="auto", learning_rate=0.01, confidence_threshold=0.25,
        iou_threshold=0.45, export_format="onnx",
    )
    kwargs.update(overrides)
    return ModelConfig(**kwargs)


def _valid_training(**overrides) -> TrainingConfig:
    kwargs = dict(
        seed=42, workers=0, mixed_precision=True, early_stopping_patience=10,
        checkpoint_frequency=-1, experiment_name="exp", tensorboard_dir="tb",
        resume=False,
    )
    kwargs.update(overrides)
    return TrainingConfig(**kwargs)


class TestLoadYaml(unittest.TestCase):

    def test_missing_file_raises(self):
        with self.assertRaises(ConfigError):
            load_yaml(Path("does/not/exist.yaml"))

    def test_non_mapping_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.yaml"
            path.write_text("- just\n- a\n- list\n", encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_yaml(path)


class TestRealConfigFiles(unittest.TestCase):
    """The committed configs in ai/object_detection/configs/ must always load and validate."""

    def test_dataset_yaml_loads(self):
        cfg = load_dataset_config()
        self.assertEqual(cfg.nc, len(cfg.names))

    def test_model_yaml_loads(self):
        cfg = load_model_config()
        self.assertEqual(cfg.pretrained_weights, f"yolov8{cfg.size}.pt")

    def test_training_yaml_loads(self):
        cfg = load_training_config()
        self.assertTrue(cfg.experiment_name)

    def test_missing_key_names_file_and_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "training.yaml"
            path.write_text("seed: 1\n", encoding="utf-8")
            with self.assertRaises(ConfigError) as ctx:
                load_training_config(path)
            self.assertIn("workers", str(ctx.exception))


class TestDatasetConfigValidation(unittest.TestCase):

    def test_valid_config_passes(self):
        _valid_dataset().validate()

    def test_root_dir_is_under_ai_root(self):
        self.assertEqual(
            _valid_dataset().root_dir, MODULE_ROOT / "datasets/processed"
        )

    def test_absolute_root_rejected(self):
        with self.assertRaises(ConfigError):
            _valid_dataset(root="C:/data").validate()

    def test_absolute_split_rejected(self):
        with self.assertRaises(ConfigError):
            _valid_dataset(train="/images/train").validate()

    def test_nc_names_mismatch_rejected(self):
        with self.assertRaises(ConfigError):
            _valid_dataset(nc=2).validate()

    def test_nc_below_one_rejected(self):
        with self.assertRaises(ConfigError):
            _valid_dataset(nc=0, names=[]).validate()


class TestModelConfigValidation(unittest.TestCase):

    def test_valid_config_passes(self):
        _valid_model().validate()

    def test_invalid_size_rejected(self):
        with self.assertRaises(ConfigError):
            _valid_model(size="xxl").validate()

    def test_zero_epochs_rejected(self):
        with self.assertRaises(ConfigError):
            _valid_model(epochs=0).validate()

    def test_tiny_image_size_rejected(self):
        with self.assertRaises(ConfigError):
            _valid_model(image_size=16).validate()

    def test_batch_size_auto_allowed(self):
        _valid_model(batch_size=-1).validate()

    def test_batch_size_zero_rejected(self):
        with self.assertRaises(ConfigError):
            _valid_model(batch_size=0).validate()

    def test_invalid_optimizer_rejected(self):
        with self.assertRaises(ConfigError):
            _valid_model(optimizer="RMSprop").validate()

    def test_negative_learning_rate_rejected(self):
        with self.assertRaises(ConfigError):
            _valid_model(learning_rate=-0.1).validate()

    def test_confidence_out_of_range_rejected(self):
        with self.assertRaises(ConfigError):
            _valid_model(confidence_threshold=1.5).validate()

    def test_iou_out_of_range_rejected(self):
        with self.assertRaises(ConfigError):
            _valid_model(iou_threshold=0.0).validate()


class TestTrainingConfigValidation(unittest.TestCase):

    def test_valid_config_passes(self):
        _valid_training().validate()

    def test_negative_workers_rejected(self):
        with self.assertRaises(ConfigError):
            _valid_training(workers=-1).validate()

    def test_negative_patience_rejected(self):
        with self.assertRaises(ConfigError):
            _valid_training(early_stopping_patience=-1).validate()

    def test_checkpoint_frequency_disabled_allowed(self):
        _valid_training(checkpoint_frequency=-1).validate()

    def test_checkpoint_frequency_zero_rejected(self):
        with self.assertRaises(ConfigError):
            _valid_training(checkpoint_frequency=0).validate()

    def test_empty_experiment_name_rejected(self):
        with self.assertRaises(ConfigError):
            _valid_training(experiment_name="  ").validate()


if __name__ == "__main__":
    unittest.main()
