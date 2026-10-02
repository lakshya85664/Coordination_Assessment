import json

import pytest

from coordination import (
    CoordinationEngine,
    CoordinationError,
    FailureType,
)


def test_dependency_graph_can_be_created():
    engine = CoordinationEngine()

    engine.add_task("task_a")
    engine.add_task("task_b")
    engine.add_task(
        "task_c",
        depends_on={"task_a", "task_b"},
    )

    graph = engine.dependency_graph()

    assert graph == {
        "task_a": [],
        "task_b": [],
        "task_c": ["task_a", "task_b"],
    }


def test_dependencies_can_be_validated():
    engine = CoordinationEngine()

    engine.add_task("task_a")
    engine.add_task(
        "task_b",
        depends_on={"task_a"},
    )

    assert engine.validate_dependencies() is True


def test_cycle_check_succeeds_for_valid_graph():
    engine = CoordinationEngine()

    engine.add_task("task_a")
    engine.add_task(
        "task_b",
        depends_on={"task_a"},
    )
    engine.add_task(
        "task_c",
        depends_on={"task_b"},
    )

    assert engine.detect_cycle() is False


def test_unknown_dependency_is_rejected():
    engine = CoordinationEngine()

    engine.add_task("task_a")

    with pytest.raises(CoordinationError) as exc_info:
        engine.add_task(
            "task_b",
            depends_on={"missing_task"},
        )

    assert exc_info.value.failure_type == FailureType.DEPENDENCY_NOT_FOUND


def test_duplicate_task_is_rejected():
    engine = CoordinationEngine()

    engine.add_task("task_a")

    with pytest.raises(CoordinationError) as exc_info:
        engine.add_task("task_a")

    assert exc_info.value.failure_type == FailureType.DUPLICATE_TASK


def test_unknown_task_lookup_is_rejected():
    engine = CoordinationEngine()

    with pytest.raises(CoordinationError) as exc_info:
        engine.get_task("missing_task")

    assert exc_info.value.failure_type == FailureType.TASK_NOT_FOUND


def test_secret_like_dependency_is_rejected():
    engine = CoordinationEngine()

    engine.add_task("task_a")

    with pytest.raises(CoordinationError) as exc_info:
        engine.add_task(
            "task_b",
            depends_on={"api_key=supersecret"},
        )

    assert exc_info.value.failure_type == FailureType.SECRET_DETECTED


def test_dependency_trace_can_be_saved(tmp_path):
    engine = CoordinationEngine()

    engine.add_task("task_a")
    engine.add_task(
        "task_b",
        depends_on={"task_a"},
    )

    engine.validate_dependencies()

    trace_path = tmp_path / "task1_trace.json"

    engine.save_trace(str(trace_path))

    assert trace_path.exists()

    data = json.loads(
        trace_path.read_text(encoding="utf-8")
    )

    assert data["step_count"] == 3
    assert data["max_steps"] == 20
    assert len(data["events"]) == 3

    event_names = [
        event["event"]
        for event in data["events"]
    ]

    assert "task_added" in event_names
    assert "dependencies_validated" in event_names