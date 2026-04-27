"""Deterministic event-to-action automation.

Processes events from EventBus and applies explicit rules. This module avoids
LLM-dependent decisions for safety-critical automation.
"""
from dataclasses import dataclass
import hashlib
import json
import sqlite3
import time
from typing import Any

from .approval_service import ApprovalService
from .config import Config
from .event_bus import EventBus, Event
from .vision_analyze import analyze_frame_b64


@dataclass
class EventProcessingSummary:
    processed: int
    approvals_created: int
    skipped: int
    duplicates: int
    throttled: int
    failures: int
    items: list[dict[str, Any]]


class EventAutomation:
    """Apply deterministic automation rules to unprocessed events."""

    def __init__(self, config: Config):
        self.config = config
        self.bus = EventBus(config.event_bus_db)
        self.approvals = ApprovalService(config)
        self._init_state()

    def _init_state(self) -> None:
        with sqlite3.connect(self.config.event_bus_db) as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS automation_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    event_id TEXT NOT NULL,
                    correlation_id TEXT,
                    event_kind TEXT NOT NULL,
                    action TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    approval_id TEXT
                )
                """
            )
            cols = {
                row[1]
                for row in con.execute("PRAGMA table_info(automation_actions)").fetchall()
            }
            if "correlation_id" not in cols:
                con.execute("ALTER TABLE automation_actions ADD COLUMN correlation_id TEXT")
            con.execute(
                """
                CREATE INDEX IF NOT EXISTS automation_actions_kind_ts_idx
                ON automation_actions(event_kind, ts)
                """
            )

    def _idempotency_key(self, event: Event) -> str:
        canonical_payload = json.dumps(event.payload or {}, sort_keys=True, default=str)
        material = f"{event.kind}|{event.source}|{canonical_payload}"
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    def _already_processed(self, idem_key: str) -> bool:
        with sqlite3.connect(self.config.event_bus_db) as con:
            row = con.execute(
                "SELECT 1 FROM automation_actions WHERE idempotency_key = ? LIMIT 1",
                (idem_key,),
            ).fetchone()
        return row is not None

    def _is_throttled(self, event_kind: str) -> bool:
        max_per_hour = self.config.event_alerts_max_per_hour_by_kind.get(event_kind)
        if not max_per_hour or max_per_hour <= 0:
            return False

        since = time.time() - 3600
        with sqlite3.connect(self.config.event_bus_db) as con:
            row = con.execute(
                """
                SELECT COUNT(*) FROM automation_actions
                WHERE event_kind = ? AND ts >= ? AND action = 'approval_created'
                """,
                (event_kind, since),
            ).fetchone()
        count = row[0] if row else 0
        return count >= max_per_hour

    def _record_action(
        self,
        event: Event,
        action: str,
        idem_key: str,
        approval_id: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        with sqlite3.connect(self.config.event_bus_db) as con:
            con.execute(
                """
                INSERT INTO automation_actions (
                    ts, event_id, correlation_id, event_kind, action, idempotency_key, approval_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    time.time(),
                    event.id,
                    correlation_id,
                    event.kind,
                    action,
                    idem_key,
                    approval_id,
                ),
            )

    def _event_correlation_id(self, event: Event) -> str:
        return event.correlation_id

    def _rule_webhook_github(self, event: Event) -> str | None:
        payload = event.payload or {}
        event_type = payload.get("event_type") or "unknown"
        inner = payload.get("payload") or {}
        repo = inner.get("repository", {}).get("full_name") if isinstance(inner.get("repository"), dict) else inner.get("repo", "")
        action = inner.get("action", "")
        path = payload.get("path", "")

        subject = f"GitHub webhook: {event_type}"
        body = (
            f"GitHub webhook received. event_type={event_type}; "
            f"repo={repo or 'n/a'}; action={action or 'n/a'}; path={path or '/'}"
        )

        return self.approvals.request(
            "message_send",
            {
                "channel": self.config.event_alert_channel,
                "recipient": self.config.event_alert_recipient,
                "subject": subject,
                "body": body,
            },
            correlation_id=self._event_correlation_id(event),
        )

    def _rule_filesystem_new_file(self, event: Event) -> str | None:
        payload = event.payload or {}
        name = payload.get("name") or "unknown"
        path = payload.get("path") or ""
        size = payload.get("size_bytes")

        subject = f"New file detected: {name}"
        body = f"Filesystem monitor detected a new file: {name} ({size} bytes) at {path}"

        return self.approvals.request(
            "message_send",
            {
                "channel": self.config.event_alert_channel,
                "recipient": self.config.event_alert_recipient,
                "subject": subject,
                "body": body,
            },
            correlation_id=self._event_correlation_id(event),
        )

    def _rule_vision_frame(self, event: Event) -> str | None:
        payload = event.payload or {}
        device = payload.get("device") or "iphone"
        frame_id = payload.get("frame_id") or "n/a"
        labels = payload.get("labels") or []
        text = payload.get("text") or ""
        image_url = payload.get("image_url") or ""
        accepted = payload.get("frame_accepted")
        size_bytes = payload.get("frame_size_bytes")
        enrichment = self._vision_frame_enrichment(payload)

        labels_text = ", ".join([str(label) for label in labels[:5]]) or "none"
        body_parts = [
            f"Vision frame received from {device}.",
            f"frame_id={frame_id}",
            f"labels={labels_text}",
            f"frame_accepted={accepted}",
            f"frame_size_bytes={size_bytes}",
        ]
        if "face_count" in enrichment:
            body_parts.append(f"face_count={enrichment['face_count']}")
            # Include landmark summary if available
            landmarks = enrichment.get("landmarks") or []
            if landmarks:
                landmark_summary = self._format_landmarks_summary(landmarks)
                if landmark_summary:
                    body_parts.append(f"landmarks={landmark_summary}")
        colors = enrichment.get("colors") or []
        if colors:
            body_parts.append(f"dominant_colors={self._format_color_summary(colors)}")
        if text:
            body_parts.append(f"ocr_text={text[:280]}")
        if image_url:
            body_parts.append(f"image_url={image_url}")

        return self.approvals.request(
            "message_send",
            {
                "channel": self.config.event_alert_channel,
                "recipient": self.config.event_alert_recipient,
                "subject": f"Vision frame alert: {device}",
                "body": "; ".join(body_parts),
            },
            correlation_id=self._event_correlation_id(event),
        )

    def _vision_frame_enrichment(self, payload: dict[str, Any]) -> dict[str, Any]:
        analysis = payload.get("vision_analysis")
        if isinstance(analysis, dict):
            face_count = analysis.get("face_count")
            colors = analysis.get("colors")
            landmarks = analysis.get("landmarks")
            out: dict[str, Any] = {}
            
            # Gate face_count on embedded analysis faces
            if isinstance(face_count, int) and face_count > 0:
                faces = payload.get("vision_faces")
                if self._passes_face_confidence_gate(faces):
                    out["face_count"] = face_count
            
            # Gate colors on coverage
            if isinstance(colors, list) and colors:
                if self._passes_color_coverage_gate(colors):
                    out["colors"] = colors
            
            # Include landmarks if face detection passed
            if isinstance(landmarks, list) and landmarks and "face_count" in out:
                out["landmarks"] = landmarks
            
            return out

        image_b64 = payload.get("image_base64")
        if not isinstance(image_b64, str) or not image_b64.strip():
            return {}

        try:
            result = analyze_frame_b64(image_b64.strip(), max_colors=3)
        except Exception:
            return {}

        if not result.get("ok"):
            return {}

        face_count = result.get("face_count")
        colors = result.get("colors")
        faces = result.get("faces")
        landmarks = result.get("landmarks")
        out: dict[str, Any] = {}
        
        # Gate face_count on all detected faces' confidence
        if isinstance(face_count, int) and face_count > 0:
            if self._passes_face_confidence_gate(faces):
                out["face_count"] = face_count
        
        # Gate colors on total coverage
        if isinstance(colors, list) and colors:
            if self._passes_color_coverage_gate(colors):
                out["colors"] = colors
        
        # Include landmarks if face detection passed
        if isinstance(landmarks, list) and landmarks and "face_count" in out:
            out["landmarks"] = landmarks
        
        return out

    def _passes_face_confidence_gate(self, faces: Any) -> bool:
        """Check if all faces meet min confidence threshold."""
        if not isinstance(faces, list) or not faces:
            return False
        threshold = self.config.vision_min_face_confidence
        for face in faces:
            if not isinstance(face, dict):
                continue
            confidence = face.get("confidence")
            if not isinstance(confidence, (int, float)):
                return False
            if confidence < threshold:
                return False
        return len(faces) > 0

    def _passes_color_coverage_gate(self, colors: list[dict[str, Any]]) -> bool:
        """Check if total color coverage meets min threshold."""
        if not isinstance(colors, list) or not colors:
            return False
        threshold = self.config.vision_min_color_coverage
        total_pct = sum(c.get("pct", 0) for c in colors if isinstance(c, dict))
        return total_pct >= (threshold * 100)

    def _format_color_summary(self, colors: list[dict[str, Any]]) -> str:
        parts: list[str] = []
        for color in colors[:3]:
            if not isinstance(color, dict):
                continue
            name = str(color.get("name") or "").strip()
            if not name:
                continue
            pct = color.get("pct")
            if isinstance(pct, (int, float)):
                parts.append(f"{name}:{float(pct):.1f}%")
            else:
                parts.append(name)
        return ", ".join(parts) if parts else "none"

    def _format_landmarks_summary(self, landmarks: list[dict[str, Any]]) -> str:
        """Format landmark features for human-readable alert text."""
        parts: list[str] = []
        for i, landmark_item in enumerate(landmarks[:2]):  # Limit to first 2 faces
            if not isinstance(landmark_item, dict):
                continue
            features = landmark_item.get("features") or {}
            gaze = features.get("gaze")
            head_pose = features.get("head_pose")
            face_parts = []
            if gaze:
                face_parts.append(f"gaze={gaze}")
            if head_pose:
                tilt = head_pose.get("tilt")
                nod = head_pose.get("nod")
                if tilt and nod:
                    face_parts.append(f"pose={tilt}_{nod}")
                elif tilt:
                    face_parts.append(f"tilt={tilt}")
                elif nod:
                    face_parts.append(f"nod={nod}")
            if face_parts:
                parts.append(f"face{i}[{','.join(face_parts)}]")
        return "; ".join(parts) if parts else ""

    def _apply_rules(self, event: Event) -> str | None:
        if event.kind == "webhook_github":
            return self._rule_webhook_github(event)

        if event.kind == "filesystem_new_file":
            return self._rule_filesystem_new_file(event)

        if event.kind == "vision_frame":
            return self._rule_vision_frame(event)

        return None

    def process_unprocessed(self, limit: int = 50) -> EventProcessingSummary:
        events = self.bus.list_unprocessed(limit=limit)
        items: list[dict[str, Any]] = []
        approvals_created = 0
        skipped = 0
        duplicates = 0
        throttled = 0
        failures = 0

        for event in events:
            try:
                correlation_id = self._event_correlation_id(event)
                idem_key = self._idempotency_key(event)
                if self._already_processed(idem_key):
                    duplicates += 1
                    self.bus.mark_processed(event.id, notes="automation: duplicate")
                    items.append(
                        {
                            "event_id": event.id,
                            "correlation_id": correlation_id,
                            "kind": event.kind,
                            "action": "duplicate",
                        }
                    )
                    continue

                if self._is_throttled(event.kind):
                    throttled += 1
                    self._record_action(
                        event,
                        "throttled",
                        idem_key,
                        correlation_id=correlation_id,
                    )
                    self.bus.mark_processed(event.id, notes="automation: throttled")
                    items.append(
                        {
                            "event_id": event.id,
                            "correlation_id": correlation_id,
                            "kind": event.kind,
                            "action": "throttled",
                        }
                    )
                    continue

                approval_id = self._apply_rules(event)
                if approval_id:
                    approvals_created += 1
                    self._record_action(
                        event,
                        "approval_created",
                        idem_key,
                        approval_id,
                        correlation_id=correlation_id,
                    )
                    self.bus.mark_processed(
                        event.id,
                        notes=f"automation: approval_created:{approval_id}",
                    )
                    items.append(
                        {
                            "event_id": event.id,
                            "correlation_id": correlation_id,
                            "kind": event.kind,
                            "action": "approval_created",
                            "approval_id": approval_id,
                        }
                    )
                else:
                    skipped += 1
                    self._record_action(
                        event,
                        "no_rule",
                        idem_key,
                        correlation_id=correlation_id,
                    )
                    self.bus.mark_processed(event.id, notes="automation: no_rule")
                    items.append(
                        {
                            "event_id": event.id,
                            "correlation_id": correlation_id,
                            "kind": event.kind,
                            "action": "no_rule",
                        }
                    )
            except Exception as exc:
                failures += 1
                items.append(
                    {
                        "event_id": event.id,
                        "correlation_id": self._event_correlation_id(event),
                        "kind": event.kind,
                        "action": "error",
                        "error": str(exc),
                    }
                )

        return EventProcessingSummary(
            processed=len(events),
            approvals_created=approvals_created,
            skipped=skipped,
            duplicates=duplicates,
            throttled=throttled,
            failures=failures,
            items=items,
        )

    def list_recent_actions(
        self,
        limit: int = 50,
        event_kind: str | None = None,
        correlation_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return recent automation actions, newest first."""
        with sqlite3.connect(self.config.event_bus_db) as con:
            if event_kind and correlation_id:
                rows = con.execute(
                    """
                    SELECT ts, event_id, correlation_id, event_kind, action, idempotency_key, approval_id
                    FROM automation_actions
                    WHERE event_kind = ? AND correlation_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (event_kind, correlation_id, limit),
                ).fetchall()
            elif event_kind:
                rows = con.execute(
                    """
                    SELECT ts, event_id, correlation_id, event_kind, action, idempotency_key, approval_id
                    FROM automation_actions
                    WHERE event_kind = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (event_kind, limit),
                ).fetchall()
            elif correlation_id:
                rows = con.execute(
                    """
                    SELECT ts, event_id, correlation_id, event_kind, action, idempotency_key, approval_id
                    FROM automation_actions
                    WHERE correlation_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (correlation_id, limit),
                ).fetchall()
            else:
                rows = con.execute(
                    """
                    SELECT ts, event_id, correlation_id, event_kind, action, idempotency_key, approval_id
                    FROM automation_actions
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()

        return [
            {
                "ts": row[0],
                "event_id": row[1],
                "correlation_id": row[2] or "",
                "event_kind": row[3],
                "action": row[4],
                "idempotency_key": row[5],
                "approval_id": row[6],
            }
            for row in rows
        ]

    def prune_actions(self, older_than_days: int) -> int:
        """Delete automation action rows older than the specified day threshold.

        Returns number of deleted rows.
        """
        days = max(1, int(older_than_days))
        cutoff_ts = time.time() - (days * 86400)

        with sqlite3.connect(self.config.event_bus_db) as con:
            cursor = con.execute(
                "DELETE FROM automation_actions WHERE ts < ?",
                (cutoff_ts,),
            )
            con.commit()
            return cursor.rowcount
