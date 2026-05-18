# Phase 05 - Verification Matrix

<!-- markdownlint-disable MD013 -->

## Clean Context Start

Before doing this phase, read [README.md](./README.md), [handoff-log.md](./handoff-log.md), [TODO.md](./TODO.md), and Phase 03-04 handoff entries. Use actual tags, branches, and documented commands from the handoff log.

## Goal

Verify that stable and next installs work end to end without official repo changes.

## Local Package Verification

Run from the integration branch:

```bash
npm run verify
```

Expected:

- Python tests pass.
- `npm pack --dry-run` includes expected skill files.
- smoke test passes.

## Module Shape Verification

Check required module files:

```bash
test -f skills/module.yaml
test -f skills/module-help.csv
test -f skills/bmad-story-automator/SKILL.md
test -f skills/bmad-story-automator-review/SKILL.md
```

Check metadata and custom-source discovery fields:

```bash
node -e 'console.log(require("./package.json").version)'
node - <<'NODE'
const m = require("./.claude-plugin/marketplace.json");
const p = m.plugins.find((plugin) => plugin.name === "bmad-automator");
const expectedSkills = ["./skills/bmad-story-automator", "./skills/bmad-story-automator-review"];
if (!p) throw new Error("missing bmad-automator plugin");
if (p.source !== "./") throw new Error(`unexpected source ${p.source}`);
if (p.version !== "1.15.0-next.1") throw new Error(`unexpected plugin version ${p.version}`);
if (JSON.stringify(p.skills) !== JSON.stringify(expectedSkills)) throw new Error(`unexpected skills ${JSON.stringify(p.skills)}`);
console.log(JSON.stringify({ name: p.name, source: p.source, version: p.version, skills: p.skills }, null, 2));
NODE
python3 - <<'PY'
from pathlib import Path
print(Path("skills/module.yaml").read_text())
PY
```

Expected version:

```text
1.15.0-next.1
```

## Installer Verification

Use a disposable BMAD project. Do not run against a real project first.

### Registry Default Next

```bash
npx bmad-method install --modules baut --tools codex --yes --directory /tmp/baut-default-smoke
```

Expected:

- installs `baut`
- records or reports `main @ <sha>`
- installed skills match current `main`, not PR #3 unless PR #3 has already been merged

### Stable Pin

```bash
npx bmad-method install --modules baut --pin baut=v1.14.2 --tools claude-code --yes --directory /tmp/baut-stable-smoke
```

Expected:

- installs `baut`
- records `channel: pinned`
- records `version: v1.14.2`
- installed skills do not include Codex runtime changes

### Next Preview Pin

Run only after Phase 05.5 creates and a remote-enabled agent pushes `v1.15.0-next.1`.

```bash
npx bmad-method install --modules baut --pin baut=v1.15.0-next.1 --tools codex --yes --directory /tmp/baut-next-smoke
```

Expected:

- installs `baut`
- records `channel: pinned`
- records `version: v1.15.0-next.1`
- installed skills include Codex runtime support
- `skills/bmad-story-automator/src/story_automator/core/runtime_layout.py` exists
- `skills/bmad-story-automator/src/story_automator/core/stop_hooks.py` exists

### Custom Source Branch

Run only after Phase 02 creates and pushes `next/codex-runtime-support`.

```bash
npx bmad-method install --custom-source https://github.com/bmad-code-org/bmad-automator@next/codex-runtime-support --tools codex --yes --directory /tmp/baut-branch-smoke
```

Expected:

- custom source resolves
- module discovery finds `.claude-plugin/marketplace.json`
- plugin resolver finds both skills from the manifest `skills` array
- installed module code is `baut`
- installed skills match the branch commit
- custom-source cache HEAD matches the requested branch commit
- installed runtime files exist; do not require `_bmad/_config/manifest.yaml` to record the branch ref when the custom source uses the official module code `baut`, because BMAD-METHOD 6.6.0 writes official external-module metadata for that code even when custom-source content is copied

## Regression Checks

Confirm stable resolver does not pick prerelease tags:

```bash
npx bmad-method install --modules baut --all-stable --tools claude-code --yes --directory /tmp/baut-all-stable-smoke
```

Expected:

- selected version is latest pure semver tag, not `v1.15.0-next.1`

## Exit Criteria

- All smoke paths pass.
- Install docs match verified commands.
- Any failed installer command is captured exactly with stderr and root cause.

## Handoff Requirements

Append a Phase 05 entry to [handoff-log.md](./handoff-log.md) with:

- each verification command and pass/fail result
- temp directories used
- installed manifest snippets or key fields checked
- exact failure output and root cause for failures
- any docs or command corrections made during verification
- release readiness recommendation for Phase 06
