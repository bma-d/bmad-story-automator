# Installation And Layout

This doc explains what `npx bmad-story-automator` installs, what it requires, and how it handles migration from older installs.

## BMAD Method Channels

Automator is also available through the BMAD Method official module code `baut`. Because the official registry currently sets `baut` to `default_channel: next`, channel selection must be explicit:

- `--modules baut --all-stable` resolves to the latest pure-semver stable tag.
- `--pin baut=v1.15.0` resolves to the first Codex-capable stable tag.
- `--pin baut=v1.14.2` resolves to the pre-Codex stable tag and is the safest rollback path for Claude Code users.
- `--custom-source https://github.com/bmad-code-org/bmad-automator@next/codex-runtime-support` resolves to the branch preview for unpublished follow-up fixes.
- Unqualified `--modules baut` and `--next baut` resolve to `main` HEAD while `default_channel: next` remains. After Codex support lands on `main`, those commands include Codex support but are not reproducible stable installs.

Run these commands from the target BMAD project root, or add `--directory /absolute/path/to/your-bmad-project`.

Stable install:

```bash
npx bmad-method install --modules baut --all-stable --tools claude-code --yes
```

Stable pin:

```bash
npx bmad-method install --modules baut --pin baut=v1.15.0 --tools codex --yes
```

Pre-Codex rollback:

```bash
npx bmad-method install --modules baut --pin baut=v1.14.2 --tools claude-code --yes
```

Branch preview install for unpublished follow-up fixes:

```bash
npx bmad-method install --custom-source https://github.com/bmad-code-org/bmad-automator@next/codex-runtime-support --tools codex --yes
```

Rollback from preview or branch testing to the pre-Codex stable tag:

```bash
npx bmad-method install --modules baut --pin baut=v1.14.2 --tools claude-code --yes
```

or:

```bash
npx bmad-method install --modules baut --all-stable --tools claude-code --yes
```

If custom-source discovery asks which plugin to install after reading the branch, choose `bmad-automator`. For custom-source branch testing, confirm the custom-source cache HEAD and installed runtime files; installer metadata can still report the registry `next` ref when the custom source uses official module code `baut`.

The BMAD Method commands above install through `bmad-method` for the requested `--tools` target. The sections below describe the standalone `npx bmad-story-automator` installer and its layout behavior.

## Installer Flow

```mermaid
flowchart TD
    A["Run install.sh <project>"] --> B["Verify target is a BMAD project"]
    B --> C["Verify root skills exist in this repo"]
    C --> D["Verify required sibling skills exist in target project"]
    D --> E["Resolve optional QA skill if present"]
    E --> F["Backup current installs and legacy story-automator paths"]
    F --> G["Copy skills into .claude/skills"]
    G --> H["Remove obsolete legacy command shims"]
    H --> I["Print installed paths and verified sibling entrypoints"]
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

- `.claude/skills/bmad-create-story/SKILL.md`
- `.claude/skills/bmad-dev-story/SKILL.md`
- `.claude/skills/bmad-retrospective/SKILL.md`

Only the `SKILL.md` entrypoint is required for sibling BMAD skills. Extra files such as `workflow.md`, `workflow.yaml`, checklists, and templates are resolved when present, but install must not depend on those internal layouts.

Optional:

- `.claude/skills/bmad-qa-generate-e2e-tests/SKILL.md`

If the optional QA skill is missing:

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

## Repo Layout

Repo layout:

- `skills/` for directly copyable skill folders
- `skills/bmad-story-automator/` for the main skill and bundled Python runtime
- `skills/bmad-story-automator-review/` for the bundled review skill
- `.claude-plugin/plugin.json` for Claude Code plugin loading
- `install.sh` for installation logic
- `bin/bmad-story-automator` for npm entrypoint
- `scripts/` for repo-level smoke verification

No installer-only payload tree exists. The installer copies the same skill folders that can be manually copied into `.claude/skills/`.

## Operator Notes

- install target must be a BMAD project with `_bmad/`
- required sibling skill `SKILL.md` files must already exist
- the review workflow is installed alongside the main orchestrator because review gating is part of completion semantics

## Read Next

- [How It Works](./how-it-works.md)
- [CLI Reference](./cli-reference.md)
- [Development](./development.md)
