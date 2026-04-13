from __future__ import annotations

import json
import os
from pathlib import Path

from story_automator.core.runtime_policy import PolicyError
from story_automator.core.success_verifiers import create_story_artifact, resolve_success_contract


def cmd_validate_story_creation(args: list[str]) -> int:
    action = args[0] if args else ""
    rest = args[1:] if args else []
    project_root = os.environ.get("PROJECT_ROOT", os.getcwd())
    artifacts_dir = Path(project_root) / "_bmad-output" / "implementation-artifacts"

    def story_prefix(story_id: str) -> str:
        return story_id.replace(".", "-")

    def count_files(story_id: str, folder: Path) -> int:
        return len(list(folder.glob(f"{story_prefix(story_id)}-*.md")))

    def check_usage() -> int:
        print(
            "Usage: validate-story-creation check <story_id> [--state-file PATH] [--before N --after N]",
            file=os.sys.stderr,
        )
        return 1

    def create_check_payload(story_id: str, state_file: str) -> dict[str, object]:
        contract = resolve_success_contract(project_root, "create", state_file=state_file or None)
        payload = create_story_artifact(project_root=project_root, story_key=story_id, contract=contract)
        expected = int(payload.get("expectedMatches", 1) or 1)
        actual = int(payload.get("actualMatches", 0) or 0)
        valid = bool(payload.get("verified"))
        if valid:
            reason = "Exactly 1 story file created as expected" if expected == 1 else f"Exactly {expected} story files created as expected"
        elif actual == 0:
            reason = "No story file created - session may have failed"
        elif actual > expected:
            reason = f"RUNAWAY CREATION: {actual} files created instead of {expected}"
        else:
            reason = f"Unexpected story artifact count: {actual} files instead of {expected}"
        response: dict[str, object] = {
            "valid": valid,
            "verified": valid,
            "created_count": actual,
            "expected": expected,
            "prefix": story_prefix(story_id),
            "action": "proceed" if valid else "escalate",
            "reason": reason,
            "source": payload.get("source", ""),
            "pattern": payload.get("pattern", ""),
            "matches": payload.get("matches", []),
        }
        if payload.get("story"):
            response["story"] = payload["story"]
        return response

    if action == "count":
        if not rest:
            print("Usage: validate-story-creation count <story_id>", file=os.sys.stderr)
            return 1
        story_id = rest[0]
        for idx, arg in enumerate(rest[1:]):
            if arg == "--artifacts-dir" and idx + 2 < len(rest):
                artifacts_dir = Path(rest[idx + 2])
        print(count_files(story_id, artifacts_dir))
        return 0

    if action == "check":
        if not rest:
            return check_usage()
        story_id = rest[0]
        state_file = ""
        before = after = ""
        idx = 1
        while idx < len(rest):
            if rest[idx] == "--before" and idx + 1 < len(rest):
                before = rest[idx + 1]
                idx += 2
                continue
            if rest[idx] == "--after" and idx + 1 < len(rest):
                after = rest[idx + 1]
                idx += 2
                continue
            if rest[idx] == "--artifacts-dir" and idx + 1 < len(rest):
                artifacts_dir = Path(rest[idx + 1])
                idx += 2
                continue
            if rest[idx] == "--state-file" and idx + 1 < len(rest):
                state_file = rest[idx + 1]
                idx += 2
                continue
            idx += 1
        if artifacts_dir != Path(project_root) / "_bmad-output" / "implementation-artifacts":
            print("validate-story-creation check no longer supports --artifacts-dir overrides; use count/list for custom folders", file=os.sys.stderr)
            return 1
        try:
            payload = create_check_payload(story_id, state_file)
        except (PolicyError, ValueError) as exc:
            print(json.dumps({"valid": False, "verified": False, "action": "escalate", "reason": str(exc)}, separators=(",", ":")))
            return 1
        if before:
            payload["before"] = before
        if after:
            payload["after"] = after
        print(json.dumps(payload, separators=(",", ":")))
        return 0

    if action == "list":
        if not rest:
            print("Usage: validate-story-creation list <story_id>", file=os.sys.stderr)
            return 1
        story_id = rest[0]
        print(f"Story files matching {story_prefix(story_id)}-*.md:")
        matches = list(artifacts_dir.glob(f"{story_prefix(story_id)}-*.md"))
        if not matches:
            print("  (none found)")
            return 0
        for match in matches:
            info = match.stat()
            print(f"-rw-r--r-- 1 {info.st_mode} {info.st_size} {match}")
        return 0

    if action == "prefix":
        if not rest:
            return 1
        print(story_prefix(rest[0]))
        return 0

    if action and len(rest) >= 2 and rest[0].isdigit() and rest[1].isdigit():
        return cmd_validate_story_creation(["check", action, "--before", rest[0], "--after", rest[1]])

    print("Usage: validate-story-creation <action> [args]", file=os.sys.stderr)
    print("", file=os.sys.stderr)
    print("Actions:", file=os.sys.stderr)
    print("  count <story_id>              - Count current story files", file=os.sys.stderr)
    print("  check <story_id> [--state-file PATH]   - Compatibility wrapper for create verifier", file=os.sys.stderr)
    print("  list <story_id>               - List matching files", file=os.sys.stderr)
    print("  prefix <story_id>             - Convert story ID to file prefix", file=os.sys.stderr)
    return 1
