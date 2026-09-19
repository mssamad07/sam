"""
Browser Automation & Web Navigation Capability for Sam.
Enables opening URLs, searching Google/YouTube, and automating browser tasks.
"""
import urllib.parse
import webbrowser
from typing import Any

from sam_capabilities.base import BaseSkill, ToolDefinition, ToolParameter, ToolResult
from sam_core.logger import get_logger

logger = get_logger("capabilities.browser_agent")


class BrowserAutomationSkill(BaseSkill):
    """Automates web browsing, YouTube playback, and web search."""

    @property
    def name(self) -> str:
        return "browser_automation"

    @property
    def description(self) -> str:
        return "Open websites, search and play YouTube videos, and navigate the web in browser."

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="browser_open_url",
                description="Open a specific URL in the default web browser.",
                parameters=[
                    ToolParameter(
                        name="url",
                        type="string",
                        description="Full web URL to open (e.g. https://www.google.com)",
                        required=True,
                    ),
                ],
            ),
            ToolDefinition(
                name="browser_search_youtube",
                description="Search YouTube and open video results or play a song/video.",
                parameters=[
                    ToolParameter(
                        name="query",
                        type="string",
                        description="Search keywords or video name (e.g. 'Arijit Singh lo-fi songs')",
                        required=True,
                    ),
                ],
            ),
            ToolDefinition(
                name="browser_search_google",
                description="Search Google directly in the browser and display results.",
                parameters=[
                    ToolParameter(
                        name="query",
                        type="string",
                        description="Search query to search on Google",
                        required=True,
                    ),
                ],
            ),
        ]

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> ToolResult:
        if tool_name == "browser_open_url":
            url = arguments.get("url", "").strip()
            if not url:
                return ToolResult(success=False, error="URL cannot be empty.")
            if not (url.startswith("http://") or url.startswith("https://")):
                url = "https://" + url

            try:
                webbrowser.open(url)
                logger.info(f"Opened URL in browser: {url}")
                return ToolResult(
                    success=True,
                    data={"url": url, "status": "opened"},
                    summary=f"Opened {url} in web browser.",
                )
            except Exception as exc:
                return ToolResult(success=False, error=f"Failed to open browser: {exc}")

        elif tool_name == "browser_search_youtube":
            query = arguments.get("query", "").strip()
            if not query:
                return ToolResult(success=False, error="Query cannot be empty.")

            encoded = urllib.parse.quote_plus(query)
            yt_url = f"https://www.youtube.com/results?search_query={encoded}"
            try:
                webbrowser.open(yt_url)
                logger.info(f"YouTube search opened: {query}")
                return ToolResult(
                    success=True,
                    data={"query": query, "url": yt_url},
                    summary=f"Searched YouTube for '{query}' and opened results.",
                )
            except Exception as exc:
                return ToolResult(success=False, error=f"Failed to search YouTube: {exc}")

        elif tool_name == "browser_search_google":
            query = arguments.get("query", "").strip()
            if not query:
                return ToolResult(success=False, error="Query cannot be empty.")

            encoded = urllib.parse.quote_plus(query)
            search_url = f"https://www.google.com/search?q={encoded}"
            try:
                webbrowser.open(search_url)
                logger.info(f"Google search opened: {query}")
                return ToolResult(
                    success=True,
                    data={"query": query, "url": search_url},
                    summary=f"Searched Google for '{query}' in browser.",
                )
            except Exception as exc:
                return ToolResult(success=False, error=f"Failed to search Google: {exc}")

        return ToolResult(success=False, error=f"Unknown tool '{tool_name}' in browser_automation skill.")
