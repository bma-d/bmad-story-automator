# CLI Reference

The installed helper command is usually:

```text
.claude/skills/bmad-story-automator/scripts/story-automator
```

It exposes one flat command surface with grouped responsibilities.

## Command Families

```mermaid
flowchart TD
    A["story-automator"] --> B["Parsing"]
    A --> C["State"]
    A --> D["tmux"]
    A --> E["Orchestrator helpers"]
    A --> F["Agent config"]
    A --> G["Basic utilities"]
```

## Parsing Commands

- `parse-epic --file <path>`
- `parse-story --epic <path> --story <id> --rules <file>`
- `parse-story-range --input <selection> --total <count> --ids <csv>`
- `epic-complete --epic <path> --range <csv>`

Use these during preflight to keep story selection and complexity scoring deterministic.

## State Commands

- `build-state-doc`
- `state-metrics --state <file>`
- `validate-state --state <file>`
- `sprint-compare --state <file> --sprint <file>`

Use these to create, inspect, and validate orchestration state.

## tmux Commands

- `tmux-wrapper spawn`
- `tmux-wrapper build-cmd`
- `tmux-wrapper kill`
- `tmux-wrapper list`
- `monitor-session`
- `tmux-status-check`
- `codex-status-check`
- `heartbeat-check`

Critical rule:

- always pass `--command` to `tmux-wrapper spawn`

## Orchestrator Helper Commands

- `orchestrator-helper sprint-status get|exists|check-epic`
- `orchestrator-helper state-list`
- `orchestrator-helper state-latest`
- `orchestrator-helper state-latest-incomplete`
- `orchestrator-helper state-summary`
- `orchestrator-helper state-update`
- `orchestrator-helper marker create|remove|check|heartbeat`
- `orchestrator-helper verify-code-review`
- `orchestrator-helper get-epic-stories`
- `orchestrator-helper check-epic-complete`
- `orchestrator-helper agents-build`
- `orchestrator-helper agents-resolve`

These commands are the orchestration control plane.

## Agent Config Commands

- `agent-config list`
- `agent-config save`
- `agent-config ...`

These support saved presets and generated agent plans.

## Basic Utility Commands

- `derive-project-slug`
- `ensure-marker-gitignore`
- `ensure-stop-hook`
- `stop-hook`
- `list-sessions`
- `commit-story`
- `validate-story-creation`

## Typical Patterns

### Build And Spawn

```bash
scripts=".claude/skills/bmad-story-automator/scripts/story-automator"
cmd="$("$scripts" tmux-wrapper build-cmd review 1.2 --agent claude)"
session="$("$scripts" tmux-wrapper spawn review 1 1.2 --agent claude --command "$cmd")"
```

### Monitor With Review Verification

```bash
"$scripts" monitor-session "$session" --json --agent claude --workflow review --story-key 1.2
```

### Resolve Agent For A Story Task

```bash
"$scripts" orchestrator-helper agents-resolve --state-file "$state_file" --story 1.2 --task review
```

## Read Next

- [Agents And Monitoring](./agents-and-monitoring.md)
- [Troubleshooting](./troubleshooting.md)
