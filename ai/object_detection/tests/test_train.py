"""Tests: ai.object_detection.training.train — session preparation and model init, fully mocked."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from ai.object_detection.training.train import (
    TrainingSession,
    build_model,
    main,
    missing_split_dirs,
    prepare_session,
    write_resolved_dataset_yaml,
)
from ai.object_detection.config import ConfigError, DatasetConfig, ModelConfig, TrainingConfig
from ai.object_detection.paths import MODULE_ROOT


def _dataset_in(tmp: Path, create_splits: bool) -> DatasetConfig:
    """DatasetConfig whose relative root resolves into the given tmp dir."""
    root = os.path.relpath(tmp, MODULE_ROOT)
    cfg = DatasetConfig(
        root=root, train="images/train", val="images/val", test="images/test",
        nc=2, names=["fire", "smoke"],
    )
    if create_splits:
        for split in ("images/train", "images/val", "images/test"):
            (tmp / split).mkdir(parents=True, exist_ok=True)
    return cfg


_MODEL = ModelConfig(
    size="s", epochs=5, image_size=320, batch_size=8, device="cpu",
    optimizer="SGD", learning_rate=0.005, confidence_threshold=0.3,
    iou_threshold=0.5, export_format="onnx",
)

_TRAINING = TrainingConfig(
    seed=7, workers=0, mixed_precision=False, early_stopping_patience=4,
    checkpoint_frequency=-1, experiment_name="unit", tensorboard_dir="tb",
    resume=False,
)


class TestWriteResolvedDatasetYaml(unittest.TestCase):

    def test_written_yaml_has_absolute_root_and_classes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cfg = _dataset_in(tmp_path / "data", create_splits=False)
            out = write_resolved_dataset_yaml(cfg, tmp_path / "run")
            data = yaml.safe_load(out.read_text(encoding="utf-8"))
            self.assertTrue(Path(data["path"]).is_absolute())
            self.assertEqual(data["nc"], 2)
            self.assertEqual(data["names"], ["fire", "smoke"])
            self.assertEqual(data["train"], "images/train")


class TestMissingSplitDirs(unittest.TestCase):

    def test_all_missing_when_root_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _dataset_in(Path(tmp) / "data", create_splits=False)
            self.assertEqual(len(missing_split_dirs(cfg)), 3)

    def test_empty_when_all_splits_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = _dataset_in(Path(tmp), create_splits=True)
            self.assertEqual(missing_split_dirs(cfg), [])


class TestPrepareSession(unittest.TestCase):

    def test_missing_dataset_raises_config_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cfg = _dataset_in(tmp_path / "data", create_splits=False)
            with self.assertRaises(ConfigError) as ctx:
                prepare_session(
                    training=_TRAINING, dataset=cfg, model=_MODEL,
                    checkpoints_dir=tmp_path / "ckpt",
                )
            self.assertIn("missing", str(ctx.exception).lower())

    def test_session_kwargs_map_configs_to_ultralytics_args(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cfg = _dataset_in(tmp_path, create_splits=True)
            session = prepare_session(
                training=_TRAINING, dataset=cfg, model=_MODEL,
                checkpoints_dir=tmp_path / "ckpt",
            )
            kw = session.train_kwargs
            self.assertEqual(kw["epochs"], 5)
            self.assertEqual(kw["imgsz"], 320)
            self.assertEqual(kw["batch"], 8)
            self.assertEqual(kw["device"], "cpu")
            self.assertEqual(kw["optimizer"], "SGD")
            self.assertEqual(kw["lr0"], 0.005)
            self.assertEqual(kw["seed"], 7)
            self.assertEqual(kw["amp"], False)
            self.assertEqual(kw["patience"], 4)
            self.assertEqual(kw["save_period"], -1)
            self.assertEqual(kw["resume"], False)
            self.assertEqual(kw["data"], str(session.data_yaml))

    def test_session_creates_run_and_tensorboard_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cfg = _dataset_in(tmp_path, create_splits=True)
            session = prepare_session(
                training=_TRAINING, dataset=cfg, model=_MODEL,
                checkpoints_dir=tmp_path / "ckpt",
            )
            self.assertTrue(session.run_name.startswith("unit-"))
            self.assertTrue(session.run_dir.is_dir())
            self.assertTrue(session.data_yaml.is_file())
            self.assertEqual(session.tensorboard_dir, session.run_dir / "tb")
            self.assertTrue(session.tensorboard_dir.is_dir())

    def test_require_data_false_skips_dataset_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cfg = _dataset_in(tmp_path / "data", create_splits=False)
            session = prepare_session(
                training=_TRAINING, dataset=cfg, model=_MODEL,
                checkpoints_dir=tmp_path / "ckpt", require_data=False,
            )
            self.assertIsInstance(session, TrainingSession)


class TestBuildModel(unittest.TestCase):

    def test_loads_pretrained_checkpoint_for_transfer_learning(self):
        yolo_class = MagicMock()
        with patch("ai.object_detection.training.train.load_yolo_class", return_value=yolo_class):
            build_model(_MODEL)
        yolo_class.assert_called_once_with("yolov8s.pt")

    def test_build_model_never_starts_training(self):
        yolo_class = MagicMock()
        with patch("ai.object_detection.training.train.load_yolo_class", return_value=yolo_class):
            model = build_model(_MODEL)
        model.train.assert_not_called()


class TestMain(unittest.TestCase):

    def test_main_trains_with_prepared_session_kwargs(self):
        session = MagicMock(spec=TrainingSession)
        session.train_kwargs = {"epochs": 5, "data": "x.yaml"}
        session.run_name = "unit-run"
        session.run_dir = Path("unused")
        session.model = _MODEL
        mock_model = MagicMock()
        with patch("ai.object_detection.training.train.prepare_session", return_value=session), \
             patch("ai.object_detection.training.train.build_model", return_value=mock_model):
            main()
        mock_model.train.assert_called_once_with(epochs=5, data="x.yaml")


if __name__ == "__main__":
    unittest.main()
