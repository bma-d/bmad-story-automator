# Phase 03 - Prerelease Tag Channel

<!-- markdownlint-disable MD013 -->

## Clean Context Start

Before doing this phase, read [README.md](./README.md), [handoff-log.md](./handoff-log.md), [TODO.md](./TODO.md), and the Phase 02 handoff entry. Use the integration branch and version recorded there.

## Goal

Create a reproducible next preview without changing the official registry.

## Why Tags

BMAD-METHOD `stable` ignores prerelease tags because it only selects pure semver releases. `--pin baut=<tag>` can still install a prerelease tag from the official `baut` repo.

This gives:

- stable installs unchanged
- exact preview ref
- no registry dependency
- rollback by installing the previous stable tag

## Tag Policy

Use semver prerelease tags:

```text
v1.15.0-next.0
v1.15.0-next.1
v1.15.0-next.2
```

Rules:

- Never move a pushed preview tag.
- For fixes, cut the next prerelease number.
- Promote to `v1.15.0` only after stable approval.

## Create Preview Tag

After Phase 05.5 superseded the local-only `v1.15.0-next.0` tag, the current preview publication target is `v1.15.0-next.1`:

```bash
git push automator next/codex-runtime-support
git push automator v1.15.0-next.1
```

## Optional npm Next Dist Tag

If the `npx bmad-story-automator` path should also preview Codex support:

```bash
npm publish --tag next
```

This is optional. The BMad module installer path works from git tags without npm changes.

## Exit Criteria

- Tag exists on `bmad-code-org/bmad-automator`.
- Tag points to the integration branch commit.
- Stable tag selection still resolves to latest pure semver, not `*-next.*`.

## Handoff Requirements

Append a Phase 03 entry to [handoff-log.md](./handoff-log.md) with:

- pushed branch name and SHA
- created tag and tag target SHA
- whether npm `next` publish was skipped or completed
- exact push output or failure text
- stable tag resolver sanity result
- install command Phase 04 should document as canonical
