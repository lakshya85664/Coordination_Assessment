import pytest

from coordination import (
    CoordinationEngine,
    CoordinationError,
    FailureType,
    TaskStatus,
)


def test_join_reports_complete_when_all_tasks_succeed():
    engine = CoordinationEngine()

    engine.add_task("task_a")
    engine.add_task("task_b")

    engine.ready_set()

    engine.start_task("task_a")
    engine.start_task("task_b")

    engine.mark_success(
        "task_a",
        "Task A completed.",
    )

    engine.mark_success(
        "task_b",
        "Task B completed.",
    )

    result = engine.join(
        ["task_a", "task_b"]
    )

    assert result["overall_status"] == "completed"
    assert result["completed_count"] == 2
    assert result["failure_count"] == 0
    assert result["all_tasks_completed"] is True


def test_join_reports_partial_completion_when_some_tasks_fail():
    engine = CoordinationEngine(max_concurrency=3)

    engine.add_task("task_a")
    engine.add_task("task_b")
    engine.add_task("task_c")

    engine.ready_set()

    engine.start_task("task_a")
    engine.start_task("task_b")
    engine.start_task("task_c")

    engine.mark_success(
        "task_a",
        "Task A completed.",
    )

    engine.mark_failed(
        "task_b",
        "Task B failed.",
    )

    engine.mark_success(
        "task_c",
        "Task C completed.",
    )

    result = engine.join(
        ["task_a", "task_b", "task_c"]
    )

    assert result["overall_status"] == "partial_completion"
    assert result["successful_tasks"] == [
        "task_a",
        "task_c",
    ]
    assert result["failed_tasks"] == ["task_b"]
    assert result["completed_count"] == 2
    assert result["failure_count"] == 1
    assert result["all_tasks_completed"] is False


def test_failed_dependency_blocks_downstream_task():
    engine = CoordinationEngine()

    engine.add_task("task_a")
    engine.add_task(
        "task_b",
        depends_on={"task_a"},
    )

    engine.ready_set()

    engine.start_task("task_a")

    engine.mark_failed(
        "task_a",
        "Task A failed.",
    )

    engine.ready_set()

    assert engine.get_task("task_b").status == TaskStatus.BLOCKED

    result = engine.join(
        ["task_a", "task_b"]
    )

    assert result["blocked_tasks"] == ["task_b"]
    assert result["failed_tasks"] == ["task_a"]
    assert result["all_tasks_completed"] is False


def test_cancelled_task_is_reported_by_join():
    engine = CoordinationEngine()

    engine.add_task("task_a")
    engine.add_task("task_b")

    engine.ready_set()

    engine.cancel_task(
        "task_b",
        "Cancelled by coordinator.",
    )

    result = engine.join(
        ["task_a", "task_b"]
    )

    assert result["cancelled_tasks"] == ["task_b"]
    assert result["overall_status"] == "in_progress"
    assert result["all_tasks_completed"] is False


def test_join_reports_in_progress_when_non_terminal_tasks_remain():
    engine = CoordinationEngine()

    engine.add_task("task_a")
    engine.add_task("task_b")

    engine.ready_set()

    engine.start_task("task_a")

    engine.mark_success(
        "task_a",
        "Task A completed.",
    )

    result = engine.join(
        ["task_a", "task_b"]
    )

    assert result["overall_status"] == "partial_in_progress"
    assert result["successful_tasks"] == ["task_a"]
    assert result["ready_tasks"] == ["task_b"]
    assert result["all_tasks_completed"] is False


def test_duplicate_join_task_ids_are_rejected():
    engine = CoordinationEngine()

    engine.add_task("task_a")

    with pytest.raises(CoordinationError) as exc_info:
        engine.join(
            ["task_a", "task_a"]
        )

    assert exc_info.value.failure_type == FailureType.VALIDATION


def test_unknown_join_task_is_rejected():
    engine = CoordinationEngine()

    engine.add_task("task_a")

    with pytest.raises(CoordinationError) as exc_info:
        engine.join(
            ["unknown_task"]
        )

    assert exc_info.value.failure_type == FailureType.TASK_NOT_FOUND


def test_empty_join_is_rejected():
    engine = CoordinationEngine()

    with pytest.raises(CoordinationError) as exc_info:
        engine.join([])

    assert exc_info.value.failure_type == FailureType.VALIDATION


def test_cancel_task_records_cancelled_status():
    engine = CoordinationEngine()

    engine.add_task("task_a")

    engine.ready_set()

    task = engine.cancel_task(
        "task_a",
        "Cancelled for testing.",
    )

    assert task.status == TaskStatus.CANCELLED
    assert task.error == "Cancelled for testing."


def test_join_records_trace_event():
    engine = CoordinationEngine()

    engine.add_task("task_a")

    engine.ready_set()

    result = engine.join(["task_a"])

    assert result["overall_status"] == "in_progress"

    events = [
        event.event
        for event in engine.trace
    ]

    assert "join_computed" in events


def test_secret_like_join_input_is_rejected():
    engine = CoordinationEngine()

    engine.add_task("task_a")

    with pytest.raises(CoordinationError) as exc_info:
        engine.join(
            ["api_key=SECRET_VALUE_12345"]
        )

    assert exc_info.value.failure_type == FailureType.SECRET_DETECTED


def test_secret_like_cancellation_reason_is_rejected():
    engine = CoordinationEngine()

    engine.add_task("task_a")

    engine.ready_set()

    with pytest.raises(CoordinationError) as exc_info:
        engine.cancel_task(
            "task_a",
            "api_key=SECRET_VALUE_12345",
        )

    assert exc_info.value.failure_type == FailureType.SECRET_DETECTED