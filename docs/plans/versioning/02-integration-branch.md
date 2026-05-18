# Phase 02 - Integration Branch

<!-- markdownlint-disable MD013 -->

## Clean Context Start

Before doing this phase, read [README.md](./README.md), [handoff-log.md](./handoff-log.md), [TODO.md](./TODO.md), and the Phase 01 handoff entry. Treat the handoff as current implementation context.

## Goal

Create an automator-owned branch that combines current `main` with PR #3 and preserves module installability.

## Branch Shape

Recommended branch:

```bash
next/codex-runtime-support
```

Base it on current `automator/main`, then bring PR #3 commits onto it.

## Implementation Steps

1. Create the branch from current main.

```bash
git fetch automator main '+refs/pull/3/head:refs/remotes/automator/pr/3' --no-tags
git switch -c next/codex-runtime-support automator/main
```

1. Cherry-pick or merge PR #3.

Preferred when clean:

```bash
git cherry-pick cf96221 b3a4c9e 05dad8c
```

Fallback when conflicts are easier to resolve as a merge:

```bash
git merge --no-ff automator/pr/3
```

1. Preserve current module files from `main`.

Required files:

- `skills/module.yaml`
- `skills/module-help.csv`
- `.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`

1. Fix metadata regressions.

Expected official repo identity:

- package/plugin name: `bmad-automator` where marketplace-facing
- repository: `https://github.com/bmad-code-org/bmad-automator`
- owner email: `support@bmadcode.com`

Keep npm package identity as:

- package name: `bmad-story-automator`
- binary: `bmad-story-automator`

1. Make `.claude-plugin/marketplace.json` custom-source compatible.

The BMad custom-source resolver needs plugin-level `skills` entries. Use the BMB-style plugin shape while keeping automator identity:

```json
{
  "name": "bmad-automator",
  "source": "./",
  "description": "BMAD story automation skills for create/dev/QA/review/retro orchestration.",
  "version": "1.15.0-next.1",
  "author": {
    "name": "bma-d",
    "email": "support@bmadcode.com"
  },
  "skills": [
    "./skills/bmad-story-automator",
    "./skills/bmad-story-automator-review"
  ]
}
```

Keep any existing homepage, repository, license, keywords, category, and tags fields that remain accurate.

1. Bump release-facing preview versions consistently.

Current preview after the Phase 05.5 supersession:

```text
1.15.0-next.1
```

The original `1.15.0-next.0` local preview is historical only and must not be published.

Update:

- `package.json`
- `.claude-plugin/plugin.json`
- `skills/bmad-story-automator/pyproject.toml`
- `skills/bmad-story-automator/src/story_automator/__init__.py` only if it intentionally tracks the installed helper release; current `main` leaves this at `1.12.0`, so verify before changing it.
- `.claude-plugin/marketplace.json` plugin `version`
- any workflow/runtime version strings that intentionally track package version

Do not blindly bump `skills/module.yaml` `module_version`. BMB precedent has package/plugin release version at `1.8.0` while `skills/module.yaml` keeps `module_version: 1.0.0`; treat `module_version` as release-facing only if Automator deliberately uses it that way. Current Automator `main` does set `module_version: "1.14.2"`, so Phase 02 must decide and record whether to keep that local convention or align with BMB semantics.

## Exit Criteria

- Branch contains PR #3 runtime changes.
- Branch contains `skills/module.yaml`.
- Branch metadata points to `bmad-code-org/bmad-automator`.
- `.claude-plugin/marketplace.json` includes `source: "./"`, preview `version`, and `skills` entries for custom-source discovery.
- `git diff automator/main...HEAD` shows Codex runtime changes plus version/metadata changes only.

## Handoff Requirements

Append a Phase 02 entry to [handoff-log.md](./handoff-log.md) with:

- integration branch name and HEAD SHA
- exact PR commits applied or merge commit used
- conflicts encountered and how each was resolved
- files changed outside the PR diff
- final version string used
- decision on whether `skills/module.yaml` `module_version` was bumped or intentionally left unchanged
- verification run locally and result
- next command Phase 03 should run
