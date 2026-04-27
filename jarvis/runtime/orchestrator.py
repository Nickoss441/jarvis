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
    priority: int = 0
    status: str = "pending"
    attempts: int = 0
    last_error: str = ""


class RuntimeTaskQueue:
    """Deterministic in-memory priority queue for orchestrator tasks."""

    def __init__(self) -> None:
        self._pending: list[RuntimeTask] = []
        self._in_progress: dict[str, RuntimeTask] = {}
        self._completed: dict[str, RuntimeTask] = {}
        self._failed: dict[str, RuntimeTask] = {}
        self._counter: int = 0

    def enqueue(
        self,
        name: str,
        payload: dict[str, Any] | None = None,
        *,
        priority: int = 0,
    ) -> RuntimeTask:
        task_name = str(name or "").strip()
        if not task_name:
            raise ValueError("task name is required")
        if not isinstance(priority, int):
            raise ValueError("task priority must be an integer")

        self._counter += 1
        task = RuntimeTask(
            id=f"task-{self._counter}",
            name=task_name,
            payload=dict(payload or {}),
            created_ts=time(),
            priority=priority,
        )
        self._pending.append(task)
        return task

    def _highest_priority_pending_index(self) -> int | None:
        if not self._pending:
            return None
        best_index = 0
        best_priority = self._pending[0].priority
        for idx, task in enumerate(self._pending[1:], start=1):
            if task.priority > best_priority:
                best_priority = task.priority
                best_index = idx
        return best_index

    def dequeue(self) -> RuntimeTask | None:
        selected = self._highest_priority_pending_index()
        if selected is None:
            return None
        task = self._pending.pop(selected)
        task.status = "in_progress"
        self._in_progress[task.id] = task
        return task

    def preempt_if_needed(self, task_id: str) -> RuntimeTask | None:
        current = self._in_progress.get(task_id)
        selected = self._highest_priority_pending_index()
        if current is None or selected is None:
            return None

        candidate = self._pending[selected]
        if candidate.priority <= current.priority:
            return None

        self._in_progress.pop(task_id, None)
        current.status = "pending"
        current.attempts += 1
        current.last_error = f"preempted_by:{candidate.id}"
        self._pending.append(current)

        promoted = self._pending.pop(selected)
        promoted.status = "in_progress"
        self._in_progress[promoted.id] = promoted
        return promoted

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

    def enqueue_task(
        self,
        name: str,
        payload: dict[str, Any] | None = None,
        *,
        priority: int = 0,
    ) -> RuntimeTask:
        return self.task_queue.enqueue(name=name, payload=payload, priority=priority)

    def next_task(self) -> RuntimeTask | None:
        return self.task_queue.dequeue()

    def complete_task(self, task_id: str) -> bool:
        return self.task_queue.complete(task_id)

    def fail_task(self, task_id: str, *, error: str = "") -> bool:
        return self.task_queue.fail(task_id, error=error)

    def preempt_task_if_needed(self, task_id: str) -> RuntimeTask | None:
        return self.task_queue.preempt_if_needed(task_id)

    @staticmethod
    def text_from_blocks(blocks: Iterable[Any]) -> str:
        return "".join(
            block.text for block in blocks if getattr(block, "type", None) == "text"
        ).strip()

    @classmethod
    def final_text_from_blocks(cls, blocks: Iterable[Any]) -> str:
        text = cls.text_from_blocks(blocks)
        return text or "(no text response)"
