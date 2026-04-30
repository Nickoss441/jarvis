"""Tests for voice_trigger module."""
import pytest
from jarvis.voice_trigger import (
    VoiceCommand,
    parse_voice_command,
    should_respond_vocally,
    extract_vocal_payload,
)


class TestParseVoiceCommand:
    """Test voice command trigger parsing."""
    
    def test_respond_vocally_pattern(self):
        """Test basic 'respond vocally: X' pattern."""
        cmd = parse_voice_command("respond vocally: status report")
        assert cmd is not None
        assert cmd.trigger_type == "respond_vocally"
        assert cmd.payload == "status report"
        assert cmd.raw_text == "respond vocally: status report"
    
    def test_respond_vocally_with_whitespace(self):
        """Test pattern with extra whitespace."""
        cmd = parse_voice_command("  respond vocally:   what is the weather  ")
        assert cmd is not None
        assert cmd.trigger_type == "respond_vocally"
        assert cmd.payload == "what is the weather"
    
    def test_respond_vocally_case_insensitive(self):
        """Test pattern is case-insensitive."""
        cmd = parse_voice_command("RESPOND VOCALLY: hello")
        assert cmd is not None
        assert cmd.trigger_type == "respond_vocally"
        assert cmd.payload == "hello"
    
    def test_respond_vocally_with_and_clause(self):
        """Test pattern with 'and' continuation (captures only command)."""
        cmd = parse_voice_command("respond vocally: status report and show the dashboard")
        assert cmd is not None
        assert cmd.trigger_type == "respond_vocally"
        assert cmd.payload == "status report"  # 'and' clause should not be captured
    
    def test_no_trigger_pattern(self):
        """Test text with no trigger pattern returns None."""
        cmd = parse_voice_command("just tell me the weather")
        assert cmd is None
    
    def test_empty_text(self):
        """Test empty text returns None."""
        cmd = parse_voice_command("")
        assert cmd is None
    
    def test_none_text(self):
        """Test None text returns None."""
        cmd = parse_voice_command(None)
        assert cmd is None
    
    def test_respond_vocally_with_complex_command(self):
        """Test pattern with complex multi-word command."""
        cmd = parse_voice_command("respond vocally: what is the current bitcoin price and market sentiment")
        assert cmd is not None
        assert cmd.trigger_type == "respond_vocally"
        assert "bitcoin price" in cmd.payload
        assert "market sentiment" in cmd.payload


class TestShouldRespondVocally:
    """Test vocal response detection."""
    
    def test_responds_true_for_vocal_command(self):
        """Test returns True for respond_vocally trigger."""
        cmd = VoiceCommand(
            trigger_type="respond_vocally",
            payload="test",
            raw_text="respond vocally: test",
        )
        assert should_respond_vocally(cmd) is True
    
    def test_responds_false_for_non_vocal_command(self):
        """Test returns False for other trigger types."""
        cmd = VoiceCommand(
            trigger_type="wake_word",
            payload="test",
            raw_text="jarvis",
        )
        assert should_respond_vocally(cmd) is False
    
    def test_responds_false_for_none(self):
        """Test returns False for None command."""
        assert should_respond_vocally(None) is False


class TestExtractVocalPayload:
    """Test payload extraction."""
    
    def test_extracts_payload(self):
        """Test payload extraction from command."""
        cmd = VoiceCommand(
            trigger_type="respond_vocally",
            payload="status report",
            raw_text="respond vocally: status report",
        )
        assert extract_vocal_payload(cmd) == "status report"
    
    def test_extracts_empty_from_none(self):
        """Test returns empty string for None."""
        assert extract_vocal_payload(None) == ""


class TestVoiceCommandIntegration:
    """Integration tests for full voice command workflow."""
    
    def test_parse_then_check_vocal(self):
        """Test parsing followed by vocal check."""
        text = "respond vocally: what is the weather"
        cmd = parse_voice_command(text)
        assert cmd is not None
        assert should_respond_vocally(cmd)
        assert extract_vocal_payload(cmd) == "what is the weather"
    
    def test_parse_then_check_non_vocal(self):
        """Test parsing non-vocal text."""
        text = "just tell me the weather"
        cmd = parse_voice_command(text)
        assert cmd is None
        assert not should_respond_vocally(cmd)
        assert extract_vocal_payload(cmd) == ""
    
    def test_multiple_commands_in_sequence(self):
        """Test handling multiple voice commands."""
        commands = [
            "respond vocally: status report",
            "just ask me about the weather",
            "respond vocally: what is bitcoin",
            "remind me tomorrow",
        ]
        
        parsed = [parse_voice_command(c) for c in commands]
        vocal = [should_respond_vocally(p) for p in parsed]
        
        # Expect alternating pattern
        assert vocal[0] is True   # vocal command
        assert vocal[1] is False  # non-vocal
        assert vocal[2] is True   # vocal command
        assert vocal[3] is False  # non-vocal
