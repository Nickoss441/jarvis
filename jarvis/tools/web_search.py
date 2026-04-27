"""Web search via DuckDuckGo (no API key needed)."""
from typing import Any

from . import Tool


def _handler(query: str, max_results: int = 5) -> dict[str, Any]:
    DDGS = None
    try:
        # New upstream package name.
        from ddgs import DDGS  # type: ignore
    except ImportError:
        try:
            # Backward-compatible import for older environments.
            from duckduckgo_search import DDGS  # type: ignore
        except ImportError:
            return {
                "error": "search dependency missing. "
                         "Install with: pip install ddgs"
            }
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return {
            "results": [
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                }
                for r in results
            ]
        }
    except Exception as e:
        return {"error": f"search failed: {e}"}


web_search = Tool(
    name="web_search",
    description=(
        "Search the web via DuckDuckGo. Returns title, URL, and snippet for "
        "each hit. Use first; then web_fetch on the best URL to read the page."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {
                "type": "integer",
                "description": "Number of results (default 5)",
                "default": 5,
            },
        },
        "required": ["query"],
    },
    handler=_handler,
    tier="open",
)
