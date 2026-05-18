# Automator Versioning Plan

<!-- markdownlint-disable MD013 -->

## Purpose

Create a repo-local versioning path for BMad Automator that supports:

- `stable`: released semver tags already consumable by the BMad installer.
- `next`: Codex runtime support from PR #3 before it is promoted to stable.
- `pinned`: explicit prerelease tags for reproducible installs.

## Constraint

Assume no changes can be made to BMAD-METHOD or the official BMad marketplace registry.

That means:

- no installer behavior changes
- no official `default_channel` change
- no registry `next_ref` field
- no official marketplace entry edits

The plan must work using only changes in `bmad-code-org/bmad-automator`, tags, branches, npm metadata, `.claude-plugin/marketplace.json`, and user-facing docs.

## Key Finding

BMAD-METHOD already resolves external modules this way:

- `stable`: highest pure semver git tag
- `next`: repository default branch HEAD
- `pinned`: explicit tag

The official marketplace registry currently sets `baut` to `default_channel: next`. Therefore an unqualified `--modules baut` install resolves to `main` HEAD, not the latest stable tag. Use `--all-stable`, `--channel stable`, or `--pin baut=<stable-tag>` when a stable install is required.

Because official `next` resolves to the default branch, it cannot point at PR #3 unless PR #3 is merged to `main`. For pre-merge testing, use a repo-local integration branch plus a prerelease tag, then install with `--pin baut=<tag>` or `--custom-source <repo>@<branch-or-tag>`.

## Recommended Channel Model

| Channel | Ref Source | Install Path | Registry Change Needed |
| --- | --- | --- | --- |
| Stable | `vX.Y.Z` pure semver tag | `--modules baut --all-stable` or `--pin baut=vX.Y.Z` | No |
| Next preview | `vX.Y.Z-next.N` prerelease tag, after Phase 03 creates it | `--pin baut=vX.Y.Z-next.N` | No |
| Branch preview | `next/codex-runtime-support` branch plus marketplace `skills` entries, after Phase 02 creates it | `--custom-source https://github.com/bmad-code-org/bmad-automator@next/codex-runtime-support` | No |
| Registry default next | `main` HEAD | `--modules baut` or `--next baut` | Already configured; useful for PR #3 only after merge |

## Phase Files

1. [Phase 01 - Baseline And Constraints](./01-baseline-and-constraints.md)
2. [Phase 02 - Integration Branch](./02-integration-branch.md)
3. [Phase 03 - Prerelease Tag Channel](./03-prerelease-tag-channel.md)
4. [Phase 04 - Consumer Install Paths](./04-consumer-install-paths.md)
5. [Phase 05 - Verification Matrix](./05-verification-matrix.md)
6. [Phase 06 - Promotion To Stable](./06-promotion-to-stable.md)
7. [Phase 07 - Rollback And Support](./07-rollback-and-support.md)
8. [Handoff Log](./handoff-log.md)
9. [TODO](./TODO.md)

## Clean Context Agent Protocol

Each phase may be implemented by a different clean-context agent. Every agent must treat this folder as the continuity source.

Before starting a phase:

1. Read this README.
2. Read the assigned phase file.
3. Read [handoff-log.md](./handoff-log.md), especially entries from all earlier phases.
4. Check [TODO.md](./TODO.md) for current status.

During the phase:

- Update the phase doc if reality differs from the plan.
- Preserve exact commands, refs, SHAs, tag names, errors, and decisions.
- Do not rely on thread memory for information the next agent needs.

Before ending the phase:

- Append a dated entry to [handoff-log.md](./handoff-log.md).
- Mark completed items in [TODO.md](./TODO.md).
- Include blockers, open questions, changed assumptions, and next recommended command.

The next phase agent must reference the handoff log as input, not just the static phase plan.
