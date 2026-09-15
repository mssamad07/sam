"""
Base interfaces and data structures for modular skills and capabilities in Sam.
Provides extensible foundations for tools, schema exports, and safe execution results.
"""
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from sam_core.permissions.policy import RiskTier


class ToolParameter(BaseModel):
    """Specification of an input argument for a tool."""
    name: str
    type_str: str = "string"
    description: str
    required: bool = True
    default: Any | None = None


class ToolDefinition(BaseModel):
    """Specification of a callable function/tool provided by a skill."""
    name: str
    description: str
    risk_tier: RiskTier = RiskTier.TIER_1_SAFE
    parameters: list[ToolParameter] = Field(default_factory=list)
    parameters_schema: dict[str, Any] | None = None

    def to_gemini_dict(self) -> dict[str, Any]:
        """Convert tool definition to Gemini function declaration schema."""
        if self.parameters_schema:
            return {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema,
            }

        properties = {}
        required = []
        for param in self.parameters:
            properties[param.name] = {
                "type": param.type_str,
                "description": param.description,
            }
            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "OBJECT",
                "properties": properties,
                "required": required,
            },
        }

    def to_openai_dict(self) -> dict[str, Any]:
        """Convert tool definition to OpenAI function definition schema."""
        if self.parameters_schema:
            return {
                "type": "function",
                "function": {
                    "name": self.name,
                    "description": self.description,
                    "parameters": self.parameters_schema,
                },
            }

        properties = {}
        required = []
        for param in self.parameters:
            properties[param.name] = {
                "type": param.type_str,
                "description": param.description,
            }
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


class ToolResult(BaseModel):
    """Standardized output returned by any tool execution."""
    success: bool
    data: Any = None
    error: str | None = None
    confirmation_required: bool = False
    confirmation_token: str | None = None
    message: str | None = None


class BaseSkill(ABC):
    """
    Abstract base class for all Sam capabilities and skills.
    Any new tool, capability, or user skill inherits from BaseSkill.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this skill."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this skill provides."""

    @property
    def version(self) -> str:
        """Skill version string."""
        return "0.1.0"

    @abstractmethod
    def get_tools(self) -> list[ToolDefinition]:
        """Return the list of tools declared by this skill."""

    @abstractmethod
    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ToolResult:
        """
        Execute a tool declared by this skill.
        Must return a structured ToolResult.
        """
