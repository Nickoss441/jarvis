"""Transparent PyQt HUD scaffold.

This module intentionally keeps PyQt imports lazy so the project can run in
non-GUI environments without requiring Qt at install time.
"""

from dataclasses import dataclass


class PyQtUnavailableError(RuntimeError):
    """Raised when PyQt is not installed but HUD runtime was requested."""


@dataclass(frozen=True)
class TransparentHudConfig:
    """Minimal shape/styling config for the transparent HUD shell."""

    title: str = "Jarvis HUD"
    width: int = 720
    height: int = 180
    opacity: float = 0.82
    x: int | None = 24
    y: int | None = 24
    click_through: bool = True
    subtitle: str = "Transparent overlay scaffold active"
    status_label: str = "SYSTEM READY"
    neon_rgb: tuple[int, int, int] = (58, 196, 255)


def _clamp_opacity(value: float) -> float:
    if value < 0.1:
        return 0.1
    if value > 1.0:
        return 1.0
    return value


def build_overlay_stylesheet(config: TransparentHudConfig) -> str:
    """Build a neon-forward stylesheet for the overlay shell."""
    opacity = _clamp_opacity(config.opacity)
    r, g, b = config.neon_rgb
    glow = f"rgba({r}, {g}, {b}, 0.42)"
    frame = f"rgba({r}, {g}, {b}, 0.65)"
    surface = f"rgba(7, 13, 24, {opacity:.2f})"
    line = f"rgba({r}, {g}, {b}, 0.85)"

    return (
        "QWidget#hudRoot {"
        f"background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {surface}, stop:1 rgba(5, 9, 18, {opacity:.2f}));"
        f"border: 1px solid {frame};"
        "border-radius: 14px;"
        f"box-shadow: 0 0 24px {glow};"
        "}"
        "QLabel#hudTitle {"
        "color: #dff6ff;"
        "font-size: 20px;"
        "font-weight: 700;"
        "letter-spacing: 1px;"
        "}"
        "QLabel#hudSubline {"
        "color: #8dcde9;"
        "font-size: 12px;"
        "}"
        "QLabel#hudStatusChip {"
        f"color: {line};"
        "font-size: 11px;"
        "font-weight: 700;"
        "padding: 4px 8px;"
        "border-radius: 10px;"
        f"border: 1px solid {line};"
        f"background: rgba({r}, {g}, {b}, 0.14);"
        "}"
        "QFrame#hudScanlineTop, QFrame#hudScanlineBottom {"
        f"background: {line};"
        "min-height: 1px;"
        "max-height: 1px;"
        "border: none;"
        "}"
    )


def compute_window_flags(config: TransparentHudConfig, qtcore: object) -> int:
    """Compute window flags for transparent always-on-top overlay behavior."""
    window_type = qtcore.Qt.WindowType
    flags = (
        window_type.FramelessWindowHint
        | window_type.WindowStaysOnTopHint
        | window_type.Tool
    )
    if config.click_through:
        flags |= window_type.WindowTransparentForInput
    return int(flags)


def _load_qt_modules() -> tuple[object, object]:
    from PyQt6 import QtCore, QtWidgets  # type: ignore

    return QtCore, QtWidgets


def run_transparent_hud(
    config: TransparentHudConfig | None = None,
    *,
    duration_ms: int | None = None,
) -> None:
    """Run the transparent HUD window until closed or optional timer expiry."""
    cfg = config or TransparentHudConfig()

    try:
        qtcore, qtwidgets = _load_qt_modules()
    except ImportError as exc:
        raise PyQtUnavailableError(
            "PyQt6 is required for hud-run. Install with: pip install PyQt6"
        ) from exc

    app = qtwidgets.QApplication.instance()
    if app is None:
        app = qtwidgets.QApplication([])

    window = qtwidgets.QWidget()
    window.setObjectName("hudRoot")
    window.setWindowTitle(cfg.title)
    window.resize(cfg.width, cfg.height)
    if cfg.x is not None and cfg.y is not None:
        window.move(cfg.x, cfg.y)

    window.setWindowFlags(compute_window_flags(cfg, qtcore))
    window.setAttribute(qtcore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
    window.setAttribute(qtcore.Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

    layout = qtwidgets.QVBoxLayout(window)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(4)

    scanline_top = qtwidgets.QFrame()
    scanline_top.setObjectName("hudScanlineTop")
    layout.addWidget(scanline_top)

    title = qtwidgets.QLabel(cfg.title)
    title.setObjectName("hudTitle")
    layout.addWidget(title)

    status = qtwidgets.QLabel(cfg.status_label)
    status.setObjectName("hudStatusChip")
    layout.addWidget(status)

    subline = qtwidgets.QLabel(cfg.subtitle)
    subline.setObjectName("hudSubline")
    layout.addWidget(subline)

    scanline_bottom = qtwidgets.QFrame()
    scanline_bottom.setObjectName("hudScanlineBottom")
    layout.addWidget(scanline_bottom)

    window.setStyleSheet(build_overlay_stylesheet(cfg))
    window.show()

    if duration_ms is not None and duration_ms > 0:
        qtcore.QTimer.singleShot(int(duration_ms), app.quit)

    app.exec()
