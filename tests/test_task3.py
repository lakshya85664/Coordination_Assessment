import pytest

from coordination import (
    CoordinationEngine,
    CoordinationError,
    FailureType,
    TaskStatus,
)


def build_engine(max_concurrency=2):
    engine = CoordinationEngine(
        max_concurrency=max_concurrency
    )

    engine.add_task("task_a")
    engine.add_task("task_b")
    engine.add_task("task_c")

    engine.ready_set()

    return engine


def test_two_tasks_can_run_with_concurrency_limit_two():
    engine = build_engine(max_concurrency=2)

    engine.start_task("task_a")
    engine.start_task("task_b")

    assert engine.get_task("task_a").status == TaskStatus.RUNNING
    assert engine.get_task("task_b").status == TaskStatus.RUNNING
    assert engine.available_slots() == 0


def test_third_task_is_rejected_when_limit_is_reached():
    engine = build_engine(max_concurrency=2)

    engine.start_task("task_a")
    engine.start_task("task_b")

    with pytest.raises(CoordinationError) as exc_info:
        engine.start_task("task_c")

    assert exc_info.value.failure_type == FailureType.CONCURRENCY_LIMIT
    assert engine.get_task("task_c").status == TaskStatus.READY


def test_completed_task_frees_concurrency_slot():
    engine = build_engine(max_concurrency=2)

    engine.start_task("task_a")
    engine.start_task("task_b")

    assert engine.available_slots() == 0

    engine.mark_success(
        "task_a",
        "Task A completed.",
    )

    assert engine.available_slots() == 1


def test_freed_slot_allows_ready_task_to_start():
    engine = build_engine(max_concurrency=2)

    engine.start_task("task_a")
    engine.start_task("task_b")

    engine.mark_success(
        "task_a",
        "Task A completed.",
    )

    engine.start_task("task_c")

    assert engine.get_task("task_c").status == TaskStatus.RUNNING
    assert engine.available_slots() == 0


def test_running_tasks_are_reported_deterministically():
    engine = build_engine(max_concurrency=2)

    engine.start_task("task_b")
    engine.start_task("task_a")

    running = engine.running_tasks()

    assert [task.id for task in running] == [
        "task_a",
        "task_b",
    ]


def test_unknown_task_start_is_rejected():
    engine = build_engine()

    with pytest.raises(CoordinationError) as exc_info:
        engine.start_task("unknown_task")

    assert exc_info.value.failure_type == FailureType.TASK_NOT_FOUND


def test_non_ready_task_start_is_rejected():
    engine = build_engine()

    engine.start_task("task_a")

    with pytest.raises(CoordinationError) as exc_info:
        engine.start_task("task_a")

    assert exc_info.value.failure_type == FailureType.VALIDATION


def test_invalid_concurrency_limit_is_rejected():
    with pytest.raises(CoordinationError) as exc_info:
        CoordinationEngine(max_concurrency=0)

    assert exc_info.value.failure_type == FailureType.VALIDATION


def test_concurrency_events_are_recorded():
    engine = build_engine(max_concurrency=2)

    engine.start_task("task_a")
    engine.start_task("task_b")

    engine.mark_success(
        "task_a",
        "Task A completed.",
    )

    events = [
        event.event
        for event in engine.trace
    ]

    assert "task_started" in events
    assert "task_succeeded" in events


def test_secret_like_result_is_rejected():
    engine = build_engine()

    with pytest.raises(CoordinationError) as exc_info:
        engine.mark_success(
            "task_a",
            "api_key=SECRET_VALUE_12345",
        )

    assert exc_info.value.failure_type == FailureType.SECRET_DETECTED