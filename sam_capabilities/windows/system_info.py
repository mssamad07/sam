"""
System Information Capability for Sam.
Retrieves CPU, RAM, battery, disk metrics, and active window state.
Tier 1 Safe operations.
"""
import platform
from typing import Any

import psutil

from sam_capabilities.base import BaseSkill, ToolDefinition, ToolParameter, ToolResult
from sam_core.logger import get_logger
from sam_core.permissions.policy import RiskTier

logger = get_logger("capabilities.system_info")


class SystemInfoSkill(BaseSkill):
    """Provides system diagnostics, resource utilization, and window context."""

    @property
    def name(self) -> str:
        return "system_info"

    @property
    def description(self) -> str:
        return "Inspect system metrics, hardware resources, battery, and active windows."

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="get_system_metrics",
                description="Get current CPU, RAM, battery status, and disk usage.",
                risk_tier=RiskTier.TIER_1_SAFE,
            ),
            ToolDefinition(
                name="get_os_info",
                description="Get OS platform, architecture, hostname, and Python version.",
                risk_tier=RiskTier.TIER_1_SAFE,
            ),
            ToolDefinition(
                name="list_running_processes",
                description="List running processes with highest memory usage.",
                risk_tier=RiskTier.TIER_1_SAFE,
                parameters=[
                    ToolParameter(
                        name="limit",
                        type_str="integer",
                        description="Max number of processes to return (default: 10)",
                        required=False,
                        default=10,
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
        if tool_name == "get_system_metrics":
            try:
                cpu = psutil.cpu_percent(interval=0.1)
                mem = psutil.virtual_memory()
                disk = psutil.disk_usage("/")
                battery = psutil.sensors_battery()

                battery_info = None
                if battery:
                    battery_info = {
                        "percent": battery.percent,
                        "power_plugged": battery.power_plugged,
                        "secsleft": battery.secsleft,
                    }

                return ToolResult(
                    success=True,
                    data={
                        "cpu_percent": cpu,
                        "ram_percent": mem.percent,
                        "ram_available_mb": round(mem.available / (1024 * 1024), 2),
                        "disk_percent": disk.percent,
                        "disk_free_gb": round(disk.free / (1024 * 1024 * 1024), 2),
                        "battery": battery_info,
                    },
                )
            except Exception as exc:
                return ToolResult(success=False, error=str(exc))

        elif tool_name == "get_os_info":
            return ToolResult(
                success=True,
                data={
                    "platform": platform.platform(),
                    "system": platform.system(),
                    "release": platform.release(),
                    "architecture": platform.machine(),
                    "python_version": platform.python_version(),
                },
            )

        elif tool_name == "list_running_processes":
            limit = int(arguments.get("limit", 10))
            processes = []
            for p in sorted(
                psutil.process_iter(["pid", "name", "memory_percent", "cpu_percent"]),
                key=lambda x: (x.info.get("memory_percent") or 0.0),
                reverse=True,
            )[:limit]:
                processes.append(p.info)
            return ToolResult(success=True, data={"count": len(processes), "processes": processes})

        return ToolResult(success=False, error=f"Unknown tool '{tool_name}' in {self.name}")
