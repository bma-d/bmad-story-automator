# Phase 01 - Baseline And Constraints

<!-- markdownlint-disable MD013 -->

## Clean Context Start

Before doing this phase, read [README.md](./README.md), [handoff-log.md](./handoff-log.md), and [TODO.md](./TODO.md). If earlier entries changed assumptions, follow the handoff log and update this phase doc.

## Goal

Lock down what is already true before building the repo-local versioning flow.

## Current State

- Automator is listed as official module code `baut`.
- Official marketplace registry currently has `baut` set to `default_channel: next`, so unqualified `--modules baut` installs `main` HEAD.
- Current stable tag is `v1.14.2`.
- Current `main` contains `skills/module.yaml`.
- PR #3 adds Codex runtime support.
- PR #3 branched before the current `main` module-manifest commits.
- PR #3 currently carries older metadata in `.claude-plugin/*`.

## Constraints

- Do not change BMAD-METHOD installer code.
- Do not change the official marketplace registry.
- Do not depend on `--next baut` for the PR preview unless the PR is merged to `main`.
- Do not retag an existing stable version.
- Keep stable users on pure semver tags by documenting `--all-stable`, `--channel stable`, or explicit `--pin` usage.

## Required Local Facts

Before implementation, confirm:

```bash
git fetch automator main '+refs/pull/3/head:refs/remotes/automator/pr/3' --no-tags
git show automator/main:skills/module.yaml
git diff --name-status automator/main...automator/pr/3
gh pr view https://github.com/bmad-code-org/bmad-automator/pull/3 --comments --json state,mergeable,headRefName,baseRefName,files
gh api repos/bmad-code-org/bmad-plugins-marketplace/contents/registry/official.yaml --jq .content | base64 -d | sed -n '/name: bmad-automator/,/trust_tier/p'
```

## Decisions

Use two preview paths:

1. A prerelease tag, installed through official module pinning:

```bash
npx bmad-method install --modules baut --pin baut=v1.15.0-next.1 --tools codex --yes
```

1. A branch preview, installed as custom source:

```bash
npx bmad-method install --custom-source https://github.com/bmad-code-org/bmad-automator@next/codex-runtime-support --tools codex --yes
```

The prerelease tag is the primary next channel because it is reproducible and uses the existing official `baut` registry entry. The original local-only `v1.15.0-next.0` preview was superseded before publication; use `v1.15.0-next.1` for the current preview.

## Handoff Requirements

Append a Phase 01 entry to [handoff-log.md](./handoff-log.md) with:

- current `origin/main`, `automator/main`, and PR #3 SHAs
- latest stable tag found
- whether PR #3 still lacks or includes `skills/module.yaml`
- exact command output for any failed fetch or PR lookup
- recommendation for Phase 02 branch base and merge strategy
