"""
Web Page Fetching and Reading Capability for Sam.
Retrieves remote web pages, strips HTML boilerplate, and extracts readable text.
"""
import re
from typing import Any

import httpx

from sam_capabilities.base import BaseSkill, ToolDefinition, ToolParameter, ToolResult
from sam_core.logger import get_logger
from sam_core.permissions.policy import RiskTier

logger = get_logger("capabilities.web_fetch")


def clean_html(raw_html: str) -> str:
    """Strip scripts, styles, and tags to extract readable content."""
    # Remove script and style elements
    text = re.sub(r"<script.*?</script>", " ", raw_html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    # Remove all HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


class WebFetchSkill(BaseSkill):
    """Fetches and cleans web pages."""

    @property
    def name(self) -> str:
        return "web_fetch"

    @property
    def description(self) -> str:
        return "Fetch and read the plain text content of a web page URL."

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="fetch_web_page",
                description="Fetch the text contents of a public URL (limited to 32KB).",
                risk_tier=RiskTier.TIER_1_SAFE,
                parameters=[
                    ToolParameter(name="url", type_str="string", description="Full HTTP/HTTPS URL", required=True),
                ],
            )
        ]

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ToolResult:
        if tool_name != "fetch_web_page":
            return ToolResult(success=False, error=f"Unknown tool '{tool_name}'")

        url = arguments.get("url", "").strip()
        if not url:
            return ToolResult(success=False, error="Parameter 'url' cannot be empty.")

        if not (url.startswith("http://") or url.startswith("https://")):
            return ToolResult(success=False, error="URL must start with http:// or https://")

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"HTTP request failed with code {resp.status_code}")

                raw_html = resp.text

            clean_text = clean_html(raw_html)[:32768]
            return ToolResult(
                success=True,
                data={
                    "url": url,
                    "title": resp.headers.get("title", ""),
                    "content": clean_text,
                    "length": len(clean_text),
                },
                message=f"Fetched {len(clean_text)} characters from '{url}'.",
            )

        except Exception as exc:
            logger.error(f"Error fetching URL '{url}': {exc}")
            return ToolResult(success=False, error=f"Failed to fetch URL: {exc}")
