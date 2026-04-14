# TODO

Execute in order. Do not skip ahead unless the dependency line says it is safe.

Status backfill: checked against shipped code and `npm run verify` on 2026-04-13.

Notes:
- Item 1 remains open because the original pre-edit baseline notes were not preserved in-repo.
- Item 14 remains open because the review payload still relies on the extra instruction `auto-fix all issues without prompting` instead of encoding autonomous fix behavior directly in `instructions.xml`.

## Phase 0: Baseline

1. [ ] Capture current behavior baselines.
   Files: `source/src/story_automator/commands/tmux.py`, `source/src/story_automator/commands/orchestrator_parse.py`, `source/src/story_automator/commands/orchestrator.py`, `source/src/story_automator/core/review_verify.py`
   Actions:
   - run `npm run verify`
   - capture `tmux-wrapper build-cmd` output for `create`, `auto`, `review`, `retro`
   - note current review/crash limits and review completion behavior
   Done when:
   - baseline commands are saved in working notes
   - current default behavior is explicit before edits start

2. [x] Freeze the target JSON settings shape.
   Depends on: 1
   Files: `docs/plans/json-settings/02-policy-model.md`
   Actions:
   - confirm final top-level keys
   - confirm snapshot file path
   - confirm verifier names
   Done when:
   - no open schema ambiguity remains

## Phase 1: Policy Loader And Default Policy

3. [x] Add bundled default policy JSON and data directories.
   Depends on: 2
   Files:
   - `payload/.claude/skills/bmad-story-automator/data/orchestration-policy.json`
   - `payload/.claude/skills/bmad-story-automator/data/prompts/*.md`
   - `payload/.claude/skills/bmad-story-automator/data/parse/*.json`
   Actions:
   - encode current behavior exactly
   - keep prompt wording as close to current strings as possible
   Done when:
   - payload contains complete default machine contract

4. [x] Implement `runtime_policy.py`.
   Depends on: 3
   Files:
   - `source/src/story_automator/core/runtime_policy.py`
   Actions:
   - load bundled policy
   - load optional `_bmad/bmm/story-automator.policy.json`
   - deep-merge maps, replace arrays
   - validate known keys and verifier names
   - resolve relative paths
   - write stable snapshot JSON with hash
   Done when:
   - one call can return effective policy plus snapshot metadata

5. [x] Refactor required/optional asset resolution behind policy.
   Depends on: 4
   Files:
   - `source/src/story_automator/core/workflow_paths.py`
   - `source/src/story_automator/core/runtime_policy.py`
   Actions:
   - move candidate-list resolution behind policy
   - fail closed on missing required assets
   - preserve compatibility wrappers where helpful
   Done when:
   - required assets never silently resolve to non-existent placeholders

6. [x] Add state metadata for policy snapshots.
   Depends on: 4
   Files:
   - `source/src/story_automator/commands/state.py`
   - `source/src/story_automator/core/frontmatter.py`
   Actions:
   - write `policyVersion`
   - write `policySnapshotFile`
   - write `policySnapshotHash`
   - add `legacyPolicy` handling
   Done when:
   - new state docs point at a snapshot instead of embedding policy

## Phase 2: Prompt And Parse Externalization

7. [x] Replace hard-coded tmux prompts with template rendering.
   Depends on: 4, 5, 6
   Files:
   - `source/src/story_automator/commands/tmux.py`
   Actions:
   - load step contract from effective policy
   - render prompt from template file
   - preserve current Codex/Claude boot logic
   - preserve current default prompt text behavior
   Done when:
   - `build-cmd` no longer uses the hard-coded prompt map

8. [x] Replace hard-coded parse schema switch with policy-backed contracts.
   Depends on: 4
   Files:
   - `source/src/story_automator/commands/orchestrator_parse.py`
   Actions:
   - load step parse schema JSON
   - render parser prompt from label + schema
   - validate returned JSON against required keys
   Done when:
   - parser behavior comes from data files, not `if step == ...`

9. [x] Move retry budgets into policy-backed reads.
   Depends on: 4
   Files:
   - `source/src/story_automator/commands/orchestrator.py`
   Actions:
   - source review max cycles from policy
   - source crash retry limit from policy
   - remove direct env-default dependence from active run behavior
   Done when:
   - budgets come from effective snapshot

## Phase 3: Success Verifiers

10. [x] Add verifier registry and concrete implementations.
    Depends on: 4
    Files:
    - `source/src/story_automator/core/success_verifiers.py`
    - `source/src/story_automator/core/review_verify.py`
    Actions:
    - implement `session_exit`
    - implement `create_story_artifact`
    - implement `review_completion`
    - implement `epic_complete`
    - keep backward-compatible wrapper for existing review helper
    Done when:
    - verifiers are selected by name and tested independently

11. [x] Wire `monitor-session` to policy-backed verifier dispatch.
    Depends on: 7, 10
    Files:
    - `source/src/story_automator/commands/tmux.py`
    Actions:
    - remove permanent review special case
    - use step contract `success.verifier`
    - pass verifier config and story context
    Done when:
    - completion logic is step-driven, not `workflow == "review"` driven

12. [x] Fold create story validation into `create_story_artifact`.
    Depends on: 10, 11
    Files:
    - `source/src/story_automator/commands/orchestrator.py`
    - `source/src/story_automator/core/success_verifiers.py`
    Actions:
    - remove duplicated create validation trigger logic
    - route create pass/fail through verifier
    Done when:
    - create success semantics exist in one place only

## Phase 4: Review Payload Alignment

13. [x] Add structured review contract file.
    Depends on: 3
    Files:
    - `payload/.claude/skills/bmad-story-automator-review/contract.json`
    - `payload/.claude/skills/bmad-story-automator-review/workflow.yaml`
    Actions:
    - move machine completion semantics into JSON
    - make workflow point to the contract
    Done when:
    - review machine truth is no longer hidden inside prose only

14. [ ] Align review instructions with autonomous mode.
    Depends on: 13
    Files:
    - `payload/.claude/skills/bmad-story-automator-review/instructions.xml`
    Actions:
    - remove reliance on prompt folklore for auto-fix behavior
    - make automatic fix path explicit for autonomous mode
    Done when:
    - review payload no longer contradicts runtime prompt defaults

15. [x] Update main workflow prose to reference runtime policy.
    Depends on: 3
    Files:
    - `payload/.claude/skills/bmad-story-automator/workflow.md`
    Actions:
    - reference `orchestration-policy.json`
    - describe fixed loop as default policy
    - align terms with runtime policy language
    Done when:
    - payload docs and runtime use the same contract vocabulary

## Phase 5: Testing

16. [x] Add Python unit tests for policy and verifiers.
    Depends on: 4, 8, 10
    Files:
    - `source/tests/test_runtime_policy.py`
    - `source/tests/test_success_verifiers.py`
    - `source/tests/test_orchestrator_parse.py`
    - `source/tests/test_state_policy_metadata.py`
    Actions:
    - use stdlib `unittest`
    - cover merge, validation, snapshot, verifier behavior, parser loading
    Done when:
    - policy-specific behavior has direct automated coverage

17. [x] Update smoke tests for installed policy assets and defaults.
    Depends on: 7, 8, 11, 13, 14, 15
    Files:
    - `scripts/smoke-test.sh`
    Actions:
    - assert policy JSON exists after install
    - assert prompt templates and parse files exist
    - assert default prompt output still matches baseline expectations
    Done when:
    - installer/integration behavior remains covered end to end

18. [x] Update local verify flow.
    Depends on: 16, 17
    Files:
    - `package.json`
    - `docs/development.md`
    Actions:
    - add Python unit test command
    - fold it into `npm run verify`
    - document new verify sequence
    Done when:
    - one verify command covers unit + smoke + package dry run

## Phase 6: Compatibility And Cleanup

19. [x] Implement legacy resume behavior and strict new-state validation.
    Depends on: 6, 10, 11
    Files:
    - `source/src/story_automator/commands/state.py`
    - `source/src/story_automator/core/runtime_policy.py`
    - any resume path using state metadata
    Actions:
    - old state without snapshot -> legacy defaults + `legacyPolicy: true`
    - new state with missing snapshot -> validation failure
    Done when:
    - resume is deterministic and explicit in both modes

20. [x] Preserve env compatibility for one release cycle.
    Depends on: 9
    Files:
    - `source/src/story_automator/core/runtime_policy.py`
    - docs as needed
    Actions:
    - read legacy env vars once at orchestration start
    - bake effective values into snapshot
    - document deprecation path
    Done when:
    - old env knobs still work without mutating resumed runs

21. [x] Remove or shrink obsolete hard-coded helpers.
    Depends on: 7, 8, 9, 10, 11
    Files:
    - `source/src/story_automator/commands/tmux.py`
    - `source/src/story_automator/commands/orchestrator_parse.py`
    - `source/src/story_automator/commands/orchestrator.py`
    Actions:
    - delete dead prompt-schema branches
    - remove stale helpers after tests pass
    Done when:
    - no duplicate machine contract remains in code

## Final Gate

22. [ ] Run full verification and review default behavior drift.
    Depends on: 1 through 21
    Actions:
    - run Python unit tests
    - run `npm run verify`
    - compare prompt baselines against phase 0 captures
    - review installed payload tree manually once
    Done when:
    - zero-config behavior matches baseline
    - customization surfaces work
    - resume uses snapshots only
