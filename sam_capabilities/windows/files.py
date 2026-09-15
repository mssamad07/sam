"""
Safe File Operations Capability for Sam.
Enforces system path blacklisting, safe trash recycling, and permission gating.
"""
from pathlib import Path
from typing import Any

from send2trash import send2trash

from sam_capabilities.base import BaseSkill, ToolDefinition, ToolParameter, ToolResult
from sam_core.logger import get_logger
from sam_core.permissions.manager import permission_manager
from sam_core.permissions.policy import RiskTier

logger = get_logger("capabilities.files")


class SafeFileSkill(BaseSkill):
    """File operations protected by guardrails and Recycle Bin safety."""

    @property
    def name(self) -> str:
        return "safe_files"

    @property
    def description(self) -> str:
        return "List directories, read/write files, and safely recycle files/folders."

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="list_directory",
                description="List files and folders within a directory.",
                risk_tier=RiskTier.TIER_1_SAFE,
                parameters=[
                    ToolParameter(
                        name="path",
                        type_str="string",
                        description="Directory path to inspect",
                        required=True,
                    )
                ],
            ),
            ToolDefinition(
                name="read_file",
                description="Read contents of a text file (limited to first 64KB).",
                risk_tier=RiskTier.TIER_1_SAFE,
                parameters=[
                    ToolParameter(
                        name="path",
                        type_str="string",
                        description="Path to the file to read",
                        required=True,
                    )
                ],
            ),
            ToolDefinition(
                name="write_file",
                description="Create or update a text file at the given path.",
                risk_tier=RiskTier.TIER_2_REVIEW,
                parameters=[
                    ToolParameter(name="path", type_str="string", description="Target file path", required=True),
                    ToolParameter(name="content", type_str="string", description="Text content to write", required=True),
                    ToolParameter(name="overwrite", type_str="boolean", description="Whether to overwrite existing", required=False, default=True),
                ],
            ),
            ToolDefinition(
                name="recycle_file",
                description="Safely move a file or folder to the Recycle Bin. CRITICAL: Requires user confirmation.",
                risk_tier=RiskTier.TIER_3_CRITICAL,
                parameters=[
                    ToolParameter(
                        name="path",
                        type_str="string",
                        description="Path of the file or folder to move to Recycle Bin",
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
        raw_path = arguments.get("path", "").strip()
        if not raw_path:
            return ToolResult(success=False, error="Parameter 'path' cannot be empty.")

        target_path = Path(raw_path).expanduser().resolve()

        # Guardrail check against protected paths
        if permission_manager.is_path_protected(str(target_path)):
            error_msg = f"SECURITY GUARDRAIL: Path '{target_path}' is a protected Windows system path and cannot be manipulated."
            logger.error(error_msg)
            return ToolResult(success=False, error=error_msg)

        if tool_name == "list_directory":
            if not target_path.exists():
                return ToolResult(success=False, error=f"Directory '{target_path}' does not exist.")
            if not target_path.is_dir():
                return ToolResult(success=False, error=f"Path '{target_path}' is not a directory.")

            entries = []
            for child in sorted(target_path.iterdir())[:100]:
                entries.append({
                    "name": child.name,
                    "is_dir": child.is_dir(),
                    "size_bytes": child.stat().st_size if child.is_file() else None,
                })
            return ToolResult(success=True, data={"path": str(target_path), "count": len(entries), "entries": entries})

        elif tool_name == "read_file":
            if not target_path.exists():
                return ToolResult(success=False, error=f"File '{target_path}' does not exist.")
            if not target_path.is_file():
                return ToolResult(success=False, error=f"Path '{target_path}' is not a file.")

            try:
                content = target_path.read_text(encoding="utf-8", errors="replace")[:65536]
                return ToolResult(success=True, data={"path": str(target_path), "content": content})
            except Exception as exc:
                return ToolResult(success=False, error=f"Failed to read file: {exc}")

        elif tool_name == "write_file":
            overwrite = arguments.get("overwrite", True)
            content = arguments.get("content", "")

            if target_path.exists() and not overwrite:
                return ToolResult(success=False, error=f"File '{target_path}' already exists and overwrite is False.")

            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(content, encoding="utf-8")
                return ToolResult(
                    success=True,
                    data={"path": str(target_path), "bytes_written": len(content.encode("utf-8"))},
                    message=f"File '{target_path.name}' written successfully.",
                )
            except Exception as exc:
                return ToolResult(success=False, error=f"Failed to write file: {exc}")

        elif tool_name == "recycle_file":
            if not target_path.exists():
                return ToolResult(success=False, error=f"Target '{target_path}' does not exist.")

            try:
                send2trash(str(target_path))
                logger.info(f"Safely moved '{target_path}' to Recycle Bin")
                return ToolResult(
                    success=True,
                    data={"recycled": True, "path": str(target_path)},
                    message=f"Item '{target_path.name}' moved safely to Recycle Bin.",
                )
            except Exception as exc:
                logger.error(f"Failed to recycle '{target_path}': {exc}")
                return ToolResult(success=False, error=f"Recycle Bin operation failed: {exc}")

        return ToolResult(success=False, error=f"Unknown tool '{tool_name}' in {self.name}")
