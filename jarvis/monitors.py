"""Monitor base class for perception layer.

Monitors are background workers that observe external systems (calendar, RSS, webhooks, etc.)
and emit structured events to the event bus.
"""
from abc import ABC, abstractmethod
from collections import deque
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import hmac
import json
from pathlib import Path
from typing import Any
import logging
import threading
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

from .event_bus import Event, EventBus
from .vision_analyze import analyze_frame_b64


logger = logging.getLogger(__name__)


class Monitor(ABC):
    """Abstract base class for perception monitors.

    Each monitor observes a specific data stream and emits events to the bus.
    Monitors run periodically or continuously, checking for new data and emitting
    events when relevant changes occur.
    """

    def __init__(self, event_bus: EventBus, source: str):
        """Initialize monitor.

        Args:
            event_bus: EventBus instance for emitting events
            source: Monitor source identifier (e.g., "calendar", "rss_tech_news")
        """
        self.bus = event_bus
        self.source = source

    @abstractmethod
    def run(self) -> int:
        """Run one iteration of the monitor.

        Should check for new data from the external system and emit events if
        relevant changes are detected. This method is called periodically by
        the monitor runner.

        Returns:
            Number of events emitted in this iteration
        """
        pass

    def emit_event(
        self,
        kind: str,
        payload: dict[str, Any],
        notes: str = "",
    ) -> str:
        """Emit an event to the event bus.

        Args:
            kind: Event kind (e.g., "calendar_event", "rss_article")
            payload: Event payload (structured data)
            notes: Optional metadata

        Returns:
            Event ID
        """
        event = Event(
            kind=kind,
            source=self.source,
            payload=payload,
            notes=notes,
        )
        event_id = self.bus.emit(event)
        logger.debug(f"Monitor {self.source} emitted {kind}: {event_id}")
        return event_id


class CalendarMonitor(Monitor):
    """Monitor for calendar events.

    Polls a calendar source (ICS file, CalDAV, Google Calendar, etc.) and emits
    events for upcoming appointments, reminders, and all-day events.
    """

    def __init__(self, event_bus: EventBus, calendar_path: str):
        """Initialize calendar monitor.

        Args:
            event_bus: EventBus instance
            calendar_path: Path to .ics file or calendar endpoint
        """
        super().__init__(event_bus, source="calendar")
        self.calendar_path = calendar_path
        self._seen_event_keys: set[str] = set()
        self._bootstrapped = False

    def _parse_ics_events(self) -> list[dict[str, str]]:
        path = Path(self.calendar_path)
        if not path.exists():
            return []

        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        events: list[dict[str, str]] = []
        in_event = False
        current: dict[str, str] = {}

        for raw in lines:
            line = raw.strip()
            if line == "BEGIN:VEVENT":
                in_event = True
                current = {}
                continue
            if line == "END:VEVENT":
                if current:
                    events.append(current)
                in_event = False
                current = {}
                continue
            if not in_event or ":" not in line:
                continue

            key, value = line.split(":", 1)
            field = key.split(";", 1)[0].upper()
            if field in {"UID", "SUMMARY", "DTSTART", "DTEND", "LOCATION", "DESCRIPTION"}:
                current[field] = value.strip()

        return events

    def run(self) -> int:
        """Check for new events in an ICS calendar file."""
        events = self._parse_ics_events()
        if not events:
            return 0

        keys = {
            (e.get("UID") or f"{e.get('SUMMARY','')}|{e.get('DTSTART','')}")
            for e in events
        }

        if not self._bootstrapped:
            self._seen_event_keys = keys
            self._bootstrapped = True
            return 0

        emitted = 0
        for event in events:
            key = event.get("UID") or f"{event.get('SUMMARY','')}|{event.get('DTSTART','')}"
            if key in self._seen_event_keys:
                continue

            self.emit_event(
                kind="calendar_event",
                payload={
                    "uid": event.get("UID", ""),
                    "title": event.get("SUMMARY", ""),
                    "start": event.get("DTSTART", ""),
                    "end": event.get("DTEND", ""),
                    "location": event.get("LOCATION", ""),
                    "description": event.get("DESCRIPTION", ""),
                },
            )
            self._seen_event_keys.add(key)
            emitted += 1

        return emitted


class RSSMonitor(Monitor):
    """Monitor for RSS feeds.

    Polls RSS/Atom feeds and emits events for new articles.
    """

    def __init__(self, event_bus: EventBus, feed_url: str, source_name: str):
        """Initialize RSS monitor.

        Args:
            event_bus: EventBus instance
            feed_url: URL to RSS/Atom feed
            source_name: Friendly name for this feed (e.g., "tech_news", "hacker_news")
        """
        super().__init__(event_bus, source=f"rss_{source_name}")
        self.feed_url = feed_url
        self.last_seen_items: set[str] = set()
        self._bootstrapped = False

    def _fetch_feed(self) -> str:
        if self.feed_url.startswith("file://"):
            return Path(self.feed_url[7:]).read_text(encoding="utf-8", errors="ignore")

        with urllib.request.urlopen(self.feed_url, timeout=10) as response:
            return response.read().decode("utf-8", errors="ignore")

    def _parse_feed_items(self, feed_xml: str) -> list[dict[str, str]]:
        root = ET.fromstring(feed_xml)
        items: list[dict[str, str]] = []

        channel = root.find("channel")
        if channel is not None:
            for item in channel.findall("item"):
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                guid = (item.findtext("guid") or "").strip()
                pub_date = (item.findtext("pubDate") or "").strip()
                item_id = guid or link or title
                if not item_id:
                    continue
                items.append(
                    {
                        "id": item_id,
                        "title": title,
                        "url": link,
                        "published": pub_date,
                    }
                )
            return items

        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("atom:entry", ns):
            title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
            entry_id = (entry.findtext("atom:id", default="", namespaces=ns) or "").strip()
            updated = (entry.findtext("atom:updated", default="", namespaces=ns) or "").strip()
            link = ""
            link_el = entry.find("atom:link", ns)
            if link_el is not None:
                link = (link_el.attrib.get("href") or "").strip()

            item_id = entry_id or link or title
            if not item_id:
                continue
            items.append(
                {
                    "id": item_id,
                    "title": title,
                    "url": link,
                    "published": updated,
                }
            )
        return items

    def run(self) -> int:
        """Check for new RSS/Atom items and emit events for unseen ones."""
        try:
            raw_feed = self._fetch_feed()
            items = self._parse_feed_items(raw_feed)
        except Exception as exc:
            logger.warning(f"RSS monitor failed for {self.feed_url}: {exc}")
            return 0

        ids = {item["id"] for item in items}
        if not self._bootstrapped:
            self.last_seen_items = ids
            self._bootstrapped = True
            return 0

        emitted = 0
        for item in items:
            if item["id"] in self.last_seen_items:
                continue
            self.emit_event(
                kind="rss_article",
                payload={
                    "id": item["id"],
                    "title": item["title"],
                    "url": item["url"],
                    "published": item["published"],
                },
            )
            self.last_seen_items.add(item["id"])
            emitted += 1

        return emitted


class WebhookMonitor(Monitor):
    """Monitor for webhook events.

    Receives HTTP POST requests and emits structured events.
    Runs an HTTP server listening for webhook callbacks (e.g., from IFTTT, Zapier, GitHub).
    """

    def __init__(
        self,
        event_bus: EventBus,
        source_name: str,
        host: str = "127.0.0.1",
        port: int = 9000,
        signing_secret: str = "",
        path_kind_map: dict[str, str] | None = None,
    ):
        """Initialize webhook monitor.

        Args:
            event_bus: EventBus instance
            source_name: Friendly name for this webhook (e.g., "github", "ifttt")
            host: HTTP host to bind to
            port: HTTP port to bind to
            signing_secret: Optional HMAC secret for signature verification
            path_kind_map: Optional mapping of path-prefix to event kind
        """
        super().__init__(event_bus, source=f"webhook_{source_name}")
        self.host = host
        self.port = port
        self.signing_secret = signing_secret
        self.path_kind_map = path_kind_map or {}
        self.server: ThreadingHTTPServer | None = None
        self._server_thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._pending: deque[dict[str, Any]] = deque()

    def _resolve_kind(self, path: str) -> str:
        """Resolve event kind from configured path-prefix routing."""
        for prefix, kind in self.path_kind_map.items():
            if prefix and path.startswith(prefix):
                return kind
        return "webhook_event"

    def _signature_valid(self, headers: dict[str, str], raw_body: bytes) -> bool:
        """Validate webhook signature when signing_secret is configured."""
        if not self.signing_secret:
            return True

        header_value = headers.get("X-Jarvis-Signature") or headers.get("X-Hub-Signature-256")
        if not header_value:
            return False

        expected = "sha256=" + hmac.new(
            self.signing_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(header_value.strip(), expected)

    def ingest(
        self,
        payload: dict[str, Any],
        path: str = "/",
        headers: dict[str, str] | None = None,
        kind: str | None = None,
    ) -> int:
        """Queue webhook payload for processing on next run()."""
        entry = {
            "payload": payload,
            "path": path,
            "headers": headers or {},
            "received_at": time.time(),
            "kind": kind or self._resolve_kind(path),
        }
        with self._lock:
            self._pending.append(entry)
            return len(self._pending)

    def start_server(self) -> tuple[str, int]:
        """Start local HTTP server for webhook ingestion.

        Returns:
            Tuple of bound host and bound port.
        """
        if self.server is not None:
            return self.server.server_address

        monitor = self

        class _WebhookHandler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802 (http method name)
                length = int(self.headers.get("Content-Length", "0") or "0")
                raw = self.rfile.read(length) if length > 0 else b""

                header_map = {k: v for k, v in self.headers.items()}
                if not monitor._signature_valid(header_map, raw):
                    body = json.dumps({"queued": False, "error": "invalid_signature"}).encode("utf-8")
                    self.send_response(401)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return

                content_type = self.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    try:
                        payload = json.loads(raw.decode("utf-8") or "{}")
                    except Exception:
                        payload = {"raw": raw.decode("utf-8", errors="ignore")}
                else:
                    payload = {"raw": raw.decode("utf-8", errors="ignore")}

                monitor.ingest(
                    payload=payload,
                    path=self.path,
                    headers=header_map,
                    kind=monitor._resolve_kind(self.path),
                )

                body = json.dumps({"queued": True}).encode("utf-8")
                self.send_response(202)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                return

        self.server = ThreadingHTTPServer((self.host, self.port), _WebhookHandler)
        self._server_thread = threading.Thread(
            target=self.server.serve_forever,
            name=f"WebhookMonitor:{self.source}",
            daemon=True,
        )
        self._server_thread.start()
        bound_host, bound_port = self.server.server_address
        logger.info(f"Webhook monitor listening on http://{bound_host}:{bound_port}")
        return bound_host, bound_port

    def stop_server(self) -> None:
        """Stop local webhook HTTP server if running."""
        if self.server is None:
            return
        self.server.shutdown()
        self.server.server_close()
        self.server = None
        self._server_thread = None

    def run(self) -> int:
        """Process queued webhook payloads and emit events."""
        with self._lock:
            batch = list(self._pending)
            self._pending.clear()

        if not batch:
            return 0

        emitted = 0
        for item in batch:
            event_type = (
                item["headers"].get("X-Event-Type")
                or item["headers"].get("X-GitHub-Event")
                or "webhook_event"
            )
            self.emit_event(
                kind=item.get("kind", "webhook_event"),
                payload={
                    "event_type": event_type,
                    "path": item["path"],
                    "headers": item["headers"],
                    "payload": item["payload"],
                    "received_at": item["received_at"],
                },
            )
            emitted += 1

        return emitted


class VisionIngestMonitor(WebhookMonitor):
    """Monitor for camera frame ingestion.

    Accepts JSON HTTP payloads from phone-based bridge apps and emits
    ``vision_frame`` events with compact metadata for automation.
    """

    def __init__(
        self,
        event_bus: EventBus,
        source_name: str = "iphone",
        host: str = "127.0.0.1",
        port: int = 9021,
        signing_secret: str = "",
        max_frame_bytes: int = 2_000_000,
    ):
        super().__init__(
            event_bus=event_bus,
            source_name=source_name,
            host=host,
            port=port,
            signing_secret=signing_secret,
            path_kind_map={"/": "vision_frame"},
        )
        self.max_frame_bytes = max(1, int(max_frame_bytes))

    def _estimate_b64_size(self, value: str) -> int:
        padded_len = len(value) + (-len(value) % 4)
        return int((padded_len * 3) / 4)

    def _frame_digest(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _coerce_labels(self, labels: Any) -> list[str]:
        if isinstance(labels, list):
            return [str(item).strip() for item in labels if str(item).strip()]
        if isinstance(labels, str):
            parsed = [part.strip() for part in labels.split(",")]
            return [part for part in parsed if part]
        return []

    def _analysis_summary(self, frame_b64: str, frame_accepted: bool) -> dict[str, Any]:
        if not frame_b64 or not frame_accepted:
            return {}
        try:
            result = analyze_frame_b64(frame_b64, max_colors=3)
        except Exception:
            return {}
        if not result.get("ok"):
            return {}
        return {
            "face_count": int(result.get("face_count") or 0),
            "colors": result.get("colors") if isinstance(result.get("colors"), list) else [],
            "faces": result.get("faces") if isinstance(result.get("faces"), list) else [],
            "landmarks": result.get("landmarks") if isinstance(result.get("landmarks"), list) else [],
        }

    def _payload_to_vision_data(self, item: dict[str, Any]) -> dict[str, Any]:
        payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
        frame_b64 = str(payload.get("image_base64") or "").strip()
        has_frame = bool(frame_b64)
        frame_size_bytes = self._estimate_b64_size(frame_b64) if has_frame else 0

        accepted = (not has_frame) or (frame_size_bytes <= self.max_frame_bytes)
        notes = ""
        if has_frame and not accepted:
            notes = (
                f"frame_rejected_too_large:{frame_size_bytes}>"
                f"{self.max_frame_bytes}"
            )

        frame_sha256 = self._frame_digest(frame_b64) if has_frame else ""
        text = str(payload.get("text") or payload.get("ocr_text") or "").strip()
        labels = self._coerce_labels(payload.get("labels"))
        vision_analysis = self._analysis_summary(frame_b64=frame_b64, frame_accepted=accepted)
        vision_faces = vision_analysis.get("faces", [])

        return {
            "event_type": item["headers"].get("X-Event-Type") or "vision_frame",
            "path": item["path"],
            "received_at": item["received_at"],
            "device": str(payload.get("device") or payload.get("source") or "iphone").strip(),
            "stream": str(payload.get("stream") or "camera").strip(),
            "frame_id": str(payload.get("frame_id") or "").strip(),
            "frame_ts": payload.get("frame_ts") or payload.get("timestamp"),
            "image_url": str(payload.get("image_url") or "").strip(),
            "has_frame": has_frame,
            "frame_accepted": accepted,
            "frame_size_bytes": frame_size_bytes,
            "frame_sha256": frame_sha256,
            "max_frame_bytes": self.max_frame_bytes,
            "text": text,
            "labels": labels,
            "vision_analysis": vision_analysis,
            "vision_faces": vision_faces,
            "headers": item["headers"],
            "notes": notes,
        }

    def _decode_request_payload(self, raw: bytes, content_type: str) -> dict[str, Any]:
        lower_ct = (content_type or "").lower()

        if "application/json" in lower_ct:
            try:
                parsed = json.loads(raw.decode("utf-8") or "{}")
                return parsed if isinstance(parsed, dict) else {"payload": parsed}
            except Exception:
                return {"raw": raw.decode("utf-8", errors="ignore")}

        if "multipart/form-data" in lower_ct:
            boundary = ""
            for part in content_type.split(";"):
                item = part.strip()
                if item.lower().startswith("boundary="):
                    boundary = item.split("=", 1)[1].strip().strip('"')
                    break

            if not boundary:
                return {"raw": raw.decode("utf-8", errors="ignore")}

            payload: dict[str, Any] = {}
            marker = ("--" + boundary).encode("utf-8")
            chunks = raw.split(marker)
            for chunk in chunks:
                part = chunk.strip()
                if not part or part == b"--":
                    continue
                if part.startswith(b"--"):
                    part = part[2:]
                part = part.strip(b"\r\n")
                if b"\r\n\r\n" not in part:
                    continue

                header_blob, body = part.split(b"\r\n\r\n", 1)
                body = body.rstrip(b"\r\n")
                header_lines = header_blob.decode("latin-1", errors="ignore").split("\r\n")
                headers: dict[str, str] = {}
                for line in header_lines:
                    if ":" not in line:
                        continue
                    k, v = line.split(":", 1)
                    headers[k.strip().lower()] = v.strip()

                disposition = headers.get("content-disposition", "")
                disp_parts = [d.strip() for d in disposition.split(";") if d.strip()]
                params: dict[str, str] = {}
                for dp in disp_parts[1:]:
                    if "=" not in dp:
                        continue
                    key, value = dp.split("=", 1)
                    params[key.strip().lower()] = value.strip().strip('"')

                name = params.get("name", "").strip()
                filename = params.get("filename", "").strip()

                if filename:
                    payload["image_base64"] = base64.b64encode(body).decode("ascii")
                    payload["filename"] = filename
                    continue

                if name:
                    payload[name] = body.decode("utf-8", errors="ignore")

            return payload

        if lower_ct.startswith("image/") or "application/octet-stream" in lower_ct:
            return {"image_base64": base64.b64encode(raw).decode("ascii")}

        return {"raw": raw.decode("utf-8", errors="ignore")}

    def start_server(self) -> tuple[str, int]:
        """Start local HTTP server for camera frame ingestion."""
        if self.server is not None:
            return self.server.server_address

        monitor = self

        class _VisionHandler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802 (http method name)
                length = int(self.headers.get("Content-Length", "0") or "0")
                raw = self.rfile.read(length) if length > 0 else b""

                header_map = {k: v for k, v in self.headers.items()}
                if not monitor._signature_valid(header_map, raw):
                    body = json.dumps({"queued": False, "error": "invalid_signature"}).encode("utf-8")
                    self.send_response(401)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return

                content_type = self.headers.get("Content-Type", "")
                payload = monitor._decode_request_payload(raw=raw, content_type=content_type)

                # Allow metadata via headers for binary posts.
                if "device" not in payload and self.headers.get("X-Device"):
                    payload["device"] = self.headers.get("X-Device")
                if "frame_id" not in payload and self.headers.get("X-Frame-Id"):
                    payload["frame_id"] = self.headers.get("X-Frame-Id")
                if "labels" not in payload and self.headers.get("X-Labels"):
                    payload["labels"] = self.headers.get("X-Labels")
                if "text" not in payload and self.headers.get("X-Text"):
                    payload["text"] = self.headers.get("X-Text")

                monitor.ingest(
                    payload=payload,
                    path=self.path,
                    headers=header_map,
                    kind="vision_frame",
                )

                body = json.dumps({"queued": True}).encode("utf-8")
                self.send_response(202)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                return

        self.server = ThreadingHTTPServer((self.host, self.port), _VisionHandler)
        self._server_thread = threading.Thread(
            target=self.server.serve_forever,
            name=f"VisionIngestMonitor:{self.source}",
            daemon=True,
        )
        self._server_thread.start()
        bound_host, bound_port = self.server.server_address
        logger.info(f"Vision monitor listening on http://{bound_host}:{bound_port}")
        return bound_host, bound_port

    def run(self) -> int:
        with self._lock:
            batch = list(self._pending)
            self._pending.clear()

        if not batch:
            return 0

        emitted = 0
        for item in batch:
            payload = self._payload_to_vision_data(item)
            self.emit_event(kind="vision_frame", payload=payload, notes=payload.get("notes", ""))
            emitted += 1

        return emitted


class FilesystemMonitor(Monitor):
    """Monitor for filesystem changes.

    Watches a directory (drop zone) for new files and emits events.
    """

    def __init__(self, event_bus: EventBus, watch_dir: str):
        """Initialize filesystem monitor.

        Args:
            event_bus: EventBus instance
            watch_dir: Directory to watch for new files
        """
        super().__init__(event_bus, source="filesystem")
        self.watch_dir = watch_dir
        self.processed_files: set[str] = set()
        self._bootstrapped = False

    def run(self) -> int:
        """Check for new files in watch directory and emit events for unseen files."""
        watch_path = Path(self.watch_dir)
        if not watch_path.exists() or not watch_path.is_dir():
            return 0

        files = [p for p in watch_path.iterdir() if p.is_file()]
        current_paths = {str(p.resolve()) for p in files}

        if not self._bootstrapped:
            self.processed_files = current_paths
            self._bootstrapped = True
            return 0

        emitted = 0
        for file_path in files:
            resolved = str(file_path.resolve())
            if resolved in self.processed_files:
                continue

            stat = file_path.stat()
            self.emit_event(
                kind="filesystem_new_file",
                payload={
                    "path": resolved,
                    "name": file_path.name,
                    "size_bytes": stat.st_size,
                    "modified_at": stat.st_mtime,
                },
            )
            self.processed_files.add(resolved)
            emitted += 1

        return emitted
