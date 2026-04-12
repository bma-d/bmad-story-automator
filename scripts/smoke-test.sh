#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/bmad-story-automator-smoke.XXXXXX")"

cleanup() {
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

make_fixture() {
  local root="$1"
  local qa="$2"
  local legacy="$3"

  mkdir -p "$root/_bmad" "$root/.claude/commands"
  make_required_skills "$root"

  if [ "$qa" = "yes" ]; then
    make_qa_skill "$root"
  fi

  if [ "$legacy" = "yes" ]; then
    make_legacy_story_automator_dirs "$root"
  fi

  printf 'legacy py wrapper\n' >"$root/.claude/commands/bmad-bmm-story-automator-py.md"
  printf 'old story wrapper _bmad/bmm/4-implementation/bmad-story-automator/workflow.md\n' >"$root/.claude/commands/bmad-bmm-story-automator.md"
  printf 'old review wrapper _bmad/bmm/workflows/4-implementation/story-automator-review/workflow.yaml\n' >"$root/.claude/commands/bmad-bmm-story-automator-review.md"
}

verify_common_install() {
  local root="$1"
  local story_dir="$root/.claude/skills/bmad-story-automator"
  local review_dir="$root/.claude/skills/bmad-story-automator-review"

  assert_dir "$story_dir"
  assert_dir "$review_dir"
  assert_file "$story_dir/SKILL.md"
  assert_file "$story_dir/workflow.md"
  assert_file "$story_dir/scripts/story-automator"
  assert_file "$story_dir/src/story_automator/cli.py"
  assert_file "$story_dir/pyproject.toml"
  assert_file "$story_dir/README.md"
  assert_file "$review_dir/SKILL.md"
  assert_file "$review_dir/instructions.xml"
  assert_contains "name: bmad-story-automator" "$story_dir/SKILL.md"
  assert_contains "Follow the instructions in ./workflow.md." "$story_dir/SKILL.md"

  (
    cd "$root"
    "$story_dir/scripts/story-automator" --help >/dev/null
  )

  assert_not_exists "$root/.claude/commands/bmad-bmm-story-automator-py.md"
  assert_not_exists "$root/.claude/commands/bmad-bmm-story-automator.md"
  assert_not_exists "$root/.claude/commands/bmad-bmm-story-automator-review.md"
  assert_not_exists "$root/.claude/commands/bmad-bmm-create-story.md"
  assert_not_exists "$root/.claude/commands/bmad-bmm-dev-story.md"
  assert_not_exists "$root/.claude/commands/bmad-bmm-retrospective.md"
  assert_not_exists "$root/.claude/commands/bmad-bmm-qa-generate-e2e-tests.md"
  assert_not_exists "$root/.claude/commands/bmad-tea-testarch-automate.md"
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
  assert_string_contains "codex exec --full-auto" "$auto_codex"
  assert_string_contains "READ this skill first: .claude/skills/bmad-qa-generate-e2e-tests/SKILL.md" "$auto_codex"
  assert_string_contains "READ this skill first: .claude/skills/bmad-story-automator-review/SKILL.md" "$review_claude"
  assert_string_contains "auto-fix all issues without prompting" "$review_claude"
  assert_string_contains "READ this skill first: .claude/skills/bmad-retrospective/SKILL.md" "$retro_claude"

  assert_string_not_contains "/bmad-bmm-" "$auto_claude"
  assert_string_not_contains "/bmad-tea-" "$auto_claude"
  assert_string_not_contains "_bmad/bmm/4-implementation" "$auto_codex"
  assert_string_not_contains "_bmad/bmm/workflows/4-implementation" "$auto_codex"
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

run_case() {
  local name="$1"
  local qa="$2"
  local legacy="$3"
  local root="$TMP_DIR/$name"

  make_fixture "$root" "$qa" "$legacy"
  npx --yes --package "file:$ROOT_DIR" bmad-story-automator "$root" >/dev/null
  verify_common_install "$root"

  if [ "$qa" = "yes" ]; then
    verify_qa_prompts "$root"
  fi

  if [ "$legacy" = "yes" ]; then
    verify_legacy_backups "$root"
  fi
}

run_case pure-with-qa yes no
run_case pure-without-qa no no
run_case pure-migrates-legacy yes yes

echo "smoke ok"
