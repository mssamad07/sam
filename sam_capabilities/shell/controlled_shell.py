"""
Controlled Shell Execution Capability for Sam.
Enforces command validation, risk classification, timeouts, and secret masking.
"""
import asyncio
import os
import re
from contextlib import suppress
from pathlib import Path
from typing import Any

from sam_capabilities.base import BaseSkill, ToolDefinition, ToolParameter, ToolResult
from sam_core.logger import get_logger, mask_sensitive_data
from sam_core.permissions.policy import RiskTier

logger = get_logger("capabilities.shell")

# Patterns strictly blacklisted from automated shell execution
HARD_BLOCKED_PATTERNS = [
    re.compile(r"(?i)\bformat\s+[a-z]:"),
    re.compile(r"(?i)\bdel\s+/[sfaq]*\s+[a-z]:\\windows"),
    re.compile(r"(?i)\brmdir\s+/[sq]*\s+[a-z]:\\windows"),
    re.compile(r"(?i)\breg\s+delete\b"),
    re.compile(r"(?i)\bbcdedit\b"),
    re.compile(r"(?i)\bdiskpart\b"),
]

# Read-only / inspection commands that can run under Tier 2 Review
READ_ONLY_PREFIXES = [
    "dir", "echo", "git status", "git log", "git diff", "pytest", "python --version",
    "git branch", "whoami", "hostname", "ipconfig", "systeminfo", "type"
]


def classify_command_risk(cmd: str) -> RiskTier:
    """Determine whether command is read-only or critical."""
    normalized = cmd.strip().lower()
    for prefix in READ_ONLY_PREFIXES:
        if normalized.startswith(prefix):
            return RiskTier.TIER_2_REVIEW
    return RiskTier.TIER_3_CRITICAL


class ControlledShellSkill(BaseSkill):
    """Executes validated terminal commands under safety guardrails."""

    @property
    def name(self) -> str:
        return "controlled_shell"

    @property
    def description(self) -> str:
        return "Run terminal commands safely with timeouts, risk gating, and secret masking."

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="execute_command",
                description="Execute a shell command with output capture. State-changing commands require confirmation.",
                risk_tier=RiskTier.TIER_3_CRITICAL,  # Default safety tier is Critical
                parameters=[
                    ToolParameter(name="command", type_str="string", description="Command line string to execute", required=True),
                    ToolParameter(name="cwd", type_str="string", description="Optional working directory", required=False, default=None),
                    ToolParameter(name="timeout_seconds", type_str="integer", description="Execution timeout", required=False, default=30),
                ],
            )
        ]

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ToolResult:
        if tool_name != "execute_command":
            return ToolResult(success=False, error=f"Unknown tool '{tool_name}'")

        command = arguments.get("command", "").strip()
        if not command:
            return ToolResult(success=False, error="Parameter 'command' cannot be empty.")

        # 1. Security Blacklist Check
        for pattern in HARD_BLOCKED_PATTERNS:
            if pattern.search(command):
                error_msg = f"SECURITY VIOLATION: Command '{command}' matches hard-blocked pattern."
                logger.error(error_msg)
                return ToolResult(success=False, error=error_msg)

        cwd = arguments.get("cwd")
        if cwd:
            cwd_path = Path(cwd).expanduser().resolve()
            if not cwd_path.exists() or not cwd_path.is_dir():
                return ToolResult(success=False, error=f"Working directory '{cwd}' does not exist.")
            working_dir = str(cwd_path)
        else:
            working_dir = os.getcwd()

        timeout = int(arguments.get("timeout_seconds", 30))

        # 2. Asynchronous Subprocess Execution
        logger.info(f"Running command: {command} in {working_dir} (timeout={timeout}s)")
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=float(timeout),
            )

            exit_code = process.returncode
            stdout_text = mask_sensitive_data(stdout_bytes.decode(errors="replace").strip())
            stderr_text = mask_sensitive_data(stderr_bytes.decode(errors="replace").strip())

            success = (exit_code == 0)
            return ToolResult(
                success=success,
                data={
                    "command": command,
                    "exit_code": exit_code,
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                },
                message=f"Command finished with exit code {exit_code}.",
            )

        except TimeoutError:
            logger.error(f"Command timed out after {timeout} seconds: {command}")
            with suppress(Exception):
                process.kill()
            return ToolResult(
                success=False,
                error=f"Command timed out after {timeout} seconds.",
            )
        except Exception as exc:
            logger.error(f"Execution error for command '{command}': {exc}")
            return ToolResult(success=False, error=str(exc))
