"""Calendar read scaffold with optional local ICS source.

Phase-safe implementation:
- If no ICS file is configured, returns an empty event list.
- Parsing is intentionally minimal (VEVENT + DTSTART/DTEND/SUMMARY/LOCATION).
 - On macOS, when no ICS file is present, falls back to Apple Calendar via osascript.
"""
from datetime import datetime, timezone
from pathlib import Path
import platform
import subprocess
from typing import Any

from . import Tool


def _read_apple_calendar_events(max_events: int) -> tuple[list[dict[str, Any]], str]:
    """Read upcoming Apple Calendar events on macOS using osascript.

    Returns (events, error_message). error_message is empty on success.
    """
    script = """
tell application "Calendar"
    set nowDate to current date
    set toDate to nowDate + (30 * days)
    set outLines to ""
    repeat with c in calendars
        set evs to (every event of c whose start date ≥ nowDate and start date ≤ toDate)
        repeat with e in evs
            set s to (start date of e) as string
            set t to (end date of e) as string
            set sm to (summary of e) as string
            set loc to ""
            try
                set loc to (location of e) as string
            end try
            set outLines to outLines & s & "\t" & t & "\t" & sm & "\t" & loc & "\n"
        end repeat
    end repeat
    return outLines
end tell
""".strip()

    try:
        result = subprocess.run(  # noqa: S603
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except Exception as exc:  # noqa: BLE001
        return [], f"apple_calendar_unavailable: {exc.__class__.__name__}"

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "osascript failed").strip()
        return [], f"apple_calendar_error: {detail[:160]}"

    events: list[dict[str, Any]] = []
    raw = result.stdout or ""
    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        start, end, summary, location = parts[:4]
        events.append(
            {
                "start": start,
                "end": end,
                "summary": summary,
                "location": location,
            }
        )
        if len(events) >= max(0, max_events):
            break
    return events, ""


def make_calendar_read_tool(calendar_ics_path: Path | None = None) -> Tool:
    source_path = Path(calendar_ics_path).expanduser() if calendar_ics_path else None

    def _handler(
        from_iso: str | None = None,
        to_iso: str | None = None,
        max_events: int = 10,
    ) -> dict[str, Any]:
        events: list[dict[str, Any]] = []

        if source_path is None or not source_path.exists():
            if platform.system() == "Darwin":
                apple_events, apple_error = _read_apple_calendar_events(max_events=max_events)
                return {
                    "status": "ok",
                    "source": "apple_calendar",
                    "events": apple_events,
                    "count": len(apple_events),
                    "message": (
                        "Apple Calendar fallback active."
                        if not apple_error
                        else f"Apple Calendar fallback failed ({apple_error})."
                    ),
                }
            return {
                "status": "ok",
                "source": "none",
                "events": events,
                "count": 0,
                "message": "No calendar source configured (JARVIS_CALENDAR_ICS).",
            }

        raw = source_path.read_text(encoding="utf-8", errors="ignore")
        current: dict[str, str] | None = None
        for line in raw.splitlines():
            line = line.strip()
            if line == "BEGIN:VEVENT":
                current = {}
                continue
            if line == "END:VEVENT":
                if current is not None:
                    events.append(
                        {
                            "start": current.get("DTSTART", ""),
                            "end": current.get("DTEND", ""),
                            "summary": current.get("SUMMARY", ""),
                            "location": current.get("LOCATION", ""),
                        }
                    )
                current = None
                continue
            if current is None or ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.split(";", 1)[0]
            if key in {"DTSTART", "DTEND", "SUMMARY", "LOCATION"}:
                current[key] = value

        # Time filtering uses lexical compare for ISO-like strings in this scaffold.
        if from_iso:
            events = [e for e in events if not e["start"] or e["start"] >= from_iso]
        if to_iso:
            events = [e for e in events if not e["start"] or e["start"] <= to_iso]

        events = events[: max(0, max_events)]
        return {
            "status": "ok",
            "source": str(source_path),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "events": events,
            "count": len(events),
        }

    return Tool(
        name="calendar_read",
        description="Read upcoming events from a configured local ICS calendar source.",
        input_schema={
            "type": "object",
            "properties": {
                "from_iso": {
                    "type": "string",
                    "description": "Optional lower bound timestamp (ISO-like)",
                },
                "to_iso": {
                    "type": "string",
                    "description": "Optional upper bound timestamp (ISO-like)",
                },
                "max_events": {
                    "type": "integer",
                    "description": "Maximum number of events to return",
                    "default": 10,
                },
            },
        },
        handler=_handler,
        tier="open",
    )
