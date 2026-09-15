"""
Unit tests for Phase 3 Windows capabilities: SystemInfo, SafeFiles, Apps, and Media.
"""
from pathlib import Path

import pytest

from sam_capabilities.windows.apps import ApplicationSkill
from sam_capabilities.windows.files import SafeFileSkill
from sam_capabilities.windows.media import MediaControlSkill
from sam_capabilities.windows.system_info import SystemInfoSkill


@pytest.mark.asyncio
async def test_system_info_metrics():
    skill = SystemInfoSkill()
    res = await skill.execute("get_system_metrics", {})
    assert res.success is True
    data = res.data
    assert "cpu_percent" in data
    assert "ram_percent" in data
    assert "disk_percent" in data

    os_res = await skill.execute("get_os_info", {})
    assert os_res.success is True
    assert "platform" in os_res.data


@pytest.mark.asyncio
async def test_safe_files_crud_and_guardrails(tmp_path: Path):
    skill = SafeFileSkill()
    test_file = tmp_path / "hello.txt"

    # 1. Write file
    write_res = await skill.execute(
        "write_file",
        {"path": str(test_file), "content": "Hello Sam from Phase 3!"},
    )
    assert write_res.success is True
    assert test_file.exists()

    # 2. Read file
    read_res = await skill.execute("read_file", {"path": str(test_file)})
    assert read_res.success is True
    assert "Hello Sam" in read_res.data["content"]

    # 3. List directory
    list_res = await skill.execute("list_directory", {"path": str(tmp_path)})
    assert list_res.success is True
    assert list_res.data["count"] >= 1

    # 4. Protected system directory guardrail
    protected_res = await skill.execute("write_file", {"path": "C:\\Windows\\System32\\bad.dll", "content": "bad"})
    assert protected_res.success is False
    assert "SECURITY GUARDRAIL" in protected_res.error

    # 5. Recycle file (safe trash)
    recycle_res = await skill.execute("recycle_file", {"path": str(test_file)})
    assert recycle_res.success is True
    assert not test_file.exists()


@pytest.mark.asyncio
async def test_application_skill_launch_and_kill():
    skill = ApplicationSkill()
    # Unknown process kill should report clean error rather than crash
    res = await skill.execute("kill_process", {"target": "non_existent_fake_process_99999.exe"})
    assert res.success is False
    assert "No matching running process" in res.error


@pytest.mark.asyncio
async def test_media_control_tools():
    skill = MediaControlSkill()
    tools = [t.name for t in skill.get_tools()]
    assert "volume_up" in tools
    assert "volume_down" in tools
    assert "toggle_mute" in tools
    assert "media_play_pause" in tools
