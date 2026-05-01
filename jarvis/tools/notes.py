"""Local markdown notes vault. Read/write within a sandboxed directory."""
from pathlib import Path
from typing import Any

from . import Tool


def make_notes_tools(notes_dir: Path) -> list[Tool]:
    """Build the three notes tools bound to a specific directory.

    All paths in tool args are RELATIVE to `notes_dir`. The handlers reject
    anything that resolves outside it (path traversal defense).
    """
    notes_dir = Path(notes_dir).expanduser().resolve()
    notes_dir.mkdir(parents=True, exist_ok=True)

    def _safe_path(rel: str) -> Path | None:
        if not rel or rel.startswith("/") or ".." in Path(rel).parts:
            return None
        full = (notes_dir / rel).resolve()
        try:
            full.relative_to(notes_dir)
        except ValueError:
            return None
        # Block symlinks that could point outside the sandbox
        if full.exists() and full.is_symlink():
            return None
        return full

    def list_handler() -> dict[str, Any]:
        files = sorted(
            str(p.relative_to(notes_dir))
            for p in notes_dir.rglob("*.md")
        )
        return {"notes": files, "count": len(files)}

    def read_handler(path: str) -> dict[str, Any]:
        full = _safe_path(path)
        if full is None:
            return {"error": "path escapes notes directory"}
        if not full.exists():
            return {"error": f"note '{path}' not found"}
        return {"path": path, "content": full.read_text()}

    def write_handler(path: str, content: str) -> dict[str, Any]:
        full = _safe_path(path)
        if full is None:
            return {"error": "path escapes notes directory"}
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content)
        return {"path": path, "bytes_written": len(content.encode())}

    return [
        Tool(
            name="notes_list",
            description="List all markdown files in the local notes vault.",
            input_schema={"type": "object", "properties": {}},
            handler=list_handler,
        ),
        Tool(
            name="notes_read",
            description=(
                "Read a markdown note by relative path "
                "(e.g. 'projects/jarvis.md')."
            ),
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            handler=read_handler,
        ),
        Tool(
            name="notes_write",
            description=(
                "Create or overwrite a markdown note. Path is relative to the "
                "notes vault and must not contain '..' or start with '/'."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path, e.g. 'inbox/2026-04-25.md'",
                    },
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
            handler=write_handler,
        ),
    ]
