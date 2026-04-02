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

assert_equals() {
  local expected="$1"
  local actual="$2"
  [ "$expected" = "$actual" ] || {
    echo "Expected '$expected' got '$actual'" >&2
    exit 1
  }
}

make_required_workflows() {
  local root="$1"
  local layout="$2"

  if [ "$layout" = "current" ]; then
    mkdir -p \
      "$root/_bmad/bmm/4-implementation/bmad-create-story" \
      "$root/_bmad/bmm/4-implementation/bmad-dev-story" \
      "$root/_bmad/bmm/4-implementation/bmad-retrospective"
    printf '# create-story\n' >"$root/_bmad/bmm/4-implementation/bmad-create-story/workflow.md"
    printf '# dev-story\n' >"$root/_bmad/bmm/4-implementation/bmad-dev-story/workflow.md"
    printf '# retrospective\n' >"$root/_bmad/bmm/4-implementation/bmad-retrospective/workflow.md"
    return 0
  fi

  mkdir -p \
    "$root/_bmad/bmm/workflows/4-implementation/create-story" \
    "$root/_bmad/bmm/workflows/4-implementation/dev-story" \
    "$root/_bmad/bmm/workflows/4-implementation/retrospective"
  printf '# create-story\n' >"$root/_bmad/bmm/workflows/4-implementation/create-story/workflow.md"
  printf '# dev-story\n' >"$root/_bmad/bmm/workflows/4-implementation/dev-story/workflow.md"
  printf '# retrospective\n' >"$root/_bmad/bmm/workflows/4-implementation/retrospective/workflow.md"
}

make_fixture() {
  local root="$1"
  local layout="$2"
  local mode="$3"
  local automate="$4"

  mkdir -p "$root/.claude/commands" "$root/_bmad"
  if [ "$mode" = "workflow-xml" ]; then
    mkdir -p "$root/_bmad/core/tasks"
    printf '<workflow />\n' >"$root/_bmad/core/tasks/workflow.xml"
  fi

  if [ "$layout" = "current" ]; then
    mkdir -p "$root/_bmad/bmm/4-implementation"
  else
    mkdir -p "$root/_bmad/bmm/workflows/4-implementation"
  fi

  make_required_workflows "$root" "$layout"

  if [ "$automate" = "yes" ]; then
    mkdir -p "$root/_bmad/tea/4-implementation/bmad-testarch-automate"
    printf '# automate\n' >"$root/_bmad/tea/4-implementation/bmad-testarch-automate/workflow.md"
  fi
}

verify_install() {
  local root="$1"
  local layout="$2"
  local mode="$3"
  local automate="$4"

  local impl_root story_dir review_dir
  if [ "$layout" = "current" ]; then
    impl_root="$root/_bmad/bmm/4-implementation"
    story_dir="$impl_root/bmad-story-automator"
    review_dir="$impl_root/bmad-story-automator-review"
  else
    impl_root="$root/_bmad/bmm/workflows/4-implementation"
    story_dir="$impl_root/story-automator"
    review_dir="$impl_root/story-automator-review"
  fi

  assert_dir "$story_dir"
  assert_dir "$review_dir"
  assert_file "$story_dir/bin/story-automator"
  assert_file "$story_dir/src/story_automator/cli.py"
  assert_file "$story_dir/pyproject.toml"
  assert_file "$story_dir/README.md"
  assert_file "$review_dir/instructions.xml"

  "$story_dir/bin/story-automator" --help >/dev/null

  assert_file "$root/.claude/commands/bmad-bmm-story-automator.md"
  assert_file "$root/.claude/commands/bmad-bmm-dev-story.md"
  assert_file "$root/.claude/commands/bmad-bmm-story-automator-review.md"
  assert_file "$root/.claude/commands/bmad-bmm-retrospective.md"

  local create_cmd="$root/.claude/commands/bmad-bmm-create-story.md"
  assert_file "$create_cmd"
  if [ "$layout" = "current" ]; then
    assert_equals "sentinel create command" "$(cat "$create_cmd")"
  fi

  if [ "$mode" = "workflow-xml" ]; then
    assert_contains "@{project-root}/_bmad/core/tasks/workflow.xml" "$root/.claude/commands/bmad-bmm-story-automator.md"
  else
    assert_contains "Always LOAD the FULL @{project-root}/_bmad/bmm/workflows/4-implementation/story-automator/workflow.md" "$root/.claude/commands/bmad-bmm-story-automator.md"
  fi

  if [ "$automate" = "yes" ]; then
    assert_file "$root/.claude/commands/bmad-tea-testarch-automate.md"
  else
    [ ! -e "$root/.claude/commands/bmad-tea-testarch-automate.md" ] || {
      echo "Unexpected automate command wrapper" >&2
      exit 1
    }
  fi

  [ ! -e "$root/.claude/commands/bmad-bmm-story-automator-py.md" ] || {
    echo "Legacy command wrapper should be removed" >&2
    exit 1
  }
}

run_case() {
  local name="$1"
  local layout="$2"
  local mode="$3"
  local automate="$4"
  local root="$TMP_DIR/$name"

  make_fixture "$root" "$layout" "$mode" "$automate"
  printf 'legacy wrapper\n' >"$root/.claude/commands/bmad-bmm-story-automator-py.md"
  if [ "$layout" = "current" ]; then
    printf 'sentinel create command' >"$root/.claude/commands/bmad-bmm-create-story.md"
  fi

  npx --yes --package "file:$ROOT_DIR" bmad-story-automator "$root" >/dev/null
  verify_install "$root" "$layout" "$mode" "$automate"
}

run_case current current workflow-xml yes
run_case legacy legacy direct no

echo "smoke ok"
