import pytest

from coordination import (
    CoordinationEngine,
    CoordinationError,
    FailureType,
    TaskStatus,
)


def test_metrics_report_completed_run():
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

    metrics = engine.coordination_metrics()

    assert metrics["overall_status"] == "completed"
    assert metrics["total_tasks"] == 2
    assert metrics["successful_count"] == 2
    assert metrics["failed_count"] == 0
    assert metrics["completion_rate"] == 1.0
    assert metrics["failure_rate"] == 0.0
    assert metrics["terminal_count"] == 2


def test_metrics_report_partial_completion():
    engine = CoordinationEngine(
        max_concurrency=3
    )

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

    metrics = engine.coordination_metrics()

    assert metrics["overall_status"] == "partial_completion"
    assert metrics["successful_count"] == 2
    assert metrics["failed_count"] == 1
    assert metrics["completion_rate"] == pytest.approx(2 / 3)
    assert metrics["failure_rate"] == pytest.approx(1 / 3)
    assert metrics["terminal_count"] == 3


def test_metrics_count_blocked_tasks():
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

    metrics = engine.coordination_metrics()

    assert metrics["failed_count"] == 1
    assert metrics["blocked_count"] == 1
    assert metrics["terminal_count"] == 2
    assert metrics["overall_status"] == "failed"


def test_metrics_count_cancelled_tasks():
    engine = CoordinationEngine()

    engine.add_task("task_a")
    engine.add_task("task_b")

    engine.ready_set()

    engine.cancel_task(
        "task_b",
        "Task B cancelled.",
    )

    metrics = engine.coordination_metrics()

    assert metrics["cancelled_count"] == 1
    assert metrics["terminal_count"] == 1
    assert metrics["overall_status"] == "in_progress"


def test_metrics_count_running_tasks():
    engine = CoordinationEngine()

    engine.add_task("task_a")

    engine.ready_set()
    engine.start_task("task_a")

    metrics = engine.coordination_metrics()

    assert metrics["running_count"] == 1
    assert metrics["terminal_count"] == 0
    assert metrics["overall_status"] == "in_progress"


def test_metrics_report_concurrency_capacity():
    engine = CoordinationEngine(
        max_concurrency=3
    )

    engine.add_task("task_a")
    engine.add_task("task_b")

    engine.ready_set()

    engine.start_task("task_a")

    metrics = engine.coordination_metrics()

    assert metrics["max_concurrency"] == 3
    assert metrics["running_count"] == 1
    assert metrics["available_slots"] == 2


def test_metrics_report_step_utilization():
    engine = CoordinationEngine(
        max_steps=20
    )

    engine.add_task("task_a")

    metrics = engine.coordination_metrics()

    assert metrics["step_count"] > 0
    assert metrics["max_steps"] == 20
    assert metrics["step_utilization"] == pytest.approx(
        metrics["step_count"] / 20
    )


def test_metrics_report_trace_event_count():
    engine = CoordinationEngine()

    engine.add_task("task_a")
    engine.ready_set()

    before_metrics = len(engine.trace)

    metrics = engine.coordination_metrics()

    assert metrics["trace_event_count"] == before_metrics


def test_empty_engine_metrics_are_safe():
    engine = CoordinationEngine()

    metrics = engine.coordination_metrics()

    assert metrics["overall_status"] == "no_tasks"
    assert metrics["total_tasks"] == 0
    assert metrics["successful_count"] == 0
    assert metrics["failed_count"] == 0
    assert metrics["blocked_count"] == 0
    assert metrics["cancelled_count"] == 0
    assert metrics["completion_rate"] == 0.0
    assert metrics["failure_rate"] == 0.0


def test_metrics_include_all_task_statuses():
    engine = CoordinationEngine()

    metrics = engine.coordination_metrics()

    status_counts = metrics["status_counts"]

    assert set(status_counts.keys()) == {
        "pending",
        "ready",
        "running",
        "success",
        "failed",
        "blocked",
        "cancelled",
    }


def test_metrics_secret_hygiene():
    engine = CoordinationEngine()

    engine.add_task("task_a")

    # Normal task IDs and state must not cause secret detection.
    metrics = engine.coordination_metrics()

    assert "status_counts" in metrics


def test_metrics_are_traceable():
    engine = CoordinationEngine()

    engine.add_task("task_a")

    engine.coordination_metrics()

    events = [
        event.event
        for event in engine.trace
    ]

    assert "coordination_metrics_computed" in events


def test_invalid_max_steps_is_rejected():
    with pytest.raises(CoordinationError) as exc_info:
        CoordinationEngine(max_steps=0)

    assert exc_info.value.failure_type == FailureType.VALIDATION


def test_invalid_max_concurrency_is_rejected():
    with pytest.raises(CoordinationError) as exc_info:
        CoordinationEngine(max_concurrency=0)

    assert exc_info.value.failure_type == FailureType.VALIDATION


def test_metrics_do_not_expose_task_results():
    engine = CoordinationEngine()

    engine.add_task("task_a")
    engine.ready_set()
    engine.mark_success(
        "task_a",
        "Normal result value.",
    )

    metrics = engine.coordination_metrics()

    assert "Normal result value." not in str(metrics)