"""PDF text extraction tool."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import Tool


def _handler(path: str, max_pages: int = 5) -> dict[str, Any]:
    pdf_path = Path(path).expanduser()
    if not pdf_path.exists():
        return {"error": f"file not found: {pdf_path}"}

    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return {"error": "pypdf is not installed. Install with: pip install pypdf"}

    pages_to_read = max(1, min(int(max_pages), 100))

    try:
        reader = PdfReader(str(pdf_path))
        texts: list[dict[str, Any]] = []
        for idx, page in enumerate(reader.pages[:pages_to_read]):
            text = (page.extract_text() or "").strip()
            texts.append(
                {
                    "page": idx + 1,
                    "chars": len(text),
                    "text": text,
                }
            )
        return {
            "file": str(pdf_path),
            "total_pages": len(reader.pages),
            "returned_pages": len(texts),
            "pages": texts,
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": f"pdf extraction failed: {exc}"}


pdf_reader = Tool(
    name="pdf_reader",
    description="Extract text from PDF files for summarization and analysis.",
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute or relative path to a PDF file"},
            "max_pages": {
                "type": "integer",
                "description": "Maximum number of pages to read (default 5)",
                "default": 5,
            },
        },
        "required": ["path"],
    },
    handler=_handler,
    tier="open",
)
