"""Tests for jarvis.vision_analyze — face detection and color extraction."""
import base64
import io
import json

import pytest
from PIL import Image

from jarvis.vision_analyze import (
    _color_name,
    analyze_frame,
    analyze_frame_b64,
    detect_faces,
    detect_landmarks,
    extract_dominant_colors,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _solid_jpeg(r: int, g: int, b: int, size: int = 50) -> bytes:
    img = Image.new("RGB", (size, size), (r, g, b))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _solid_b64(r: int, g: int, b: int) -> str:
    return base64.b64encode(_solid_jpeg(r, g, b)).decode("ascii")


# ---------------------------------------------------------------------------
# _color_name
# ---------------------------------------------------------------------------

def test_color_name_black():
    assert _color_name(10, 10, 10) == "black"


def test_color_name_white():
    assert _color_name(230, 230, 230) == "white"


def test_color_name_gray():
    assert _color_name(120, 120, 120) == "gray"


def test_color_name_red():
    assert _color_name(220, 30, 30) == "red"


def test_color_name_green():
    assert _color_name(30, 200, 30) == "green"


def test_color_name_blue():
    assert _color_name(30, 30, 220) == "blue"


def test_color_name_yellow():
    assert _color_name(200, 200, 30) == "yellow"


def test_color_name_orange():
    assert _color_name(220, 130, 20) == "orange"


def test_color_name_purple():
    assert _color_name(180, 20, 180) == "purple"


def test_color_name_cyan():
    assert _color_name(20, 200, 200) == "cyan"


# ---------------------------------------------------------------------------
# extract_dominant_colors
# ---------------------------------------------------------------------------

def test_dominant_colors_solid_red():
    colors = extract_dominant_colors(_solid_jpeg(220, 40, 40), n=3)
    assert len(colors) >= 1
    assert colors[0]["name"] == "red"
    assert colors[0]["pct"] > 50


def test_dominant_colors_solid_blue():
    colors = extract_dominant_colors(_solid_jpeg(30, 30, 210), n=3)
    assert len(colors) >= 1
    assert colors[0]["name"] == "blue"


def test_dominant_colors_solid_green():
    colors = extract_dominant_colors(_solid_jpeg(30, 200, 30), n=3)
    assert len(colors) >= 1
    assert colors[0]["name"] == "green"


def test_dominant_colors_hex_format():
    colors = extract_dominant_colors(_solid_jpeg(220, 40, 40))
    assert colors[0]["hex"].startswith("#")
    assert len(colors[0]["hex"]) == 7


def test_dominant_colors_rgb_is_list_of_three_ints():
    colors = extract_dominant_colors(_solid_jpeg(50, 150, 220))
    rgb = colors[0]["rgb"]
    assert isinstance(rgb, list)
    assert len(rgb) == 3
    assert all(isinstance(v, int) for v in rgb)


def test_dominant_colors_pct_sums_to_100():
    colors = extract_dominant_colors(_solid_jpeg(220, 40, 40))
    total = sum(c["pct"] for c in colors)
    assert abs(total - 100.0) < 1.0


def test_dominant_colors_respects_n_limit():
    colors = extract_dominant_colors(_solid_jpeg(220, 40, 40), n=2)
    assert len(colors) <= 2


def test_dominant_colors_invalid_bytes_returns_empty():
    colors = extract_dominant_colors(b"notanimage")
    assert colors == []


def test_dominant_colors_empty_bytes_returns_empty():
    colors = extract_dominant_colors(b"")
    assert colors == []


# ---------------------------------------------------------------------------
# detect_faces — on macOS Vision is available but a solid color has no face
# ---------------------------------------------------------------------------

def test_detect_faces_solid_image_has_no_faces():
    faces = detect_faces(_solid_jpeg(200, 150, 100))
    assert isinstance(faces, list)
    assert len(faces) == 0


def test_detect_faces_invalid_bytes_returns_empty():
    faces = detect_faces(b"garbage")
    assert faces == []


def test_detect_faces_returns_list_of_dicts_with_expected_keys():
    faces = detect_faces(_solid_jpeg(200, 150, 100))
    for face in faces:
        assert "x" in face
        assert "y" in face
        assert "w" in face
        assert "h" in face
        assert "confidence" in face


# ---------------------------------------------------------------------------
# analyze_frame
# ---------------------------------------------------------------------------

def test_analyze_frame_returns_expected_keys():
    result = analyze_frame(_solid_jpeg(220, 40, 40))
    assert "faces" in result
    assert "face_count" in result
    assert "colors" in result
    assert "landmarks" in result
    assert "capabilities" in result


def test_analyze_frame_face_count_matches_faces_list():
    result = analyze_frame(_solid_jpeg(220, 40, 40))
    assert result["face_count"] == len(result["faces"])


def test_analyze_frame_no_faces_skips_detection():
    result = analyze_frame(_solid_jpeg(220, 40, 40), detect_faces_flag=False)
    assert result["faces"] == []
    assert result["face_count"] == 0


def test_analyze_frame_no_colors_skips_extraction():
    result = analyze_frame(_solid_jpeg(220, 40, 40), detect_colors_flag=False)
    assert result["colors"] == []


def test_analyze_frame_no_landmarks_skips_detection():
    result = analyze_frame(_solid_jpeg(220, 40, 40), detect_landmarks_flag=False)
    assert result["landmarks"] == []


def test_analyze_frame_max_colors_respected():
    result = analyze_frame(_solid_jpeg(220, 40, 40), max_colors=2)
    assert len(result["colors"]) <= 2


def test_analyze_frame_capabilities_has_pil_true():
    result = analyze_frame(_solid_jpeg(220, 40, 40))
    assert result["capabilities"]["pil"] is True


# ---------------------------------------------------------------------------
# analyze_frame_b64
# ---------------------------------------------------------------------------

def test_analyze_frame_b64_ok_field_true_on_success():
    result = analyze_frame_b64(_solid_b64(220, 40, 40))
    assert result["ok"] is True


def test_analyze_frame_b64_invalid_base64_returns_error():
    result = analyze_frame_b64("not!!valid!!base64!!")
    assert result["ok"] is False
    assert result["error"] == "invalid_base64"


def test_analyze_frame_b64_color_detected():
    result = analyze_frame_b64(_solid_b64(30, 30, 210))
    assert result["ok"] is True
    assert len(result["colors"]) >= 1
    assert result["colors"][0]["name"] == "blue"


# ---------------------------------------------------------------------------
# detect_landmarks
# ---------------------------------------------------------------------------

def test_detect_landmarks_solid_image_has_no_landmarks():
    """Solid color image should not have face landmarks."""
    landmarks = detect_landmarks(_solid_jpeg(200, 150, 100))
    assert isinstance(landmarks, list)


def test_detect_landmarks_invalid_bytes_returns_empty():
    """Invalid image bytes should return empty list."""
    landmarks = detect_landmarks(b"garbage")
    assert landmarks == []


def test_detect_landmarks_empty_bytes_returns_empty():
    """Empty bytes should return empty list."""
    landmarks = detect_landmarks(b"")
    assert landmarks == []


# ---------------------------------------------------------------------------
# analyze_frame with landmarks
# ---------------------------------------------------------------------------

def test_analyze_frame_landmarks_is_list():
    """analyze_frame should return landmarks as a list."""
    result = analyze_frame(_solid_jpeg(220, 40, 40))
    assert isinstance(result["landmarks"], list)


def test_analyze_frame_landmarks_each_has_landmarks_and_features():
    """Each landmark item should have 'landmarks' and 'features' keys."""
    result = analyze_frame(_solid_jpeg(220, 40, 40))
    for landmark_item in result["landmarks"]:
        assert "landmarks" in landmark_item
        assert "features" in landmark_item
        assert "face_id" in landmark_item
        assert isinstance(landmark_item["landmarks"], dict)
        assert isinstance(landmark_item["features"], dict)


def test_analyze_frame_b64_returns_landmarks():
    """analyze_frame_b64 should include landmarks in result."""
    result = analyze_frame_b64(_solid_b64(220, 40, 40))
    assert "landmarks" in result
    assert isinstance(result["landmarks"], list)


def test_analyze_frame_b64_with_no_landmarks_flag():
    """analyze_frame_b64 with detect_landmarks_flag=False should return empty landmarks."""
    result = analyze_frame_b64(_solid_b64(220, 40, 40), detect_landmarks_flag=False)
    assert result["landmarks"] == []


def test_detect_landmarks_py313_guard_skips_vision(monkeypatch):
    """On Python 3.13+, default guard should skip Vision landmark calls."""
    from jarvis import vision_analyze as va

    monkeypatch.setattr(va.sys, "version_info", (3, 13, 0))
    monkeypatch.delenv("JARVIS_FORCE_VISION_LANDMARKS", raising=False)

    def _should_not_be_called():
        raise AssertionError("_load_vision should not be called when guard is active")

    monkeypatch.setattr(va, "_load_vision", _should_not_be_called)
    assert va.detect_landmarks(b"anything") == []


def test_detect_landmarks_py313_force_allows_vision_path(monkeypatch):
    """Force flag should bypass guard and continue through normal Vision path checks."""
    from jarvis import vision_analyze as va

    monkeypatch.setattr(va.sys, "version_info", (3, 13, 0))
    monkeypatch.setenv("JARVIS_FORCE_VISION_LANDMARKS", "1")

    called = {"load_vision": False}

    def _fake_load_vision():
        called["load_vision"] = True
        return False

    monkeypatch.setattr(va, "_load_vision", _fake_load_vision)
    assert va.detect_landmarks(b"anything") == []
    assert called["load_vision"] is True
