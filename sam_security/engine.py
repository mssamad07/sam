"""
Mobile Security and Anti-Theft Engine for Sam.
Coordinates sensor monitoring, intruder snapshots, siren alerts, and PIN security.
"""
import hashlib
import time
from typing import Any

from sam_core.events.bus import EventBus, get_event_bus
from sam_core.events.types import Event
from sam_core.logger import get_logger
from sam_security.states import SecurityState

logger = get_logger("security.engine")

SECURITY_STATE_CHANGED = "security.state_changed"
SECURITY_ALARM_TRIGGERED = "security.alarm_triggered"
SECURITY_INTRUDER_ALERT = "security.intruder_alert"


class MobileSecurityEngine:
    """
    State machine and control logic for Anti-Theft defense and intrusion detection.
    """

    def __init__(self, default_pin: str = "1234", event_bus: EventBus | None = None) -> None:
        self._state = SecurityState.DISARMED
        self._pin_hash = self._hash_pin(default_pin)
        self._event_bus = event_bus or get_event_bus()
        self._failed_unlock_attempts = 0
        self._last_alert: dict[str, Any] | None = None
        self._intruder_log: list[dict[str, Any]] = []

    @property
    def state(self) -> SecurityState:
        return self._state

    @property
    def is_armed(self) -> bool:
        return self._state in (SecurityState.ARMED, SecurityState.TRIGGERED, SecurityState.ALARMING)

    @property
    def intruder_log(self) -> list[dict[str, Any]]:
        return list(self._intruder_log)

    def _hash_pin(self, pin: str) -> str:
        return hashlib.sha256(pin.encode("utf-8")).hexdigest()

    def verify_pin(self, pin: str) -> bool:
        return self._hash_pin(pin) == self._pin_hash

    async def arm(self, pin: str) -> bool:
        """Arm the security system."""
        if not self.verify_pin(pin):
            logger.warning("Failed attempt to arm security system: invalid PIN")
            return False

        await self._transition_to(SecurityState.ARMED, reason="user_armed")
        return True

    async def disarm(self, pin: str) -> bool:
        """Disarm the security system."""
        if not self.verify_pin(pin):
            self._failed_unlock_attempts += 1
            logger.warning(f"Failed attempt to disarm security system: invalid PIN ({self._failed_unlock_attempts})")
            if self.is_armed and self._failed_unlock_attempts >= 3:
                await self.trigger_alarm("excessive_failed_pin_attempts")
            return False

        self._failed_unlock_attempts = 0
        await self._transition_to(SecurityState.DISARMED, reason="user_disarmed")
        return True

    async def trigger_alarm(self, reason: str, details: dict[str, Any] | None = None) -> None:
        """Trigger siren and defensive actions."""
        if self._state == SecurityState.ALARMING:
            return

        await self._transition_to(SecurityState.ALARMING, reason=reason)
        alert_data = {
            "reason": reason,
            "details": details or {},
            "timestamp": time.time(),
        }
        self._last_alert = alert_data
        self._intruder_log.append(alert_data)

        logger.critical(f"SECURITY ALARM TRIGGERED: {reason}")
        await self._event_bus.publish(
            Event(
                event_type=SECURITY_ALARM_TRIGGERED,
                payload=alert_data,
                source="security.engine",
            )
        )

    async def report_motion(self, acceleration: float, threshold: float = 2.5) -> None:
        """Handle accelerometer movement data while armed."""
        if self._state == SecurityState.ARMED and acceleration > threshold:
            logger.warning(f"Unauthorized motion detected while armed: acc={acceleration}")
            await self.trigger_alarm("unauthorized_movement", {"acceleration": acceleration})

    async def report_failed_unlock(self, attempt_count: int) -> None:
        """Handle failed device unlock report from Android client."""
        if self.is_armed and attempt_count >= 2:
            await self.trigger_alarm("failed_lockscreen_attempts", {"count": attempt_count})

    async def _transition_to(self, new_state: SecurityState, reason: str) -> None:
        old_state = self._state
        self._state = new_state
        logger.info(f"Security state: {old_state.value} -> {new_state.value} ({reason})")
        await self._event_bus.publish(
            Event(
                event_type=SECURITY_STATE_CHANGED,
                payload={"old_state": old_state.value, "new_state": new_state.value, "reason": reason},
                source="security.engine",
            )
        )
