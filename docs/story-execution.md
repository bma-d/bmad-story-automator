# Story Execution

This doc covers what happens after preflight has finished and the orchestrator enters the execution loop.

## Per-Story Lifecycle

Every story moves through the same high-level phases.

```mermaid
sequenceDiagram
    autonumber
    participant O as Orchestrator
    participant C as Create Session
    participant D as Dev Session
    participant A as Automate Session
    participant R as Review Session
    participant P as Sprint Status

    O->>C: Spawn create-story
    C-->>O: monitor-session result
    O->>P: Verify story file exists
    O->>D: Spawn dev-story
    D-->>O: monitor-session result
    O->>P: Verify progress source of truth
    opt Skip Automate = false
        O->>A: Spawn automate
        A-->>O: monitor-session result
    end
    loop Review cycles
        O->>R: Spawn review
        R-->>P: Update sprint-status and story status
        O->>P: Verify review completion
    end
    O->>P: Confirm story done
    O->>O: Commit verified work
```

The orchestrator does not blindly trust session completion. It verifies after each step before moving on.

## Step Ordering Rules

The execution loop follows these rules:

- `create` must succeed before `dev`
- `dev` must succeed before `review`
- `auto` is optional and controlled by `skipAutomate`
- `review` can repeat
- `git commit` happens only after review verification passes

The execution-pattern docs explicitly forbid chaining steps in a single shell loop without per-step verification.

## Code Review Loop

The review loop is the most important gate in the system.

```mermaid
flowchart TD
    A["Spawn review session"] --> B["monitor-session --workflow review --story-key"]
    B --> C{"final_state"}
    C -->|completed| D["Verify sprint-status or story file"]
    C -->|incomplete| E["Retry or escalate"]
    C -->|crashed| E
    C -->|stuck| E
    D --> F{"Story verified done?"}
    F -->|Yes| G["Exit loop and continue to commit"]
    F -->|No| E
    E --> H{"Cycle <= 5?"}
    H -->|Yes| A
    H -->|No| I["Escalate to user"]
```

What counts as a pass:

- review leaves zero critical issues after fixes
- sprint status shows the story as `done`
- or, if needed, the story file shows `Status: done`

What does not count as a pass:

- the child review session exited
- the output file looks finished but sprint status did not update
- progress text suggests success without verification

## Retry And Fallback

The orchestrator supports deterministic retries and agent fallback.

- retries are bounded
- fallback agents come from the generated agent plan
- network or transient failures can sleep before retry
- escalation happens only after retry budget is exhausted

Review, create, dev, and automate all use the same spawn/monitor pattern, but review adds verification before it can declare success.

## Epic Completion And Retrospective

Retrospective is triggered inside the execution loop, not only at final wrap-up.

```mermaid
flowchart TD
    A["Story review verified done"] --> B["Check all stories in current epic"]
    B --> C["Check sprint-status for entire epic"]
    C --> D{"Epic fully complete?"}
    D -->|No| E["Continue with next story"]
    D -->|Yes| F["Spawn retrospective with Claude"]
    F --> G["Run in YOLO mode"]
    G --> H{"Retro completed?"}
    H -->|Yes| I["Log completed retrospective"]
    H -->|No| J["Log skipped retrospective"]
    I --> E
    J --> E
```

Retrospective rules:

- always Claude
- fully automated
- non-blocking
- failure is logged but does not stop the run

## Execution Complete

After the last story:

- orchestration status changes to `EXECUTION_COMPLETE`
- the system moves to wrap-up
- wrap-up writes summary, learnings, recommendations, and removes the active marker

## Practical Operator Notes

- review verification is the real gate
- retrospective runs per completed epic, not just once at the end
- if monitoring fails, the orchestrator is supposed to re-check tmux and workflow truth directly
- `maxParallel > 1` is allowed only when story dependencies permit it

## Read Next

- [Review Workflow](./review-workflow.md)
- [Agents And Monitoring](./agents-and-monitoring.md)
- [Troubleshooting](./troubleshooting.md)
