import json

import pytest

from coordination import (
    CoordinationEngine,
    CoordinationError,
    FailureType,
    TaskStatus,
)


def build_engine():
    engine = CoordinationEngine()

    engine.add_task("task_a")
    engine.add_task("task_b")
    engine.add_task("task_c", depends_on={"task_a", "task_b"})

    return engine


def test_initial_ready_set_contains_tasks_without_dependencies():
    engine = build_engine()

    ready = engine.ready_set()

    assert [task.id for task in ready] == ["task_a", "task_b"]
    assert engine.get_task("task_a").status == TaskStatus.READY
    assert engine.get_task("task_b").status == TaskStatus.READY


def test_dependent_task_waits_for_all_dependencies():
    engine = build_engine()

    engine.ready_set()

    engine.mark_success("task_a", "A completed")

    ready = engine.ready_set()

    assert [task.id for task in ready] == []
    assert engine.get_task("task_c").status == TaskStatus.PENDING


def test_dependent_task_becomes_ready_after_all_dependencies_succeed():
    engine = build_engine()

    engine.ready_set()

    engine.mark_success("task_a", "A completed")
    engine.mark_success("task_b", "B completed")

    ready = engine.ready_set()

    assert [task.id for task in ready] == ["task_c"]
    assert engine.get_task("task_c").status == TaskStatus.READY


def test_failed_dependency_blocks_downstream_task():
    engine = build_engine()

    engine.ready_set()

    engine.mark_failed("task_a", "A failed")

    ready = engine.ready_set()

    assert [task.id for task in ready] == []
    assert engine.get_task("task_b").status == TaskStatus.READY
    assert engine.get_task("task_c").status == TaskStatus.BLOCKED


def test_multiple_ready_tasks_are_sorted_deterministically():
    engine = CoordinationEngine()

    engine.add_task("task_z")
    engine.add_task("task_a")
    engine.add_task("task_m")

    ready = engine.ready_set()

    assert [task.id for task in ready] == [
        "task_a",
        "task_m",
        "task_z",
    ]


def test_success_requires_ready_or_running_status():
    engine = build_engine()

    with pytest.raises(CoordinationError) as exc_info:
        engine.mark_success("task_c", "Invalid completion")

    assert exc_info.value.failure_type == FailureType.VALIDATION


def test_unknown_task_completion_is_rejected():
    engine = build_engine()

    with pytest.raises(CoordinationError) as exc_info:
        engine.mark_success(
            "unknown_task",
            "Invalid task completion",
        )

    assert exc_info.value.failure_type == FailureType.TASK_NOT_FOUND


def test_ready_set_records_trace_events():
    engine = build_engine()

    engine.ready_set()

    events = [event.event for event in engine.trace]

    assert "task_ready" in events
    assert "ready_set_computed" in events


def test_secret_like_result_is_rejected():
    engine = build_engine()

    engine.ready_set()

    with pytest.raises(CoordinationError) as exc_info:
        engine.mark_success(
            "task_a",
            "api_key=SECRET_VALUE_12345",
        )

    assert exc_info.value.failure_type == FailureType.SECRET_DETECTED