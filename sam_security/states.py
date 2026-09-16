"""
Security lifecycle states for Mobile Security and Anti-Theft engine.
"""
from enum import StrEnum


class SecurityState(StrEnum):
    """Lifecycle states for Sam's Mobile Security system."""
    DISARMED = "disarmed"
    ARMING = "arming"
    ARMED = "armed"
    TRIGGERED = "triggered"
    ALARMING = "alarming"
