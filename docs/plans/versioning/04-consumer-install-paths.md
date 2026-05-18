# Phase 04 - Consumer Install Paths

<!-- markdownlint-disable MD013 -->

## Clean Context Start

Before doing this phase, read [README.md](./README.md), [handoff-log.md](./handoff-log.md), [TODO.md](./TODO.md), and the Phase 03 handoff entry. Use the actual preview tag and branch from the handoff, not placeholders.

## Goal

Document exact install commands for stable users, preview testers, and rollback.

## Stable Install

Do not use unqualified `--modules baut` for stable while the official registry sets `baut` to `default_channel: next`.

Use the stable resolver explicitly:

```bash
npx bmad-method install --modules baut --all-stable --tools claude-code --yes
```

To pin stable explicitly:

```bash
npx bmad-method install --modules baut --pin baut=v1.14.2 --tools claude-code --yes
```

## Next Preview Install

Primary preview path after Phase 03 creates the prerelease tag:

```bash
npx bmad-method install --modules baut --pin baut=v1.15.0-next.1 --tools codex --yes
```

Use this for Discord testers after the remote tag is published because it stays inside the official `baut` module entry and is reproducible. Do not use the stale local-only `v1.15.0-next.0` tag.

## Branch Preview Install

Use only after Phase 02 creates the branch, when testing an unpublished branch commit:

```bash
npx bmad-method install --custom-source https://github.com/bmad-code-org/bmad-automator@next/codex-runtime-support --tools codex --yes
```

If the installer needs a specific plugin selection after discovery, choose `bmad-automator` from the custom source.

This requires the branch manifest to include plugin `skills` entries:

```json
"skills": [
  "./skills/bmad-story-automator",
  "./skills/bmad-story-automator-review"
]
```

## Official Next After Merge

The current official registry default for `baut` is already `next`, which means `main` HEAD. Before merge, it installs current `main`, not PR #3.

After Codex support lands on `main`, these become meaningful Codex-preview commands:

```bash
npx bmad-method install --modules baut --tools codex --yes
npx bmad-method install --modules baut --next baut --tools codex --yes
```

Before merge, do not use either command as the PR preview path.

## Rollback

Reinstall latest stable:

```bash
npx bmad-method install --modules baut --pin baut=v1.14.2 --tools claude-code --yes
```

Or force the stable channel:

```bash
npx bmad-method install --modules baut --all-stable --tools claude-code --yes
```

## Documentation Updates

Add a short `README.md` section after the preview tag exists:

- Stable install command
- Next preview command
- Rollback command
- Warning that `--modules baut` and `--next baut` mean `main` HEAD, not PR #3, until merge

## Handoff Requirements

Append a Phase 04 entry to [handoff-log.md](./handoff-log.md) with:

- docs updated and file paths
- final stable, preview, branch, and rollback commands
- any commands intentionally not documented and why
- known user-facing caveats
- exact docs review or lint result if run
- verification focus for Phase 05
