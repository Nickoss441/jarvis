"""PyQt HUD scaffolding helpers."""

from .pyqt_overlay import (
    PyQtUnavailableError,
    TransparentHudConfig,
    build_overlay_stylesheet,
    compute_window_flags,
    pulse_opacity_bounds,
    run_transparent_hud,
)

__all__ = [
    "PyQtUnavailableError",
    "TransparentHudConfig",
    "build_overlay_stylesheet",
    "compute_window_flags",
    "pulse_opacity_bounds",
    "run_transparent_hud",
]
