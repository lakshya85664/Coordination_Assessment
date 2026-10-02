# Topic 15 — Implement Coordination

## Project Overview

This project implements a deterministic coordination layer for multi-task AI-agent workflows. It demonstrates dependency graphs, ready-set computation, concurrency control, join semantics, partial failure handling, cancellation, and coordination metrics.

The implementation is local and deterministic, so it does not require an external API or model provider.

## Learning Objectives

- Understand coordination as a workflow-level concern rather than simple delegation.
- Represent dependencies and determine task readiness.
- Enforce bounded concurrency.
- Handle success, failure, blocked, and cancelled task states.
- Aggregate task outcomes with join semantics.
- Produce coordination-level metrics and operational traces.
- Apply validation, step limits, secret hygiene, and explicit failure classifications.

## Project Structure

```text
Coordination_Assessment/
├── coordination.py
├── task1_dependency_graph.py
├── task2_ready_set.py
├── task3_concurrency_limit.py
├── task4_join_partial_failure.py
├── task5_coordination_metrics.py
├── tests/
│   ├── test_task1.py
│   ├── test_task2.py
│   ├── test_task3.py
│   ├── test_task4.py
│   └── test_task5.py
├── traces/
├── outputs/
├── requirements.txt
└── .gitignore
```

## Task 1 — Dependency Graph

The coordinator registers tasks and their dependencies.

Implemented behavior:
- Unique task registration.
- Dependency storage and deterministic graph output.
- Validation of referenced dependencies.
- Rejection of unknown dependencies.
- Cycle-detection support.
- Operational trace events.

Example:

```text
task_a <- []
task_b <- []
task_c <- ['task_a', 'task_b']

Dependencies valid: True
Cycle detected: False
```

Invalid dependencies are rejected with `dependency_not_found`.

## Task 2 — Ready Set

A task becomes ready when all dependencies have succeeded.

Implemented behavior:
- Initial ready-set calculation.
- Readiness progression after dependency success.
- Blocking after dependency failure, blocking, or cancellation.
- Unknown-task validation.
- Trace events for readiness and blocking.

Example:

```text
Initial ready set:
['task_a', 'task_b']

After task_a succeeds:
[]

After task_b succeeds:
['task_c']
```

## Task 3 — Concurrency Limit

The coordinator tracks running tasks and available execution slots.

The demonstrated configuration uses a maximum concurrency of 2. A third concurrent task is rejected until a running task completes.

Implemented behavior:
- Running-task tracking.
- Available-slot calculation.
- Ready-state validation before start.
- Concurrency-limit enforcement.

## Task 4 — Join / Partial Failure

The coordinator aggregates task states into a workflow-level result.

Supported overall statuses include:
- `completed`
- `partial_completion`
- `partial_in_progress`
- `failed`
- `in_progress`

The join result reports successful, failed, blocked, and cancelled tasks, plus completed, failure, and terminal counts.

Example:

```text
overall_status: partial_completion
successful_tasks: ['task_a', 'task_c']
failed_tasks: ['task_b']
terminal_count: 3
```

A failed dependency can also cause a downstream task to become blocked.

## Task 5 — Coordination Metrics

The coordinator reports:
- Total tasks.
- Counts for every task status.
- Successful, failed, blocked, and cancelled counts.
- Running and terminal counts.
- Completion and failure rates.
- Maximum concurrency and available slots.
- Step count and step utilization.
- Trace event count.
- Overall coordination status.

Example:

```text
overall_status: completed
total_tasks: 3
successful_count: 3
failed_count: 0
completion_rate: 1.0
failure_rate: 0.0
max_concurrency: 2
```

## Guardrails

### Step Limit
A configurable maximum step budget is enforced. The default is 20 steps.

### Timeout and Retry Classification
`FailureType` includes `timeout` and `transient` classifications.

The assessment demonstrations use deterministic local operations, so active wall-clock timeout enforcement and automatic transient retry are not exercised. The project does not claim those behaviors as active runtime functionality.

### Validation
Validation covers task IDs, duplicates, dependencies, task-state transitions, join inputs, and concurrency configuration.

### Secret Hygiene
Secret-like values are rejected from operational task data where applicable.

### Reasoning Safety
Traces contain operational coordination state and events only. Hidden chain-of-thought is not stored.

### Task State Model

```text
pending
ready
running
success
failed
blocked
cancelled
```

## Traceability

Each demonstration saves an operational JSON trace:

```text
traces/task1_trace.json
traces/task2_trace.json
traces/task3_trace.json
traces/task4_trace.json
traces/task5_trace.json
```

## Testing

Run the complete test suite:

```cmd
python -m pytest -q
```

Final result:

```text
54 passed in 0.10s
```

All five task test modules pass together.

## Demonstration Coverage

| Task | Core Behavior | Edge / Rejection Behavior |
|---|---|---|
| 1 | Dependency graph and validation | Unknown dependency |
| 2 | Ready-set progression | Unknown task and dependency blocking |
| 3 | Running tasks and concurrency slots | Concurrency limit and invalid start |
| 4 | Complete join and partial completion | Failure, blocked, cancellation, invalid join |
| 5 | Coordination metrics | Partial failure, blocked/cancelled, empty run |

## Execution

Activate the environment and install dependencies:

```cmd
.venv\Scripts\activate
pip install -r requirements.txt
```

Run the full suite:

```cmd
python -m pytest -q
```

Run demonstrations:

```cmd
python task1_dependency_graph.py
python task2_ready_set.py
python task3_concurrency_limit.py
python task4_join_partial_failure.py
python task5_coordination_metrics.py
```

## Final Verification

The final project state was verified with:

```text
54 passed in 0.10s
```

All five demonstrations completed successfully and generated their corresponding trace files.

## Reflection

This activity helped me understand that coordination is more than assigning work to workers. A coordinator must reason about dependencies, readiness, concurrency, completion, failure, blocking, and cancellation as a connected workflow. Implementing the dependency graph showed how downstream tasks should remain unavailable until their prerequisites succeed. The ready-set implementation made this relationship operational by identifying exactly which tasks can move forward.

The concurrency task highlighted that even when several tasks are ready, execution capacity can be bounded. Tracking running tasks and available slots provides a simple control mechanism for scheduling. The join and partial-failure task showed that a multi-task job does not always have a binary success or failure outcome. A workflow can contain successful tasks alongside failures or blocked work, so explicit states make the final result more informative.

Finally, the metrics task connected internal task state to observable operational information such as completion rate, failure rate, concurrency, step utilization, and trace counts. The project reinforced the importance of validation, step limits, secret hygiene, and explicit failure classifications for reliable multi-agent workflows. Overall, this project provided a practical foundation for building reliable multi-step and multi-agent workflows while keeping operational traces separate from hidden reasoning.
