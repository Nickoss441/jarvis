from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class RuntimeEventEnvelope:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    kind: str = ""
    timestamp: float = field(default_factory=time.time)
    source: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    correlation_id: str = ""
    processed: bool = False
    processed_at: float | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        if self.correlation_id:
            return

        payload_correlation = self.payload.get("correlation_id") if isinstance(self.payload, dict) else None
        if isinstance(payload_correlation, str) and payload_correlation.strip():
            self.correlation_id = payload_correlation.strip()
            return

        self.correlation_id = self.id

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RuntimeEventEnvelope":
        return cls(**data)