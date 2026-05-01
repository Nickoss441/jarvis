"""Voice command trigger recognition and dispatch.

Handles special vocal-reply trigger phrases like "respond vocally: status report"
that instruct Jarvis to execute a command and speak the response aloud.
"""
import re
from dataclasses import dataclass
from typing import Optional


VOCAL_REPLY_PATTERN = r"respond\s+vocally:\s*(.+)(?:\s*$|\s+(?:and|then))"
"""Regex pattern matching 'respond vocally: <command>' phrases."""


@dataclass
class VoiceCommand:
    """Parsed voice command with trigger type and payload."""
    
    trigger_type: str  # "respond_vocally", "interrupt", "wake", etc.
    payload: str       # The actual command/phrase after trigger
    raw_text: str      # Original unparsed text


def parse_voice_command(text: str) -> Optional[VoiceCommand]:
    """Parse a voice input for special command triggers.
    
    Recognizes:
    - "respond vocally: <command>" → trigger_type="respond_vocally", payload="<command>"
    - Returns None if no recognized trigger pattern.
    
    Args:
        text: Raw voice transcript from STT
        
    Returns:
        VoiceCommand if trigger found, None otherwise
    """
    text = (text or "").strip()
    if not text:
        return None
    
    # Check for vocal reply trigger: "respond vocally: status report"
    match = re.search(VOCAL_REPLY_PATTERN, text, re.IGNORECASE)
    if match:
        command = match.group(1).strip()
        return VoiceCommand(
            trigger_type="respond_vocally",
            payload=command,
            raw_text=text,
        )
    
    # No recognized trigger
    return None


def should_respond_vocally(command: VoiceCommand) -> bool:
    """Check if command requires vocal response.
    
    Returns True if trigger_type is "respond_vocally", False otherwise.
    """
    if not command:
        return False
    return command.trigger_type == "respond_vocally"


def extract_vocal_payload(command: VoiceCommand) -> str:
    """Extract the actual command to execute from a voice command.
    
    For "respond vocally: status report" → returns "status report"
    """
    return command.payload if command else ""


__all__ = [
    "VoiceCommand",
    "parse_voice_command",
    "should_respond_vocally",
    "extract_vocal_payload",
    "VOCAL_REPLY_PATTERN",
]
