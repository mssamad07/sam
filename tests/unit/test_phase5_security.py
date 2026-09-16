"""
Unit tests for Sam Phase 5 Mobile Security and Anti-Theft Skill.
"""
import pytest

from sam_security.engine import MobileSecurityEngine
from sam_security.skill import MobileSecuritySkill
from sam_security.states import SecurityState


@pytest.mark.asyncio
async def test_security_engine_arm_disarm_pin():
    engine = MobileSecurityEngine(default_pin="4321")
    assert engine.state == SecurityState.DISARMED
    assert not engine.is_armed

    # Incorrect PIN cannot arm
    armed_fail = await engine.arm("0000")
    assert not armed_fail
    assert not engine.is_armed

    # Correct PIN arms system
    armed_ok = await engine.arm("4321")
    assert armed_ok
    assert engine.state == SecurityState.ARMED
    assert engine.is_armed

    # Incorrect PIN disarm fails
    disarm_fail = await engine.disarm("9999")
    assert not disarm_fail
    assert engine.is_armed

    # Correct PIN disarms
    disarm_ok = await engine.disarm("4321")
    assert disarm_ok
    assert engine.state == SecurityState.DISARMED


@pytest.mark.asyncio
async def test_security_engine_alarm_triggers():
    engine = MobileSecurityEngine(default_pin="1234")
    await engine.arm("1234")

    # Excessive failed disarm attempts trigger alarm
    await engine.disarm("0000")
    await engine.disarm("0000")
    await engine.disarm("0000")

    assert engine.state == SecurityState.ALARMING
    assert len(engine.intruder_log) >= 1

    # Motion while armed triggers alarm
    engine2 = MobileSecurityEngine(default_pin="1234")
    await engine2.arm("1234")
    await engine2.report_motion(acceleration=5.0)
    assert engine2.state == SecurityState.ALARMING


@pytest.mark.asyncio
async def test_mobile_security_skill():
    engine = MobileSecurityEngine(default_pin="9876")
    skill = MobileSecuritySkill(engine=engine)

    # 1. get_security_status
    status_res = await skill.execute("get_security_status", {})
    assert status_res.success
    assert status_res.data["state"] == "disarmed"

    # 2. arm_security
    arm_res = await skill.execute("arm_security", {"pin": "9876"})
    assert arm_res.success
    assert arm_res.data["state"] == "armed"

    # 3. trigger_panic_alarm
    panic_res = await skill.execute("trigger_panic_alarm", {"reason": "user_emergency"})
    assert panic_res.success
    assert panic_res.data["state"] == "alarming"

    # 4. disarm_security
    disarm_res = await skill.execute("disarm_security", {"pin": "9876"})
    assert disarm_res.success
    assert disarm_res.data["state"] == "disarmed"
