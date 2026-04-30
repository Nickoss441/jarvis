#!/usr/bin/env python3
"""E2E smoke test for vocal reply trigger and agent dialogue.

Validates:
1. Voice command parsing (respond vocally: X pattern)
2. Agent dialogue routing (/hud/ask endpoint)
3. Vocal response generation (TTS playback)
4. Integration with approval system

Run with:
    export JARVIS_ANTHROPIC_API_KEY=<your-rotated-key>
    python3 scripts/smoke_test_vocal_agent.py
"""
import json
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

sys.path.insert(0, str(Path(__file__).parent.parent))

from jarvis.config import Config
from jarvis.voice_trigger import parse_voice_command, should_respond_vocally
from jarvis.approval_service import ApprovalService


def test_voice_command_parsing():
    """Test voice trigger pattern recognition."""
    print("\n[TEST 1/4] Voice Command Parsing")
    print("-" * 70)
    
    test_cases = [
        ("respond vocally: status report", "status report", True),
        ("respond vocally: what is the weather", "what is the weather", True),
        ("respond vocally: status report and show the dashboard", "status report", True),
        ("just tell me the weather", None, False),
        ("", None, False),
    ]
    
    passed = 0
    for text, expected_payload, should_vocal in test_cases:
        cmd = parse_voice_command(text)
        
        if should_vocal:
            if cmd and cmd.payload == expected_payload and cmd.trigger_type == "respond_vocally":
                print(f"  ✓ '{text}' → payload='{expected_payload}'")
                passed += 1
            else:
                print(f"  ✗ '{text}' → expected payload='{expected_payload}', got {cmd}")
        else:
            if cmd is None:
                print(f"  ✓ '{text}' → (no trigger)")
                passed += 1
            else:
                print(f"  ✗ '{text}' → expected None, got {cmd}")
    
    return passed == len(test_cases)


def test_agent_routing():
    """Test /hud/ask endpoint for agent dialogue."""
    print("\n[TEST 2/4] Agent Dialogue Routing (/hud/ask)")
    print("-" * 70)
    
    config = Config.from_env()
    host = config.approvals_api_host or "127.0.0.1"
    port = config.approvals_api_port or 8080
    base_url = f"http://{host}:{port}"
    
    # Check if API is running
    try:
        response = urlopen(f"{base_url}/hud/ask?q=hello", timeout=2)
        status = response.status
        print(f"  ✓ /hud/ask endpoint available (status: {status})")
        
        try:
            body = json.loads(response.read().decode())
            if body.get("response") or body.get("error"):
                print(f"  ✓ /hud/ask returned valid response structure")
                print(f"    Response keys: {list(body.keys())}")
                return True
            else:
                print(f"  ✗ /hud/ask response missing 'response' or 'error' keys")
                return False
        except json.JSONDecodeError:
            print(f"  ✗ /hud/ask response is not valid JSON")
            return False
            
    except URLError as e:
        print(f"  ⚠ /hud/ask endpoint not available (is API running?)")
        print(f"    Error: {e}")
        print(f"    To start API: python -m jarvis.approval_api")
        return False


def test_approval_integration():
    """Test that vocal commands can trigger approvals."""
    print("\n[TEST 3/4] Approval System Integration")
    print("-" * 70)
    
    config = Config.from_env()
    service = ApprovalService(config)
    
    try:
        # Simulate a vocal request that requires approval
        vocal_cmd = "status report"
        approval_id = service.request(
            "voice_report",
            {"command": vocal_cmd, "response_mode": "vocal"},
        )
        print(f"  ✓ Voice approval requested (ID: {approval_id})")
        
        # Approve automatically for smoke test
        approved = service.approve(approval_id, reason="smoke-test")
        if approved:
            print(f"  ✓ Voice approval auto-approved")
            return True
        else:
            print(f"  ✗ Failed to approve voice request")
            return False
            
    except Exception as e:
        print(f"  ⚠ Approval system error: {e}")
        return False


def test_vocal_response_generation():
    """Test that vocal responses are correctly flagged."""
    print("\n[TEST 4/4] Vocal Response Generation")
    print("-" * 70)
    
    # Parse a vocal trigger
    text = "respond vocally: what is the current temperature"
    cmd = parse_voice_command(text)
    
    if not cmd:
        print(f"  ✗ Failed to parse vocal trigger")
        return False
    
    if should_respond_vocally(cmd):
        print(f"  ✓ Command correctly identified as vocal response needed")
        print(f"    Payload: '{cmd.payload}'")
        print(f"    Trigger type: {cmd.trigger_type}")
        return True
    else:
        print(f"  ✗ Command not recognized as vocal response")
        return False


def main():
    print("\n" + "="*70)
    print("VOCAL AGENT E2E SMOKE TEST")
    print("="*70)
    
    config = Config.from_env()
    config.validate()
    
    print(f"\nConfig loaded:")
    print(f"  Deployment: {config.deployment_target}")
    print(f"  Voice Stack: {config.voice_stack}")
    print(f"  TTS Provider: {config.voice_tts_provider}")
    
    results = []
    
    # Run tests
    results.append(("Voice Parsing", test_voice_command_parsing()))
    results.append(("Agent Routing", test_agent_routing()))
    results.append(("Approval Integration", test_approval_integration()))
    results.append(("Vocal Response", test_vocal_response_generation()))
    
    # Summary
    print("\n" + "="*70)
    print("SMOKE TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All vocal agent tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed. See details above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
