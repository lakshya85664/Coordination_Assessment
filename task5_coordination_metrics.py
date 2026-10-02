from coordination import CoordinationEngine


def print_metrics(label, metrics):
    print(label)
    print(f"overall_status: {metrics['overall_status']}")
    print(f"total_tasks: {metrics['total_tasks']}")
    print(f"status_counts: {metrics['status_counts']}")
    print(f"successful_count: {metrics['successful_count']}")
    print(f"failed_count: {metrics['failed_count']}")
    print(f"blocked_count: {metrics['blocked_count']}")
    print(f"cancelled_count: {metrics['cancelled_count']}")
    print(f"running_count: {metrics['running_count']}")
    print(f"terminal_count: {metrics['terminal_count']}")
    print(f"completion_rate: {metrics['completion_rate']}")
    print(f"failure_rate: {metrics['failure_rate']}")
    print(f"max_concurrency: {metrics['max_concurrency']}")
    print(f"available_slots: {metrics['available_slots']}")
    print(f"step_count: {metrics['step_count']}")
    print(f"max_steps: {metrics['max_steps']}")
    print(f"step_utilization: {metrics['step_utilization']}")
    print(f"trace_event_count: {metrics['trace_event_count']}")


def main():
    print("=" * 70)
    print("Topic 15 — Task 5: Coordination Metrics")
    print("=" * 70)

    # ============================================================
    # COMPLETE COORDINATION RUN
    # ============================================================

    print("\nCOMPLETE COORDINATION RUN")
    print("-" * 60)

    engine = CoordinationEngine(
        max_concurrency=2
    )

    engine.add_task("task_a")
    engine.add_task("task_b")
    engine.add_task(
        "task_c",
        depends_on={"task_a", "task_b"},
    )

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

    engine.ready_set()

    engine.start_task("task_c")

    engine.mark_success(
        "task_c",
        "Task C completed.",
    )

    metrics = engine.coordination_metrics()

    print_metrics(
        "Coordination metrics:",
        metrics,
    )

    engine.save_trace(
        "traces/task5_trace.json"
    )

    print("\nTRACE SAVED")
    print("traces/task5_trace.json")

    # ============================================================
    # PARTIAL FAILURE METRICS
    # ============================================================

    print("\nPARTIAL FAILURE METRICS")
    print("-" * 60)

    partial_engine = CoordinationEngine(
        max_concurrency=3
    )

    partial_engine.add_task("task_a")
    partial_engine.add_task("task_b")
    partial_engine.add_task("task_c")

    partial_engine.ready_set()

    partial_engine.start_task("task_a")
    partial_engine.start_task("task_b")
    partial_engine.start_task("task_c")

    partial_engine.mark_success(
        "task_a",
        "Task A completed.",
    )

    partial_engine.mark_failed(
        "task_b",
        "Task B failed.",
    )

    partial_engine.mark_success(
        "task_c",
        "Task C completed.",
    )

    partial_metrics = (
        partial_engine.coordination_metrics()
    )

    print_metrics(
        "Partial-run metrics:",
        partial_metrics,
    )

    # ============================================================
    # BLOCKED / CANCELLED METRICS
    # ============================================================

    print("\nBLOCKED / CANCELLED METRICS")
    print("-" * 60)

    status_engine = CoordinationEngine()

    status_engine.add_task("task_a")
    status_engine.add_task(
        "task_b",
        depends_on={"task_a"},
    )
    status_engine.add_task("task_c")

    status_engine.ready_set()

    status_engine.start_task("task_a")

    status_engine.mark_failed(
        "task_a",
        "Task A failed.",
    )

    status_engine.cancel_task(
        "task_c",
        "Task C cancelled by coordinator.",
    )

    status_engine.ready_set()

    status_metrics = (
        status_engine.coordination_metrics()
    )

    print_metrics(
        "Status metrics:",
        status_metrics,
    )

    # ============================================================
    # EMPTY COORDINATION METRICS
    # ============================================================

    print("\nEMPTY COORDINATION METRICS")
    print("-" * 60)

    empty_engine = CoordinationEngine()

    empty_metrics = (
        empty_engine.coordination_metrics()
    )

    print_metrics(
        "Empty-run metrics:",
        empty_metrics,
    )


if __name__ == "__main__":
    main()