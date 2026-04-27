"""Vision analysis: face detection and dominant color extraction.

Uses Apple's Vision.framework (via PyObjC + Quartz) for face detection
and PIL for color analysis.  Both are available on macOS without any
extra pip installs beyond Pillow (already a transitive dep).

Falls back gracefully when the frameworks are not available (e.g. Linux CI).
"""

from __future__ import annotations

import base64
import io
import json
import os
import sys
from typing import Any

# ---------------------------------------------------------------------------
# Optional heavy imports – we lazy-load so tests can import this module fine
# ---------------------------------------------------------------------------
_VISION_AVAILABLE: bool | None = None
_PIL_AVAILABLE: bool | None = None


def _load_vision() -> bool:
    global _VISION_AVAILABLE
    if _VISION_AVAILABLE is not None:
        return _VISION_AVAILABLE
    try:
        import objc  # noqa: F401
        import Quartz  # noqa: F401
        ns: dict = {}
        objc.loadBundle(
            "Vision",
            bundle_path="/System/Library/Frameworks/Vision.framework",
            module_globals=ns,
        )
        if "VNDetectFaceRectanglesRequest" not in ns:
            _VISION_AVAILABLE = False
        else:
            _VISION_AVAILABLE = True
    except Exception:
        _VISION_AVAILABLE = False
    return _VISION_AVAILABLE


def _load_pil() -> bool:
    global _PIL_AVAILABLE
    if _PIL_AVAILABLE is not None:
        return _PIL_AVAILABLE
    try:
        from PIL import Image  # noqa: F401
        _PIL_AVAILABLE = True
    except Exception:
        _PIL_AVAILABLE = False
    return _PIL_AVAILABLE


# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------

def _color_name(r: int, g: int, b: int) -> str:
    max_c = max(r, g, b)
    min_c = min(r, g, b)
    if max_c < 50:
        return "black"
    if min_c > 200:
        return "white"
    if max_c - min_c < 30:
        return "gray"
    # Check compound/secondary colors before primaries
    if r > 140 and g > 140 and b < 80:
        return "yellow"
    if r > 120 and b > 120 and g < 80:
        return "purple"
    if g > 120 and b > 120 and r < 80:
        return "cyan"
    # Primary colors
    if r >= g and r >= b:
        if r > 150 and g > 80 and g > b and b < 100:
            return "orange"
        return "red" if r > 150 else "dark_red"
    if g >= r and g >= b:
        return "green" if g > 150 else "dark_green"
    if b >= r and b >= g:
        return "blue" if b > 150 else "dark_blue"
    return "mixed"


def extract_dominant_colors(image_bytes: bytes, n: int = 5) -> list[dict[str, Any]]:
    """Return up to *n* dominant colors from *image_bytes* (JPEG/PNG).

    Returns an empty list when PIL is unavailable.
    """
    if not _load_pil():
        return []

    from PIL import Image

    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        return []

    small = img.resize((80, 80))

    # Use whichever pixel accessor is available
    try:
        rgb_pixels: list[tuple[int, int, int]] = list(small.get_flattened_data())  # type: ignore[arg-type]
    except AttributeError:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            rgb_pixels = list(small.getdata())  # type: ignore[arg-type]

    if not rgb_pixels:
        return []

    total = len(rgb_pixels)
    buckets: dict[str, list[int]] = {}  # name -> [sum_r, sum_g, sum_b, count]

    for pixel in rgb_pixels:
        r, g, b = int(pixel[0]), int(pixel[1]), int(pixel[2])
        name = _color_name(r, g, b)
        if name not in buckets:
            buckets[name] = [0, 0, 0, 0]
        buckets[name][0] += r
        buckets[name][1] += g
        buckets[name][2] += b
        buckets[name][3] += 1

    results: list[dict[str, Any]] = []
    for name, (sr, sg, sb, cnt) in buckets.items():
        r, g, b = sr // cnt, sg // cnt, sb // cnt
        results.append(
            {
                "name": name,
                "rgb": [r, g, b],
                "hex": f"#{r:02x}{g:02x}{b:02x}",
                "pct": round(cnt / total * 100, 1),
            }
        )

    return sorted(results, key=lambda x: -x["pct"])[:n]


# ---------------------------------------------------------------------------
# Face detection and landmarks
# ---------------------------------------------------------------------------

def _estimate_gaze_direction(
    left_eye_pos: tuple[float, float],
    right_eye_pos: tuple[float, float],
) -> str:
    """Estimate gaze direction from eye positions (normalized coords).

    Returns 'left', 'right', 'center', 'up', 'down', or 'mixed'.
    """
    lx, ly = left_eye_pos
    rx, ry = right_eye_pos
    
    # Horizontal: compare x positions
    left_right_diff = rx - lx
    
    # Vertical: compare y positions (higher = looking up in normalized coords)
    vert_diff = ry - ly
    
    # Determine primary gaze direction
    h_dir = "right" if left_right_diff > 0.02 else ("left" if left_right_diff < -0.02 else "center")
    v_dir = "up" if vert_diff > 0.02 else ("down" if vert_diff < -0.02 else "level")
    
    if h_dir == "center" and v_dir == "level":
        return "center"
    elif h_dir == "center":
        return v_dir
    elif v_dir == "level":
        return h_dir
    else:
        return f"{v_dir}_{h_dir}"  # e.g. "up_left", "down_right"


def _estimate_head_pose(
    nose_pos: tuple[float, float],
    left_eye_pos: tuple[float, float],
    right_eye_pos: tuple[float, float],
) -> dict[str, Any]:
    """Estimate head pose from landmark positions.

    Returns dict with 'tilt' (left/right) and 'nod' (up/down).
    """
    # Eye-to-eye line gives us tilt angle
    lx, ly = left_eye_pos
    rx, ry = right_eye_pos
    eye_tilt = ry - ly  # positive = right eye lower (head tilted left)
    
    # Nose relative to eye midpoint gives us nod
    eye_mid_y = (ly + ry) / 2.0
    nose_y = nose_pos[1]
    nose_nod = nose_y - eye_mid_y  # positive = nose below eyes (looking down)
    
    tilt = "left" if eye_tilt > 0.01 else ("right" if eye_tilt < -0.01 else "straight")
    nod = "down" if nose_nod > 0.02 else ("up" if nose_nod < -0.02 else "level")
    
    return {
        "tilt": tilt,
        "nod": nod,
    }


def detect_landmarks(image_bytes: bytes) -> list[dict[str, Any]]:
    """Detect facial landmarks in *image_bytes* using Apple Vision.framework.

    For each detected face, returns eyes, nose, mouth, jaw positions and
    derived features like gaze direction and head pose.
    Returns empty list when Vision is unavailable or on error.
    """
    # Vision landmark requests can SIGTRAP on some Python 3.13 + PyObjC stacks
    # after repeated calls. Keep default behavior safe unless explicitly forced.
    if sys.version_info >= (3, 13):
        force_landmarks = os.getenv("JARVIS_FORCE_VISION_LANDMARKS", "").strip().lower()
        if force_landmarks not in {"1", "true", "yes", "on"}:
            return []

    if not _load_vision():
        return []

    try:
        import objc
        import Quartz

        ns: dict = {}
        objc.loadBundle(
            "Vision",
            bundle_path="/System/Library/Frameworks/Vision.framework",
            module_globals=ns,
        )

        VNDetectFaceLandmarksRequest = ns.get("VNDetectFaceLandmarksRequest")
        if not VNDetectFaceLandmarksRequest:
            return []
        
        VNImageRequestHandler = ns["VNImageRequestHandler"]

        data_provider = Quartz.CGDataProviderCreateWithData(
            None, image_bytes, len(image_bytes), None
        )

        # Try JPEG first, then PNG
        cg_image = Quartz.CGImageCreateWithJPEGDataProvider(
            data_provider, None, False, Quartz.kCGRenderingIntentDefault
        )
        if cg_image is None:
            cg_image = Quartz.CGImageCreateWithPNGDataProvider(
                data_provider, None, False, Quartz.kCGRenderingIntentDefault
            )
        if cg_image is None:
            return []

        req = VNDetectFaceLandmarksRequest.alloc().init()
        handler = VNImageRequestHandler.alloc().initWithCGImage_options_(cg_image, {})
        handler.performRequests_error_([req], None)

        observations = req.results() or []
        landmarks_list: list[dict[str, Any]] = []
        
        for obs in observations:
            landmarks: dict[str, Any] = {}
            
            # Extract available landmark groups
            if obs.landmarks():
                lm = obs.landmarks()
                
                # Eyes
                if lm.leftEye():
                    pts = lm.leftEye().normalizedPoints()
                    if pts and len(pts) > 0:
                        landmarks["left_eye"] = {
                            "x": round(float(pts[0].x), 4),
                            "y": round(float(pts[0].y), 4),
                        }
                
                if lm.rightEye():
                    pts = lm.rightEye().normalizedPoints()
                    if pts and len(pts) > 0:
                        landmarks["right_eye"] = {
                            "x": round(float(pts[0].x), 4),
                            "y": round(float(pts[0].y), 4),
                        }
                
                # Nose
                if lm.nose():
                    pts = lm.nose().normalizedPoints()
                    if pts and len(pts) > 0:
                        landmarks["nose"] = {
                            "x": round(float(pts[0].x), 4),
                            "y": round(float(pts[0].y), 4),
                        }
                
                # Mouth
                if lm.outerLips():
                    pts = lm.outerLips().normalizedPoints()
                    if pts and len(pts) > 0:
                        landmarks["mouth"] = {
                            "x": round(float(pts[0].x), 4),
                            "y": round(float(pts[0].y), 4),
                        }
            
            # Compute derived features if we have key landmarks
            features: dict[str, Any] = {}
            
            if "left_eye" in landmarks and "right_eye" in landmarks:
                left = (landmarks["left_eye"]["x"], landmarks["left_eye"]["y"])
                right = (landmarks["right_eye"]["x"], landmarks["right_eye"]["y"])
                features["gaze"] = _estimate_gaze_direction(left, right)
            
            if "left_eye" in landmarks and "right_eye" in landmarks and "nose" in landmarks:
                left = (landmarks["left_eye"]["x"], landmarks["left_eye"]["y"])
                right = (landmarks["right_eye"]["x"], landmarks["right_eye"]["y"])
                nose = (landmarks["nose"]["x"], landmarks["nose"]["y"])
                features["head_pose"] = _estimate_head_pose(nose, left, right)
            
            landmarks_list.append(
                {
                    "landmarks": landmarks,
                    "features": features,
                    "face_id": len(landmarks_list),  # Simple per-face index
                }
            )
        
        return landmarks_list

    except Exception:
        return []


def detect_faces(image_bytes: bytes) -> list[dict[str, Any]]:
    """Detect faces in *image_bytes* using Apple Vision.framework.

    Returns a list of dicts with bounding box (normalized, origin bottom-left)
    and confidence score.  Returns an empty list when Vision is unavailable or
    on error.
    """
    if not _load_vision():
        return []

    try:
        import objc
        import Quartz

        ns: dict = {}
        objc.loadBundle(
            "Vision",
            bundle_path="/System/Library/Frameworks/Vision.framework",
            module_globals=ns,
        )

        VNDetectFaceRectanglesRequest = ns["VNDetectFaceRectanglesRequest"]
        VNImageRequestHandler = ns["VNImageRequestHandler"]

        data_provider = Quartz.CGDataProviderCreateWithData(
            None, image_bytes, len(image_bytes), None
        )

        # Try JPEG first, then PNG
        cg_image = Quartz.CGImageCreateWithJPEGDataProvider(
            data_provider, None, False, Quartz.kCGRenderingIntentDefault
        )
        if cg_image is None:
            cg_image = Quartz.CGImageCreateWithPNGDataProvider(
                data_provider, None, False, Quartz.kCGRenderingIntentDefault
            )
        if cg_image is None:
            return []

        req = VNDetectFaceRectanglesRequest.alloc().init()
        handler = VNImageRequestHandler.alloc().initWithCGImage_options_(cg_image, {})
        handler.performRequests_error_([req], None)

        observations = req.results() or []
        faces: list[dict[str, Any]] = []
        for obs in observations:
            bb = obs.boundingBox()
            # NSRect origin is bottom-left in Vision coordinate space
            faces.append(
                {
                    "x": round(float(bb.origin.x), 4),
                    "y": round(float(bb.origin.y), 4),
                    "w": round(float(bb.size.width), 4),
                    "h": round(float(bb.size.height), 4),
                    "confidence": round(float(obs.confidence()), 4),
                }
            )
        return faces

    except Exception:
        return []


# ---------------------------------------------------------------------------
# Combined analysis entry point
# ---------------------------------------------------------------------------

def analyze_frame(
    image_bytes: bytes,
    detect_faces_flag: bool = True,
    detect_colors_flag: bool = True,
    detect_landmarks_flag: bool = True,
    max_colors: int = 5,
) -> dict[str, Any]:
    """Run face detection, color analysis, and/or landmark detection on raw image bytes.

    Returns a dict with keys: ``faces``, ``face_count``, ``colors``, ``landmarks``, ``capabilities``.
    """
    faces: list[dict[str, Any]] = []
    colors: list[dict[str, Any]] = []
    landmarks: list[dict[str, Any]] = []

    if detect_faces_flag:
        faces = detect_faces(image_bytes)

    if detect_colors_flag:
        colors = extract_dominant_colors(image_bytes, n=max_colors)

    if detect_landmarks_flag:
        landmarks = detect_landmarks(image_bytes)

    return {
        "faces": faces,
        "face_count": len(faces),
        "colors": colors,
        "landmarks": landmarks,
        "capabilities": {
            "vision_framework": _load_vision(),
            "pil": _load_pil(),
        },
    }


def analyze_frame_b64(
    image_b64: str,
    detect_faces_flag: bool = True,
    detect_colors_flag: bool = True,
    detect_landmarks_flag: bool = True,
    max_colors: int = 5,
) -> dict[str, Any]:
    """Like :func:`analyze_frame` but accepts a base64-encoded image string."""
    try:
        image_bytes = base64.b64decode(image_b64)
    except Exception:
        return {
            "ok": False,
            "error": "invalid_base64",
        }
    result = analyze_frame(
        image_bytes,
        detect_faces_flag=detect_faces_flag,
        detect_colors_flag=detect_colors_flag,
        detect_landmarks_flag=detect_landmarks_flag,
        max_colors=max_colors,
    )
    result["ok"] = True
    return result

