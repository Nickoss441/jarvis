"""Fetch a URL and return cleaned text. Uses readability for HTML pages."""
from typing import Any

from . import Tool


def _handler(url: str, max_chars: int = 8000) -> dict[str, Any]:
    try:
        import httpx
    except ImportError:
        return {"error": "httpx not installed. pip install httpx"}

    try:
        resp = httpx.get(
            url,
            timeout=15.0,
            follow_redirects=True,
            headers={"User-Agent": "Jarvis/0.1 (personal agent)"},
        )
        resp.raise_for_status()
    except Exception as e:
        return {"error": f"fetch failed: {e}"}

    content_type = resp.headers.get("content-type", "")
    if "text/html" not in content_type:
        return {
            "url": str(resp.url),
            "content_type": content_type,
            "text": resp.text[:max_chars],
        }

    title = ""
    try:
        from readability import Document
        from bs4 import BeautifulSoup
        doc = Document(resp.text)
        title = doc.title() or ""
        soup = BeautifulSoup(doc.summary(), "html.parser")
        text = soup.get_text(separator="\n", strip=True)
    except ImportError:
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            title = soup.title.string if soup.title else ""
            text = soup.get_text(separator="\n", strip=True)
        except ImportError:
            text = resp.text  # last resort: raw HTML

    return {
        "url": str(resp.url),
        "title": title,
        "text": text[:max_chars],
        "truncated": len(text) > max_chars,
    }


web_fetch = Tool(
    name="web_fetch",
    description=(
        "Fetch a URL and return its main text content (HTML pages are cleaned "
        "via readability). Use after web_search to read the chosen page."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "max_chars": {
                "type": "integer",
                "description": "Truncate to this many characters (default 8000)",
                "default": 8000,
            },
        },
        "required": ["url"],
    },
    handler=_handler,
    tier="open",
)
