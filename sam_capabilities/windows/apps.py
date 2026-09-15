"""
Application and Process Management Skill for Sam.
Supports launching installed apps and terminating processes (Tier 3 gated).
"""
import os
import subprocess
from typing import Any

import psutil

from sam_capabilities.base import BaseSkill, ToolDefinition, ToolParameter, ToolResult
from sam_core.logger import get_logger
from sam_core.permissions.policy import RiskTier

logger = get_logger("capabilities.apps")

# Common Windows App shortcuts/executables
KNOWN_APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "explorer": "explorer.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "taskmgr": "taskmgr.exe",
    "edge": "msedge.exe",
    "chrome": "chrome.exe",
}


class ApplicationSkill(BaseSkill):
    """Manages application lifecycle and process monitoring."""

    @property
    def name(self) -> str:
        return "applications"

    @property
    def description(self) -> str:
        return "Launch applications, inspect processes, and terminate tasks."

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="launch_application",
                description="Launch an application by common name or executable path (e.g., 'notepad', 'calc').",
                risk_tier=RiskTier.TIER_2_REVIEW,
                parameters=[
                    ToolParameter(
                        name="app_name",
                        type_str="string",
                        description="Application name or executable path",
                        required=True,
                    )
                ],
            ),
            ToolDefinition(
                name="kill_process",
                description="Terminate a running process by PID or process name. CRITICAL: Requires user confirmation.",
                risk_tier=RiskTier.TIER_3_CRITICAL,
                parameters=[
                    ToolParameter(
                        name="target",
                        type_str="string",
                        description="Process name (e.g. 'notepad.exe') or PID number",
                        required=True,
                    )
                ],
            ),
        ]

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ToolResult:
        if tool_name == "launch_application":
            app = arguments.get("app_name", "").strip()
            if not app:
                return ToolResult(success=False, error="Parameter 'app_name' cannot be empty.")

            exe = KNOWN_APPS.get(app.lower(), app)
            try:
                # Use startfile on Windows for seamless shell resolution
                if hasattr(os, "startfile"):
                    os.startfile(exe)
                else:
                    subprocess.Popen([exe], shell=True)

                logger.info(f"Launched application '{exe}'")
                return ToolResult(
                    success=True,
                    data={"launched": True, "target": exe},
                    message=f"Application '{app}' launched successfully.",
                )
            except Exception as exc:
                logger.error(f"Failed to launch '{app}': {exc}")
                return ToolResult(success=False, error=f"Failed to launch '{app}': {exc}")

        elif tool_name == "kill_process":
            target = arguments.get("target", "").strip()
            if not target:
                return ToolResult(success=False, error="Parameter 'target' cannot be empty.")

            killed_count = 0
            killed_pids = []

            # Check if target is a PID
            if target.isdigit():
                pid = int(target)
                try:
                    p = psutil.Process(pid)
                    name = p.name()
                    p.terminate()
                    killed_count = 1
                    killed_pids.append(pid)
                    logger.info(f"Terminated process {pid} ({name})")
                except psutil.NoSuchProcess:
                    return ToolResult(success=False, error=f"No process found with PID {pid}.")
                except Exception as exc:
                    return ToolResult(success=False, error=f"Failed to terminate PID {pid}: {exc}")
            else:
                # Target is process name
                for p in psutil.process_iter(["pid", "name"]):
                    try:
                        if p.info["name"] and p.info["name"].lower() == target.lower():
                            p.terminate()
                            killed_count += 1
                            killed_pids.append(p.info["pid"])
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

            if killed_count == 0:
                return ToolResult(success=False, error=f"No matching running process found for '{target}'.")

            return ToolResult(
                success=True,
                data={"killed_count": killed_count, "pids": killed_pids, "target": target},
                message=f"Terminated {killed_count} process(es) matching '{target}'.",
            )

        return ToolResult(success=False, error=f"Unknown tool '{tool_name}' in {self.name}")
