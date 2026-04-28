#!/usr/bin/env python3
"""Automate orb-city auditing and canonical data generation.

This script reads the HUD source data in jarvis/web/hud_react/app.js,
extracts strategic markers, market cities, and major city dots, then writes:

- jarvis/web/hud_react/data/canonical_orbs.json
- docs/reports/orb_audit_report.md

It is intentionally dependency-free so it can run in CI and local shells.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HUD_APP_JS = ROOT / "jarvis" / "web" / "hud_react" / "app.js"
CANONICAL_JSON = ROOT / "jarvis" / "web" / "hud_react" / "data" / "canonical_orbs.json"
REPORT_MD = ROOT / "docs" / "reports" / "orb_audit_report.md"


@dataclass
class ParseIssue:
    severity: str
    message: str


@dataclass
class OrbRow:
    source: str
    source_id: str
    city: str
    country: str
    lat: float
    lon: float
    label: str


def _read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing source file: {path}")
    return path.read_text(encoding="utf-8")


def _extract_array_block(text: str, const_name: str) -> str:
    marker = f"const {const_name} = ["
    start = text.find(marker)
    if start == -1:
        return ""
    i = start + len(marker)
    depth = 1
    out: list[str] = []
    while i < len(text):
        ch = text[i]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                break
        out.append(ch)
        i += 1
    return "".join(out)


def _split_object_literals(array_body: str) -> list[str]:
    objs: list[str] = []
    i = 0
    while i < len(array_body):
        if array_body[i] != "{":
            i += 1
            continue
        depth = 0
        start = i
        while i < len(array_body):
            ch = array_body[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    objs.append(array_body[start : i + 1])
                    break
            i += 1
        i += 1
    return objs


def _extract_str(obj: str, key: str) -> str:
    m = re.search(rf"\b{re.escape(key)}\s*:\s*\"([^\"]*)\"", obj)
    return m.group(1).strip() if m else ""


def _extract_num(obj: str, key: str) -> float | None:
    m = re.search(rf"\b{re.escape(key)}\s*:\s*(-?\d+(?:\.\d+)?)", obj)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _parse_rows(text: str, const_name: str, source: str) -> list[OrbRow]:
    body = _extract_array_block(text, const_name)
    if not body:
        return []
    rows: list[OrbRow] = []
    for obj in _split_object_literals(body):
        source_id = _extract_str(obj, "id")
        city = _extract_str(obj, "city")
        country = _extract_str(obj, "country")
        label = _extract_str(obj, "label")
        lat = _extract_num(obj, "lat")
        lon = _extract_num(obj, "lon")

        if not city:
            city = label
        if not label:
            label = city or source_id
        if lat is None or lon is None:
            continue
        if not source_id:
            source_id = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") or "unknown"

        rows.append(
            OrbRow(
                source=source,
                source_id=source_id,
                city=city,
                country=country,
                lat=lat,
                lon=lon,
                label=label,
            )
        )
    return rows


def _merge_rows(rows: list[OrbRow]) -> tuple[list[dict[str, Any]], list[ParseIssue]]:
    # Priority: strategic > market > major_city
    priority = {"strategic_marker": 0, "market_city": 1, "major_city": 2}
    grouped: dict[str, list[OrbRow]] = {}
    issues: list[ParseIssue] = []

    for row in rows:
        key = f"{row.city.lower()}|{row.country.lower()}"
        grouped.setdefault(key, []).append(row)

    canonical: list[dict[str, Any]] = []
    for _key, bucket in sorted(grouped.items(), key=lambda kv: kv[0]):
        bucket_sorted = sorted(bucket, key=lambda r: priority.get(r.source, 99))
        primary = bucket_sorted[0]

        lat_values = [r.lat for r in bucket_sorted]
        lon_values = [r.lon for r in bucket_sorted]
        lat_spread = max(lat_values) - min(lat_values)
        lon_spread = max(lon_values) - min(lon_values)
        if lat_spread > 0.35 or lon_spread > 0.35:
            issues.append(
                ParseIssue(
                    severity="warning",
                    message=(
                        f"Coordinate divergence for {primary.city}, {primary.country}: "
                        f"spread lat={lat_spread:.3f}, lon={lon_spread:.3f}"
                    ),
                )
            )

        if not (-90 <= primary.lat <= 90 and -180 <= primary.lon <= 180):
            issues.append(
                ParseIssue(
                    severity="error",
                    message=(
                        f"Out-of-range coordinates for {primary.city}, {primary.country}: "
                        f"lat={primary.lat}, lon={primary.lon}"
                    ),
                )
            )
            continue

        canonical.append(
            {
                "id": re.sub(r"[^a-z0-9]+", "-", f"{primary.city}-{primary.country}".lower()).strip("-"),
                "city": primary.city,
                "country": primary.country,
                "lat": round(primary.lat, 6),
                "lon": round(primary.lon, 6),
                "label": primary.label,
                "primary_source": primary.source,
                "sources": [
                    {
                        "source": r.source,
                        "source_id": r.source_id,
                        "lat": r.lat,
                        "lon": r.lon,
                    }
                    for r in bucket_sorted
                ],
            }
        )

    return canonical, issues


def _build_report(canonical: list[dict[str, Any]], issues: list[ParseIssue], source_counts: dict[str, int]) -> str:
    now = datetime.now(timezone.utc).isoformat()
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]

    lines = [
        "# Orb Audit Report",
        "",
        f"Generated: {now}",
        "",
        "## Summary",
        f"- Canonical orb entries: {len(canonical)}",
        f"- Source strategic_marker rows: {source_counts.get('strategic_marker', 0)}",
        f"- Source market_city rows: {source_counts.get('market_city', 0)}",
        f"- Source major_city rows: {source_counts.get('major_city', 0)}",
        f"- Errors: {len(errors)}",
        f"- Warnings: {len(warnings)}",
        "",
    ]

    if issues:
        lines.append("## Findings")
        for idx, issue in enumerate(issues, start=1):
            lines.append(f"{idx}. [{issue.severity.upper()}] {issue.message}")
        lines.append("")
    else:
        lines.extend(["## Findings", "No parsing or coordinate issues detected.", ""])

    lines.append("## Next Automation Step")
    lines.append("Use this canonical JSON as the single source of truth for globe markers and city orbs.")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    text = _read_text(HUD_APP_JS)

    strategic = _parse_rows(text, "GLOBE_MARKERS", "strategic_marker")
    markets = _parse_rows(text, "MARKETS", "market_city")
    major = _parse_rows(text, "MAJOR_CITY_DOTS", "major_city")

    all_rows = strategic + markets + major
    source_counts = {
        "strategic_marker": len(strategic),
        "market_city": len(markets),
        "major_city": len(major),
    }

    canonical, issues = _merge_rows(all_rows)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_file": str(HUD_APP_JS.relative_to(ROOT)).replace("\\", "/"),
        "source_counts": source_counts,
        "canonical_count": len(canonical),
        "issues": [issue.__dict__ for issue in issues],
        "entries": canonical,
    }

    CANONICAL_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)

    CANONICAL_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_build_report(canonical, issues, source_counts), encoding="utf-8")

    print(f"[orb-automation] wrote {CANONICAL_JSON}")
    print(f"[orb-automation] wrote {REPORT_MD}")

    # Non-zero only on hard coordinate errors.
    if any(issue.severity == "error" for issue in issues):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
