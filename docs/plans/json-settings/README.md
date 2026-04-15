# JSON Settings Plan

Purpose: move prompt text, parse contracts, verifier thresholds, and bounded loop rules out of scattered Python constants and into deterministic JSON settings, without replacing the existing runtime engine.

## Summary

This plan chooses:

- JSON for machine settings
- markdown/XML for long prompt and workflow prose
- bundled defaults plus optional project override plus pinned snapshot
- named Python verifiers, not arbitrary expressions
- bounded workflow primitives, not user-defined workflow graphs

That gives most of the configurability value with moderate risk.

## Why This Exists

Today the behavior is split across:

- `source/src/story_automator/commands/tmux.py`
- `source/src/story_automator/commands/orchestrator_parse.py`
- `source/src/story_automator/commands/orchestrator.py`
- `source/src/story_automator/core/review_verify.py`
- `source/src/story_automator/core/workflow_paths.py`
- `payload/.claude/skills/bmad-story-automator/workflow.md`
- `payload/.claude/skills/bmad-story-automator-review/workflow.yaml`
- `payload/.claude/skills/bmad-story-automator-review/instructions.xml`

That split is the main source of drift risk. This packet defines one implementation path to pull the machine contract into JSON settings while keeping the current engine intact.

## Doc Map

- [01-why-json-settings.md](./01-why-json-settings.md)  
  Problem, goals, non-goals, and why JSON is the right fit for this repo.
- [02-policy-model.md](./02-policy-model.md)  
  Target architecture, file locations, merge rules, schema shape, and data/runtime boundaries.
- [03-code-and-payload-changes.md](./03-code-and-payload-changes.md)  
  Exact source and payload touchpoints, including new modules and file-by-file changes.
- [04-migration-testing-and-risks.md](./04-migration-testing-and-risks.md)  
  Compatibility plan, resume semantics, test strategy, and risk controls.
- [TODO.md](./TODO.md)  
  Sequential execution checklist with dependencies and exit criteria.

## Read Order

1. Read [01-why-json-settings.md](./01-why-json-settings.md)
2. Read [02-policy-model.md](./02-policy-model.md)
3. Read [03-code-and-payload-changes.md](./03-code-and-payload-changes.md)
4. Read [04-migration-testing-and-risks.md](./04-migration-testing-and-risks.md)
5. Execute [TODO.md](./TODO.md) top to bottom

## Core Decision

The implementation should use this model:

```text
bundled default policy
  + optional project override
  = effective runtime policy
  -> pinned snapshot at orchestration start
  -> state doc stores:
     - policySnapshotFile (string snapshot pointer)
     - policySnapshotHash (string snapshot hash)
     - policyVersion (string/integer runtime policy version)
     - legacyPolicy (boolean legacy-state marker)
  -> all resume/replay uses snapshot only
```

## Definition Of Done

This plan is complete when the implementation can:

- customize step prompts without editing Python
- customize parse schemas without editing Python
- customize verifier thresholds and retry budgets without editing Python
- keep zero-config behavior identical to today
- resume from a pinned snapshot even if payload or override files later change
- reject invalid settings safely

## Out Of Scope

This plan does not try to deliver:

- arbitrary user-defined workflow graphs
- custom Python or shell expressions in config
- a general workflow interpreter
- rich nested policy blobs embedded in frontmatter
