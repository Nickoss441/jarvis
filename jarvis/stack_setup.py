"""LangChain + PyQt + OpenCV stack readiness helpers."""

from __future__ import annotations

from importlib.util import find_spec


def _find_spec(module_name: str):
    return find_spec(module_name)


def _is_available(module_name: str) -> bool:
    return _find_spec(module_name) is not None


def build_stack_readiness_report(*, strict: bool = False) -> dict[str, object]:
    """Return dependency readiness for the LangChain/PyQt/OpenCV stack."""
    components = {
        "langchain": _is_available("langchain") or _is_available("langchain_core"),
        "pyqt6": _is_available("PyQt6"),
        "opencv": _is_available("cv2"),
    }
    missing = [name for name, available in components.items() if not available]
    ready = not missing

    report: dict[str, object] = {
        "ok": True,
        "strict": bool(strict),
        "ready": ready,
        "components": components,
        "missing_components": missing,
    }
    if strict and missing:
        report["ok"] = False
        report["error"] = "stack_dependencies_missing"
    return report
