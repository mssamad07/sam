"""
Unit tests for WebSearchSkill and WebFetchSkill.
"""
import pytest

from sam_capabilities.web.fetcher import WebFetchSkill, clean_html
from sam_capabilities.web.search import WebSearchSkill


def test_clean_html_stripping():
    raw = """
    <html>
        <head><style>.ad { display: none; }</style></head>
        <body>
            <h1>Sam Assistant</h1>
            <script>alert('evil');</script>
            <p>A smart personal AI assistant for Windows.</p>
        </body>
    </html>
    """
    cleaned = clean_html(raw)
    assert "Sam Assistant" in cleaned
    assert "smart personal AI assistant" in cleaned
    assert "alert('evil')" not in cleaned
    assert "display: none" not in cleaned


@pytest.mark.asyncio
async def test_web_fetch_url_validation():
    skill = WebFetchSkill()
    res = await skill.execute("fetch_web_page", {"url": "not-a-valid-url"})
    assert res.success is False
    assert "http://" in res.error or "https://" in res.error


@pytest.mark.asyncio
async def test_web_search_query_validation():
    skill = WebSearchSkill()
    res = await skill.execute("search_web", {"query": ""})
    assert res.success is False
    assert "cannot be empty" in res.error
