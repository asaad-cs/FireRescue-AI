"""
Application configuration.

All tuneable values live here. Nothing is hard-coded elsewhere.
Future phases add new fields to this dataclass as needed.
"""
from dataclasses import dataclass


@dataclass
class Settings:
    # Identity
    app_name: str = "FireRescue AI"
    version: str = "1.0.0"

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True

    # Logging
    log_level: str = "INFO"

    # WebSocket broadcast
    broadcast_interval_seconds: float = 3.0

    # Mission behaviour
    frame_timeout_seconds: float = 5.0
    max_zone_history: int = 20       # Recent frames kept per zone for perception context

    # Simulation
    sim_tick_interval_seconds: float = 1.0   # seconds between simulation ticks
    sim_drone_id: str = "sim-drone-alpha"

    # Perception — name must match a detector registered at startup.
    # Available: "ground_truth" (simulation ground truth, MVP default)
    #            "yolo"         (ONNX model trained in ai/, Version 2)
    perception_detector: str = "ground_truth"

    # YOLO detector (used only when perception_detector == "yolo", but
    # the detector is always registered so switching is config-only).
    # yolo_model_path: explicit .onnx file; empty string → newest .onnx
    # in yolo_model_dir. Relative paths resolve from the project root.
    yolo_model_path: str = ""
    yolo_model_dir: str = "ai/object_detection/models/exports"
    yolo_confidence_threshold: float = 0.25
    yolo_iou_threshold: float = 0.45
    yolo_image_size: int = 640

    # Simulated drone camera (Phase 8F): attaches an RGB image to every
    # frame via Frame.channels["rgb"]. Disabling it (or any camera
    # configuration problem) falls back to the plain simulation frames.
    camera_enabled: bool = True
    camera_config_path: str = "simulation/camera/simulation_camera.yaml"

    # Demo Mode (Phase Demo.2): when true, the simulated camera reads
    # imagery from assets/demo_dataset/ instead of the normal runtime
    # folder (simulation/camera/images/). Nothing else changes — same
    # config file, same category resolution, same selection algorithm;
    # only the image root swaps. Default False keeps Production Mode as
    # the unconditional default.
    camera_demo_mode: bool = False

    # Future placeholders (not used in Phase 3)
    database_url: str = "sqlite:///./firerescue.db"
    max_active_missions: int = 1


settings = Settings()
