"""
Camera and Vision lifecycle state definitions for Sam.
"""
from enum import StrEnum


class CameraState(StrEnum):
    """Explicit lifecycle states for Camera & Vision hardware access."""
    OFF = "off"
    REQUESTING_PERMISSION = "requesting_permission"
    READY = "ready"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
