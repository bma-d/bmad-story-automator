# Story Automator

![Story Automator](./ref.png)

Portable bundle with source for BMAD `story-automator`, packaged from the Python port and renamed so the install surface drops the `-py` suffix.

This repository is the Python port of [`bma-d/bmad-story-automator-go`](https://github.com/bma-d/bmad-story-automator-go). It has been tested less than the Go implementation, so treat the Go repository as the more battle-tested reference.

Run this after planning is complete.

## Quickstart

Install with `npx`:

```bash
cd /absolute/path/to/your-bmad-project
npx bmad-story-automator
```

Then run:

```bash
claude --dangerously-skip-permissions
# inside claude
/bmad-bmm-story-automator
```

Or run from anywhere and pass the target project explicitly:

```bash
npx bmad-story-automator /absolute/path/to/your-bmad-project
```

## What This Is

This repo packages the installable workflow payload plus the Python helper source for `story-automator` so another BMAD project can install it cleanly and still inspect the runtime.

This bundle supports:
- Claude
- Codex-monitored child sessions inside the orchestrator
- current BMAD layout: `_bmad/bmm/4-implementation/...`
- legacy BMAD layout: `_bmad/bmm/workflows/4-implementation/...`

This bundle does not support:
- Windows
- non-BMAD projects
- agent CLIs outside the bundled Claude command surface

## What Gets Installed

The installer detects the target BMAD layout and installs into the matching path:
- current BMAD:
  - `_bmad/bmm/4-implementation/bmad-story-automator`
  - `_bmad/bmm/4-implementation/bmad-story-automator-review`
- legacy BMAD:
  - `_bmad/bmm/workflows/4-implementation/story-automator`
  - `_bmad/bmm/workflows/4-implementation/story-automator-review`

If both layouts exist, the installer prefers the current `bmad-*` layout.

It also:
- installs the Python runtime as `bin/story-automator`, `src/story_automator`, and `pyproject.toml`
- installs the Claude command `bmad-bmm-story-automator`
- removes the older `bmad-bmm-story-automator-py` command if present
- creates missing Claude dependency commands for `create-story`, `dev-story`, `story-automator-review`, `retrospective` without overwriting existing project-specific wrappers
- creates automate wrappers only if a compatible automate workflow already exists in the target project:
  - `bmad-tea-testarch-automate` for legacy TEA `testarch-automate`
  - `bmad-bmm-qa-generate-e2e-tests` plus the legacy compatibility alias when the fresh BMAD `qa-generate-e2e-tests` workflow is present

## Requirements

Host requirements:
- `python3` 3.11+
- `tmux`
- Claude Code
- macOS or Linux

If the automate workflow is missing, install still succeeds. In that case run `story-automator` with `Skip Automate = true`. Compatible automate sources: legacy TEA `testarch-automate` or fresh BMAD `qa-generate-e2e-tests`.

## Package Layout

Payload copied into target projects:
- `payload/_bmad/bmm/workflows/4-implementation/story-automator/`
- `payload/_bmad/bmm/workflows/4-implementation/story-automator-review/`

Package scripts:
- `install.sh`
- `bin/bmad-story-automator`
- `package.json`

Bundled runtime source:
- `source/pyproject.toml`
- `source/bin/story-automator`
- `source/src/story_automator/`

## Verify Install

Manual checks inside a target project:

```bash
cd /path/to/project
story_dir=$(find _bmad/bmm -maxdepth 3 -type d \( -name 'bmad-story-automator' -o -name 'story-automator' \) | head -n 1)
review_dir=$(find _bmad/bmm -maxdepth 3 -type d \( -name 'bmad-story-automator-review' -o -name 'story-automator-review' \) | head -n 1)
"$story_dir/bin/story-automator" --help
grep -n "name: story-automator" "$story_dir/workflow.md"
grep -n "0 CRITICAL issues remain after fixes" "$review_dir/instructions.xml"
```

Expected:
- command help output from `story-automator`
- workflow name `story-automator`
- a matching `CRITICAL issues remain` line in `story-automator-review/instructions.xml`

## Publish To npm

Publish steps:
- `npm adduser`
- `npm publish`
