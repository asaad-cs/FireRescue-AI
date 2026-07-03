"""
Simulated RGB camera for the drone (Phase 8F).

Maps every simulation zone to a category of real photographs (safe /
fire / smoke / person / combinations) and serves one image per visit,
so detectors can run real inference instead of reading ground truth.

The package is standalone: it never imports backend or perception
code, and its heavy dependencies (yaml, cv2, numpy) are imported
lazily so the MVP keeps running when they are absent.
"""
from simulation.camera.provider import (
    CameraConfig,
    CameraConfigError,
    ZoneCategoryResolver,
    ZoneImageProvider,
    load_camera_config,
)

__all__ = [
    "CameraConfig",
    "CameraConfigError",
    "ZoneCategoryResolver",
    "ZoneImageProvider",
    "load_camera_config",
]
