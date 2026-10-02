from coordination import (
    CoordinationEngine,
    CoordinationError,
)


def main():
    print("=" * 70)
    print("Topic 15 — Task 1: Dependency Graph")
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

    engine.validate_dependencies()
    engine.detect_cycle()

    graph = engine.dependency_graph()

    print("Dependency graph:")
    for task_id, dependencies in graph.items():
        print(f"  {task_id} <- {dependencies}")

    print("Dependencies valid: True")
    print("Cycle detected: False")

    engine.save_trace("traces/task1_trace.json")

    print("\nTRACE SAVED")
    print("traces/task1_trace.json")

    # ------------------------------------------------------------
    # REJECTION PATH
    # ------------------------------------------------------------

    print("\nREJECTION PATH")
    print("-" * 60)

    rejection_engine = CoordinationEngine()

    rejection_engine.add_task("task_a")

    try:
        rejection_engine.add_task(
            "task_c",
            depends_on={"missing_task"},
        )
    except CoordinationError as exc:
        print(f"Rejected invalid dependency: {exc}")
        print(f"failure_type={exc.failure_type.value}")


if __name__ == "__main__":
    main()