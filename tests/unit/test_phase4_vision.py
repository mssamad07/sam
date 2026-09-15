"""
Unit tests for Sam Phase 4 Vision module and CameraManager.
"""
import pytest

from sam_core.ai.mock_provider import MockLLMProvider
from sam_vision.manager import CameraManager
from sam_vision.skill import VisionSkill
from sam_vision.states import CameraState


@pytest.mark.asyncio
async def test_camera_manager_lifecycle():
    cm = CameraManager()
    assert cm.state == CameraState.OFF
    assert not cm.is_active

    await cm.open_camera()
    assert cm.state == CameraState.ACTIVE
    assert cm.is_active

    await cm.close_camera()
    assert cm.state == CameraState.OFF
    assert not cm.is_active


@pytest.mark.asyncio
async def test_camera_manager_frame_capture():
    cm = CameraManager()
    # Mock frame generator returning 100 bytes
    cm.set_mock_frame_generator(lambda: b"TEST_CAMERA_FRAME_DATA_12345")

    frame = await cm.capture_frame()
    assert frame == b"TEST_CAMERA_FRAME_DATA_12345"
    # One-shot frame capture should safely return camera to OFF
    assert cm.state == CameraState.OFF


@pytest.mark.asyncio
async def test_vision_skill_tools():
    cm = CameraManager()
    cm.set_mock_frame_generator(lambda: b"CAMERA_PIXEL_DATA")
    mock_llm = MockLLMProvider("mock_vision")
    mock_llm.queue_response("You are holding a blue notebook.")

    skill = VisionSkill(camera_manager=cm, llm_provider=mock_llm)
    tools = {t.name: t for t in skill.get_tools()}

    assert "capture_camera_frame" in tools
    assert "capture_screen" in tools
    assert "get_camera_status" in tools

    # 1. get_camera_status
    status_res = await skill.execute("get_camera_status", {})
    assert status_res.success
    assert status_res.data["camera_state"] == "off"

    # 2. capture_camera_frame with LLM analysis
    frame_res = await skill.execute("capture_camera_frame", {"prompt": "What am I holding?"})
    assert frame_res.success
    assert "blue notebook" in frame_res.data["analysis"]

    # 3. capture_screen with fallback analysis
    screen_res = await skill.execute("capture_screen", {"prompt": "What is on the screen?"})
    assert screen_res.success
