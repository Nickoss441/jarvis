"""Vision observer tool for analyzing screenshots or supplied images."""
from __future__ import annotations

import base64
import platform
from typing import Any

from ..vision_analyze import analyze_frame_b64
from . import Tool
from .desktop_control import _capture_screenshot_png

_VALID_SOURCES = {"screenshot", "image_base64"}


def make_vision_observe_tool(mode: str = "live") -> Tool:
    def _handle(
        source: str = "screenshot",
        image_base64: str = "",
        target_hint: str = "",
        detect_faces: bool = True,
        detect_colors: bool = True,
        detect_landmarks: bool = True,
        max_colors: int = 5,
        **_: Any,
    ) -> dict[str, Any]:
        selected_source = (source or "screenshot").strip().lower()
        if selected_source not in _VALID_SOURCES:
            return {"ok": False, "error": f"unsupported source '{source}'"}
        if max_colors < 1:
            return {"ok": False, "error": "max_colors must be at least 1"}

        if mode == "dry_run":
            return {
                "ok": True,
                "mode": "dry_run",
                "source": selected_source,
                "detect_faces": bool(detect_faces),
                "detect_colors": bool(detect_colors),
                "detect_landmarks": bool(detect_landmarks),
                "max_colors": int(max_colors),
            }

        encoded_image = image_base64.strip()
        screenshot_byte_count = 0
        if selected_source == "screenshot":
            if platform.system() != "Darwin":
                return {"ok": False, "error": "vision_observe screenshot source currently supports macOS only"}
            try:
                image_bytes = _capture_screenshot_png()
            except RuntimeError as exc:
                return {"ok": False, "error": str(exc), "source": selected_source}
            screenshot_byte_count = len(image_bytes)
            encoded_image = base64.b64encode(image_bytes).decode("ascii")
        elif not encoded_image:
            return {"ok": False, "error": "image_base64 is required for image_base64 source"}

        result = analyze_frame_b64(
            encoded_image,
            detect_faces_flag=bool(detect_faces),
            detect_colors_flag=bool(detect_colors),
            detect_landmarks_flag=bool(detect_landmarks),
            max_colors=int(max_colors),
        )
        result["source"] = selected_source
        if screenshot_byte_count:
            result["screenshot_byte_count"] = screenshot_byte_count

        hint = (target_hint or "").strip()
        if hint:
            candidate = result.get("button_target")
            if isinstance(candidate, dict) and "x" in candidate and "y" in candidate:
                result["target_hint"] = hint
                result["ui_coordinates"] = {
                    "x": float(candidate["x"]),
                    "y": float(candidate["y"]),
                    "coordinate_space": "normalized",
                    "source": "model_button_target",
                }
            else:
                return {
                    "ok": False,
                    "error": "target_not_found",
                    "target_hint": hint,
                    "source": selected_source,
                    "analysis": result,
                }
        return result

    return Tool(
        name="vision_observe",
        description=(
            "Analyze a supplied image or the current desktop screenshot for faces, dominant colors, landmarks, and candidate button targets. "
            "Use this before UI actions that need visual confirmation."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "One of: screenshot, image_base64",
                },
                "image_base64": {
                    "type": "string",
                    "description": "Base64 image payload when source=image_base64.",
                },
                "target_hint": {
                    "type": "string",
                    "description": "Optional natural-language UI target (e.g., 'blue submit button'). Returns ui_coordinates when resolved.",
                },
                "detect_faces": {"type": "boolean"},
                "detect_colors": {"type": "boolean"},
                "detect_landmarks": {"type": "boolean"},
                "max_colors": {"type": "integer", "minimum": 1},
            },
        },
        handler=_handle,
        tier="open",
    )