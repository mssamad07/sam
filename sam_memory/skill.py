"""
Memory Skill exposing memory CRUD and recall capabilities to Sam's LLM agent.
"""
from typing import Any

from sam_capabilities.base import BaseSkill, ToolDefinition, ToolParameter, ToolResult
from sam_core.logger import get_logger
from sam_core.permissions.policy import RiskTier
from sam_memory.models import MemoryEntry
from sam_memory.semantic import SemanticMemoryEngine
from sam_memory.store import SQLiteMemoryStore

logger = get_logger("memory.skill")


class MemorySkill(BaseSkill):
    """Provides Sam with persistent memory across restarts and conversations."""

    def __init__(self, store: SQLiteMemoryStore | None = None) -> None:
        self.store = store or SQLiteMemoryStore()
        self.semantic_engine = SemanticMemoryEngine()

    @property
    def name(self) -> str:
        return "memory"

    @property
    def description(self) -> str:
        return "Long-term persistent and semantic memory management tools."

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="remember_fact",
                description="Save a key fact, preference, user information, or relationship to persistent memory.",
                parameters=[
                    ToolParameter(name="key", type="string", description="Short identifier or topic.", required=True),
                    ToolParameter(name="value", type="string", description="The fact or information to remember.", required=True),
                    ToolParameter(name="category", type="string", description="Category: profile, preference, fact, or reminder.", required=False),
                    ToolParameter(name="importance", type="integer", description="Importance level from 1 (low) to 5 (critical).", required=False),
                ],
                risk_tier=RiskTier.TIER_1_SAFE,
            ),
            ToolDefinition(
                name="recall_facts",
                description="Search long-term memory for facts, preferences, or saved details.",
                parameters=[
                    ToolParameter(name="query", type="string", description="Search query or keyword to recall.", required=True),
                    ToolParameter(name="category", type="string", description="Optional category filter.", required=False),
                ],
                risk_tier=RiskTier.TIER_1_SAFE,
            ),
            ToolDefinition(
                name="list_memories",
                description="List stored memories for user inspection.",
                parameters=[
                    ToolParameter(name="category", type="string", description="Optional category filter.", required=False),
                ],
                risk_tier=RiskTier.TIER_1_SAFE,
            ),
            ToolDefinition(
                name="forget_memory",
                description="Erase memories matching a topic or query from persistent storage.",
                parameters=[
                    ToolParameter(name="query", type="string", description="Search query or key to forget.", required=True),
                    ToolParameter(name="category", type="string", description="Optional category filter.", required=False),
                ],
                risk_tier=RiskTier.TIER_2_REVIEW,
            ),
        ]

    async def execute(
        self, tool_name: str, arguments: dict[str, Any], context: dict[str, Any] | None = None
    ) -> ToolResult:
        if tool_name == "remember_fact":
            key = arguments.get("key", "").strip()
            value = arguments.get("value", "").strip()
            category = arguments.get("category", "fact").strip()
            importance = int(arguments.get("importance", 3))
            if not key or not value:
                return ToolResult(success=False, error="Parameters 'key' and 'value' are required.")

            entry = MemoryEntry(key=key, value=value, category=category, importance=importance)
            saved = await self.store.add_memory(entry)
            return ToolResult(
                success=True,
                data={
                    "message": f"I've remembered that for you, Boss: {saved.key} = {saved.value}",
                    "id": saved.id,
                },
            )

        if tool_name == "recall_facts":
            query = arguments.get("query", "").strip()
            category = arguments.get("category")
            if not query:
                return ToolResult(success=False, error="Parameter 'query' is required.")

            # Search in SQLite store
            results = await self.store.search_memories(query, category=category, limit=5)
            # If standard search returned few results, apply semantic ranking over all items
            if not results:
                all_entries = await self.store.list_memories(category=category, limit=100)
                results = self.semantic_engine.rank(query, all_entries, limit=5)

            formatted = [
                {"key": r.entry.key, "value": r.entry.value, "category": r.entry.category, "score": r.score}
                for r in results
            ]
            return ToolResult(success=True, data={"count": len(formatted), "results": formatted})

        if tool_name == "list_memories":
            category = arguments.get("category")
            entries = await self.store.list_memories(category=category, limit=50)
            formatted = [
                {"key": e.key, "value": e.value, "category": e.category, "importance": e.importance}
                for e in entries
            ]
            return ToolResult(success=True, data={"count": len(formatted), "memories": formatted})

        if tool_name == "forget_memory":
            query = arguments.get("query", "").strip()
            category = arguments.get("category")
            if not query:
                return ToolResult(success=False, error="Parameter 'query' is required.")

            deleted_count = await self.store.forget(query, category=category)
            return ToolResult(
                success=True,
                data={
                    "message": f"Forgotten {deleted_count} memory items matching '{query}'.",
                    "deleted_count": deleted_count,
                },
            )

        return ToolResult(success=False, error=f"Unknown tool: {tool_name}")
