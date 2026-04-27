from types import SimpleNamespace

import pytest

from jarvis.hud.pyqt_overlay import (
    TransparentHudConfig,
    build_overlay_stylesheet,
    compute_window_flags,
    pulse_opacity_bounds,
)


class _FakeWindowType:
    FramelessWindowHint = 0x01
    WindowStaysOnTopHint = 0x02
    Tool = 0x04
    WindowTransparentForInput = 0x08


def test_compute_window_flags_enables_click_through_when_requested():
    qtcore = SimpleNamespace(Qt=SimpleNamespace(WindowType=_FakeWindowType))

    flags = compute_window_flags(TransparentHudConfig(click_through=True), qtcore)

    assert flags & _FakeWindowType.FramelessWindowHint
    assert flags & _FakeWindowType.WindowStaysOnTopHint
    assert flags & _FakeWindowType.Tool
    assert flags & _FakeWindowType.WindowTransparentForInput


def test_compute_window_flags_can_disable_click_through():
    qtcore = SimpleNamespace(Qt=SimpleNamespace(WindowType=_FakeWindowType))

    flags = compute_window_flags(TransparentHudConfig(click_through=False), qtcore)

    assert flags & _FakeWindowType.FramelessWindowHint
    assert flags & _FakeWindowType.WindowStaysOnTopHint
    assert flags & _FakeWindowType.Tool
    assert (flags & _FakeWindowType.WindowTransparentForInput) == 0


def test_build_overlay_stylesheet_contains_neon_surface_values():
    css = build_overlay_stylesheet(
        TransparentHudConfig(opacity=0.75, neon_rgb=(100, 200, 255))
    )

    assert "QWidget#hudRoot" in css
    assert "QLabel#hudTitle" in css
    assert "QLabel#hudStatusChip" in css
    assert "QFrame#hudScanlineTop" in css
    assert "rgba(100, 200, 255" in css
    assert "qlineargradient" in css


def test_pulse_opacity_bounds_are_centered_around_baseline():
    start, end = pulse_opacity_bounds(0.8)

    assert start == pytest.approx(0.72)
    assert end == pytest.approx(0.88)


def test_pulse_opacity_bounds_are_clamped_to_visible_range():
    start, end = pulse_opacity_bounds(1.0)

    assert start == pytest.approx(0.92)
    assert end == pytest.approx(1.0)
