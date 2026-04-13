# Installation And Layout

This doc explains what `npx bmad-story-automator` installs, what it requires, and how it handles migration from older installs.

## Installer Flow

```mermaid
flowchart TD
    A["Run install.sh <project>"] --> B["Verify target is a BMAD project"]
    B --> C["Verify payload and Python runtime exist in this repo"]
    C --> D["Verify required sibling skills exist in target project"]
    D --> E["Resolve optional QA skill if present"]
    E --> F["Backup current installs and legacy story-automator paths"]
    F --> G["Copy payload into .claude/skills"]
    G --> H["Copy Python runtime into installed skill"]
    H --> I["Remove obsolete legacy command shims"]
    I --> J["Print installed paths and verified sibling entrypoints"]
```

## Target Paths

The installer writes into the target project:

- `.claude/skills/bmad-story-automator`
- `.claude/skills/bmad-story-automator-review`

Unlike the older workflow-root layout, this Python port installs into the pure skill tree.

## Installed Tree

```mermaid
flowchart TD
    A[".claude/skills/"] --> B["bmad-story-automator/"]
    A --> C["bmad-story-automator-review/"]
    B --> D["SKILL.md"]
    B --> E["workflow.md"]
    B --> F["steps-c/ steps-v/ steps-e/"]
    B --> G["data/ templates/"]
    B --> H["scripts/story-automator"]
    B --> I["src/story_automator/"]
    B --> J["pyproject.toml README.md LICENSE"]
    C --> K["SKILL.md workflow.yaml instructions.xml checklist.md"]
```

## Required Inputs

The target project must already contain these BMAD skills:

- `.claude/skills/bmad-create-story`
- `.claude/skills/bmad-dev-story`
- `.claude/skills/bmad-retrospective`

Optional:

- `.claude/skills/bmad-qa-generate-e2e-tests`

If the optional QA skill is missing or incomplete:

- install still succeeds
- a warning is printed
- the operator should run with `Skip Automate = true`

## Migration And Backups

Before copying new content, the installer backs up:

- existing `.claude/skills/bmad-story-automator`
- existing `.claude/skills/bmad-story-automator-review`
- legacy installs under `_bmad/bmm/4-implementation/...`
- legacy installs under `_bmad/bmm/workflows/4-implementation/...`

The goal is migration safety, not in-place overwrite.

## Command Shim Cleanup

The installer removes obsolete shims only when they still target legacy workflow-root installs.

Important nuance:

- this repo does not generate new Claude command wrappers
- it only cleans up stale legacy wrappers
- the intended entrypoint is the installed skill itself

## Runtime Entry

The installed helper entrypoint is:

```text
.claude/skills/bmad-story-automator/scripts/story-automator
```

That wrapper:

- sets `PYTHONPATH` to the bundled `src`
- runs `python3 -m story_automator`

## Package Layout In This Repo

Repo layout:

- `payload/` for installed skill content
- `source/` for bundled Python runtime
- `install.sh` for installation logic
- `bin/bmad-story-automator` for npm entrypoint
- `scripts/` for repo-level smoke verification

## Operator Notes

- install target must be a BMAD project with `_bmad/`
- required sibling skills must already exist
- the review workflow is installed alongside the main orchestrator because review gating is part of completion semantics

## Read Next

- [How It Works](./how-it-works.md)
- [CLI Reference](./cli-reference.md)
- [Development](./development.md)
