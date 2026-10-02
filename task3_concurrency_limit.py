from coordination import (
    CoordinationEngine,
    CoordinationError,
)


def main():
    print("=" * 70)
    print("Topic 15 — Task 3: Concurrency Limit")
    print("=" * 70)

    # ============================================================
    # SUCCESS PATH
    # ============================================================

    print("\nSUCCESS PATH")
    print("-" * 60)

    engine = CoordinationEngine(max_concurrency=2)

    engine.add_task("task_a")
    engine.add_task("task_b")
    engine.add_task("task_c")

    ready = engine.ready_set()

    print("Initial ready set:")
    print([task.id for task in ready])

    # Start two tasks.
    engine.start_task("task_a")
    engine.start_task("task_b")

    print("Running tasks after starting two tasks:")
    print([task.id for task in engine.running_tasks()])

    print("Available concurrency slots:")
    print(engine.available_slots())

    # Complete task A.
    engine.mark_success(
        "task_a",
        "Task A completed successfully.",
    )

    print("Running tasks after task_a succeeds:")
    print([task.id for task in engine.running_tasks()])

    print("Available concurrency slots after task_a succeeds:")
    print(engine.available_slots())

    # The freed slot can now be used by task C.
    engine.start_task("task_c")

    print("Running tasks after task_c starts:")
    print([task.id for task in engine.running_tasks()])

    # Complete remaining tasks.
    engine.mark_success(
        "task_b",
        "Task B completed successfully.",
    )

    engine.mark_success(
        "task_c",
        "Task C completed successfully.",
    )

    print("Final task statuses:")

    for task_id in sorted(engine.tasks):
        task = engine.get_task(task_id)
        print(f"  {task_id}: {task.status.value}")

    engine.save_trace("traces/task3_trace.json")

    print("\nTRACE SAVED")
    print("traces/task3_trace.json")

    # ============================================================
    # CONCURRENCY LIMIT PATH
    # ============================================================

    print("\nCONCURRENCY LIMIT PATH")
    print("-" * 60)

    limited_engine = CoordinationEngine(max_concurrency=2)

    limited_engine.add_task("task_a")
    limited_engine.add_task("task_b")
    limited_engine.add_task("task_c")

    limited_engine.ready_set()

    limited_engine.start_task("task_a")
    limited_engine.start_task("task_b")

    # The third task cannot start because both slots are occupied.
    try:
        limited_engine.start_task("task_c")
    except CoordinationError as exc:
        print(f"Rejected third concurrent task: {exc}")
        print(f"failure_type={exc.failure_type.value}")

    print("Currently running:")
    print(
        [
            task.id
            for task in limited_engine.running_tasks()
        ]
    )

    # ============================================================
    # REJECTION PATH
    # ============================================================

    print("\nREJECTION PATH")
    print("-" * 60)

    # Unknown task.
    try:
        limited_engine.start_task("unknown_task")
    except CoordinationError as exc:
        print(f"Rejected unknown task start: {exc}")
        print(f"failure_type={exc.failure_type.value}")

    # Free one concurrency slot.
    limited_engine.mark_success(
        "task_a",
        "Task A completed successfully.",
    )

    # task_a is now SUCCESS, so it cannot be started again.
    try:
        limited_engine.start_task("task_a")
    except CoordinationError as exc:
        print(f"Rejected non-ready task start: {exc}")
        print(f"failure_type={exc.failure_type.value}")


if __name__ == "__main__":
    main()