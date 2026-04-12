#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<'EOF'
Usage: ./install.sh <bmad-project-root>

Installs the portable payload bundle into:
  .claude/skills/bmad-story-automator
  .claude/skills/bmad-story-automator-review

The Python helper runtime is installed inside:
  .claude/skills/bmad-story-automator/scripts/story-automator
EOF
}

err() {
  echo "Error: $*" >&2
  exit 1
}

warn() {
  echo "Warn: $*" >&2
}

resolve_abs_dir() {
  local input="$1"
  [ -d "$input" ] || err "Directory not found: $input"
  cd "$input" >/dev/null 2>&1 && pwd
}

skill_file() {
  local skill_name="$1"
  printf '.claude/skills/%s/SKILL.md\n' "$skill_name"
}

backup_if_exists() {
  local path="$1"
  if [ -e "$path" ]; then
    local backup="${path}.backup-$(date -u +%Y%m%dT%H%M%SZ)"
    mv "$path" "$backup"
    echo "Backup: ${backup#$TARGET_ROOT/}"
  fi
}

backup_legacy_story_automator_installs() {
  local legacy_path
  local legacy_paths=(
    "$TARGET_ROOT/_bmad/bmm/4-implementation/bmad-story-automator"
    "$TARGET_ROOT/_bmad/bmm/4-implementation/story-automator"
    "$TARGET_ROOT/_bmad/bmm/4-implementation/story-automator-py"
    "$TARGET_ROOT/_bmad/bmm/4-implementation/bmad-story-automator-review"
    "$TARGET_ROOT/_bmad/bmm/4-implementation/story-automator-review"
    "$TARGET_ROOT/_bmad/bmm/workflows/4-implementation/bmad-story-automator"
    "$TARGET_ROOT/_bmad/bmm/workflows/4-implementation/story-automator"
    "$TARGET_ROOT/_bmad/bmm/workflows/4-implementation/bmad-story-automator-review"
    "$TARGET_ROOT/_bmad/bmm/workflows/4-implementation/story-automator-review"
  )

  for legacy_path in "${legacy_paths[@]}"; do
    backup_if_exists "$legacy_path"
  done
}

wrapper_points_to_skill_tree() {
  local shim="$1"
  grep -Eq '\.claude/skills/' "$shim"
}

wrapper_points_to_legacy_target() {
  local shim="$1"
  grep -Eq '_bmad/bmm/(4-implementation|workflows/4-implementation)|_bmad/tea/|/bmad-bmm-|/bmad-tea-' "$shim"
}

remove_obsolete_command_shim_if_legacy() {
  local shim="$1"
  [ -f "$shim" ] || return 0
  if wrapper_points_to_skill_tree "$shim"; then
    return 0
  fi
  if wrapper_points_to_legacy_target "$shim"; then
    rm -f "$shim"
    echo "Removed obsolete command shim: ${shim#$TARGET_ROOT/}"
  fi
}

cleanup_obsolete_command_shims() {
  local command_dir="$TARGET_ROOT/.claude/commands"
  local shim

  rm -f "$command_dir/bmad-bmm-story-automator-py.md"

  for shim in \
    "$command_dir/bmad-bmm-story-automator.md" \
    "$command_dir/bmad-bmm-story-automator-review.md" \
    "$command_dir/bmad-bmm-create-story.md" \
    "$command_dir/bmad-bmm-dev-story.md" \
    "$command_dir/bmad-bmm-retrospective.md" \
    "$command_dir/bmad-bmm-qa-generate-e2e-tests.md" \
    "$command_dir/bmad-tea-testarch-automate.md"; do
    remove_obsolete_command_shim_if_legacy "$shim"
  done
}

resolve_workflow_path() {
  local candidate
  for candidate in "$@"; do
    if [ -f "$TARGET_ROOT/$candidate" ]; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

resolve_required_skill_workflow() {
  local skill_name="$1"
  local skill_path
  local workflow_path
  skill_path="$(skill_file "$skill_name")"
  [ -f "$TARGET_ROOT/$skill_path" ] || err "Required skill file missing: $skill_path"
  workflow_path="$(resolve_workflow_path \
    ".claude/skills/$skill_name/workflow.md" \
    ".claude/skills/$skill_name/workflow.yaml")" \
    || err "Required skill workflow missing: .claude/skills/$skill_name/workflow.md"
  printf '%s\n' "$workflow_path"
}

resolve_optional_skill_workflow() {
  local skill_name="$1"
  local skill_path
  local workflow_path=""
  local has_skill=0
  local has_workflow=0

  skill_path="$(skill_file "$skill_name")"
  if [ -f "$TARGET_ROOT/$skill_path" ]; then
    has_skill=1
  fi
  if workflow_path="$(resolve_workflow_path \
    ".claude/skills/$skill_name/workflow.md" \
    ".claude/skills/$skill_name/workflow.yaml")"; then
    has_workflow=1
  fi

  if [ "$has_skill" -eq 1 ] && [ "$has_workflow" -eq 1 ]; then
    printf '%s\n' "$workflow_path"
    return 0
  fi

  if [ "$has_skill" -eq 1 ] || [ "$has_workflow" -eq 1 ]; then
    warn "Optional skill incomplete: .claude/skills/$skill_name requires both SKILL.md and workflow.md|workflow.yaml. Story-automator still installs, but run with 'Skip Automate' enabled unless you fix that skill."
  fi
  return 1
}

if [ $# -ne 1 ]; then
  usage
  exit 1
fi

TARGET_ROOT="$(resolve_abs_dir "$1")"
TARGET_BMAD="$TARGET_ROOT/_bmad"
TARGET_SKILLS="$TARGET_ROOT/.claude/skills"
TARGET_STORY="$TARGET_SKILLS/bmad-story-automator"
TARGET_STORY_REVIEW="$TARGET_SKILLS/bmad-story-automator-review"
CREATE_STORY_SKILL="$(skill_file "bmad-create-story")"
DEV_STORY_SKILL="$(skill_file "bmad-dev-story")"
RETROSPECTIVE_SKILL="$(skill_file "bmad-retrospective")"
OPTIONAL_AUTOMATE_SKILL="$(skill_file "bmad-qa-generate-e2e-tests")"
PAYLOAD_ROOT="$SCRIPT_DIR/payload"
STORY_PAYLOAD="$PAYLOAD_ROOT/.claude/skills/bmad-story-automator"
STORY_REVIEW_PAYLOAD="$PAYLOAD_ROOT/.claude/skills/bmad-story-automator-review"
SOURCE_ROOT="$SCRIPT_DIR/source"
SOURCE_WRAPPER="$SOURCE_ROOT/scripts/story-automator"
SOURCE_PACKAGE_DIR="$SOURCE_ROOT/src/story_automator"
SOURCE_PYPROJECT="$SOURCE_ROOT/pyproject.toml"
SOURCE_README="$SOURCE_ROOT/README.md"
SOURCE_LICENSE="$SOURCE_ROOT/LICENSE"

[ -d "$TARGET_BMAD" ] || err "Target is not a BMAD project: missing $TARGET_BMAD"
[ -d "$STORY_PAYLOAD" ] || err "Missing story-automator payload: $STORY_PAYLOAD"
[ -d "$STORY_REVIEW_PAYLOAD" ] || err "Missing story-automator-review payload: $STORY_REVIEW_PAYLOAD"
[ -f "$SOURCE_WRAPPER" ] || err "Missing runtime wrapper: $SOURCE_WRAPPER"
[ -d "$SOURCE_PACKAGE_DIR" ] || err "Missing runtime package dir: $SOURCE_PACKAGE_DIR"
[ -f "$SOURCE_PYPROJECT" ] || err "Missing runtime pyproject: $SOURCE_PYPROJECT"
[ -f "$SOURCE_README" ] || err "Missing runtime README: $SOURCE_README"
[ -f "$SOURCE_LICENSE" ] || err "Missing runtime license: $SOURCE_LICENSE"

CREATE_STORY_PATH="$(resolve_required_skill_workflow "bmad-create-story")"
DEV_STORY_PATH="$(resolve_required_skill_workflow "bmad-dev-story")"
RETROSPECTIVE_PATH="$(resolve_required_skill_workflow "bmad-retrospective")"

OPTIONAL_AUTOMATE_PATH=""
if ! OPTIONAL_AUTOMATE_PATH="$(resolve_optional_skill_workflow "bmad-qa-generate-e2e-tests")"; then
  if [ ! -f "$TARGET_ROOT/$OPTIONAL_AUTOMATE_SKILL" ]; then
    warn "Optional skill not found: .claude/skills/bmad-qa-generate-e2e-tests. Story-automator still installs, but run with 'Skip Automate' enabled unless you install that skill."
  fi
fi

backup_if_exists "$TARGET_STORY"
backup_if_exists "$TARGET_STORY_REVIEW"
backup_legacy_story_automator_installs

mkdir -p "$TARGET_STORY" "$TARGET_STORY_REVIEW"
cp -a "$STORY_PAYLOAD"/. "$TARGET_STORY"/
cp -a "$STORY_REVIEW_PAYLOAD"/. "$TARGET_STORY_REVIEW"/

cp -a "$SOURCE_PYPROJECT" "$TARGET_STORY/pyproject.toml"
cp -a "$SOURCE_README" "$TARGET_STORY/README.md"
cp -a "$SOURCE_LICENSE" "$TARGET_STORY/LICENSE"
mkdir -p "$TARGET_STORY/scripts" "$TARGET_STORY/src"
cp -a "$SOURCE_ROOT/scripts"/. "$TARGET_STORY/scripts"/
cp -a "$SOURCE_ROOT/src"/. "$TARGET_STORY/src"/
chmod +x "$TARGET_STORY/scripts/story-automator"

cleanup_obsolete_command_shims

echo "Installed story-automator skill into: $TARGET_STORY"
echo "Installed story-automator-review skill into: $TARGET_STORY_REVIEW"
echo "Runtime helper: $TARGET_STORY/scripts/story-automator"
echo "Verified dependency skill entrypoints:"
echo "  create-story: $CREATE_STORY_SKILL + $CREATE_STORY_PATH"
echo "  dev-story: $DEV_STORY_SKILL + $DEV_STORY_PATH"
echo "  retrospective: $RETROSPECTIVE_SKILL + $RETROSPECTIVE_PATH"
if [ -n "$OPTIONAL_AUTOMATE_PATH" ]; then
  echo "  qa-generate-e2e-tests: $OPTIONAL_AUTOMATE_SKILL + $OPTIONAL_AUTOMATE_PATH"
fi
echo "Claude command wrappers are not generated; invoke the bmad-story-automator skill directly."
