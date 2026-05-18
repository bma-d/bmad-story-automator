# Versioning TODO

<!-- markdownlint-disable MD013 -->

## Phase 01 - Baseline

- [x] Read `README.md`, assigned phase doc, and `handoff-log.md`.
- [x] Fetch current `automator/main`.
- [x] Fetch PR #3 head.
- [x] Confirm `skills/module.yaml` exists on `main`.
- [x] Confirm PR #3 diff still applies cleanly.
- [x] Record current latest stable tag.
- [x] Append Phase 01 notes to `handoff-log.md`.

## Phase 02 - Integration Branch

- [x] Read `README.md`, assigned phase doc, and `handoff-log.md`.
- [x] Create `next/codex-runtime-support` from current `main`.
- [x] Apply PR #3 commits.
- [x] Resolve conflicts without dropping `skills/module.yaml`.
- [x] Restore official `bmad-code-org/bmad-automator` metadata.
- [x] Add marketplace `skills` entries for custom-source discovery.
- [x] Bump preview versions to `1.15.0-next.0`.
- [x] Record whether `skills/module.yaml` `module_version` tracks release tags for Automator.
- [x] Append Phase 02 notes to `handoff-log.md`.

## Phase 03 - Preview Tag

- [x] Read `README.md`, assigned phase doc, and `handoff-log.md`.
- [x] Run local verification.
- [x] Push integration branch.
- [x] Create annotated `v1.15.0-next.0` tag locally.
- [x] Push preview tag.
- [x] Optional: publish npm package with `--tag next` skipped.
- [x] Append local Phase 03 prep notes to `handoff-log.md`.
- [x] Append remote push output to `handoff-log.md`.

## Phase 04 - Consumer Docs

- [x] Read `README.md`, assigned phase doc, and `handoff-log.md`.
- [x] Add stable install command.
- [x] Add preview pin install command.
- [x] Add branch custom-source install command.
- [x] Add rollback command.
- [x] Warn that `--modules baut` and `--next baut` track `main` while registry `default_channel: next` remains.
- [x] Append Phase 04 notes to `handoff-log.md`.

## Phase 05 - Verification

- [x] Read `README.md`, assigned phase doc, and `handoff-log.md`.
- [x] Verify stable pin install in temp project.
- [x] Verify preview pin install in temp project.
- [x] Verify custom-source branch install in temp project.
- [x] Verify all-stable does not select prerelease.
- [x] Capture command output for any failure.
- [x] Append Phase 05 notes to `handoff-log.md`.

## Phase 05.5 - Preview Supersession

- [x] Read `README.md`, `05-verification-matrix.md`, `TODO.md`, and `handoff-log.md`.
- [x] Bump local integration preview metadata and docs from `1.15.0-next.0` to `1.15.0-next.1`.
- [x] Run product verification.
- [x] Commit the integration branch preview supersession.
- [x] Create local annotated `v1.15.0-next.1` tag.
- [x] Append Phase 05.5 notes to `handoff-log.md`.

## Phase 06 - Stable Promotion

- [x] Read `README.md`, assigned phase doc, and `handoff-log.md`.
- [x] Merge PR/integration into `main`.
- [x] Bump stable version to `1.15.0`.
- [x] Run `npm run verify`.
- [x] Tag `v1.15.0`.
- [ ] Optional: `npm publish`.
- [x] Update docs from preview to stable.
- [x] Append Phase 06 notes to `handoff-log.md`.

## Phase 07 - Rollback

- [x] Read `README.md`, assigned phase doc, and `handoff-log.md`.
- [ ] If preview breaks, cut `v1.15.0-next.2`.
- [ ] If stable breaks, cut patch tag after revert/fix.
- [x] Keep install support notes updated.
- [x] Append Phase 07 notes to `handoff-log.md`.
