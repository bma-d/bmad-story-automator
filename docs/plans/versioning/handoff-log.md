# Versioning Handoff Log

<!-- markdownlint-disable MD013 -->

## Purpose

This file carries implementation context between clean-context agents. Each phase agent must read all earlier entries before starting and append a new entry before ending.

Do not rely on conversation history for phase continuity. Put the facts here.

## Entry Template

````md
## Phase NN - YYYY-MM-DD - agent/session

### Summary

- What changed or was verified.

### Commands Run

```bash
exact command
```

### Results

- Pass/fail.
- Important SHAs, tags, paths, versions.

### Decisions And Assumptions

- Decision made and why.
- Assumptions the next phase should preserve or re-check.

### Blockers Or Risks

- Blocker, owner, next action.
- Or `None`.

### Next Phase Notes

- Read these files.
- Run this command next.
- Watch for this failure mode.
````

## Phase Entries

## Phase 01 - 2026-05-17 - Codex quick-dev

### Summary

- Completed the Phase 01 baseline refresh for the repo-local Automator versioning path.
- Refetched `automator/main` and PR #3 head.
- Confirmed `automator/main` contains `skills/module.yaml`.
- Confirmed PR #3 still lacks `skills/module.yaml`.
- Confirmed PR #3 still applies cleanly to current `automator/main` with `git merge-tree --write-tree`.
- Reconfirmed official registry `baut` has `default_channel: next`.

### Commands Run

```bash
git fetch automator main '+refs/pull/3/head:refs/remotes/automator/pr/3' --no-tags
git rev-parse HEAD origin/main automator/main automator/pr/3
git show automator/main:skills/module.yaml
git diff --name-status automator/main...automator/pr/3
git tag -l 'v[0-9]*.[0-9]*.[0-9]*' --sort=-v:refname | rg '^v[0-9]+\.[0-9]+\.[0-9]+$' | head -1 || true
git ls-remote --tags --refs automator 'v*' | awk '{print $2}' | sed 's#refs/tags/##' | rg '^v[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail -1
gh pr view https://github.com/bmad-code-org/bmad-automator/pull/3 --comments --json state,mergeable,headRefName,baseRefName,files,commits,headRepositoryOwner,headRepository,updatedAt
gh api repos/bmad-code-org/bmad-plugins-marketplace/contents/registry/official.yaml --jq .content | base64 -d | sed -n '/name: bmad-automator/,/trust_tier/p'
git show automator/pr/3:skills/module.yaml
git merge-tree --write-tree automator/main automator/pr/3
```

### Results

- Current local `HEAD`: `deaf297f3a420ca3787c00dcb1a70888940f3b07`.
- Current `origin/main`: `8074e088e443c6bfceefcf25e8a2597e1dd1204a`.
- Current `automator/main`: `956198ca52bb3342b73567f76f5981950286f8d8`.
- Current PR #3 head: `05dad8c85d8f7e80110a92c2905c144219fe473e`.
- PR #3 remains `OPEN`, `MERGEABLE`, base `main`, head `dicky/codex-runtime-support`, updated `2026-05-14T04:13:29Z`.
- PR #3 commits remain `cf96221deff2ca87bd2f9ab427dbbea3890f1d55`, `b3a4c9e85b8e4a26cb9e22ed7cc79867155bde92`, and `05dad8c85d8f7e80110a92c2905c144219fe473e`.
- Latest pure semver stable tag on `automator`: `v1.14.2`.
- `automator/main:skills/module.yaml` exists with `module_version: "1.14.2"`.
- `automator/pr/3:skills/module.yaml` is absent: `fatal: path 'skills/module.yaml' does not exist in 'automator/pr/3'`.
- `git merge-tree --write-tree automator/main automator/pr/3` exited `0` and produced tree `5491e8857a5a92f60d2020082f39ddbe44340e4f`.
- Official registry entry still has `default_channel: next`.
- No failed fetch, PR lookup, registry lookup, or clean-apply command output to capture; the expected PR #3 manifest absence is captured above.

### Decisions And Assumptions

- Phase 02 should still base the integration branch on freshly fetched `automator/main` at `956198ca52bb3342b73567f76f5981950286f8d8`.
- Phase 02 can apply PR #3 from `automator/pr/3` because the current merge-tree check is clean.
- Phase 02 must preserve or restore `skills/module.yaml` from `automator/main` because PR #3 does not contain it.
- Preserve the prior plan assumption that `--modules baut` and `--next baut` resolve to `main` while official registry `default_channel: next` remains.

### Blockers Or Risks

- `automator/main`, PR #3 mergeability, and registry state are live remote facts; re-fetch at the start of Phase 02.
- `module_version` policy remains a Phase 02 decision: Automator currently tracks release version in `skills/module.yaml`, while BMB precedent may not.

### Next Phase Notes

- Read `02-integration-branch.md`, this entry, and the Plan Audit entry before Phase 02.
- Recommended first command: `git fetch automator main '+refs/pull/3/head:refs/remotes/automator/pr/3' --no-tags`.
- Build `next/codex-runtime-support` from current `automator/main`, apply PR #3, preserve `skills/module.yaml`, restore official `bmad-code-org/bmad-automator` metadata, add marketplace `skills` entries, and bump preview versions to `1.15.0-next.0`.

## Plan Audit - 2026-05-16 - Codex review loop

### Summary

- Verified the plan against BMAD-METHOD installer behavior, BMB precedent, current Automator `main`, and PR #3.
- Corrected the plan docs where research did not match current reality.
- No implementation branch, preview tag, or release was created.

### Commands Run

```bash
git fetch automator main '+refs/pull/3/head:refs/remotes/automator/pr/3' --no-tags
gh pr view https://github.com/bmad-code-org/bmad-automator/pull/3 --comments --json state,mergeable,headRefName,baseRefName,files,commits,headRepositoryOwner,headRepository,updatedAt
gh api repos/bmad-code-org/bmad-plugins-marketplace/contents/registry/official.yaml --jq .content | base64 -d
npm pack bmad-method@6.6.0 --json
npx --yes bmad-method@6.6.0 install --modules baut --tools codex --yes --directory /tmp/baut-default-smoke
git ls-remote --heads --tags automator next/codex-runtime-support v1.15.0-next.0 main v1.14.2
```

### Results

- Current `automator/main`: `956198ca52bb3342b73567f76f5981950286f8d8`.
- Current `origin/main` and local `HEAD`: `8074e088e443c6bfceefcf25e8a2597e1dd1204a`.
- PR #3 head: `05dad8c85d8f7e80110a92c2905c144219fe473e`; state `OPEN`; mergeable `MERGEABLE`.
- PR #3 commits are still `cf96221`, `b3a4c9e`, `05dad8c`.
- Latest stable tag on `bmad-code-org/bmad-automator`: `v1.14.2` at `593f338532ea730b5c1a2dd86681e87b5b4f04dd`.
- `next/codex-runtime-support` and `v1.15.0-next.0` do not exist yet on `automator`.
- Official registry currently sets `baut` to `default_channel: next`; unqualified `--modules baut` installed `baut` as `channel: next`, `version: main`, `sha: 956198ca52bb3342b73567f76f5981950286f8d8`.
- BMB `.claude-plugin/marketplace.json` uses plugin-level `source: "./"`, `version`, and `skills` entries; this validates the plan's custom-source shape.
- BMB package/plugin version is `1.8.0`, but BMB `skills/module.yaml` keeps `module_version: 1.0.0`; Automator currently uses `module_version: "1.14.2"`, so Phase 02 must explicitly decide whether to preserve Automator's local release-version convention.

### Decisions And Assumptions

- Stable docs must not present unqualified `--modules baut` as stable while registry `default_channel: next` remains.
- Stable installs should use `--all-stable`, `--channel stable`, or explicit `--pin baut=<stable-tag>`.
- PR preview remains a prerelease tag or custom-source branch, not `--modules baut`/`--next baut`, until PR #3 lands on `main`.
- Phase 05 must verify `.claude-plugin/marketplace.json` plugin `source`, `version`, and exact `skills`, not just the presence of a `skills` array.

### Blockers Or Risks

- Preview refs are placeholders until Phase 02/03 creates and pushes `next/codex-runtime-support` and `v1.15.0-next.0`.
- `module_version` semantics are ambiguous across BMB and Automator; Phase 02 owner must decide and document.

### Next Phase Notes

- Start Phase 01 with the current registry-default fact above.
- If implementing Phase 02, base on `automator/main` `956198c` or refetch first.
- After applying PR #3, inspect auto-merged `README.md`, `skills/bmad-story-automator/src/story_automator/commands/orchestrator.py`, and `skills/bmad-story-automator/src/story_automator/commands/state.py`.

## Phase 02 - 2026-05-17 - Codex quick-dev

### Summary

- Completed local `next/codex-runtime-support` integration branch in `<integration-worktree>`.
- Based branch on fetched `automator/main` `956198ca52bb3342b73567f76f5981950286f8d8`.
- Integrated PR #3 runtime support as branch-local commits, then fixed clean-context review findings.
- Preserved `skills/module.yaml` and `skills/module-help.csv`.
- Kept marketplace-facing identity as `bmad-automator` and `bmad-code-org/bmad-automator`.
- Added custom-source marketplace `source: "./"` and both Automator skill entries.
- Bumped preview-facing versions to `1.15.0-next.0`.

### Commands Run

```bash
git fetch automator main '+refs/pull/3/head:refs/remotes/automator/pr/3' --no-tags
git status --short --branch
git rev-parse HEAD automator/main automator/pr/3
git --no-pager diff --name-status automator/main...HEAD
git --no-pager diff --check automator/main...HEAD
PYTHONPATH=skills/bmad-story-automator/src python3 -m unittest tests.test_runtime_layout tests.test_state_policy_metadata tests.test_stop_hooks
npm run verify
git ls-remote --heads --tags automator next/codex-runtime-support v1.15.0-next.0 main v1.14.2
git add skills/bmad-story-automator/src/story_automator/__init__.py skills/bmad-story-automator/src/story_automator/commands/orchestrator_epic_agents.py skills/bmad-story-automator/src/story_automator/commands/state.py skills/bmad-story-automator/src/story_automator/core/agent_config.py skills/bmad-story-automator/steps-c/step-01-init.md tests/test_runtime_layout.py tests/test_state_policy_metadata.py tests/test_stop_hooks.py
git commit -m "fix: harden codex preview runtime defaults"
```

### Results

- Integration branch: `next/codex-runtime-support`.
- Final local branch HEAD: `f0c2a0a48b1a6f3065b732d003715eabcaaaf659`.
- Base: `automator/main` `956198ca52bb3342b73567f76f5981950286f8d8`.
- PR #3 head at start: `05dad8c85d8f7e80110a92c2905c144219fe473e`.
- Branch commits over `automator/main`:
  - `a05f635e8027d9af0a8a5d48ca11a318ab138e69` - `feat: add Codex runtime support`
  - `386421ea43b3edf34b1e6aa10885a9eb691e1e51` - `fix: separate runtime provider from child agent selection`
  - `76447bae58fe09d6a2ef3bad6b3afed596f5bc81` - `fix: tighten docs and runtime layout portability`
  - `7244bedb2f8d2eb45966b2b6dd2f40bf009b4786` - `chore: prepare codex runtime preview branch`
  - `4bba55bdfe1d17a810608c0e2fb0d498451c02cf` - `chore: keep versioning plan docs off preview branch`
  - `f0c2a0a48b1a6f3065b732d003715eabcaaaf659` - `fix: harden codex preview runtime defaults`
- `git cherry -v` showed PR commits `b3a4c9e85b8e4a26cb9e22ed7cc79867155bde92` and `05dad8c85d8f7e80110a92c2905c144219fe473e` patch-equivalent on the branch. PR commit `cf96221deff2ca87bd2f9ab427dbbea3890f1d55` was integrated as adapted branch commit `a05f635e8027d9af0a8a5d48ca11a318ab138e69` on top of newer `automator/main`.
- No merge conflicts were encountered in this session.
- `git diff --check automator/main...HEAD` passed.
- Targeted tests passed: `72 tests in 2.153s`.
- `npm run verify` passed: `203` Python tests, `npm pack --dry-run`, and smoke test `smoke ok`.
- Smoke test emitted expected optional-skill warnings for missing `bmad-qa-generate-e2e-tests`.
- Remote refs after local work: `automator/main` and tag `v1.14.2` exist; remote `next/codex-runtime-support` and `v1.15.0-next.0` still do not exist because Phase 02 did not push.

### Decisions And Assumptions

- `skills/module.yaml` `module_version` was bumped to `1.15.0-next.0`. Automator currently tracks module manifest version with release tags (`1.14.2` on current `main`), so the preview branch keeps that local convention rather than adopting BMB's static `1.0.0` precedent.
- `.claude-plugin/marketplace.json` intentionally uses plugin-level `source: "./"` for custom-source branch discovery. This is a repo-local marketplace shape, not an official registry edit.
- Python helper `pyproject.toml` uses PEP 440 preview equivalent `1.15.0.dev0`; `story_automator.__version__` was updated to the same Python runtime version.
- Missing `agentConfig` now resolves fallback to disabled (`false`) to match the branch documentation; explicit fallback values remain honored.
- Codex stop-hook initialization now halts on `verificationState: "pending_trust"` even when hook files are already present and unchanged.
- Product integration branch intentionally excludes `docs/plans/versioning/**`; those clean-context planning docs remain on `bma-d/versioning`.

### Blockers Or Risks

- Remote branch and preview tag are not pushed/created yet. Phase 03 owns that.
- `next/codex-runtime-support` is local only in `<integration-worktree>`.
- Official registry `default_channel: next` still points unqualified `--modules baut` at `main`, not this local preview branch.

### Next Phase Notes

- Read `03-prerelease-tag-channel.md`, this entry, and `TODO.md`.
- Recommended first command:

```bash
cd <integration-worktree> && git status --short --branch && git rev-parse HEAD automator/main
```

- Phase 03 should push `next/codex-runtime-support`, create annotated tag `v1.15.0-next.0` at `f0c2a0a48b1a6f3065b732d003715eabcaaaf659`, push the tag, and optionally publish npm with `--tag next`.

## Phase 03 - 2026-05-17 - Codex quick-dev

### Summary

- Completed local Phase 03 preview preparation in `<integration-worktree>`.
- Verified `next/codex-runtime-support` is clean and still at Phase 02 HEAD `f0c2a0a48b1a6f3065b732d003715eabcaaaf659`.
- Ran local verification successfully.
- Created local annotated tag `v1.15.0-next.0` targeting the integration HEAD.
- Did not push the branch or tag because quick-dev Step 3 forbids remote operations.
- Skipped optional `npm publish --tag next`; the BMad module preview path will work from the remote git tag after `git push automator v1.15.0-next.0`.

### Commands Run

```bash
git status --short --branch
git rev-parse HEAD automator/main
git tag -l 'v1.15.0-next.0' --format='%(refname:short) %(objectname) %(taggerdate:iso8601)'
npm run verify
git tag -a v1.15.0-next.0 -m "v1.15.0-next.0"
git show-ref --tags v1.15.0-next.0
git rev-parse v1.15.0-next.0^{}
git tag -l 'v[0-9]*.[0-9]*.[0-9]*' --sort=-v:refname | rg '^v[0-9]+\.[0-9]+\.[0-9]+$' | head -1 || true
git log --oneline --decorate -1
```

### Results

- Integration worktree status: `## next/codex-runtime-support...automator/main [ahead 6]`.
- Branch HEAD: `f0c2a0a48b1a6f3065b732d003715eabcaaaf659`.
- Base `automator/main`: `956198ca52bb3342b73567f76f5981950286f8d8`.
- `v1.15.0-next.0` did not exist locally before this phase.
- Local tag object: `5acda521145da911a1f97e10d685125bf7959d6c`.
- Local tag target: `f0c2a0a48b1a6f3065b732d003715eabcaaaf659`.
- Latest pure semver tag remains `v1.14.2`; prerelease `v1.15.0-next.0` does not affect stable selection.
- `npm run verify` passed: `203` Python tests, `npm pack --dry-run`, and smoke test `smoke ok`.
- Smoke test emitted expected optional-skill warnings for missing `bmad-qa-generate-e2e-tests`.
- Remote push commands intentionally not run:

```bash
git push automator next/codex-runtime-support
git push automator v1.15.0-next.0
```

### Decisions And Assumptions

- Treat local tag creation as completed preparation, not remote publication.
- Keep Phase 03 remote publication tasks open until a remote-enabled agent pushes both the branch and the tag.
- Do not publish npm `next` for this phase; document the git tag/module installer path first.
- Canonical Phase 04 preview install command after remote tag push: `--pin baut=v1.15.0-next.0`.
- Branch preview command for Phase 04 docs after remote branch push: `--custom-source https://github.com/bmad-code-org/bmad-automator@next/codex-runtime-support`.

### Blockers Or Risks

- Remote `next/codex-runtime-support` and remote `v1.15.0-next.0` still need publication.
- Do not move `v1.15.0-next.0` after it is pushed; fixes must use `v1.15.0-next.1` or later.
- Official registry `default_channel: next` still makes unqualified `--modules baut` resolve to `main`, not this preview.

### Next Phase Notes

- Remote-enabled publication command sequence:

```bash
cd <integration-worktree>
git status --short --branch
git push automator next/codex-runtime-support
git push automator v1.15.0-next.0
```

- After pushing, append the exact push output here and mark the remaining Phase 03 TODO push and push-output items complete before starting Phase 04.

## Phase 04 - 2026-05-17 - Codex quick-dev

### Summary

- Updated consumer-facing install docs on the local integration worktree in `<integration-worktree>`.
- Committed product docs as `7603220ef1b39671977accfd2ea14b72c8ab52a3` (`docs: document automator install channels`) on `next/codex-runtime-support`.
- Documented stable, pinned preview, branch preview, and rollback install paths.
- Preserved the warning that official `baut` currently has `default_channel: next`, so unqualified `--modules baut` and `--next baut` resolve to `main` HEAD.
- Kept Phase 03 remote publication tasks open; preview commands are documented with the requirement that the remote tag or branch must exist first.

### Commands Run

```bash
cd <integration-worktree> && git status --short --branch
cd <integration-worktree> && git diff --check
cd <plan-worktree> && git diff --check
cd <integration-worktree> && npm exec -- markdownlint --version
cd <integration-worktree> && npx --yes bmad-method@6.6.0 install --help
tmp=$(mktemp -d); cd "$tmp" && npm pack bmad-method@6.6.0 --json >/dev/null && tar -xzf bmad-method-6.6.0.tgz && sed -n '1,130p' package/tools/installer/modules/custom-module-manager.js && sed -n '130,260p' package/tools/installer/modules/custom-module-manager.js
```

### Results

- Product docs updated:
  - `<integration-worktree>/README.md`
  - `<integration-worktree>/docs/installation-and-layout.md`
- Product docs commit: `7603220ef1b39671977accfd2ea14b72c8ab52a3`.
- `<integration-worktree>` status after product docs commit: `## next/codex-runtime-support...automator/main [ahead 7]`.
- `git diff --check` passed in `<integration-worktree>`.
- `git diff --check` passed in `<plan-worktree>`.
- `npm exec -- markdownlint --version` failed because no local markdownlint executable was available: `npm error could not determine executable to run`.
- `npx --yes bmad-method@6.6.0 install --help` confirmed `--directory <path>` is available and defaults to the current directory.
- `bmad-method@6.6.0` custom-source parser was inspected from the npm package; it extracts an optional version suffix from the last `@`, permits slash characters in refs, and passes the ref to `git clone --branch`, so `@next/codex-runtime-support` is syntactically supported. Full install behavior still belongs to Phase 05 verification after the remote branch exists.
- Stable channel-forced command:

```bash
npx bmad-method install --modules baut --all-stable --tools claude-code --yes
```

- Stable pin command:

```bash
npx bmad-method install --modules baut --pin baut=v1.14.2 --tools claude-code --yes
```

- Codex preview pin command, valid after remote tag publication:

```bash
npx bmad-method install --modules baut --pin baut=v1.15.0-next.0 --tools codex --yes
```

- Branch preview command, valid after remote branch publication:

```bash
npx bmad-method install --custom-source https://github.com/bmad-code-org/bmad-automator@next/codex-runtime-support --tools codex --yes
```

- Rollback commands:

```bash
npx bmad-method install --modules baut --pin baut=v1.14.2 --tools claude-code --yes
npx bmad-method install --modules baut --all-stable --tools claude-code --yes
```

### Decisions And Assumptions

- Stable rollback remains documented with `claude-code` because `v1.14.2` is the current stable release and Codex support is still preview-only.
- The primary Codex preview path is the pinned prerelease tag because it stays inside the official `baut` module entry and is reproducible after the tag is pushed.
- The branch preview path is for unpublished branch testing only after `next/codex-runtime-support` is available remotely.
- If custom-source discovery asks for a plugin, choose `bmad-automator`.

### Blockers Or Risks

- Remote `next/codex-runtime-support` and remote `v1.15.0-next.0` are still not pushed in this plan state.
- Do not move `v1.15.0-next.0` after it is pushed; cut `v1.15.0-next.1` for fixes.
- Published docs must not imply that current unqualified `--modules baut` installs the preview before PR #3 reaches `main`.

### Next Phase Notes

- Phase 05 should verify each documented command in a temp BMAD project.
- Start with stable pin and `--all-stable` checks because they do not depend on Phase 03 remote publication.
- Verify preview pin and branch preview only after the remote tag and branch are pushed; otherwise capture the exact failure output and leave the remote-publication dependency visible.

## Phase 05 - 2026-05-17 - Codex quick-dev

### Summary

- Ran Phase 05 local package, metadata, stable/default installer, and preview-blocker verification.
- Verified `<integration-worktree>` still packages as `1.15.0-next.0`.
- Verified official registry default installs `baut` from `main @ 956198c`, not the pre-merge preview.
- Verified stable pin installs select `v1.14.2`.
- Observed all-stable selects `v1.14.2` under current remote refs; true prerelease-exclusion remains unverified because no remote prerelease tag exists.
- Confirmed remote `v1.15.0-next.0` tag and remote `next/codex-runtime-support` branch are still absent.
- Confirmed the local preview tag points at `f0c2a0a48b1a6f3065b732d003715eabcaaaf659`, while the integration branch HEAD is later docs commit `7603220ef1b39671977accfd2ea14b72c8ab52a3`.

### Commands Run

```bash
cd <integration-worktree> && npm run verify
cd <integration-worktree> && test -f skills/module.yaml && test -f skills/module-help.csv && test -f skills/bmad-story-automator/SKILL.md && test -f skills/bmad-story-automator-review/SKILL.md
cd <integration-worktree> && node -e 'console.log(require("./package.json").version)'
cd <integration-worktree> && node - <<'NODE'
const m = require("./.claude-plugin/marketplace.json");
const p = m.plugins.find((plugin) => plugin.name === "bmad-automator");
const expectedSkills = ["./skills/bmad-story-automator", "./skills/bmad-story-automator-review"];
if (!p) throw new Error("missing bmad-automator plugin");
if (p.source !== "./") throw new Error(`unexpected source ${p.source}`);
if (p.version !== "1.15.0-next.0") throw new Error(`unexpected plugin version ${p.version}`);
if (JSON.stringify(p.skills) !== JSON.stringify(expectedSkills)) throw new Error(`unexpected skills ${JSON.stringify(p.skills)}`);
console.log(JSON.stringify({ name: p.name, source: p.source, version: p.version, skills: p.skills }, null, 2));
NODE
cd <integration-worktree> && python3 - <<'PY'
from pathlib import Path
print(Path("skills/module.yaml").read_text())
PY
rm -rf /tmp/baut-home-default /tmp/baut-npm-default /tmp/baut-default-smoke-isolated && env HOME=/tmp/baut-home-default NPM_CONFIG_CACHE=/tmp/baut-npm-default npx --yes bmad-method@6.6.0 install --modules baut --tools codex --yes --directory /tmp/baut-default-smoke-isolated
rm -rf /tmp/baut-home-stable /tmp/baut-npm-stable /tmp/baut-stable-smoke-isolated && env HOME=/tmp/baut-home-stable NPM_CONFIG_CACHE=/tmp/baut-npm-stable npx --yes bmad-method@6.6.0 install --modules baut --pin baut=v1.14.2 --tools claude-code --yes --directory /tmp/baut-stable-smoke-isolated
rm -rf /tmp/baut-home-all-stable /tmp/baut-npm-all-stable /tmp/baut-all-stable-smoke-isolated && env HOME=/tmp/baut-home-all-stable NPM_CONFIG_CACHE=/tmp/baut-npm-all-stable npx --yes bmad-method@6.6.0 install --modules baut --all-stable --tools claude-code --yes --directory /tmp/baut-all-stable-smoke-isolated
rm -rf /tmp/baut-home-next /tmp/baut-npm-next /tmp/baut-next-smoke-isolated && env HOME=/tmp/baut-home-next NPM_CONFIG_CACHE=/tmp/baut-npm-next npx --yes bmad-method@6.6.0 install --modules baut --pin baut=v1.15.0-next.0 --tools codex --yes --directory /tmp/baut-next-smoke-isolated
rm -rf /tmp/baut-home-branch /tmp/baut-npm-branch /tmp/baut-branch-smoke-isolated && env HOME=/tmp/baut-home-branch NPM_CONFIG_CACHE=/tmp/baut-npm-branch npx --yes bmad-method@6.6.0 install --custom-source https://github.com/bmad-code-org/bmad-automator@next/codex-runtime-support --tools codex --yes --directory /tmp/baut-branch-smoke-isolated
sed -n '1,220p' /tmp/baut-default-smoke-isolated/_bmad/_config/manifest.yaml
sed -n '1,220p' /tmp/baut-stable-smoke-isolated/_bmad/_config/manifest.yaml
sed -n '1,220p' /tmp/baut-all-stable-smoke-isolated/_bmad/_config/manifest.yaml
if test -f /tmp/baut-default-smoke-isolated/.agents/skills/bmad-story-automator/src/story_automator/core/runtime_layout.py || test -f /tmp/baut-default-smoke-isolated/.agents/skills/bmad-story-automator/src/story_automator/core/stop_hooks.py; then echo default_runtime_files=present; else echo default_runtime_files=absent; fi
if test -f /tmp/baut-stable-smoke-isolated/.claude/skills/bmad-story-automator/src/story_automator/core/runtime_layout.py || test -f /tmp/baut-stable-smoke-isolated/.claude/skills/bmad-story-automator/src/story_automator/core/stop_hooks.py; then echo stable_runtime_files=present; else echo stable_runtime_files=absent; fi
if test -f /tmp/baut-all-stable-smoke-isolated/.claude/skills/bmad-story-automator/src/story_automator/core/runtime_layout.py || test -f /tmp/baut-all-stable-smoke-isolated/.claude/skills/bmad-story-automator/src/story_automator/core/stop_hooks.py; then echo all_stable_runtime_files=present; else echo all_stable_runtime_files=absent; fi
if [ -e /tmp/baut-next-smoke-isolated/_bmad/_config/manifest.yaml ]; then sed -n '1,220p' /tmp/baut-next-smoke-isolated/_bmad/_config/manifest.yaml; else echo 'next_isolated_manifest=absent'; fi
sed -n '1,220p' /tmp/baut-branch-smoke-isolated/_bmad/_config/manifest.yaml
find /tmp/baut-branch-smoke-isolated -maxdepth 4 -type d \( -name '*automator*' -o -name 'baut' \) | sort
git ls-remote --heads --tags automator next/codex-runtime-support v1.15.0-next.0 main v1.14.2
```

### Results

- `npm run verify` passed: `203` Python tests, `npm pack --dry-run`, and smoke test `smoke ok`.
- Module shape checks passed for `skills/module.yaml`, `skills/module-help.csv`, `skills/bmad-story-automator/SKILL.md`, and `skills/bmad-story-automator-review/SKILL.md`.
- `package.json` version output: `1.15.0-next.0`.
- Marketplace metadata check passed:

```json
{
  "name": "bmad-automator",
  "source": "./",
  "version": "1.15.0-next.0",
  "skills": [
    "./skills/bmad-story-automator",
    "./skills/bmad-story-automator-review"
  ]
}
```

- `skills/module.yaml` contains `module_version: "1.15.0-next.0"`.
- `/tmp/baut-default-smoke-isolated` passed and installed `BMad Automator (main @ 956198c)`.
- `/tmp/baut-default-smoke-isolated/_bmad/_config/manifest.yaml` records `channel: next`, `version: main`, and SHA `956198ca52bb3342b73567f76f5981950286f8d8`.
- `/tmp/baut-default-smoke-isolated` does not include `runtime_layout.py` or `stop_hooks.py`, confirming current registry default is not the pre-merge Codex runtime preview.
- `/tmp/baut-stable-smoke-isolated` passed and installed `BMad Automator (v1.14.2)`.
- `/tmp/baut-stable-smoke-isolated/_bmad/_config/manifest.yaml` records `channel: pinned`, `version: v1.14.2`, and SHA `593f338532ea730b5c1a2dd86681e87b5b4f04dd`.
- `/tmp/baut-all-stable-smoke-isolated` passed and installed `BMad Automator (v1.14.2)`.
- `/tmp/baut-all-stable-smoke-isolated/_bmad/_config/manifest.yaml` records `channel: stable`, `version: v1.14.2`, and SHA `593f338532ea730b5c1a2dd86681e87b5b4f04dd`.
- Because remote `v1.15.0-next.0` is absent, this all-stable run verifies current stable selection only; it does not prove prerelease exclusion in the presence of a remote prerelease tag.
- Stable and all-stable installs do not include `runtime_layout.py` or `stop_hooks.py`.
- Preview pin failed because the remote prerelease tag is absent:

```text
Installation failed: Tag 'v1.15.0-next.0' not found in bmad-code-org/bmad-automator.
```

- Branch custom-source command printed a clone failure for the missing remote branch but exited `0` and installed only core:

```text
Failed to resolve https://github.com/bmad-code-org/bmad-automator@next/codex-runtime-support
Failed to clone https://github.com/bmad-code-org/bmad-automator@next/codex-runtime-support: Command failed: git clone --depth 1 --branch "next/codex-runtime-support" "https://github.com/bmad-code-org/bmad-automator" "/tmp/baut-home-branch/.bmad/cache/custom-modules/github.com/bmad-code-org/bmad-automator"
fatal: Remote branch next/codex-runtime-support not found in upstream origin
```

- `/tmp/baut-next-smoke-isolated` has no `_bmad/_config/manifest.yaml`.
- `/tmp/baut-branch-smoke-isolated/_bmad/_config/manifest.yaml` contains only the built-in `core` module. There is no `baut` or custom Automator module directory under that smoke project.
- `git ls-remote` showed only `automator/main` and `v1.14.2`; remote `next/codex-runtime-support` and `v1.15.0-next.0` are absent.
- Initial parallel installer smoke attempts against the shared global cache failed. These were superseded by isolated disposable `HOME`/npm-cache runs above. Exact failure lines:

```text
fatal: shallow file has changed since we read it
ENOENT: no such file or directory, scandir '<home>/.bmad/cache/external-modules/baut/skills'
fatal: destination path '<home>/.bmad/cache/external-modules/baut' already exists and is not an empty directory.
```

### Decisions And Assumptions

- Use `bmad-method@6.6.0` for reproducible Phase 05 smoke output because prior plan entries inspected and documented installer behavior against that version.
- Leave Phase 05 preview pin, branch verification, and all-stable prerelease-exclusion TODO items unchecked because their intended remote prerelease/branch refs are not published.
- Treat the custom-source command's `0` exit on missing branch as a release-readiness risk: automation must inspect the manifest or output, not just exit code, before claiming branch preview install success.
- The local preview tag does not include the Phase 04 docs commit. If branch and tag are both pushed as currently prepared, preview pin and branch preview install different content. Do not push the stale local `v1.15.0-next.0` tag without deciding whether that divergence is intentional. If the docs commit belongs in the preview tag, bump release-facing metadata to `1.15.0-next.1`, verify, tag, and publish that new prerelease instead.

### Blockers Or Risks

- Remote preview publication is still incomplete.
- `v1.15.0-next.0` must not be moved after publication; if the docs commit should be included, bump metadata and use `v1.15.0-next.1`.
- Custom-source branch install can fail to resolve the requested branch while returning exit `0`; Phase 06/publish automation should verify installed manifest fields explicitly.
- Concurrent installer runs against the same BMAD cache path can race; use isolated `HOME`/cache roots for parallel verification or run installer smokes sequentially.
- Remote pushes remain out of scope for quick-dev Step 3 and this repo policy unless explicitly requested.

### Next Phase Notes

- This Phase 05 entry supersedes earlier handoff notes that simply said to push `v1.15.0-next.0`; resolve the tag target/version decision first.
- Before Phase 06 promotion, publish, supersede, or intentionally abandon the preview refs.
- If publishing a preview that includes current branch HEAD, first bump package/plugin/module metadata to the new prerelease version and verify locally. Then a remote-enabled agent can push branch and tag:

```bash
cd <integration-worktree>
git status --short --branch
node -e 'console.log(require("./package.json").version)'
git push automator next/codex-runtime-support
git push automator <verified-preview-tag>
```

- After publication, rerun:

```bash
npx --yes bmad-method@6.6.0 install --modules baut --pin baut=<verified-preview-tag> --tools codex --yes --directory /tmp/baut-next-smoke
npx --yes bmad-method@6.6.0 install --custom-source https://github.com/bmad-code-org/bmad-automator@next/codex-runtime-support --tools codex --yes --directory /tmp/baut-branch-smoke
```

## Phase 05.5 - 2026-05-17 - Codex quick-dev

### Summary

- Superseded the stale local-only preview tag plan with `v1.15.0-next.1`.
- Bumped integration worktree preview metadata, docs, module, Python helper, runtime version, and regression expectation from `next.0`/`dev0` to `next.1`/`dev1`.
- Committed product branch `next/codex-runtime-support` as `ef18ba5a4e1d4e1414adba7b1a1ef2f8d164b94c`.
- Created local annotated tag `v1.15.0-next.1` at `ef18ba5a4e1d4e1414adba7b1a1ef2f8d164b94c`.
- Left remote publication tasks open; no push or npm publish was run.

### Commands Run

```bash
git -C <integration-worktree> diff --check
git -C <integration-worktree> grep -n -E '1\.15\.0-next\.0|1\.15\.0\.dev0|v1\.15\.0-next\.0|next\.0' -- ':(exclude)skills/bmad-story-automator/dist/**' || true
npm run test:python
npm run verify
git add package.json .claude-plugin/plugin.json .claude-plugin/marketplace.json skills/module.yaml skills/bmad-story-automator/pyproject.toml skills/bmad-story-automator/src/story_automator/__init__.py tests/test_runtime_layout.py README.md docs/installation-and-layout.md
git commit -m "chore: prepare next preview supersession"
git tag -a v1.15.0-next.1 -m "v1.15.0-next.1"
git tag -l 'v1.15.0-next.*' --format='%(refname:short) %(objecttype) %(objectname) %(taggerdate:iso8601) -> %(subject)'
git rev-parse v1.15.0-next.0^{} v1.15.0-next.1^{}
git ls-remote --heads --tags automator next/codex-runtime-support 'v1.15.0*' main v1.14.2
```

### Results

- `git diff --check` passed.
- Tracked-source grep found no remaining `1.15.0-next.0`, `1.15.0.dev0`, `v1.15.0-next.0`, or `next.0` references outside the excluded stale local wheel under `skills/bmad-story-automator/dist/`.
- `npm run test:python` passed: `203` tests.
- `npm run verify` passed: `203` Python tests, dry pack for `bmad-story-automator@1.15.0-next.1`, and smoke test `smoke ok`.
- A first full `npm run verify` attempt exited `254` during smoke after optional-skill warnings and no final error line; standalone smoke and the rerun full verify both passed.
- Product commit: `ef18ba5a4e1d4e1414adba7b1a1ef2f8d164b94c`.
- Local tag objects and targets:
  - `v1.15.0-next.0` tag object `5acda521145da911a1f97e10d685125bf7959d6c`, target `f0c2a0a48b1a6f3065b732d003715eabcaaaf659`.
  - `v1.15.0-next.1` tag object `4736b5c39a1c7a6306212efdb484499a69ba2227`, target `ef18ba5a4e1d4e1414adba7b1a1ef2f8d164b94c`.
- Remote refs still show only `automator/main` `956198ca52bb3342b73567f76f5981950286f8d8` and `v1.14.2` `593f338532ea730b5c1a2dd86681e87b5b4f04dd`.

### Decisions And Assumptions

- `v1.15.0-next.0` is stale and local-only. Do not push it.
- `v1.15.0-next.1` is the intended preview tag because it includes the Phase 04 docs commit and matching release metadata.
- Keep Phase 06 blocked until a remote-enabled run pushes `next/codex-runtime-support` and `v1.15.0-next.1`, then verifies preview pin, branch custom-source, and all-stable prerelease exclusion.

### Blockers Or Risks

- Remote preview publication is still incomplete.
- Custom-source install may fail branch resolution while exiting `0`; verify manifests after publication.
- The stale local wheel under `skills/bmad-story-automator/dist/` still contains `1.15.0.dev0`, but `package.json` excludes that directory from npm packaging.

### Next Phase Notes

- Remote-enabled publication command sequence:

```bash
cd <integration-worktree>
git status --short --branch
git push automator next/codex-runtime-support
git push automator v1.15.0-next.1
git ls-remote --tags automator v1.15.0-next.1
```

- After publication, confirm the remote tag exists, then rerun Phase 05 preview pin, branch custom-source, and all-stable prerelease-exclusion checks against the pushed refs before announcing preview docs or starting Phase 06 stable promotion.

## Phase 06 Readiness Gate - 2026-05-17 - Codex quick-dev

### Summary

- Evaluated Phase 06 stable promotion readiness only; no merge, version bump, stable tag, push, publish, or docs promotion was run.
- Marked only the Phase 06 read step complete in `TODO.md`.
- Confirmed stable promotion remains blocked because preview publication and post-publication install verification are incomplete.

### Commands Run

```bash
sed -n '1,220p' docs/plans/versioning/README.md
sed -n '1,220p' docs/plans/versioning/06-promotion-to-stable.md
tail -n 260 docs/plans/versioning/handoff-log.md
sed -n '1,180p' docs/plans/versioning/TODO.md
git status --short
git -C <integration-worktree> status --short --branch
git -C <integration-worktree> rev-parse HEAD
git -C <integration-worktree> tag -l 'v1.15.0-next.*' --format='%(refname:short) %(objectname) %(taggerdate:iso8601)'
git -C <integration-worktree> ls-remote --heads --tags automator next/codex-runtime-support v1.15.0-next.1 main v1.14.2
```

### Results

- Plan repo status before edits: only `docs/plans/versioning/impl_artifacts/spec-phase-06-readiness-gate.md` was untracked.
- Loaded `README.md`, `06-promotion-to-stable.md`, `handoff-log.md`, and `TODO.md` before marking the Phase 06 read step complete.
- Product worktree status: `## next/codex-runtime-support...automator/main [ahead 8]`; no file changes listed.
- Product worktree HEAD: `ef18ba5a4e1d4e1414adba7b1a1ef2f8d164b94c`.
- Local preview tags:
  - `v1.15.0-next.0` tag object `5acda521145da911a1f97e10d685125bf7959d6c`, created `2026-05-17 08:29:09 -0300`; stale/local-only, do not push.
  - `v1.15.0-next.1` tag object `4736b5c39a1c7a6306212efdb484499a69ba2227`, created `2026-05-17 10:20:03 -0300`; intended preview tag.
- Remote ref check returned only:
  - `refs/heads/main` at `5196bb2e3bf88b4c7c9e1ad260ff826c372e01b6`.
  - `refs/tags/v1.14.2` at `593f338532ea730b5c1a2dd86681e87b5b4f04dd`.
- Remote `next/codex-runtime-support` is absent.
- Remote `v1.15.0-next.1` is absent.

### Decisions And Assumptions

- Keep Phase 03 push tasks unchecked until a remote-enabled run publishes `next/codex-runtime-support` and `v1.15.0-next.1`.
- Keep Phase 05 preview pin, branch custom-source, and all-stable prerelease-exclusion checks unchecked until they are rerun against published remote preview refs.
- Keep all Phase 06 merge/tag/publish/version-bump tasks unchecked because stable promotion preconditions are not met.
- Do not push stale local `v1.15.0-next.0`; `v1.15.0-next.1` supersedes it.
- The remote `main` SHA now reported by `ls-remote` is newer than earlier handoff entries; remote-enabled promotion work must inspect/rebase/merge deliberately before any stable release action.

### Blockers Or Risks

- Blocked: remote preview branch `next/codex-runtime-support` is not published.
- Blocked: remote preview tag `v1.15.0-next.1` is not published.
- Blocked: Phase 05 preview pin install is not verified against a remote prerelease tag.
- Blocked: Phase 05 branch custom-source install is not verified against a remote preview branch.
- Blocked: Phase 05 all-stable prerelease-exclusion is not verified with a remote prerelease tag present.
- Risk: custom-source branch install can fail to resolve the requested branch while exiting `0`; verification must assert installed manifest/files, not exit status alone.
- Risk: remote `main` advanced to `5196bb2e3bf88b4c7c9e1ad260ff826c372e01b6` since earlier plan entries.

### Next Phase Notes

- Remote-enabled publication commands:

```bash
cd <integration-worktree>
git status --short --branch
git ls-remote --heads --tags automator next/codex-runtime-support v1.15.0-next.1 main v1.14.2
git push automator next/codex-runtime-support
git push automator v1.15.0-next.1
git ls-remote --heads --tags automator next/codex-runtime-support v1.15.0-next.1 main v1.14.2
```

- Post-publication verification commands:

```bash
rm -rf /tmp/baut-next-smoke /tmp/baut-branch-smoke /tmp/baut-all-stable-smoke /tmp/baut-home-next /tmp/baut-home-branch /tmp/baut-home-all-stable /tmp/baut-npm-next /tmp/baut-npm-branch /tmp/baut-npm-all-stable
env HOME=/tmp/baut-home-next NPM_CONFIG_CACHE=/tmp/baut-npm-next npx --yes bmad-method@6.6.0 install --modules baut --pin baut=v1.15.0-next.1 --tools codex --yes --directory /tmp/baut-next-smoke
env HOME=/tmp/baut-home-branch NPM_CONFIG_CACHE=/tmp/baut-npm-branch npx --yes bmad-method@6.6.0 install --custom-source https://github.com/bmad-code-org/bmad-automator@next/codex-runtime-support --tools codex --yes --directory /tmp/baut-branch-smoke
env HOME=/tmp/baut-home-all-stable NPM_CONFIG_CACHE=/tmp/baut-npm-all-stable npx --yes bmad-method@6.6.0 install --modules baut --all-stable --tools claude-code --yes --directory /tmp/baut-all-stable-smoke
rg -n 'name: baut|channel: pinned|version: v1\.15\.0-next\.1' /tmp/baut-next-smoke/_bmad/_config/manifest.yaml
rg -n 'name: (baut|bmad-automator)|source: custom|channel: pinned|version: next/codex-runtime-support|sha:' /tmp/baut-branch-smoke/_bmad/_config/manifest.yaml
rg -n 'name: baut|channel: stable|version: v[0-9]+\.[0-9]+\.[0-9]+$' /tmp/baut-all-stable-smoke/_bmad/_config/manifest.yaml
if rg -n 'version: v[0-9]+\.[0-9]+\.[0-9]+-' /tmp/baut-all-stable-smoke/_bmad/_config/manifest.yaml; then echo 'all-stable selected prerelease' >&2; exit 1; fi
test -f /tmp/baut-next-smoke/.agents/skills/bmad-story-automator/src/story_automator/core/runtime_layout.py
test -f /tmp/baut-next-smoke/.agents/skills/bmad-story-automator/src/story_automator/core/stop_hooks.py
test -f /tmp/baut-branch-smoke/.agents/skills/bmad-story-automator/src/story_automator/core/runtime_layout.py
test -f /tmp/baut-branch-smoke/.agents/skills/bmad-story-automator/src/story_automator/core/stop_hooks.py
```

- Start Phase 06 stable promotion only after preview publication and the post-publication checks above pass and are recorded.

## Phase 07 - 2026-05-17 - Codex quick-dev

### Summary

- Completed local Phase 07 rollback-support preparation only.
- Updated `07-rollback-and-support.md` with current support state, the observed manifest path, and a support triage template.
- Updated `.github/ISSUE_TEMPLATE/bug_report.yml` to collect install path type, tag/branch/package version, target tool, manifest, and installer stdout/stderr.
- Updated `docs/troubleshooting.md` with BMAD Method rollback, `--next baut` confusion, and custom-source false-success guidance.
- Marked only non-incident Phase 07 tasks complete in `TODO.md`: read, support notes, and handoff.
- Did not cut `v1.15.0-next.2` because no bad published preview exists.
- Did not cut a stable patch tag because `v1.15.0` has not shipped.

### Commands Run

```bash
sed -n '1,260p' docs/plans/versioning/README.md
sed -n '1,260p' docs/plans/versioning/07-rollback-and-support.md
sed -n '520,920p' docs/plans/versioning/handoff-log.md
sed -n '1,120p' docs/plans/versioning/TODO.md
git -C <integration-worktree> status --short --branch
git -C <integration-worktree> rev-parse HEAD
git -C <integration-worktree> tag -l 'v1.15.0-next.*' --format='%(refname:short) %(objectname) %(taggerdate:iso8601)'
git -C <integration-worktree> ls-remote --heads --tags automator next/codex-runtime-support v1.15.0-next.1 main v1.14.2
git diff --check
python3 - <<'PY'
from pathlib import Path
import yaml
yaml.safe_load(Path('.github/ISSUE_TEMPLATE/bug_report.yml').read_text())
print('yaml_ok')
PY
```

### Results

- Product worktree status: `## next/codex-runtime-support...automator/main [ahead 8]`.
- Product worktree HEAD: `ef18ba5a4e1d4e1414adba7b1a1ef2f8d164b94c`.
- Local preview tags:
  - `v1.15.0-next.0` tag object `5acda521145da911a1f97e10d685125bf7959d6c`; stale/local-only, do not push.
  - `v1.15.0-next.1` tag object `4736b5c39a1c7a6306212efdb484499a69ba2227`; intended preview tag.
- Remote ref check returned only:
  - `refs/heads/main` at `5196bb2e3bf88b4c7c9e1ad260ff826c372e01b6`.
  - `refs/tags/v1.14.2` at `593f338532ea730b5c1a2dd86681e87b5b4f04dd`.
- Remote `next/codex-runtime-support` remains absent.
- Remote `v1.15.0-next.1` remains absent.
- Support notes now ask for `_bmad/_config/manifest.yaml`; `_bmad/install-manifest.csv` is listed only if present.
- Public bug reports now collect the Phase 07 support fields needed for install, rollback, pin, and custom-source failures.
- Issue-template YAML parsed successfully with `PyYAML`.
- Troubleshooting now warns that `--modules baut` and `--next baut` are not stable rollback or pre-merge preview paths while the registry default remains `next`.

### Decisions And Assumptions

- No active preview incident exists because the intended preview tag is not published.
- No active stable incident exists because `v1.15.0` has not shipped.
- Keep `v1.15.0-next.2` as the first bad-preview replacement tag only after a published `v1.15.0-next.1` incident.
- Keep stable rollback as a future patch release from last-good stable base or a revert commit only after `v1.15.0` ships.

### Blockers Or Risks

- Remote preview branch and tag publication are still incomplete.
- Phase 05 preview pin, branch custom-source, and all-stable prerelease-exclusion checks still need reruns after publication.
- Phase 06 stable promotion remains blocked.
- Custom-source install can fail branch resolution while exiting `0`; support and verification must inspect manifest fields and installed runtime files.

### Next Phase Notes

- Remote-enabled preview publication remains the next unblocker:

```bash
cd <integration-worktree>
git status --short --branch
git ls-remote --heads --tags automator next/codex-runtime-support v1.15.0-next.1 main v1.14.2
git push automator next/codex-runtime-support
git push automator v1.15.0-next.1
git ls-remote --heads --tags automator next/codex-runtime-support v1.15.0-next.1 main v1.14.2
```

- After publication, run the Phase 06 post-publication verification command block before any stable promotion.
- If `v1.15.0-next.1` later breaks after publication, fix forward with `v1.15.0-next.2`; do not move or delete the pushed tag.

## Remote Publication And Post-Publication Verification - 2026-05-17 - Codex quick-dev

### Summary

- Published the remote preview branch `next/codex-runtime-support`.
- Published the remote preview tag `v1.15.0-next.1`.
- Verified preview pin install succeeds and installs Codex runtime files.
- Verified `--all-stable` still selects pure-semver stable `v1.14.2`, not the prerelease tag.
- Ran custom-source branch install after publication; it installed Codex runtime files, but the generated manifest still records registry `next`/`main` metadata. Keep the Phase 05 custom-source verification item open until this is accepted as installer metadata drift or fixed upstream.
- Added consumer channel docs to `README.md` and `docs/installation-and-layout.md` so Phase 04 completion is represented on this branch.
- Did not start Phase 06 stable promotion because custom-source branch verification is not fully clean.

### Commands Run

```bash
cd <integration-worktree>
git status --short --branch
git ls-remote --heads --tags automator next/codex-runtime-support v1.15.0-next.1 main v1.14.2
git rev-parse HEAD v1.15.0-next.1^{}
git push automator next/codex-runtime-support
git push automator v1.15.0-next.1
git ls-remote --heads --tags automator next/codex-runtime-support v1.15.0-next.1 main v1.14.2
rm -rf /tmp/baut-next-smoke /tmp/baut-branch-smoke /tmp/baut-all-stable-smoke /tmp/baut-home-next /tmp/baut-home-branch /tmp/baut-home-all-stable /tmp/baut-npm-next /tmp/baut-npm-branch /tmp/baut-npm-all-stable
env HOME=/tmp/baut-home-next NPM_CONFIG_CACHE=/tmp/baut-npm-next npx --yes bmad-method@6.6.0 install --modules baut --pin baut=v1.15.0-next.1 --tools codex --yes --directory /tmp/baut-next-smoke
env HOME=/tmp/baut-home-branch NPM_CONFIG_CACHE=/tmp/baut-npm-branch npx --yes bmad-method@6.6.0 install --custom-source https://github.com/bmad-code-org/bmad-automator@next/codex-runtime-support --tools codex --yes --directory /tmp/baut-branch-smoke
env HOME=/tmp/baut-home-all-stable NPM_CONFIG_CACHE=/tmp/baut-npm-all-stable npx --yes bmad-method@6.6.0 install --modules baut --all-stable --tools claude-code --yes --directory /tmp/baut-all-stable-smoke
rg -n 'name: baut|channel: pinned|version: v1\.15\.0-next\.1' /tmp/baut-next-smoke/_bmad/_config/manifest.yaml
rg -n 'name: (baut|bmad-automator)|source: custom|channel: pinned|version: next/codex-runtime-support|sha:' /tmp/baut-branch-smoke/_bmad/_config/manifest.yaml
rg -n 'name: baut|channel: stable|version: v[0-9]+\.[0-9]+\.[0-9]+$' /tmp/baut-all-stable-smoke/_bmad/_config/manifest.yaml
if rg -n 'version: v[0-9]+\.[0-9]+\.[0-9]+-' /tmp/baut-all-stable-smoke/_bmad/_config/manifest.yaml; then echo 'all-stable selected prerelease' >&2; exit 1; fi
test -f /tmp/baut-next-smoke/.agents/skills/bmad-story-automator/src/story_automator/core/runtime_layout.py
test -f /tmp/baut-next-smoke/.agents/skills/bmad-story-automator/src/story_automator/core/stop_hooks.py
test -f /tmp/baut-branch-smoke/.agents/skills/bmad-story-automator/src/story_automator/core/runtime_layout.py
test -f /tmp/baut-branch-smoke/.agents/skills/bmad-story-automator/src/story_automator/core/stop_hooks.py
sed -n '1,80p' /tmp/baut-next-smoke/_bmad/_config/manifest.yaml
sed -n '1,80p' /tmp/baut-branch-smoke/_bmad/_config/manifest.yaml
sed -n '1,80p' /tmp/baut-all-stable-smoke/_bmad/_config/manifest.yaml
```

### Results

- Product worktree status before publication: `## next/codex-runtime-support...automator/main [ahead 8]`.
- Product worktree HEAD and tag target both resolved to `ef18ba5a4e1d4e1414adba7b1a1ef2f8d164b94c`.
- Initial remote ref check returned only `main` at `5196bb2e3bf88b4c7c9e1ad260ff826c372e01b6` and `v1.14.2` at `593f338532ea730b5c1a2dd86681e87b5b4f04dd`.
- Branch push output:

```text
* [new branch]      next/codex-runtime-support -> next/codex-runtime-support
```

- Tag push output:

```text
* [new tag]         v1.15.0-next.1 -> v1.15.0-next.1
```

- Post-push remote ref check returned:
  - `refs/heads/main` at `5196bb2e3bf88b4c7c9e1ad260ff826c372e01b6`.
  - `refs/heads/next/codex-runtime-support` at `ef18ba5a4e1d4e1414adba7b1a1ef2f8d164b94c`.
  - `refs/tags/v1.14.2` at `593f338532ea730b5c1a2dd86681e87b5b4f04dd`.
  - `refs/tags/v1.15.0-next.1` tag object `4736b5c39a1c7a6306212efdb484499a69ba2227`.
- Preview pin install passed. Manifest records `name: baut`, `version: v1.15.0-next.1`, `channel: pinned`, and SHA `ef18ba5a4e1d4e1414adba7b1a1ef2f8d164b94c`. Runtime files `runtime_layout.py` and `stop_hooks.py` exist under `.agents/skills`.
- All-stable install passed. Manifest records `name: baut`, `version: v1.14.2`, `channel: stable`, and SHA `593f338532ea730b5c1a2dd86681e87b5b4f04dd`. The prerelease-regex guard found no prerelease version in the all-stable manifest.
- Custom-source branch install cloned the custom repository and installed runtime files. The installed helper package reports `1.15.0.dev1`, matching the preview branch content.
- Custom-source branch manifest mismatch: `/tmp/baut-branch-smoke/_bmad/_config/manifest.yaml` records `version: main`, `channel: next`, and SHA `5196bb2e3bf88b4c7c9e1ad260ff826c372e01b6` instead of `next/codex-runtime-support` or `ef18ba5a4e1d4e1414adba7b1a1ef2f8d164b94c`.

### Decisions And Assumptions

- Phase 03 remote publication is complete.
- Phase 05 preview pin verification is complete.
- Phase 05 all-stable prerelease-exclusion verification is complete.
- Phase 05 custom-source branch verification remains open because the manifest records registry `next`/`main` metadata even though branch runtime files installed.
- Phase 06 stable promotion remains blocked until the custom-source manifest mismatch is resolved, explicitly accepted as known installer metadata drift, or removed as a release gate.

### Next Phase Notes

- Decide whether custom-source manifest metadata drift blocks stable promotion.
- If blocking, fix BMAD-METHOD custom-source manifest recording or adjust Automator release criteria after documenting the installer behavior.
- If accepted, update `TODO.md` to mark the custom-source check complete with this caveat, then run Phase 06 stable promotion from a current `automator/main` base.

## Custom-Source Blocker Resolution - 2026-05-17 - Codex quick-dev

### Summary

- Root cause: BMAD-METHOD 6.6.0 has separate install-content and manifest-metadata paths for official module codes.
- Install content path checks `CustomModuleManager.getResolution(moduleName)` first and installs the custom-source plugin resolution for `baut`.
- Manifest metadata path checks `ExternalModuleManager.getModuleByCode(moduleName)` before custom-source resolution, so official `baut` metadata wins and the manifest records registry `next`/`main`.
- Verified the branch content actually installed:
  - custom-source cache HEAD: `ef18ba5a4e1d4e1414adba7b1a1ef2f8d164b94c`
  - cache branch: `next/codex-runtime-support`
  - installed files match custom-source cache and differ from external registry cache
  - installed helper version: `1.15.0.dev1`
  - installed runtime files: `runtime_layout.py`, `stop_hooks.py`
- Accepted this as BMAD-METHOD metadata drift, not Automator preview failure.
- Updated verification/support docs to require custom-source cache HEAD and installed runtime-file checks instead of requiring manifest branch metadata for official code `baut`.
- Marked Phase 05 custom-source verification complete in `TODO.md`.

### Commands Run

```bash
git -C /tmp/baut-home-branch/.bmad/cache/custom-modules/github.com/bmad-code-org/bmad-automator rev-parse HEAD
git -C /tmp/baut-home-branch/.bmad/cache/custom-modules/github.com/bmad-code-org/bmad-automator branch --show-current
git -C /tmp/baut-home-branch/.bmad/cache/external-modules/baut rev-parse HEAD
cmp -s /tmp/baut-branch-smoke/.agents/skills/bmad-story-automator/src/story_automator/core/runtime_layout.py /tmp/baut-home-branch/.bmad/cache/custom-modules/github.com/bmad-code-org/bmad-automator/skills/bmad-story-automator/src/story_automator/core/runtime_layout.py
cmp -s /tmp/baut-branch-smoke/.agents/skills/bmad-story-automator/src/story_automator/core/runtime_layout.py /tmp/baut-home-branch/.bmad/cache/external-modules/baut/skills/bmad-story-automator/src/story_automator/core/runtime_layout.py
rg -n "version|__version__" /tmp/baut-branch-smoke/.agents/skills/bmad-story-automator/pyproject.toml /tmp/baut-branch-smoke/.agents/skills/bmad-story-automator/src/story_automator/__init__.py
sed -n '270,360p' /tmp/baut-npm-branch/_npx/d1483d74adee2f79/node_modules/bmad-method/tools/installer/core/manifest.js
sed -n '600,665p' /tmp/baut-npm-branch/_npx/d1483d74adee2f79/node_modules/bmad-method/tools/installer/core/installer.js
```

### Results

- Custom-source cache HEAD is `ef18ba5a4e1d4e1414adba7b1a1ef2f8d164b94c` on branch `next/codex-runtime-support`.
- External registry cache HEAD is `5196bb2e3bf88b4c7c9e1ad260ff826c372e01b6` on branch `main`.
- Installed `runtime_layout.py` matches the custom-source cache.
- Installed `runtime_layout.py` differs from the external registry cache.
- Installed `pyproject.toml` and `__init__.py` both report `1.15.0.dev1`.

### Decisions And Assumptions

- Custom-source branch install is verified by content/cache evidence.
- `_bmad/_config/manifest.yaml` is not reliable branch-ref evidence for custom-source installs that reuse an official module code.
- Phase 06 stable promotion may proceed after this handoff entry and a final clean status/check pass.

## Phase 06 Stable Promotion - 2026-05-17 - Codex quick-dev

### Summary

- Promoted Codex runtime support to stable `v1.15.0`.
- Fetched current `automator/main` first and found a newer `main` commit, `5196bb2e3bf88b4c7c9e1ad260ff826c372e01b6` (`Rename module code from baut to automator (#10)`).
- Created local promotion branch `bma-d/stable-promotion` from `automator/main`.
- Merged `next/codex-runtime-support` into the promotion branch with no conflicts.
- Preserved current `main` source truth in `skills/module.yaml`: `code: automator`.
- Bumped release metadata to `1.15.0`.
- Ran `npm run verify` successfully.
- Created annotated tag `v1.15.0`.
- Pushed promotion branch HEAD to `automator/main`.
- Pushed tag `v1.15.0`.
- Ran post-promotion stable, pinned, and registry-next install checks.
- Skipped optional `npm publish`; no npm publish was requested.

### Commands Run

```bash
cd <integration-worktree>
git fetch automator main --tags
git switch -c bma-d/stable-promotion automator/main
git merge --no-ff next/codex-runtime-support -m "Merge branch 'next/codex-runtime-support'"
git add .claude-plugin/marketplace.json .claude-plugin/plugin.json README.md docs/installation-and-layout.md docs/changelog/260517.md package.json skills/bmad-story-automator/pyproject.toml skills/bmad-story-automator/src/story_automator/__init__.py skills/module.yaml tests/test_runtime_layout.py
git commit -m "chore: release 1.15.0"
git tag -a v1.15.0 -m "v1.15.0"
git push automator HEAD:main
git push automator v1.15.0
git ls-remote --heads --tags automator main v1.15.0 v1.15.0-next.1 v1.14.2
```

Verification:

```bash
npm run verify
env HOME=/tmp/baut-home-stable-115 NPM_CONFIG_CACHE=/tmp/baut-npm-stable-115 npx --yes bmad-method@6.6.0 install --modules baut --all-stable --tools codex --yes --directory /tmp/baut-stable-115-smoke
env HOME=/tmp/baut-home-pin-115 NPM_CONFIG_CACHE=/tmp/baut-npm-pin-115 npx --yes bmad-method@6.6.0 install --modules baut --pin baut=v1.15.0 --tools codex --yes --directory /tmp/baut-pin-115-smoke
env HOME=/tmp/baut-home-next-main NPM_CONFIG_CACHE=/tmp/baut-npm-next-main npx --yes bmad-method@6.6.0 install --modules baut --tools codex --yes --directory /tmp/baut-next-main-smoke
test -f /tmp/baut-stable-115-smoke/.agents/skills/bmad-story-automator/src/story_automator/core/runtime_layout.py
test -f /tmp/baut-stable-115-smoke/.agents/skills/bmad-story-automator/src/story_automator/core/stop_hooks.py
test -f /tmp/baut-pin-115-smoke/.agents/skills/bmad-story-automator/src/story_automator/core/runtime_layout.py
test -f /tmp/baut-pin-115-smoke/.agents/skills/bmad-story-automator/src/story_automator/core/stop_hooks.py
test -f /tmp/baut-next-main-smoke/.agents/skills/bmad-story-automator/src/story_automator/core/runtime_layout.py
test -f /tmp/baut-next-main-smoke/.agents/skills/bmad-story-automator/src/story_automator/core/stop_hooks.py
```

### Results

- Stable release commit: `acafaed1f369214c37b44415698fd6a76c820e7f` (`chore: release 1.15.0`).
- Merge commit: `3563ab6` (`Merge branch 'next/codex-runtime-support'`).
- Remote refs after push:
  - `refs/heads/main` at `acafaed1f369214c37b44415698fd6a76c820e7f`.
  - `refs/tags/v1.15.0` tag object `2f8006c62117b638fc522af066ab9b11290f3232`.
  - `refs/tags/v1.15.0-next.1` tag object `4736b5c39a1c7a6306212efdb484499a69ba2227`.
  - `refs/tags/v1.14.2` at `593f338532ea730b5c1a2dd86681e87b5b4f04dd`.
- `npm run verify` passed:
  - 203 Python tests.
  - dry pack for `bmad-story-automator@1.15.0`.
  - smoke test `smoke ok`.
- Stable all-stable install passed. Manifest records `version: v1.15.0`, `channel: stable`, SHA `acafaed1f369214c37b44415698fd6a76c820e7f`; Codex runtime files exist.
- Pinned stable install passed. Manifest records `version: v1.15.0`, `channel: pinned`, SHA `acafaed1f369214c37b44415698fd6a76c820e7f`; Codex runtime files exist.
- Registry default next install passed. Manifest records `version: main`, `channel: next`, SHA `acafaed1f369214c37b44415698fd6a76c820e7f`; Codex runtime files exist.

### Decisions And Assumptions

- Continue documenting install commands with official registry code `baut` because the official marketplace registry still lists `code: baut`.
- Keep `skills/module.yaml` at `code: automator` because that is now current `automator/main` source truth.
- Optional npm stable publish remains open/skipped.
- Stable rollback, if needed, should be a patch tag from last-good stable base or a revert/fix commit; do not move `v1.15.0`.

### Next Phase Notes

- Phase 07 stable incident work is not active unless a concrete `v1.15.0` regression appears.
- If npm distribution should also expose `1.15.0`, run an explicit npm publish flow separately.
