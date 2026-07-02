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

    # Perception — name must match a detector registered at startup
    perception_detector: str = "ground_truth"

    # Future placeholders (not used in Phase 3)
    database_url: str = "sqlite:///./firerescue.db"
    max_active_missions: int = 1


settings = Settings()
