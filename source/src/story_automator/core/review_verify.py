from __future__ import annotations

from pathlib import Path

from .frontmatter import find_frontmatter_value_case
from .sprint import sprint_status_get
from .story_keys import normalize_story_key


def verify_code_review_completion(project_root: str, story_key: str) -> dict[str, object]:
    norm = normalize_story_key(project_root, story_key)
    if norm is None:
        return {"verified": False, "reason": "could_not_normalize_key", "input": story_key}
    status = sprint_status_get(project_root, norm.id)
    if status.done:
        return {"verified": True, "story": norm.key, "sprint_status": "done", "source": "sprint-status.yaml"}
    matches = sorted((Path(project_root) / "_bmad-output" / "implementation-artifacts").glob(f"{norm.prefix}-*.md"))
    story_status = find_frontmatter_value_case(matches[0], "Status") if matches else ""
    if story_status == "done":
        return {
            "verified": True,
            "story": norm.key,
            "sprint_status": status.status,
            "story_file_status": "done",
            "source": "story-file",
            "note": "sprint_status_not_updated",
        }
    return {
        "verified": False,
        "story": norm.key,
        "sprint_status": status.status,
        "story_file_status": story_status or "unknown",
        "reason": "workflow_not_complete",
    }
