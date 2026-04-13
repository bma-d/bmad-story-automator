# State And Resume

This doc explains the orchestration state document, the active-run marker, and the resume, validate, and edit flows.

## State Document Anatomy

The state document is generated from `templates/state-document.md` and written as:

```text
_bmad-output/story-automator/orchestration-<epic>-<timestamp>.md
```

It has two parts:

1. frontmatter for machine-readable orchestration state
2. markdown sections for operator-facing progress and logs

### Frontmatter Fields

Important frontmatter fields:

- `epic`
- `epicName`
- `storyRange`
- `status`
- `currentStory`
- `currentStep`
- `stepsCompleted`
- `lastUpdated`
- `aiCommand`
- `overrides`
- `customInstructions`
- `agentsFile`
- `complexityFile`
- `agentConfig`
- `activeSessions`
- `completedSessions`

### Body Sections

Important markdown sections:

- `Configuration`
- `Story Progress`
- `Action Log`
- `Session References`
- `Pending Decisions`
- `Learnings & Recommendations`

## State Lifecycle

```mermaid
flowchart TD
    A["No state file"] --> B["INITIALIZING"]
    B --> C["READY"]
    C --> D["IN_PROGRESS"]
    D --> E["EXECUTION_COMPLETE"]
    E --> F["COMPLETE"]
    D --> G["PAUSED"]
    G --> D
    D --> H["ABORTED"]
```

The state file is updated throughout the run. It is not just a final report.

## Marker File

During active orchestration, Story Automator writes:

```text
.claude/.story-automator-active
```

The marker contains:

- current epic
- current story
- remaining story count
- state file path
- heartbeat data
- project slug and pid metadata

Purpose:

- block accidental stop-hook exits while work remains
- make resume logic safer
- distinguish orchestrator children from unrelated top-level sessions

The marker is removed in wrap-up.

## Resume Flow

```mermaid
flowchart TD
    A["Resume requested"] --> B["Find provided or latest incomplete state"]
    B --> C["Summarize epic, step, status, last action"]
    C --> D["Compare with sprint-status.yaml"]
    D --> E["List live tmux sessions for this project slug"]
    E --> F["Present menu: Resume / View / Modify / Start Over / Abort"]
    F -->|Resume| G["Recreate marker"]
    G --> H["Route to saved step"]
    F -->|View| I["Show action log excerpt"]
    F -->|Modify| J["Enter edit flow"]
    F -->|Start Over| K["Backup state and restart preflight"]
    F -->|Abort| L["Set state to ABORTED"]
```

Resume is step-aware. It does not blindly restart from the beginning.

## Validate Flow

Validation is a first-class mode, not an ad hoc debug routine.

It checks:

- required frontmatter fields
- valid status enums
- YAML/frontmatter integrity
- session references vs live tmux sessions
- per-story progress consistency
- stalled or impossible progress combinations

The validation flow combines structure, session, and progress checks before reporting a final severity bucket.

## Edit Flow

Edit mode lets an operator change orchestration configuration without hand-editing markdown.

Editable areas:

- status
- story range
- execution overrides
- custom context
- AI command
- project-document paths

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant E as Edit Flow
    participant S as State Doc
    participant V as Validate Flow

    U->>E: Open edit mode
    E->>S: Load current state
    E-->>U: Show edit menu
    U->>E: Change fields
    E->>S: Save updates
    E-->>U: Resume / Validate / Exit
    opt Validate
        E->>V: Route into validation steps
    end
```

## Source Of Truth Rules

Not all state is equal.

- state document = orchestration control state
- tmux sessions = execution-state truth
- story files and sprint status = workflow truth

When these disagree:

- the orchestrator should trust source-of-truth artifacts over stale monitor output
- validation should report the mismatch rather than hiding it
- resume should surface the mismatch before continuing

## Practical Operator Notes

- keep the state file; it is the audit trail for the run
- use validate mode when a run looks suspicious before resuming
- use edit mode instead of raw manual frontmatter edits when possible
- a missing marker does not mean a run is complete; check the state file and tmux sessions together

## Read Next

- [Agents And Monitoring](./agents-and-monitoring.md)
- [Troubleshooting](./troubleshooting.md)
