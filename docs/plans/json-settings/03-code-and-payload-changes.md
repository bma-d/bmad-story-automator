# Code And Payload Changes

## Implementation Principle

Keep files under control. Avoid one giant refactor file.

Recommended new source modules:

- `source/src/story_automator/core/runtime_policy.py`
- `source/src/story_automator/core/success_verifiers.py`

Keep prompt rendering small enough to live in existing command modules unless it grows past a reasonable size.

## Source Changes

### New: `source/src/story_automator/core/runtime_policy.py`

Responsibilities:

- load bundled default policy JSON
- load optional project override JSON
- merge deterministically
- validate structure
- resolve step asset paths
- write effective snapshot JSON
- load policy from snapshot during resume
- expose helpers such as `load_effective_policy()` and `step_contract()`

Notes:

- this module is the only policy merge point
- it should normalize relative paths against project root or installed skill root
- it should reject unknown verifier names and invalid step references early

### New: `source/src/story_automator/core/success_verifiers.py`

Responsibilities:

- named verifier registry
- `session_exit`
- `create_story_artifact`
- `review_completion`
- `epic_complete`

Notes:

- keep `verify_code_review_completion()` as a backward-compatible wrapper
- verifier config comes from policy, verifier execution stays in Python

### `source/src/story_automator/commands/tmux.py`

Replace hard-coded prompt assembly with policy-driven prompt rendering.

Changes:

- stop building prompts from inline string map
- load step contract from snapshot or effective policy
- render step prompt from `prompt.templateFile`
- use policy-driven step label instead of `_automate_workflow_label()`
- shrink `_build_retro_prompt()` into data-backed template usage
- make `monitor-session` call the configured verifier, not a permanent review special case

Keep in Python:

- Codex/Claude CLI invocation
- `CODEX_HOME` setup
- `tmux` session lifecycle
- heartbeat/status logic

### `source/src/story_automator/commands/orchestrator_parse.py`

Replace the `if step == ...` schema tree.

Changes:

- read `parse.schemaFile` and optional parser prompt template
- inject `label` and schema into parser call
- validate returned JSON against required keys from schema
- preserve current command output shape

### `source/src/story_automator/core/review_verify.py`

Reduce it to a compatibility wrapper.

Changes:

- keep current public function
- delegate to `success_verifiers.review_completion`
- allow contract-driven status values and source order

### `source/src/story_automator/commands/orchestrator.py`

Move hard-coded budgets into policy.

Changes:

- `review-loop` limit comes from `workflow.repeat.review.maxCycles`
- `session-crash` limit comes from `workflow.crash.maxRetries`
- story creation validation becomes part of `create_story_artifact`
- escalation actions stay in Python

### `source/src/story_automator/commands/state.py`

Add policy metadata at state document creation.

Changes:

- write `policyVersion`
- write `policySnapshotFile`
- write `policySnapshotHash`
- optionally write `legacyPolicy`
- surface these in state summary and validation

Do not:

- embed full policy JSON in frontmatter

### `source/src/story_automator/core/frontmatter.py`

Keep changes minimal.

Possible work:

- teach state readers to return new scalar metadata
- no nested policy parser

### `source/src/story_automator/core/workflow_paths.py`

Refactor into policy-backed asset resolution.

Changes:

- resolve explicit path or candidate list from policy
- distinguish required vs optional assets
- fail fast for missing required assets
- preserve compatibility wrappers where useful

Important fix:

- required assets must no longer silently return the first candidate string when nothing exists

## Payload Changes

### New: `payload/.claude/skills/bmad-story-automator/data/orchestration-policy.json`

This is the default machine contract for the installed skill.

### New: `payload/.claude/skills/bmad-story-automator/data/prompts/*.md`

Add prompt templates for:

- create
- dev
- auto
- review
- retro

### New: `payload/.claude/skills/bmad-story-automator/data/parse/*.json`

Add step parse contracts for:

- create
- dev
- auto
- review
- retro

### `payload/.claude/skills/bmad-story-automator/workflow.md`

Keep this human-facing and orchestration-facing.

Changes:

- reference the runtime policy file explicitly
- describe the current sequence as the default policy, not the only possible future shape
- align wording with policy terms: prompt contract, parse contract, success verifier, snapshot

### `payload/.claude/skills/bmad-story-automator-review/workflow.yaml`

Keep this file human-facing only.

The machine contract should stay in step policy:

- `steps.review.success.contractFile = ".claude/skills/bmad-story-automator-review/contract.json"`

### New: `payload/.claude/skills/bmad-story-automator-review/contract.json`

Store structured review completion semantics:

- blocking severity
- allowed done values
- allowed in-progress values
- source order
- sprint sync expectations

### `payload/.claude/skills/bmad-story-automator-review/instructions.xml`

Keep the adversarial review behavior, but align it with autonomous mode.

Changes:

- stop relying on prompt folklore to override user-choice branches
- make automatic fix behavior driven by explicit interaction mode
- keep review prose separate from machine completion rules

## Installer And Packaging Impact

### `install.sh`

Likely no logic change needed because the installer already copies the whole payload tree.

Needed checks:

- verify new payload files exist after install
- update smoke tests to assert new data files are present

### `package.json`

Likely no change needed because `payload/` and `source/` are already in `files`.

## Verification Surface Changes

### `scripts/smoke-test.sh`

Must update smoke coverage for:

- installed policy JSON presence
- installed prompt template presence
- installed parse JSON presence
- prompt-building behavior still matching default policy
- policy-backed build-cmd output for create/auto/review/retro

### Suggested new tests under `source/tests/`

- `test_runtime_policy.py`
- `test_success_verifiers.py`
- `test_orchestrator_parse.py`
- `test_state_policy_metadata.py`

Use stdlib `unittest` unless a dependency-free alternative is clearly better.

## Recommended Module Boundaries

To keep files under roughly 500 LOC:

- `runtime_policy.py`: load, merge, validate, snapshot, resolve
- `success_verifiers.py`: registry and concrete verifiers
- `tmux.py`: session behavior plus prompt rendering entrypoint only
- `orchestrator_parse.py`: parser command plus schema validation

If `runtime_policy.py` grows too large, split only after phase 1 lands.
