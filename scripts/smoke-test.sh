#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/bmad-story-automator-smoke.XXXXXX")"
PACK_TARBALL=""

cleanup() {
  if [ -n "$PACK_TARBALL" ] && [ -f "$PACK_TARBALL" ]; then
    rm -f "$PACK_TARBALL"
  fi
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

assert_file() {
  local path="$1"
  [ -f "$path" ] || {
    echo "Missing file: $path" >&2
    exit 1
  }
}

assert_dir() {
  local path="$1"
  [ -d "$path" ] || {
    echo "Missing dir: $path" >&2
    exit 1
  }
}

assert_contains() {
  local needle="$1"
  local path="$2"
  grep -Fq "$needle" "$path" || {
    echo "Missing content in $path: $needle" >&2
    exit 1
  }
}

assert_not_contains() {
  local needle="$1"
  local path="$2"
  if grep -Fq "$needle" "$path"; then
    echo "Unexpected content in $path: $needle" >&2
    exit 1
  fi
}

assert_not_exists() {
  local path="$1"
  [ ! -e "$path" ] || {
    echo "Unexpected path exists: $path" >&2
    exit 1
  }
}

assert_string_contains() {
  local needle="$1"
  local haystack="$2"
  case "$haystack" in
    *"$needle"*) ;;
    *)
      echo "Missing content in string: $needle" >&2
      exit 1
      ;;
  esac
}

assert_string_not_contains() {
  local needle="$1"
  local haystack="$2"
  case "$haystack" in
    *"$needle"*)
      echo "Unexpected content in string: $needle" >&2
      exit 1
      ;;
  esac
}

make_skill() {
  local root="$1"
  local name="$2"
  mkdir -p "$root/.claude/skills/$name"
  printf -- '---\nname: %s\n---\n\nFollow ./workflow.md.\n' "$name" >"$root/.claude/skills/$name/SKILL.md"
  printf '# %s\n' "$name" >"$root/.claude/skills/$name/workflow.md"
}

make_workflow_only_skill() {
  local root="$1"
  local name="$2"
  mkdir -p "$root/.claude/skills/$name"
  printf '# %s\n' "$name" >"$root/.claude/skills/$name/workflow.md"
}

make_skill_only_skill() {
  local root="$1"
  local name="$2"
  mkdir -p "$root/.claude/skills/$name"
  printf -- '---\nname: %s\n---\n\nFollow ./workflow.md.\n' "$name" >"$root/.claude/skills/$name/SKILL.md"
}

make_required_skills() {
  local root="$1"
  make_skill "$root" bmad-create-story
  printf '# discover\n' >"$root/.claude/skills/bmad-create-story/discover-inputs.md"
  printf '# template\n' >"$root/.claude/skills/bmad-create-story/template.md"
  printf '# checklist\n' >"$root/.claude/skills/bmad-create-story/checklist.md"

  make_skill "$root" bmad-dev-story
  printf '# checklist\n' >"$root/.claude/skills/bmad-dev-story/checklist.md"

  make_skill "$root" bmad-retrospective
}

make_required_workflow_only_skills() {
  local root="$1"
  make_workflow_only_skill "$root" bmad-create-story
  make_workflow_only_skill "$root" bmad-dev-story
  make_workflow_only_skill "$root" bmad-retrospective
}

make_required_skill_only_skills() {
  local root="$1"
  make_skill_only_skill "$root" bmad-create-story
  make_skill_only_skill "$root" bmad-dev-story
  make_skill_only_skill "$root" bmad-retrospective
}

make_qa_skill() {
  local root="$1"
  make_skill "$root" bmad-qa-generate-e2e-tests
  printf '# checklist\n' >"$root/.claude/skills/bmad-qa-generate-e2e-tests/checklist.md"
}

make_legacy_story_automator_dirs() {
  local root="$1"
  mkdir -p \
    "$root/_bmad/bmm/4-implementation/bmad-story-automator" \
    "$root/_bmad/bmm/4-implementation/bmad-story-automator-review" \
    "$root/_bmad/bmm/workflows/4-implementation/story-automator" \
    "$root/_bmad/bmm/workflows/4-implementation/story-automator-review"
  printf 'old current story\n' >"$root/_bmad/bmm/4-implementation/bmad-story-automator/old.txt"
  printf 'old current review\n' >"$root/_bmad/bmm/4-implementation/bmad-story-automator-review/old.txt"
  printf 'old legacy story\n' >"$root/_bmad/bmm/workflows/4-implementation/story-automator/old.txt"
  printf 'old legacy review\n' >"$root/_bmad/bmm/workflows/4-implementation/story-automator-review/old.txt"
}

seed_command_shims() {
  local root="$1"
  local story_wrapper_mode="$2"

  printf 'legacy py wrapper\n' >"$root/.claude/commands/bmad-bmm-story-automator-py.md"
  if [ "$story_wrapper_mode" = "repointed" ]; then
    cat >"$root/.claude/commands/bmad-bmm-story-automator.md" <<'EOF'
Use .claude/skills/bmad-story-automator/workflow.md
# legacy note: _bmad/bmm/4-implementation/bmad-story-automator/workflow.md
EOF
  else
    printf 'old story wrapper _bmad/bmm/4-implementation/bmad-story-automator/workflow.md\n' >"$root/.claude/commands/bmad-bmm-story-automator.md"
  fi
  printf 'old review wrapper _bmad/bmm/workflows/4-implementation/story-automator-review/workflow.yaml\n' >"$root/.claude/commands/bmad-bmm-story-automator-review.md"
  printf 'old create wrapper /bmad-bmm-create-story\n' >"$root/.claude/commands/bmad-bmm-create-story.md"
  printf 'old dev wrapper /bmad-bmm-dev-story\n' >"$root/.claude/commands/bmad-bmm-dev-story.md"
  printf 'old retro wrapper /bmad-bmm-retrospective\n' >"$root/.claude/commands/bmad-bmm-retrospective.md"
  printf 'old qa wrapper /bmad-bmm-qa-generate-e2e-tests\n' >"$root/.claude/commands/bmad-bmm-qa-generate-e2e-tests.md"
  printf 'old automate wrapper /bmad-tea-testarch-automate\n' >"$root/.claude/commands/bmad-tea-testarch-automate.md"
}

make_fixture() {
  local root="$1"
  local qa="$2"
  local legacy="$3"
  local deps_mode="${4:-full}"
  local story_wrapper_mode="${5:-legacy}"

  mkdir -p "$root/_bmad" "$root/.claude/commands"
  case "$deps_mode" in
    workflow-only) make_required_workflow_only_skills "$root" ;;
    skill-only) make_required_skill_only_skills "$root" ;;
    *) make_required_skills "$root" ;;
  esac

  case "$qa" in
    yes|full) make_qa_skill "$root" ;;
    workflow-only) make_workflow_only_skill "$root" bmad-qa-generate-e2e-tests ;;
    skill-only) make_skill_only_skill "$root" bmad-qa-generate-e2e-tests ;;
  esac

  if [ "$legacy" = "yes" ]; then
    make_legacy_story_automator_dirs "$root"
  fi

  seed_command_shims "$root" "$story_wrapper_mode"
}

verify_common_install() {
  local root="$1"
  local story_wrapper_expectation="${2:-removed}"
  local story_dir="$root/.claude/skills/bmad-story-automator"
  local review_dir="$root/.claude/skills/bmad-story-automator-review"

  assert_dir "$story_dir"
  assert_dir "$review_dir"
  assert_file "$story_dir/SKILL.md"
  assert_file "$story_dir/workflow.md"
  assert_file "$story_dir/scripts/story-automator"
  assert_file "$story_dir/src/story_automator/cli.py"
  assert_file "$story_dir/data/orchestration-policy.json"
  assert_file "$story_dir/data/prompts/create.md"
  assert_file "$story_dir/data/prompts/review.md"
  assert_file "$story_dir/data/parse/create.json"
  assert_file "$story_dir/data/parse/review.json"
  assert_file "$story_dir/pyproject.toml"
  assert_file "$story_dir/README.md"
  assert_file "$review_dir/SKILL.md"
  assert_file "$review_dir/instructions.xml"
  assert_file "$review_dir/contract.json"
  assert_contains "name: bmad-story-automator" "$story_dir/SKILL.md"
  assert_contains "Follow the instructions in ./workflow.md." "$story_dir/SKILL.md"

  (
    cd "$root"
    "$story_dir/scripts/story-automator" --help >/dev/null
  )

  assert_not_exists "$root/.claude/commands/bmad-bmm-story-automator-py.md"
  assert_not_exists "$root/.claude/commands/bmad-bmm-story-automator-review.md"
  assert_not_exists "$root/.claude/commands/bmad-bmm-create-story.md"
  assert_not_exists "$root/.claude/commands/bmad-bmm-dev-story.md"
  assert_not_exists "$root/.claude/commands/bmad-bmm-retrospective.md"
  assert_not_exists "$root/.claude/commands/bmad-bmm-qa-generate-e2e-tests.md"
  assert_not_exists "$root/.claude/commands/bmad-tea-testarch-automate.md"
  if [ "$story_wrapper_expectation" = "preserved" ]; then
    assert_file "$root/.claude/commands/bmad-bmm-story-automator.md"
    assert_contains ".claude/skills/bmad-story-automator/workflow.md" "$root/.claude/commands/bmad-bmm-story-automator.md"
  else
    assert_not_exists "$root/.claude/commands/bmad-bmm-story-automator.md"
  fi
  assert_contains "outside .claude/skills/" "$review_dir/instructions.xml"
  assert_contains 'installed helper at `scripts/story-automator`' "$story_dir/data/scripts-reference.md"
  assert_not_contains "bin/" "$story_dir/data/monitoring-pattern.md"
  assert_contains 'state-file "$state_file"' "$story_dir/data/code-review-loop.md"
  assert_contains 'build-cmd review {story_id} --agent "$review_agent" --state-file "$state_file"' "$story_dir/data/code-review-loop.md"
  assert_contains 'workflow review --story-key {story_id} --state-file "$state_file"' "$story_dir/data/code-review-loop.md"
  assert_contains 'parse-output "$output_file" review --state-file "$state_file"' "$story_dir/data/code-review-loop.md"
  assert_contains 'verify-code-review {story_id} --state-file "$state_file"' "$story_dir/data/code-review-loop.md"
  assert_contains 'orchestrator-helper verify-step create {story_id} --state-file "$state_file"' "$story_dir/steps-c/step-03-execute.md"
  assert_contains 'build-cmd create {story_id} --agent "$current_agent" --state-file "$state_file"' "$story_dir/steps-c/step-03-execute.md"
  assert_contains 'validation_passed=$(echo "$validation" | jq -r '\''.verified'\'')' "$story_dir/data/retry-fallback-implementation.md"
  assert_contains 'build-cmd {step} {story_id} --agent "$current_agent" --state-file "$state_file"' "$story_dir/data/retry-fallback-implementation.md"
  assert_contains 'orchestrator-helper verify-step create 5.3 --state-file "$state_file"' "$story_dir/data/monitoring-pattern.md"
  assert_contains 'workflow create --story-key 5.3 --state-file "$state_file"' "$story_dir/data/monitoring-pattern.md"
  assert_not_contains 'parse-output "$output_file" create' "$story_dir/data/monitoring-pattern.md"
  assert_contains '| `$scripts orchestrator-helper verify-step` | Shared success verifier checks per step |' "$story_dir/data/scripts-reference.md"
}

verify_qa_prompts() {
  local root="$1"
  local story_dir="$root/.claude/skills/bmad-story-automator"
  local auto_claude auto_codex review_claude retro_claude

  auto_claude="$(cd "$root" && "$story_dir/scripts/story-automator" tmux-wrapper build-cmd auto 5.3 --agent claude)"
  auto_codex="$(cd "$root" && "$story_dir/scripts/story-automator" tmux-wrapper build-cmd auto 5.3 --agent codex)"
  review_claude="$(cd "$root" && "$story_dir/scripts/story-automator" tmux-wrapper build-cmd review 5.3 --agent claude)"
  retro_claude="$(cd "$root" && "$story_dir/scripts/story-automator" tmux-wrapper build-cmd retro 5 --agent claude)"

  assert_string_contains "claude --dangerously-skip-permissions" "$auto_claude"
  assert_string_contains "READ this skill first: .claude/skills/bmad-qa-generate-e2e-tests/SKILL.md" "$auto_claude"
  assert_string_contains "READ this workflow file next: .claude/skills/bmad-qa-generate-e2e-tests/workflow.md" "$auto_claude"
  assert_string_contains "CODEX_HOME=\"/tmp/sa-codex-home-" "$auto_codex"
  assert_string_contains "codex exec -s workspace-write" "$auto_codex"
  assert_string_contains "approval_policy=\"never\"" "$auto_codex"
  assert_string_contains "--disable plugins --disable sqlite --disable shell_snapshot" "$auto_codex"
  assert_string_contains "READ this skill first: .claude/skills/bmad-qa-generate-e2e-tests/SKILL.md" "$auto_codex"
  assert_string_contains "READ this skill first: .claude/skills/bmad-story-automator-review/SKILL.md" "$review_claude"
  assert_string_contains "auto-fix all issues without prompting" "$review_claude"
  assert_string_contains "READ this skill first: .claude/skills/bmad-retrospective/SKILL.md" "$retro_claude"
  assert_string_contains "Assume the user will NOT provide any input to the retrospective directly." "$retro_claude"
  assert_string_contains "Update docs that have verified discrepancies" "$retro_claude"

  assert_string_not_contains "/bmad-bmm-" "$auto_claude"
  assert_string_not_contains "/bmad-tea-" "$auto_claude"
  assert_string_not_contains "_bmad/bmm/4-implementation" "$auto_codex"
  assert_string_not_contains "_bmad/bmm/workflows/4-implementation" "$auto_codex"
}

verify_qa_prompts_absent() {
  local root="$1"
  local story_dir="$root/.claude/skills/bmad-story-automator"
  local auto_claude

  auto_claude="$(cd "$root" && "$story_dir/scripts/story-automator" tmux-wrapper build-cmd auto 5.3 --agent claude)"
  assert_string_not_contains "READ this skill first: .claude/skills/bmad-qa-generate-e2e-tests/SKILL.md" "$auto_claude"
  assert_string_not_contains "READ this workflow file next: .claude/skills/bmad-qa-generate-e2e-tests/workflow.md" "$auto_claude"
  assert_string_not_contains "Validate with: .claude/skills/bmad-qa-generate-e2e-tests/checklist.md" "$auto_claude"
}

verify_legacy_backups() {
  local root="$1"
  compgen -G "$root/_bmad/bmm/4-implementation/bmad-story-automator.backup-*" >/dev/null || {
    echo "Missing current story backup" >&2
    exit 1
  }
  compgen -G "$root/_bmad/bmm/4-implementation/bmad-story-automator-review.backup-*" >/dev/null || {
    echo "Missing current review backup" >&2
    exit 1
  }
  compgen -G "$root/_bmad/bmm/workflows/4-implementation/story-automator.backup-*" >/dev/null || {
    echo "Missing legacy story backup" >&2
    exit 1
  }
  compgen -G "$root/_bmad/bmm/workflows/4-implementation/story-automator-review.backup-*" >/dev/null || {
    echo "Missing legacy review backup" >&2
    exit 1
  }
}

pack_fixture_tarball() {
  PACK_TARBALL="$(cd "$ROOT_DIR" && npm pack --silent)"
  PACK_TARBALL="$ROOT_DIR/$PACK_TARBALL"
  [ -f "$PACK_TARBALL" ] || {
    echo "Missing packed tarball: $PACK_TARBALL" >&2
    exit 1
  }
}

run_case() {
  local name="$1"
  local qa="$2"
  local legacy="$3"
  local deps_mode="${4:-full}"
  local story_wrapper_mode="${5:-legacy}"
  local root="$TMP_DIR/$name"

  make_fixture "$root" "$qa" "$legacy" "$deps_mode" "$story_wrapper_mode"
  npx --yes --package "file:$PACK_TARBALL" bmad-story-automator "$root" >/dev/null
  if [ "$story_wrapper_mode" = "repointed" ]; then
    verify_common_install "$root" preserved
  else
    verify_common_install "$root"
  fi

  if [ "$qa" = "yes" ] || [ "$qa" = "full" ]; then
    verify_qa_prompts "$root"
  fi

  if [ "$legacy" = "yes" ]; then
    verify_legacy_backups "$root"
  fi
}

run_failure_case() {
  local name="$1"
  local deps_mode="$2"
  local expected_error="$3"
  local root="$TMP_DIR/$name"
  local install_log="$root/install.log"

  make_fixture "$root" no no "$deps_mode" legacy
  if npx --yes --package "file:$PACK_TARBALL" bmad-story-automator "$root" >"$install_log" 2>&1; then
    echo "Expected install failure for dependency fixture: $name" >&2
    exit 1
  fi
  assert_contains "$expected_error" "$install_log"
}

run_optional_qa_partial_case() {
  local name="$1"
  local qa_mode="$2"
  local root="$TMP_DIR/$name"
  local install_log="$root/install.log"

  make_fixture "$root" "$qa_mode" no full legacy
  npx --yes --package "file:$PACK_TARBALL" bmad-story-automator "$root" >"$install_log" 2>&1
  verify_common_install "$root"
  verify_qa_prompts_absent "$root"
  assert_contains "Optional skill incomplete: .claude/skills/bmad-qa-generate-e2e-tests requires both SKILL.md and workflow.md|workflow.yaml." "$install_log"
  assert_not_contains "qa-generate-e2e-tests:" "$install_log"
}

pack_fixture_tarball
run_case pure-with-qa yes no
run_case pure-without-qa no no
run_case pure-migrates-legacy yes yes
run_case repointed-wrapper-survives yes no full repointed
run_failure_case workflow-only-deps workflow-only "Required skill file missing: .claude/skills/bmad-create-story/SKILL.md"
run_failure_case skill-only-deps skill-only "Required skill workflow missing: .claude/skills/bmad-create-story/workflow.md"
run_optional_qa_partial_case partial-qa-workflow-only workflow-only
run_optional_qa_partial_case partial-qa-skill-only skill-only

echo "smoke ok"
