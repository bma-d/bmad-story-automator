# Why JSON Settings

## Problem

The current system already behaves like it has a policy layer, but that policy is scattered.

Examples:

- step prompts are assembled inline in `source/src/story_automator/commands/tmux.py`
- parse contracts are hard-coded in `source/src/story_automator/commands/orchestrator_parse.py`
- retry limits and escalation budgets are hard-coded in `source/src/story_automator/commands/orchestrator.py`
- review completion logic is fixed in `source/src/story_automator/core/review_verify.py`
- step asset discovery is encoded in `source/src/story_automator/core/workflow_paths.py`
- human-facing loop rules live in payload docs under `payload/.claude/skills/bmad-story-automator/`

That creates four problems:

1. the real contract is hard to see in one place
2. docs and runtime can drift
3. customization requires source edits
4. resume determinism is fragile if behavior depends on live files

## Goals

The implementation should make these customizable:

- per-step prompt templates
- parse contracts and output schema expectations
- success verifier thresholds and source order
- bounded loop settings such as retry counts and review max cycles
- step asset resolution rules

It should also preserve:

- zero-config current behavior
- install layout
- current runtime engine model
- deterministic resume/replay

## Non-Goals

This work should not become:

- a generic DSL
- a plugin system for arbitrary verifier code
- a graph workflow engine
- a rewrite of tmux/session execution

## Why JSON

This repo should choose JSON settings instead of YAML for the machine contract.

Reasons:

1. No new dependency.
   The repo currently has no YAML parser dependency in the Python package. JSON keeps the runtime dependency-free.

2. Existing code already speaks JSON.
   `state.py`, `orchestrator_parse.py`, agent config helpers, and multiple command surfaces already pass JSON around.

3. Snapshot determinism is simpler.
   Stable sorting, hashing, and byte-for-byte snapshots are easier with JSON.

4. Parse schemas are already a JSON-shaped concept.
   Moving step parse contracts into `.json` files is a natural fit.

5. Settings are machine-facing.
   Long prose belongs in markdown/XML files anyway, so readability pressure on the main settings file is lower than it would be for a human-authored workflow language.

## Why Not YAML First

YAML would be nicer for comments and long-form hand editing, but it adds cost now:

- new parsing dependency or hand-rolled parser
- more edge cases around scalars and lists
- more work to normalize and hash deterministically

If operator ergonomics later require comments, the safer follow-up is JSONC or a small translator layer, not immediate YAML adoption.

## Existing Repo Fit

The repo already has a natural home for settings files:

- `payload/.claude/skills/bmad-story-automator/data/`

That directory already holds:

- rules docs
- retry docs
- complexity JSON
- prompt-related docs
- monitoring docs

Adding JSON policy and parse files there follows the existing layout instead of inventing a new storage pattern.

## Architectural Principle

Use:

```text
declarative contracts
+ imperative engine
```

Declarative:

- prompts
- parse schema
- verifier parameters
- asset path candidates
- loop budgets

Imperative:

- tmux spawning
- session capture
- crash/stuck detection
- file reads/writes
- snapshot creation
- verifier execution

## Success Standard

This refactor is worth doing only if it makes behavior easier to change without making runtime behavior harder to trust.

Practical success means:

- changing prompt text means editing a payload file or override, not Python
- changing review completion thresholds means editing JSON settings, not Python
- changing retry budgets means editing JSON settings, not env-only knobs
- resume always uses the same effective contract as the run start

