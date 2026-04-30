#!/usr/bin/env python3
"""Simple test runner for voice_trigger module (no pytest required)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from jarvis.voice_trigger import (
    VoiceCommand,
    parse_voice_command,
    should_respond_vocally,
    extract_vocal_payload,
)


def test_respond_vocally_pattern():
    """Test basic 'respond vocally: X' pattern."""
    cmd = parse_voice_command("respond vocally: status report")
    assert cmd is not None, "Failed to parse basic pattern"
    assert cmd.trigger_type == "respond_vocally"
    assert cmd.payload == "status report"
    assert cmd.raw_text == "respond vocally: status report"
    print("✓ test_respond_vocally_pattern")


def test_respond_vocally_with_whitespace():
    """Test pattern with extra whitespace."""
    cmd = parse_voice_command("  respond vocally:   what is the weather  ")
    assert cmd is not None
    assert cmd.trigger_type == "respond_vocally"
    assert cmd.payload == "what is the weather"
    print("✓ test_respond_vocally_with_whitespace")


def test_respond_vocally_case_insensitive():
    """Test pattern is case-insensitive."""
    cmd = parse_voice_command("RESPOND VOCALLY: hello")
    assert cmd is not None
    assert cmd.trigger_type == "respond_vocally"
    assert cmd.payload == "hello"
    print("✓ test_respond_vocally_case_insensitive")


def test_respond_vocally_with_and_clause():
    """Test pattern with 'and' continuation (captures only command)."""
    cmd = parse_voice_command("respond vocally: status report and show the dashboard")
    assert cmd is not None
    assert cmd.trigger_type == "respond_vocally"
    assert cmd.payload == "status report"
    print("✓ test_respond_vocally_with_and_clause")


def test_no_trigger_pattern():
    """Test text with no trigger pattern returns None."""
    cmd = parse_voice_command("just tell me the weather")
    assert cmd is None
    print("✓ test_no_trigger_pattern")


def test_empty_text():
    """Test empty text returns None."""
    cmd = parse_voice_command("")
    assert cmd is None
    print("✓ test_empty_text")


def test_none_text():
    """Test None text returns None."""
    cmd = parse_voice_command(None)
    assert cmd is None
    print("✓ test_none_text")


def test_responds_true_for_vocal_command():
    """Test returns True for respond_vocally trigger."""
    cmd = VoiceCommand(
        trigger_type="respond_vocally",
        payload="test",
        raw_text="respond vocally: test",
    )
    assert should_respond_vocally(cmd) is True
    print("✓ test_responds_true_for_vocal_command")


def test_responds_false_for_non_vocal_command():
    """Test returns False for other trigger types."""
    cmd = VoiceCommand(
        trigger_type="wake_word",
        payload="test",
        raw_text="jarvis",
    )
    assert should_respond_vocally(cmd) is False
    print("✓ test_responds_false_for_non_vocal_command")


def test_responds_false_for_none():
    """Test returns False for None command."""
    assert should_respond_vocally(None) is False
    print("✓ test_responds_false_for_none")


def test_extracts_payload():
    """Test payload extraction from command."""
    cmd = VoiceCommand(
        trigger_type="respond_vocally",
        payload="status report",
        raw_text="respond vocally: status report",
    )
    assert extract_vocal_payload(cmd) == "status report"
    print("✓ test_extracts_payload")


def test_extracts_empty_from_none():
    """Test returns empty string for None."""
    assert extract_vocal_payload(None) == ""
    print("✓ test_extracts_empty_from_none")


def test_parse_then_check_vocal():
    """Test parsing followed by vocal check."""
    text = "respond vocally: what is the weather"
    cmd = parse_voice_command(text)
    assert cmd is not None
    assert should_respond_vocally(cmd)
    assert extract_vocal_payload(cmd) == "what is the weather"
    print("✓ test_parse_then_check_vocal")


def test_parse_then_check_non_vocal():
    """Test parsing non-vocal text."""
    text = "just tell me the weather"
    cmd = parse_voice_command(text)
    assert cmd is None
    assert not should_respond_vocally(cmd)
    assert extract_vocal_payload(cmd) == ""
    print("✓ test_parse_then_check_non_vocal")


def test_multiple_commands_in_sequence():
    """Test handling multiple voice commands."""
    commands = [
        "respond vocally: status report",
        "just ask me about the weather",
        "respond vocally: what is bitcoin",
        "remind me tomorrow",
    ]
    
    parsed = [parse_voice_command(c) for c in commands]
    vocal = [should_respond_vocally(p) for p in parsed]
    
    assert vocal[0] is True   # vocal command
    assert vocal[1] is False  # non-vocal
    assert vocal[2] is True   # vocal command
    assert vocal[3] is False  # non-vocal
    print("✓ test_multiple_commands_in_sequence")


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("VOICE TRIGGER TEST SUITE")
    print("="*70 + "\n")
    
    tests = [
        test_respond_vocally_pattern,
        test_respond_vocally_with_whitespace,
        test_respond_vocally_case_insensitive,
        test_respond_vocally_with_and_clause,
        test_no_trigger_pattern,
        test_empty_text,
        test_none_text,
        test_responds_true_for_vocal_command,
        test_responds_false_for_non_vocal_command,
        test_responds_false_for_none,
        test_extracts_payload,
        test_extracts_empty_from_none,
        test_parse_then_check_vocal,
        test_parse_then_check_non_vocal,
        test_multiple_commands_in_sequence,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: Unexpected error: {e}")
            failed += 1
    
    print(f"\n" + "="*70)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*70 + "\n")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
