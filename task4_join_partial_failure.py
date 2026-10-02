from coordination import (
    CoordinationEngine,
    CoordinationError,
)


def print_join_result(label, result):
    print(label)
    print(f"overall_status: {result['overall_status']}")
    print(f"total_tasks: {result['total_tasks']}")
    print(f"successful_tasks: {result['successful_tasks']}")
    print(f"failed_tasks: {result['failed_tasks']}")
    print(f"blocked_tasks: {result['blocked_tasks']}")
    print(f"cancelled_tasks: {result['cancelled_tasks']}")
    print(f"completed_count: {result['completed_count']}")
    print(f"failure_count: {result['failure_count']}")
    print(f"terminal_count: {result['terminal_count']}")
    print(f"all_tasks_completed: {result['all_tasks_completed']}")


def main():
    print("=" * 70)
    print("Topic 15 — Task 4: Join / Partial Failure")
    print("=" * 70)

    # ============================================================
    # COMPLETE JOIN PATH
    # ============================================================

    print("\nCOMPLETE JOIN PATH")
    print("-" * 60)

    engine = CoordinationEngine()

    engine.add_task("task_a")
    engine.add_task("task_b")
    engine.add_task("task_c")

    engine.ready_set()

    engine.start_task("task_a")
    engine.start_task("task_b")

    engine.mark_success(
        "task_a",
        "Task A completed successfully.",
    )

    engine.mark_success(
        "task_b",
        "Task B completed successfully.",
    )

    engine.start_task("task_c")

    engine.mark_success(
        "task_c",
        "Task C completed successfully.",
    )

    result = engine.join(
        ["task_a", "task_b", "task_c"]
    )

    print_join_result(
        "Join result:",
        result,
    )

    # ============================================================
    # PARTIAL FAILURE PATH
    # ============================================================

    print("\nPARTIAL FAILURE PATH")
    print("-" * 60)

    partial_engine = CoordinationEngine()

    partial_engine.add_task("task_a")
    partial_engine.add_task("task_b")
    partial_engine.add_task("task_c")

    partial_engine.ready_set()

    partial_engine.start_task("task_a")
    partial_engine.start_task("task_b")

    partial_engine.mark_success(
        "task_a",
        "Task A completed successfully.",
    )

    partial_engine.mark_failed(
        "task_b",
        "Task B failed during execution.",
    )

    partial_engine.start_task("task_c")

    partial_engine.mark_success(
        "task_c",
        "Task C completed successfully.",
    )

    partial_result = partial_engine.join(
        ["task_a", "task_b", "task_c"]
    )

    print_join_result(
        "Join result:",
        partial_result,
    )

    # ============================================================
    # BLOCKED DEPENDENCY PATH
    # ============================================================

    print("\nBLOCKED DEPENDENCY PATH")
    print("-" * 60)

    blocked_engine = CoordinationEngine()

    blocked_engine.add_task("task_a")
    blocked_engine.add_task(
        "task_b",
        depends_on={"task_a"},
    )

    blocked_engine.ready_set()

    blocked_engine.start_task("task_a")

    blocked_engine.mark_failed(
        "task_a",
        "Task A failed.",
    )

    blocked_engine.ready_set()

    blocked_result = blocked_engine.join(
        ["task_a", "task_b"]
    )

    print_join_result(
        "Join result:",
        blocked_result,
    )

    print(
        f"task_b status: "
        f"{blocked_engine.get_task('task_b').status.value}"
    )

    # ============================================================
    # CANCELLATION PATH
    # ============================================================

    print("\nCANCELLATION PATH")
    print("-" * 60)

    cancelled_engine = CoordinationEngine()

    cancelled_engine.add_task("task_a")
    cancelled_engine.add_task("task_b")

    cancelled_engine.ready_set()

    cancelled_engine.cancel_task(
        "task_b",
        "Task B cancelled by coordinator.",
    )

    cancelled_result = cancelled_engine.join(
        ["task_a", "task_b"]
    )

    print_join_result(
        "Join result:",
        cancelled_result,
    )

    # ============================================================
    # REJECTION PATH
    # ============================================================

    print("\nREJECTION PATH")
    print("-" * 60)

    try:
        engine.join(
            ["task_a", "task_a"]
        )
    except CoordinationError as exc:
        print(f"Rejected duplicate join task IDs: {exc}")
        print(f"failure_type={exc.failure_type.value}")

    try:
        engine.join(
            ["unknown_task"]
        )
    except CoordinationError as exc:
        print(f"Rejected unknown join task: {exc}")
        print(f"failure_type={exc.failure_type.value}")

    engine.save_trace(
        "traces/task4_trace.json"
    )

    print("\nTRACE SAVED")
    print("traces/task4_trace.json")


if __name__ == "__main__":
    main()