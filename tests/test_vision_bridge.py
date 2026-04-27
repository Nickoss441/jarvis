import json

from jarvis.vision_bridge import (
    build_shortcut_guide,
    build_shortcut_template,
    build_signature,
)


def test_build_signature_is_deterministic():
    payload = {
        "b": 2,
        "a": 1,
    }
    s1 = build_signature("secret", payload)
    s2 = build_signature("secret", {"a": 1, "b": 2})

    assert s1.startswith("sha256=")
    assert s1 == s2


def test_shortcut_template_includes_signature_when_secret_present():
    template = build_shortcut_template("http://127.0.0.1:9021/frame", secret="secret")

    request = template["request"]
    assert request["url"].endswith("/frame")
    assert request["method"] == "POST"
    assert request["headers"]["Content-Type"] == "application/json"
    assert request["headers"]["X-Event-Type"] == "vision.frame"
    assert request["headers"]["X-Jarvis-Signature"].startswith("sha256=")


def test_shortcut_template_without_secret_has_no_signature():
    template = build_shortcut_template("http://127.0.0.1:9021/frame", secret="")

    headers = template["request"]["headers"]
    assert "X-Jarvis-Signature" not in headers


def test_shortcut_template_payload_is_json_serializable():
    template = build_shortcut_template("http://127.0.0.1:9021/frame", secret="")
    rendered = json.dumps(template)
    assert "rayban_meta" in rendered


def test_shortcut_guide_without_signing_has_no_signature_step():
    guide = build_shortcut_guide("http://127.0.0.1:9021/frame", signing_enabled=False)
    titles = [step["title"] for step in guide["steps"]]

    assert guide["signing_enabled"] is False
    assert "Enable Signature" not in titles


def test_shortcut_guide_with_signing_includes_signature_step():
    guide = build_shortcut_guide("http://127.0.0.1:9021/frame", signing_enabled=True)
    titles = [step["title"] for step in guide["steps"]]

    assert guide["signing_enabled"] is True
    assert "Enable Signature" in titles
    assert guide["steps"][0]["step"] == 1
    assert guide["steps"][-1]["step"] == len(guide["steps"])
