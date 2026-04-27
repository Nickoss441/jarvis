import base64

import jarvis.tools.vision_observe as vision_observe
from jarvis.tools.vision_observe import make_vision_observe_tool


def test_vision_observe_dry_run_screenshot_defaults() -> None:
    tool = make_vision_observe_tool(mode="dry_run")

    out = tool.handler()

    assert out == {
        "ok": True,
        "mode": "dry_run",
        "source": "screenshot",
        "detect_faces": True,
        "detect_colors": True,
        "detect_landmarks": True,
        "max_colors": 5,
    }


def test_vision_observe_analyzes_provided_base64(monkeypatch) -> None:
    tool = make_vision_observe_tool(mode="live")
    payload = base64.b64encode(b"png-bytes").decode("ascii")

    captured: dict[str, object] = {}

    def _fake_analyze(image_b64: str, **kwargs):
        captured["image_b64"] = image_b64
        captured["kwargs"] = kwargs
        return {"ok": True, "button_target": {"x": 12, "y": 34}}

    monkeypatch.setattr(vision_observe, "analyze_frame_b64", _fake_analyze)

    out = tool.handler(source="image_base64", image_base64=payload, detect_landmarks=False, max_colors=3)

    assert captured["image_b64"] == payload
    assert captured["kwargs"] == {
        "detect_faces_flag": True,
        "detect_colors_flag": True,
        "detect_landmarks_flag": False,
        "max_colors": 3,
    }
    assert out["source"] == "image_base64"
    assert out["button_target"] == {"x": 12, "y": 34}


def test_vision_observe_captures_screenshot_before_analysis(monkeypatch) -> None:
    tool = make_vision_observe_tool(mode="live")

    monkeypatch.setattr(vision_observe.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(vision_observe, "_capture_screenshot_png", lambda: b"screen-bytes")
    monkeypatch.setattr(
        vision_observe,
        "analyze_frame_b64",
        lambda image_b64, **_kwargs: {"ok": True, "image_b64": image_b64},
    )

    out = tool.handler(source="screenshot")

    assert out["source"] == "screenshot"
    assert out["screenshot_byte_count"] == len(b"screen-bytes")
    assert out["image_b64"] == base64.b64encode(b"screen-bytes").decode("ascii")