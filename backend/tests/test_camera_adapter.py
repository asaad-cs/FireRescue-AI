"""Tests: CameraSimAdapter, make_data_source, and pipeline integration."""
from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

import numpy as np

from backend.config.settings import settings
from backend.ingestion.camera_adapter import CameraSimAdapter, make_data_source
from backend.ingestion.interface import DataSource
from backend.ingestion.sim_adapter import SimAdapter
from backend.models.frame import Frame, Pose
from simulation.camera.provider import (
    ZoneCategoryResolver,
    ZoneImageProvider,
)
from simulation.runner import SimulationRunner
from simulation.scenarios import default_scenario
from simulation.tests.test_camera import make_config, write_png


class StubSource(DataSource):
    """Emits one prepared frame, records stop() calls."""

    def __init__(self, frame: Frame) -> None:
        self.frame = frame
        self.stopped = False

    async def start(self, mission_id, on_frame_callback) -> None:
        await on_frame_callback(self.frame)

    async def stop(self) -> None:
        self.stopped = True


class StubProvider:
    """image_for_zone returns a fixed value and records requests."""

    def __init__(self, image) -> None:
        self.image = image
        self.requested = []

    def image_for_zone(self, zone_id: str):
        self.requested.append(zone_id)
        return self.image


def make_frame() -> Frame:
    return Frame(
        mission_id="m-1",
        drone_id="d-1",
        pose=Pose(x=4, y=2, floor=1),
        channels={"environmental": {"temperature": 25.0}},
        metadata={"tick": 3},
    )


def run_through_adapter(adapter: DataSource) -> list[Frame]:
    received: list[Frame] = []

    async def collect(frame: Frame) -> None:
        received.append(frame)

    asyncio.run(adapter.start("m-1", collect))
    return received


class TestCameraSimAdapter(unittest.TestCase):

    def test_rgb_channel_attached(self):
        image = np.zeros((8, 8, 3), dtype=np.uint8)
        provider = StubProvider(image)
        adapter = CameraSimAdapter(StubSource(make_frame()), provider)
        (frame,) = run_through_adapter(adapter)
        self.assertIs(frame.channels["rgb"], image)
        self.assertEqual(provider.requested, ["4_2_1"])

    def test_only_rgb_changes(self):
        original = make_frame()
        adapter = CameraSimAdapter(
            StubSource(original), StubProvider(np.zeros((4, 4, 3), np.uint8))
        )
        (frame,) = run_through_adapter(adapter)
        self.assertEqual(frame.frame_id, original.frame_id)
        self.assertEqual(frame.pose, original.pose)
        self.assertEqual(frame.metadata, {"tick": 3})
        self.assertEqual(
            frame.channels["environmental"], {"temperature": 25.0}
        )
        self.assertEqual(
            set(frame.channels), {"environmental", "rgb"}
        )

    def test_no_image_leaves_frame_untouched(self):
        adapter = CameraSimAdapter(StubSource(make_frame()), StubProvider(None))
        (frame,) = run_through_adapter(adapter)
        self.assertNotIn("rgb", frame.channels)

    def test_stop_delegates(self):
        source = StubSource(make_frame())
        adapter = CameraSimAdapter(source, StubProvider(None))
        asyncio.run(adapter.stop())
        self.assertTrue(source.stopped)


class TestMakeDataSource(unittest.TestCase):

    def setUp(self):
        self._enabled = settings.camera_enabled
        self._path = settings.camera_config_path
        self.addCleanup(self._restore)
        self.scenario = default_scenario()
        self.runner = SimulationRunner(scenario=self.scenario, tick_interval=1.0)

    def _restore(self):
        settings.camera_enabled = self._enabled
        settings.camera_config_path = self._path

    def test_disabled_returns_plain_sim_adapter(self):
        settings.camera_enabled = False
        adapter = make_data_source(self.runner, self.scenario)
        self.assertIsInstance(adapter, SimAdapter)
        self.assertNotIsInstance(adapter, CameraSimAdapter)

    def test_bad_config_degrades_gracefully(self):
        settings.camera_enabled = True
        settings.camera_config_path = "does/not/exist.yaml"
        adapter = make_data_source(self.runner, self.scenario)
        self.assertIsInstance(adapter, SimAdapter)

    def test_valid_config_wraps_with_camera(self):
        settings.camera_enabled = True
        adapter = make_data_source(self.runner, self.scenario)
        self.assertIsInstance(adapter, CameraSimAdapter)


class TestEndToEndCameraToDetector(unittest.TestCase):
    """Camera image → Frame → YOLODetector, without mocking the provider."""

    def test_critical_zone_image_reaches_detector(self):
        from perception.detectors.yolo import YOLODetector
        from perception.tests.test_yolo_detector import (
            FIRE,
            FakeSession,
            make_raw,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_png(root / "fire" / "blaze.png")
            provider = ZoneImageProvider(
                config=make_config(),
                resolver=ZoneCategoryResolver(
                    config=make_config(),
                    hazard_levels={"4_2_1": "CRITICAL"},
                    victim_zones=set(),
                ),
                image_root=root,
            )
            adapter = CameraSimAdapter(StubSource(make_frame()), provider)
            (frame,) = run_through_adapter(adapter)
            self.assertIn("rgb", frame.channels)

            detector = YOLODetector(model_path="unused.onnx")
            detector._session = FakeSession(
                make_raw([(320, 320, 100, 100, FIRE, 0.9)])
            )
            detector._input_name = "images"
            result = detector.process(frame)
            self.assertEqual(result.detector_name, "yolo")
            self.assertEqual(result.metadata["detections"], 1)


class TestBackendBoot(unittest.TestCase):
    """The app must boot with the camera under either detector."""

    def setUp(self):
        self._detector = settings.perception_detector
        self.addCleanup(self._restore)

    def _restore(self):
        settings.perception_detector = self._detector

    def test_boot_with_camera_and_ground_truth(self):
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as client:
            self.assertEqual(client.get("/health").status_code, 200)
            self.assertIsInstance(
                client.app.state.adapter, (CameraSimAdapter, SimAdapter)
            )

    def test_boot_with_camera_and_yolo(self):
        from fastapi.testclient import TestClient
        from backend.main import app

        settings.perception_detector = "yolo"
        with TestClient(app) as client:
            self.assertEqual(client.get("/health").status_code, 200)
            self.assertIsNotNone(client.app.state.manager.get_state())


if __name__ == "__main__":
    unittest.main()
