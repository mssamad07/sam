"""
Web Search Capability for Sam.
Queries public search engines (DuckDuckGo / Open Search) without requiring paid API keys.
"""
import re
from typing import Any

import httpx

from sam_capabilities.base import BaseSkill, ToolDefinition, ToolParameter, ToolResult
from sam_core.logger import get_logger
from sam_core.permissions.policy import RiskTier

logger = get_logger("capabilities.web_search")


class WebSearchSkill(BaseSkill):
    """Provides web search capability."""

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Search the live internet for recent information, facts, and documentation."

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="search_web",
                description="Search the web for a query and return top web results.",
                risk_tier=RiskTier.TIER_1_SAFE,
                parameters=[
                    ToolParameter(name="query", type_str="string", description="Search query string", required=True),
                    ToolParameter(name="limit", type_str="integer", description="Max results (default: 5)", required=False, default=5),
                ],
            )
        ]

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ToolResult:
        if tool_name != "search_web":
            return ToolResult(success=False, error=f"Unknown tool '{tool_name}'")

        query = arguments.get("query", "").strip()
        if not query:
            return ToolResult(success=False, error="Parameter 'query' cannot be empty.")

        limit = int(arguments.get("limit", 5))

        try:
            # Query DuckDuckGo HTML search
            url = "https://html.duckduckgo.com/html/"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.post(url, data={"q": query}, headers=headers)
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"Search request failed with HTTP {resp.status_code}")

                html = resp.text

            # Parse search results using regex patterns
            results = []
            # Find result snippets
            links = re.findall(r'<a class="result__url"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html)
            snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', html)

            for i in range(min(len(links), limit)):
                url_match, title = links[i]
                clean_title = re.sub(r"<[^>]+>", "", title).strip()
                clean_snippet = re.sub(r"<[^>]+>", "", snippets[i]).strip() if i < len(snippets) else ""
                results.append({
                    "title": clean_title or f"Result {i+1}",
                    "url": url_match,
                    "snippet": clean_snippet,
                })

            if not results:
                # Fallback: simple status if no links parsed
                return ToolResult(
                    success=True,
                    data={"query": query, "count": 0, "results": [], "message": "No direct results found."},
                )

            return ToolResult(
                success=True,
                data={"query": query, "count": len(results), "results": results},
                message=f"Found {len(results)} web results for '{query}'.",
            )

        except Exception as exc:
            logger.error(f"Web search error for '{query}': {exc}")
            return ToolResult(success=False, error=f"Web search error: {exc}")
