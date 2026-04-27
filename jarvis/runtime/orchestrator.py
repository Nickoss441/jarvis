"""Helpers for orchestrating runtime turns and queued tasks."""
from dataclasses import dataclass
from time import time
from typing import Any, Iterable

from .turn import RuntimeTurnContext


@dataclass
class RuntimeTask:
    """A queued orchestrator task."""

    id: str
    name: str
    payload: dict[str, Any]
    created_ts: float
    status: str = "pending"
    attempts: int = 0
    last_error: str = ""


class RuntimeTaskQueue:
    """Deterministic in-memory FIFO queue for orchestrator tasks."""

    def __init__(self) -> None:
        self._pending: list[RuntimeTask] = []
        self._in_progress: dict[str, RuntimeTask] = {}
        self._completed: dict[str, RuntimeTask] = {}
        self._failed: dict[str, RuntimeTask] = {}
        self._counter: int = 0

    def enqueue(self, name: str, payload: dict[str, Any] | None = None) -> RuntimeTask:
        task_name = str(name or "").strip()
        if not task_name:
            raise ValueError("task name is required")

        self._counter += 1
        task = RuntimeTask(
            id=f"task-{self._counter}",
            name=task_name,
            payload=dict(payload or {}),
            created_ts=time(),
        )
        self._pending.append(task)
        return task

    def dequeue(self) -> RuntimeTask | None:
        if not self._pending:
            return None
        task = self._pending.pop(0)
        task.status = "in_progress"
        self._in_progress[task.id] = task
        return task

    def complete(self, task_id: str) -> bool:
        task = self._in_progress.pop(task_id, None)
        if task is None:
            return False
        task.status = "completed"
        self._completed[task.id] = task
        return True

    def fail(self, task_id: str, *, error: str = "") -> bool:
        task = self._in_progress.pop(task_id, None)
        if task is None:
            return False
        task.status = "failed"
        task.last_error = str(error or "")
        self._failed[task.id] = task
        return True

    def requeue(self, task_id: str, *, error: str = "") -> bool:
        task = self._in_progress.pop(task_id, None)
        if task is None:
            return False
        task.status = "pending"
        task.attempts += 1
        task.last_error = str(error or "")
        self._pending.append(task)
        return True

    def snapshot(self) -> dict[str, int]:
        return {
            "pending": len(self._pending),
            "in_progress": len(self._in_progress),
            "completed": len(self._completed),
            "failed": len(self._failed),
        }

    @property
    def pending_count(self) -> int:
        return len(self._pending)


class RuntimeOrchestrator:
    """Small coordination helper for the current brain loop.

    This package is the landing zone for future runtime-stage extraction.
    For now it centralizes turn state and common response shaping without
    changing the public behavior of the CLI or tests.
    """

    def __init__(self, max_iterations: int):
        self.max_iterations = max_iterations
        self.task_queue = RuntimeTaskQueue()

    def start_turn(self, user_input: str, correlation_id: str) -> RuntimeTurnContext:
        return RuntimeTurnContext(
            user_input=user_input,
            correlation_id=correlation_id,
            max_iterations=self.max_iterations,
        )

    def enqueue_task(self, name: str, payload: dict[str, Any] | None = None) -> RuntimeTask:
        return self.task_queue.enqueue(name=name, payload=payload)

    def next_task(self) -> RuntimeTask | None:
        return self.task_queue.dequeue()

    def complete_task(self, task_id: str) -> bool:
        return self.task_queue.complete(task_id)

    def fail_task(self, task_id: str, *, error: str = "") -> bool:
        return self.task_queue.fail(task_id, error=error)

    @staticmethod
    def text_from_blocks(blocks: Iterable[Any]) -> str:
        return "".join(
            block.text for block in blocks if getattr(block, "type", None) == "text"
        ).strip()

    @classmethod
    def final_text_from_blocks(cls, blocks: Iterable[Any]) -> str:
        text = cls.text_from_blocks(blocks)
        return text or "(no text response)"
