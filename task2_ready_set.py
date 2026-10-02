from coordination import (
    CoordinationEngine,
    CoordinationError,
)


def main():
    print("=" * 70)
    print("Topic 15 — Task 2: Ready Set")
    print("=" * 70)

    # ------------------------------------------------------------
    # SUCCESS PATH
    # ------------------------------------------------------------

    print("\nSUCCESS PATH")
    print("-" * 60)

    engine = CoordinationEngine()

    engine.add_task("task_a")
    engine.add_task("task_b")
    engine.add_task(
        "task_c",
        depends_on={"task_a", "task_b"},
    )

    ready = engine.ready_set()

    print("Initial ready set:")
    print([task.id for task in ready])

    engine.mark_success(
        "task_a",
        "Task A completed successfully.",
    )

    ready = engine.ready_set()

    print("Ready set after task_a succeeds:")
    print([task.id for task in ready])

    engine.mark_success(
        "task_b",
        "Task B completed successfully.",
    )

    ready = engine.ready_set()

    print("Ready set after task_b succeeds:")
    print([task.id for task in ready])

    engine.save_trace("traces/task2_trace.json")

    print("\nTRACE SAVED")
    print("traces/task2_trace.json")

    # ------------------------------------------------------------
    # FAILURE / BLOCKING PATH
    # ------------------------------------------------------------

    print("\nFAILURE / BLOCKING PATH")
    print("-" * 60)

    failure_engine = CoordinationEngine()

    failure_engine.add_task("task_a")
    failure_engine.add_task(
        "task_b",
        depends_on={"task_a"},
    )

    failure_engine.ready_set()

    failure_engine.mark_failed(
        "task_a",
        "Source task failed during execution.",
    )

    ready = failure_engine.ready_set()

    print("Ready set after dependency failure:")
    print([task.id for task in ready])

    print(
        f"task_b status: "
        f"{failure_engine.get_task('task_b').status.value}"
    )

    print("\nREJECTION PATH")
    print("-" * 60)

    try:
        engine.mark_success(
            "unknown_task",
            "Invalid task completion.",
        )
    except CoordinationError as exc:
        print(f"Rejected premature success: {exc}")
        print(f"failure_type={exc.failure_type.value}")


if __name__ == "__main__":
    main()