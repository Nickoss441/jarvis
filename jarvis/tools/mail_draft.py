"""Local mail draft scaffold.

Writes drafts to a local JSONL file for safe phase-1 style operation.
"""
import json
import time
import uuid
from pathlib import Path
from typing import Any

from . import Tool


def make_mail_draft_tool(drafts_path: Path) -> Tool:
    drafts_path = Path(drafts_path).expanduser()

    def _handler(
        to: str,
        subject: str,
        body: str,
    ) -> dict[str, Any]:
        if not to.strip() or not subject.strip() or not body.strip():
            return {"error": "to, subject, and body are required"}

        draft = {
            "id": str(uuid.uuid4()),
            "ts": time.time(),
            "to": to,
            "subject": subject,
            "body": body,
        }

        drafts_path.parent.mkdir(parents=True, exist_ok=True)
        with drafts_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(draft, sort_keys=True) + "\n")

        return {
            "status": "draft_saved",
            "draft_id": draft["id"],
            "path": str(drafts_path),
        }

    return Tool(
        name="mail_draft",
        description="Create and store a local email draft (does not send).",
        input_schema={
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["to", "subject", "body"],
        },
        handler=_handler,
        tier="open",
    )
