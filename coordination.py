from dataclasses import dataclass
from enum import Enum
import json
import re
from typing import Any, Callable


class TaskStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class FailureType(str, Enum):
    VALIDATION = "validation"
    DUPLICATE_TASK = "duplicate_task"
    TASK_NOT_FOUND = "task_not_found"
    DEPENDENCY_NOT_FOUND = "dependency_not_found"
    STEP_LIMIT = "step_limit"
    TIMEOUT = "timeout"
    TRANSIENT = "transient"
    SECRET_DETECTED = "secret_detected"
    CYCLE_DETECTED = "cycle_detected"
    CONCURRENCY_LIMIT = "concurrency_limit"


class CoordinationError(Exception):
    def __init__(self, message: str, failure_type: FailureType):
        super().__init__(message)
        self.failure_type = failure_type


@dataclass
class Task:
    id: str
    depends_on: set[str]
    handler: Callable[[], str] | None = None
    status: TaskStatus = TaskStatus.PENDING
    result: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class CoordinationEvent:
    step: int
    event: str
    details: dict[str, Any]


SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{10,}"),
    re.compile(r"(?i)api[_-]?key\s*[:=]\s*\S+"),
    re.compile(r"(?i)password\s*[:=]\s*\S+"),
    re.compile(r"(?i)secret\s*[:=]\s*\S+"),
    re.compile(r"(?i)token\s*[:=]\s*\S+"),
]


def contains_secret_like_value(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            contains_secret_like_value(key)
            or contains_secret_like_value(item)
            for key, item in value.items()
        )

    if isinstance(value, (list, tuple, set)):
        return any(
            contains_secret_like_value(item)
            for item in value
        )

    if isinstance(value, str):
        return any(
            pattern.search(value)
            for pattern in SECRET_PATTERNS
        )

    return False


class CoordinationEngine:
    MAX_STEPS = 20

    def __init__(
        self,
        max_steps: int = MAX_STEPS,
        max_concurrency: int = 2,
    ):
        if not isinstance(max_steps, int) or max_steps <= 0:
            raise CoordinationError(
                "max_steps must be a positive integer.",
                FailureType.VALIDATION,
            )

        if not isinstance(max_concurrency, int) or max_concurrency <= 0:
            raise CoordinationError(
                "max_concurrency must be a positive integer.",
                FailureType.VALIDATION,
            )

        self.max_steps = max_steps
        self.max_concurrency = max_concurrency
        self.step_count = 0
        self.tasks: dict[str, Task] = {}
        self.trace: list[CoordinationEvent] = []

    def _step(self) -> None:
        if self.step_count >= self.max_steps:
            raise CoordinationError(
                "Coordination step limit exceeded.",
                FailureType.STEP_LIMIT,
            )

        self.step_count += 1

    def _record(self, event: str, **details: Any) -> None:
        self.trace.append(
            CoordinationEvent(
                step=self.step_count,
                event=event,
                details=details,
            )
        )

    # ============================================================
    # Task 1 — Dependency Graph
    # ============================================================

    def add_task(self, task_id, depends_on=None, handler=None) -> Task:
        self._step()

        if not isinstance(task_id, str) or not task_id.strip():
            raise CoordinationError(
                "Task ID must be a non-empty string.",
                FailureType.VALIDATION,
            )

        if depends_on is None:
            depends_on = set()

        if not isinstance(depends_on, set):
            raise CoordinationError(
                "depends_on must be a set of task IDs.",
                FailureType.VALIDATION,
            )

        if not callable(handler) and handler is not None:
            raise CoordinationError(
                "Task handler must be callable or None.",
                FailureType.VALIDATION,
            )

        if contains_secret_like_value(
            {
                "task_id": task_id,
                "depends_on": depends_on,
            }
        ):
            raise CoordinationError(
                "Secret-like content detected in task definition.",
                FailureType.SECRET_DETECTED,
            )

        if task_id in self.tasks:
            raise CoordinationError(
                f"Task '{task_id}' is already registered.",
                FailureType.DUPLICATE_TASK,
            )

        unknown_dependencies = depends_on - set(self.tasks.keys())

        if unknown_dependencies:
            missing = sorted(unknown_dependencies)

            raise CoordinationError(
                f"Task '{task_id}' references unknown dependencies: {missing}",
                FailureType.DEPENDENCY_NOT_FOUND,
            )

        task = Task(
            id=task_id,
            depends_on=set(depends_on),
            handler=handler,
        )

        self.tasks[task_id] = task

        self._record(
            "task_added",
            task_id=task_id,
            depends_on=sorted(depends_on),
        )

        return task

    def get_task(self, task_id: str) -> Task:
        self._step()

        if task_id not in self.tasks:
            raise CoordinationError(
                f"Task '{task_id}' is not registered.",
                FailureType.TASK_NOT_FOUND,
            )

        task = self.tasks[task_id]

        self._record(
            "task_lookup",
            task_id=task_id,
            status=task.status.value,
        )

        return task

    def dependency_graph(self) -> dict[str, list[str]]:
        self._step()

        graph = {
            task_id: sorted(task.depends_on)
            for task_id, task in self.tasks.items()
        }

        self._record(
            "dependency_graph_read",
            graph=graph,
        )

        return graph

    def validate_dependencies(self) -> bool:
        self._step()

        task_ids = set(self.tasks.keys())

        for task in self.tasks.values():
            missing = task.depends_on - task_ids

            if missing:
                raise CoordinationError(
                    f"Task '{task.id}' has unknown dependencies: "
                    f"{sorted(missing)}",
                    FailureType.DEPENDENCY_NOT_FOUND,
                )

        self._record(
            "dependencies_validated",
            task_count=len(self.tasks),
        )

        return True

    def detect_cycle(self) -> bool:
        self._step()

        visiting = set()
        visited = set()

        def visit(task_id: str) -> bool:
            if task_id in visiting:
                return True

            if task_id in visited:
                return False

            visiting.add(task_id)

            for dependency in self.tasks[task_id].depends_on:
                if dependency not in self.tasks:
                    continue

                if visit(dependency):
                    return True

            visiting.remove(task_id)
            visited.add(task_id)

            return False

        has_cycle = any(
            visit(task_id)
            for task_id in self.tasks
        )

        self._record(
            "cycle_checked",
            has_cycle=has_cycle,
        )

        if has_cycle:
            raise CoordinationError(
                "Dependency graph contains a cycle.",
                FailureType.CYCLE_DETECTED,
            )

        return False

    # ============================================================
    # Task 2 — Ready Set
    # ============================================================

    def ready_set(self) -> list[Task]:
        self._step()

        ready_tasks = []

        for task in self.tasks.values():

            if task.status != TaskStatus.PENDING:
                continue

            dependency_tasks = [
                self.tasks[dependency]
                for dependency in task.depends_on
            ]

            if any(
                dependency.status
                in {
                    TaskStatus.FAILED,
                    TaskStatus.BLOCKED,
                    TaskStatus.CANCELLED,
                }
                for dependency in dependency_tasks
            ):
                task.status = TaskStatus.BLOCKED

                self._record(
                    "task_blocked",
                    task_id=task.id,
                    dependencies=sorted(task.depends_on),
                )

                continue

            if all(
                dependency.status == TaskStatus.SUCCESS
                for dependency in dependency_tasks
            ):
                task.status = TaskStatus.READY

                ready_tasks.append(task)

                self._record(
                    "task_ready",
                    task_id=task.id,
                    dependencies=sorted(task.depends_on),
                )

        ready_tasks.sort(
            key=lambda task: task.id
        )

        self._record(
            "ready_set_computed",
            ready_tasks=[
                task.id
                for task in ready_tasks
            ],
        )

        return ready_tasks

    def mark_success(
        self,
        task_id: str,
        result: str,
    ) -> Task:

        self._step()

        if task_id not in self.tasks:
            raise CoordinationError(
                f"Task '{task_id}' is not registered.",
                FailureType.TASK_NOT_FOUND,
            )

        if not isinstance(result, str) or not result.strip():
            raise CoordinationError(
                "Task result must be a non-empty string.",
                FailureType.VALIDATION,
            )

        if contains_secret_like_value(result):
            raise CoordinationError(
                "Secret-like content detected in task result.",
                FailureType.SECRET_DETECTED,
            )

        task = self.tasks[task_id]

        if task.status not in {
            TaskStatus.READY,
            TaskStatus.RUNNING,
        }:
            raise CoordinationError(
                f"Task '{task_id}' cannot be marked successful "
                f"from status '{task.status.value}'.",
                FailureType.VALIDATION,
            )

        task.status = TaskStatus.SUCCESS
        task.result = result
        task.error = None

        self._record(
            "task_succeeded",
            task_id=task_id,
            result=result,
        )

        return task

    def mark_failed(
        self,
        task_id: str,
        error: str,
    ) -> Task:

        self._step()

        if task_id not in self.tasks:
            raise CoordinationError(
                f"Task '{task_id}' is not registered.",
                FailureType.TASK_NOT_FOUND,
            )

        if not isinstance(error, str) or not error.strip():
            raise CoordinationError(
                "Task error must be a non-empty string.",
                FailureType.VALIDATION,
            )

        if contains_secret_like_value(error):
            raise CoordinationError(
                "Secret-like content detected in task error.",
                FailureType.SECRET_DETECTED,
            )

        task = self.tasks[task_id]

        if task.status not in {
            TaskStatus.READY,
            TaskStatus.RUNNING,
        }:
            raise CoordinationError(
                f"Task '{task_id}' cannot be marked failed "
                f"from status '{task.status.value}'.",
                FailureType.VALIDATION,
            )

        task.status = TaskStatus.FAILED
        task.error = error
        task.result = None

        self._record(
            "task_failed",
            task_id=task_id,
            error=error,
        )

        return task

    # ============================================================
    # Task 3 — Concurrency Limit
    # ============================================================

    def running_tasks(self) -> list[Task]:
        self._step()

        running = [
            task
            for task in self.tasks.values()
            if task.status == TaskStatus.RUNNING
        ]

        running.sort(
            key=lambda task: task.id
        )

        self._record(
            "running_tasks_read",
            running_tasks=[
                task.id
                for task in running
            ],
        )

        return running

    def available_slots(self) -> int:
        self._step()

        running_count = sum(
            1
            for task in self.tasks.values()
            if task.status == TaskStatus.RUNNING
        )

        slots = max(
            0,
            self.max_concurrency - running_count,
        )

        self._record(
            "concurrency_slots_read",
            max_concurrency=self.max_concurrency,
            running_count=running_count,
            available_slots=slots,
        )

        return slots

    def start_task(self, task_id: str) -> Task:
        self._step()

        if task_id not in self.tasks:
            raise CoordinationError(
                f"Task '{task_id}' is not registered.",
                FailureType.TASK_NOT_FOUND,
            )

        task = self.tasks[task_id]

        if task.status != TaskStatus.READY:
            raise CoordinationError(
                f"Task '{task_id}' cannot start from status "
                f"'{task.status.value}'.",
                FailureType.VALIDATION,
            )

        running_count = sum(
            1
            for existing_task in self.tasks.values()
            if existing_task.status == TaskStatus.RUNNING
        )

        if running_count >= self.max_concurrency:
            raise CoordinationError(
                f"Concurrency limit reached: "
                f"{self.max_concurrency} task(s) already running.",
                FailureType.CONCURRENCY_LIMIT,
            )

        task.status = TaskStatus.RUNNING

        self._record(
            "task_started",
            task_id=task_id,
            running_count=running_count + 1,
            max_concurrency=self.max_concurrency,
        )

        return task

    # ============================================================
    # Task 4 — Join / Partial Failure
    # ============================================================

    def cancel_task(
        self,
        task_id: str,
        reason: str = "Task cancelled by coordinator.",
    ) -> Task:

        self._step()

        if task_id not in self.tasks:
            raise CoordinationError(
                f"Task '{task_id}' is not registered.",
                FailureType.TASK_NOT_FOUND,
            )

        if not isinstance(reason, str) or not reason.strip():
            raise CoordinationError(
                "Cancellation reason must be a non-empty string.",
                FailureType.VALIDATION,
            )

        if contains_secret_like_value(reason):
            raise CoordinationError(
                "Secret-like content detected in cancellation reason.",
                FailureType.SECRET_DETECTED,
            )

        task = self.tasks[task_id]

        if task.status not in {
            TaskStatus.PENDING,
            TaskStatus.READY,
            TaskStatus.RUNNING,
        }:
            raise CoordinationError(
                f"Task '{task_id}' cannot be cancelled from status "
                f"'{task.status.value}'.",
                FailureType.VALIDATION,
            )

        task.status = TaskStatus.CANCELLED
        task.error = reason
        task.result = None

        self._record(
            "task_cancelled",
            task_id=task_id,
            reason=reason,
        )

        return task

    def join(
        self,
        task_ids: list[str] | None = None,
    ) -> dict[str, Any]:

        self._step()

        if task_ids is None:
            task_ids = sorted(self.tasks.keys())

        if not isinstance(task_ids, list) or not task_ids:
            raise CoordinationError(
                "task_ids must be a non-empty list.",
                FailureType.VALIDATION,
            )

        if any(
            not isinstance(task_id, str) or not task_id.strip()
            for task_id in task_ids
        ):
            raise CoordinationError(
                "Every task ID must be a non-empty string.",
                FailureType.VALIDATION,
            )

        if len(task_ids) != len(set(task_ids)):
            raise CoordinationError(
                "Join task IDs must be unique.",
                FailureType.VALIDATION,
            )

        if contains_secret_like_value(task_ids):
            raise CoordinationError(
                "Secret-like content detected in join task IDs.",
                FailureType.SECRET_DETECTED,
            )

        missing = [
            task_id
            for task_id in task_ids
            if task_id not in self.tasks
        ]

        if missing:
            raise CoordinationError(
                f"Join references unknown tasks: {sorted(missing)}",
                FailureType.TASK_NOT_FOUND,
            )

        selected_tasks = [
            self.tasks[task_id]
            for task_id in task_ids
        ]

        success_tasks = [
            task.id
            for task in selected_tasks
            if task.status == TaskStatus.SUCCESS
        ]

        failed_tasks = [
            task.id
            for task in selected_tasks
            if task.status == TaskStatus.FAILED
        ]

        blocked_tasks = [
            task.id
            for task in selected_tasks
            if task.status == TaskStatus.BLOCKED
        ]

        cancelled_tasks = [
            task.id
            for task in selected_tasks
            if task.status == TaskStatus.CANCELLED
        ]

        pending_tasks = [
            task.id
            for task in selected_tasks
            if task.status == TaskStatus.PENDING
        ]

        ready_tasks = [
            task.id
            for task in selected_tasks
            if task.status == TaskStatus.READY
        ]

        running_tasks = [
            task.id
            for task in selected_tasks
            if task.status == TaskStatus.RUNNING
        ]

        total = len(selected_tasks)
        completed = len(success_tasks)
        failures = len(failed_tasks)

        terminal_count = (
            len(success_tasks)
            + len(failed_tasks)
            + len(blocked_tasks)
            + len(cancelled_tasks)
        )

        if terminal_count == total:
            if completed == total:
                overall_status = "completed"
            elif completed > 0:
                overall_status = "partial_completion"
            else:
                overall_status = "failed"
        else:
            if completed > 0:
                overall_status = "partial_in_progress"
            else:
                overall_status = "in_progress"

        result = {
            "overall_status": overall_status,
            "total_tasks": total,
            "successful_tasks": success_tasks,
            "failed_tasks": failed_tasks,
            "blocked_tasks": blocked_tasks,
            "cancelled_tasks": cancelled_tasks,
            "pending_tasks": pending_tasks,
            "ready_tasks": ready_tasks,
            "running_tasks": running_tasks,
            "completed_count": completed,
            "failure_count": failures,
            "terminal_count": terminal_count,
            "all_tasks_completed": completed == total,
        }

        if contains_secret_like_value(result):
            raise CoordinationError(
                "Secret-like content detected in join result.",
                FailureType.SECRET_DETECTED,
            )

        self._record(
            "join_computed",
            **result,
        )

        return result

    # ============================================================
    # Task 5 — Coordination Metrics
    # ============================================================

    def coordination_metrics(self) -> dict[str, Any]:
        self._step()

        total_tasks = len(self.tasks)

        status_counts = {
            status.value: 0
            for status in TaskStatus
        }

        for task in self.tasks.values():
            status_counts[task.status.value] += 1

        terminal_count = (
            status_counts[TaskStatus.SUCCESS.value]
            + status_counts[TaskStatus.FAILED.value]
            + status_counts[TaskStatus.BLOCKED.value]
            + status_counts[TaskStatus.CANCELLED.value]
        )

        successful_count = status_counts[
            TaskStatus.SUCCESS.value
        ]

        failed_count = status_counts[
            TaskStatus.FAILED.value
        ]

        blocked_count = status_counts[
            TaskStatus.BLOCKED.value
        ]

        cancelled_count = status_counts[
            TaskStatus.CANCELLED.value
        ]

        running_count = status_counts[
            TaskStatus.RUNNING.value
        ]

        if total_tasks == 0:
            completion_rate = 0.0
            failure_rate = 0.0
        else:
            completion_rate = (
                successful_count / total_tasks
            )

            failure_rate = (
                failed_count / total_tasks
            )

        if total_tasks == 0:
            overall_status = "no_tasks"
        elif successful_count == total_tasks:
            overall_status = "completed"
        elif terminal_count == total_tasks:
            if successful_count > 0:
                overall_status = "partial_completion"
            else:
                overall_status = "failed"
        elif successful_count > 0:
            overall_status = "partial_in_progress"
        else:
            overall_status = "in_progress"

        metrics = {
            "total_tasks": total_tasks,
            "status_counts": status_counts,
            "successful_count": successful_count,
            "failed_count": failed_count,
            "blocked_count": blocked_count,
            "cancelled_count": cancelled_count,
            "running_count": running_count,
            "terminal_count": terminal_count,
            "completion_rate": completion_rate,
            "failure_rate": failure_rate,
            "overall_status": overall_status,
            "max_concurrency": self.max_concurrency,
            "available_slots": max(
                0,
                self.max_concurrency - running_count,
            ),
            "step_count": self.step_count,
            "max_steps": self.max_steps,
            "step_utilization": (
                self.step_count / self.max_steps
            ),
            "trace_event_count": len(self.trace),
        }

        if contains_secret_like_value(metrics):
            raise CoordinationError(
                "Secret-like content detected in coordination metrics.",
                FailureType.SECRET_DETECTED,
            )

        self._record(
            "coordination_metrics_computed",
            **metrics,
        )

        return metrics

    # ============================================================
    # Trace Utilities
    # ============================================================

    def trace_to_dict(self) -> list[dict[str, Any]]:
        return [
            {
                "step": event.step,
                "event": event.event,
                "details": event.details,
            }
            for event in self.trace
        ]

    def save_trace(self, path: str) -> None:
        data = {
            "step_count": self.step_count,
            "max_steps": self.max_steps,
            "max_concurrency": self.max_concurrency,
            "events": self.trace_to_dict(),
        }

        if contains_secret_like_value(data):
            raise CoordinationError(
                "Secret-like content detected while saving trace.",
                FailureType.SECRET_DETECTED,
            )

        with open(
            path,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                data,
                file,
                indent=2,
            )


def save_trace(
    engine: CoordinationEngine,
    path: str,
) -> None:

    if not isinstance(engine, CoordinationEngine):
        raise CoordinationError(
            "save_trace requires a CoordinationEngine.",
            FailureType.VALIDATION,
        )

    engine.save_trace(path)