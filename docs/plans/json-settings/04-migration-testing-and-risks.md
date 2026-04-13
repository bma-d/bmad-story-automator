# Migration, Testing, And Risks

## Compatibility Plan

### Default behavior

Bundled default JSON settings must preserve today's behavior exactly.

That includes:

- prompt wording
- asset path candidate order
- parser labels and required fields
- review completion fallback to story file status
- review max cycles
- crash retry count
- retrospective forcing Claude

### Old state docs

If a state document has no policy metadata:

- resume in legacy mode
- load bundled defaults
- mark the run summary with `legacyPolicy: true`

This is the only safe fallback for pre-refactor state docs.

### New state docs

If a state document has:

- `policySnapshotFile`
- `policySnapshotHash`

then resume must:

- load the snapshot
- verify the hash
- fail validation if snapshot missing or mismatched

Do not silently fall back to live defaults for a new-format state doc.

### Legacy env vars

For one release cycle, continue to honor:

- `MAX_REVIEW_CYCLES`
- `MAX_CRASH_RETRIES`

But resolve them once at orchestration start and bake the effective values into the snapshot.

That preserves old operator habits without breaking deterministic resume.

## Test Strategy

### Principle

Add focused Python tests for new policy behavior, then keep the smoke suite as the installer/integration safety net.

### Recommended Test Harness

Use stdlib `unittest` first.

Reasons:

- no new dependency
- enough for merge/validation/path-resolution tests
- enough for verifier tests with temporary directories

### New Python Test Coverage

### `test_runtime_policy.py`

Cases:

- bundled default loads
- project override deep-merges maps
- arrays replace cleanly
- invalid step name rejected
- invalid verifier name rejected
- required asset missing fails
- snapshot hash stable

### `test_success_verifiers.py`

Cases:

- `create_story_artifact` returns fail for 0 matches
- `create_story_artifact` returns pass for 1 match
- `create_story_artifact` returns fail for runaway multiple matches
- `review_completion` passes on sprint status done
- `review_completion` falls back to story file `Status: done`
- `review_completion` fails on in-progress/unknown
- `epic_complete` respects sprint status values

### `test_orchestrator_parse.py`

Cases:

- parse schema loads from step contract
- invalid schema file rejected
- invalid child JSON rejected
- output shape remains compatible

### `test_state_policy_metadata.py`

Cases:

- state doc writes policy metadata
- summary surfaces policy metadata
- legacy state without policy metadata remains valid

### Smoke Test Updates

Extend `scripts/smoke-test.sh` to verify:

- installed `data/orchestration-policy.json`
- installed prompt template files
- installed parse JSON files
- `tmux-wrapper build-cmd` still emits expected default text
- review prompt still defaults to automatic fixes in autonomous mode

### Verify Command Updates

Recommended future command shape:

```bash
python3 -m unittest discover -s source/tests
npm run test:smoke
npm run pack:dry-run
```

Then fold that into `npm run verify`.

## Risk Register

| Risk | Why it matters | Mitigation |
|------|----------------|------------|
| Prompt drift changes agent behavior | Equivalent wording is not actually equivalent for model behavior | Golden prompt tests against current defaults |
| Snapshot ignored on resume | Live payload changes mutate in-flight run behavior | Resume path must require snapshot for new-format states |
| Review still asks the user in autonomous mode | Current review workflow prose still has a menu branch | Add explicit interaction-mode contract and payload alignment |
| Required asset silent fallback | Missing workflow may look valid until runtime | Resolver must fail closed for required assets |
| Custom statuses cause false positives | Review completion may pass with wrong values | Contract validation + verifier tests |
| Optional auto skill incomplete | Step contract may claim assets that do not exist | Required/optional separation in resolver |
| Policy file grows too complex | Moderate refactor turns into new engine | Keep bounded primitives only |

## Rollout Strategy

### Phase 1

Land:

- policy loader
- bundled default policy
- project override support
- pinned snapshot
- prompt templates
- parse contracts
- policy-backed retry budgets

Keep:

- fixed engine shape
- existing review special logic if needed for the first slice

### Phase 2

Land:

- verifier registry
- policy-backed `monitor-session` verifier dispatch
- `contract.json` for review
- review payload alignment for autonomous mode

### Phase 3

Land:

- policy-backed bounded loop config
- optional-step and trigger wiring
- cleanup of old hard-coded helpers

## Phase Exit Criteria

Phase 1 exit:

- zero-config build-cmd output matches baseline
- snapshot created and stored in state
- parse schemas load from JSON files

Phase 2 exit:

- review completion no longer special-cased in `monitor-session`
- review contract is structured and tested

Phase 3 exit:

- retry/repeat/trigger policy comes from snapshot
- docs and runtime use the same terms
