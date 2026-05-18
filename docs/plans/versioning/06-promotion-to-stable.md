# Phase 06 - Promotion To Stable

<!-- markdownlint-disable MD013 -->

## Clean Context Start

Before doing this phase, read [README.md](./README.md), [handoff-log.md](./handoff-log.md), [TODO.md](./TODO.md), and the Phase 05 verification handoff. Do not promote if the handoff lists unresolved release blockers.

## Goal

Promote Codex runtime support from preview to normal stable installs.

## Preconditions

- Preview tag has been tested by operators.
- No release-blocking issues remain.
- PR #3 or the integration branch is merged into `main`.
- `main` contains `skills/module.yaml`.
- `main` metadata points to `bmad-code-org/bmad-automator`.

## Stable Version

Recommended first stable:

```text
1.15.0
```

Update versions:

- `package.json`
- `.claude-plugin/plugin.json`
- `skills/bmad-story-automator/pyproject.toml`
- `.claude-plugin/marketplace.json` plugin `version`
- `skills/module.yaml` only if Phase 02 kept Automator's current convention that `module_version` tracks release tags
- `skills/bmad-story-automator/src/story_automator/__init__.py` only if Phase 02 established that it tracks the installed helper release
- changelog entry

## Release Commands

```bash
npm run verify
git tag -a v1.15.0 -m "v1.15.0"
git push automator main
git push automator v1.15.0
```

Optional npm stable publish:

```bash
npm publish
```

## Post-Promotion Install Paths

Stable:

```bash
npx bmad-method install --modules baut --all-stable --tools codex --yes
```

Official next:

```bash
npx bmad-method install --modules baut --tools codex --yes
npx bmad-method install --modules baut --next baut --tools codex --yes
```

Pinned stable:

```bash
npx bmad-method install --modules baut --pin baut=v1.15.0 --tools codex --yes
```

## Exit Criteria

- Stable install resolves to `v1.15.0`.
- `--modules baut` and `--next baut` resolve to `main` HEAD with the same or newer Codex runtime support while registry `default_channel: next` remains in place.
- Preview docs are replaced with stable docs.

## Handoff Requirements

Append a Phase 06 entry to [handoff-log.md](./handoff-log.md) with:

- stable branch and tag SHAs
- version bump files changed
- release commands run and result
- npm publish status
- post-promotion install verification result
- remaining support or rollback risks for Phase 07
