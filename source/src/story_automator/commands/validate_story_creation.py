from __future__ import annotations

import os
from pathlib import Path


def cmd_validate_story_creation(args: list[str]) -> int:
    action = args[0] if args else ""
    rest = args[1:] if args else []
    project_root = os.environ.get("PROJECT_ROOT", os.getcwd())
    artifacts_dir = Path(project_root) / "_bmad-output" / "implementation-artifacts"

    def story_prefix(story_id: str) -> str:
        return story_id.replace(".", "-")

    def count_files(story_id: str, folder: Path) -> int:
        return len(list(folder.glob(f"{story_prefix(story_id)}-*.md")))

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
            print("Usage: validate-story-creation check <story_id> --before N --after N", file=os.sys.stderr)
            return 1
        story_id = rest[0]
        before = after = None
        idx = 1
        while idx < len(rest):
            if rest[idx] == "--before" and idx + 1 < len(rest):
                before = int(rest[idx + 1])
                idx += 2
                continue
            if rest[idx] == "--after" and idx + 1 < len(rest):
                after = int(rest[idx + 1])
                idx += 2
                continue
            if rest[idx] == "--artifacts-dir" and idx + 1 < len(rest):
                artifacts_dir = Path(rest[idx + 1])
                idx += 2
                continue
            idx += 1
        if before is None or after is None:
            print("Usage: validate-story-creation check <story_id> --before N --after N", file=os.sys.stderr)
            return 1
        created = after - before
        valid = created == 1
        reason = (
            "Exactly 1 story file created as expected"
            if created == 1
            else "No story file created - session may have failed"
            if created == 0
            else f"Story files decreased ({created}) - unexpected deletion"
            if created < 0
            else f"RUNAWAY CREATION: {created} files created instead of 1"
        )
        action_name = "proceed" if valid else "escalate"
        print(
            f'{{"valid":{str(valid).lower()},"created_count":{created},"expected":1,'
            f'"before":{before},"after":{after},"prefix":"{story_prefix(story_id)}",'
            f'"action":"{action_name}","reason":"{reason}"}}'
        )
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
    print("  check <story_id> --before N --after N  - Validate creation", file=os.sys.stderr)
    print("  list <story_id>               - List matching files", file=os.sys.stderr)
    print("  prefix <story_id>             - Convert story ID to file prefix", file=os.sys.stderr)
    return 1
