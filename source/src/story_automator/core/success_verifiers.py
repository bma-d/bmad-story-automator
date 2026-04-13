from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .frontmatter import find_frontmatter_value_case
from .runtime_policy import PolicyError, load_runtime_policy, step_contract
from .sprint import sprint_status_epic, sprint_status_get
from .story_keys import normalize_story_key
from .utils import read_text

ALLOWED_REVIEW_CONTRACT_KEYS = {"blockingSeverity", "doneValues", "inProgressValues", "sourceOrder", "syncSprintStatus"}
ALLOWED_REVIEW_SOURCES = {"sprint-status.yaml", "story-file"}
DEFAULT_REVIEW_CONTRACT = {
    "blockingSeverity": ["critical"],
    "doneValues": ["done"],
    "inProgressValues": ["in-progress", "in_progress", "review", "qa"],
    "sourceOrder": ["sprint-status.yaml", "story-file"],
    "syncSprintStatus": True,
}


def resolve_success_contract(project_root: str, step: str, *, state_file: str | Path | None = None) -> dict[str, Any]:
    policy = load_runtime_policy(project_root, state_file=state_file)
    success = step_contract(policy, step).get("success") or {}
    if not isinstance(success, dict):
        raise PolicyError(f"invalid success contract for {step}")
    return success


def run_success_verifier(
    name: str,
    *,
    project_root: str,
    story_key: str = "",
    output_file: str = "",
    contract: dict[str, Any] | None = None,
) -> dict[str, object]:
    verifier = VERIFIERS.get(name)
    if verifier is None:
        raise PolicyError(f"unknown success verifier: {name}")
    return verifier(project_root=project_root, story_key=story_key, output_file=output_file, contract=contract or {})


def session_exit(
    *,
    project_root: str,
    story_key: str = "",
    output_file: str = "",
    contract: dict[str, Any] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {"verified": True, "source": "session_exit"}
    if story_key:
        payload["story"] = story_key
    if output_file:
        payload["outputFile"] = output_file
    return payload


def create_story_artifact(
    *,
    project_root: str,
    story_key: str,
    output_file: str = "",
    contract: dict[str, Any] | None = None,
) -> dict[str, object]:
    norm = normalize_story_key(project_root, story_key)
    if norm is None:
        return {"verified": False, "reason": "could_not_normalize_key", "input": story_key}
    config = _success_config(contract)
    raw_glob = str(config.get("glob") or "_bmad-output/implementation-artifacts/{story_prefix}-*.md")
    expected = int(config.get("expectedMatches", 1))
    pattern = _format_story_pattern(raw_glob, norm)
    matches = sorted(Path(project_root).glob(pattern))
    payload: dict[str, object] = {
        "verified": len(matches) == expected,
        "story": norm.key,
        "source": "artifact_glob",
        "pattern": pattern,
        "expectedMatches": expected,
        "actualMatches": len(matches),
        "matches": [str(match) for match in matches],
    }
    if not bool(payload["verified"]):
        payload["reason"] = "unexpected_story_artifact_count"
    return payload


def review_completion(
    *,
    project_root: str,
    story_key: str,
    output_file: str = "",
    contract: dict[str, Any] | None = None,
) -> dict[str, object]:
    norm = normalize_story_key(project_root, story_key)
    if norm is None:
        return {"verified": False, "reason": "could_not_normalize_key", "input": story_key}
    review_contract = _load_review_contract(project_root, contract or {})
    done_values = {value.lower() for value in review_contract["doneValues"]}
    sprint = sprint_status_get(project_root, norm.id)
    story_file = _story_artifact_path(project_root, norm.prefix)
    story_status = find_frontmatter_value_case(story_file, "Status") if story_file else ""
    for source in review_contract["sourceOrder"]:
        if source == "sprint-status.yaml" and sprint.status.lower() in done_values:
            return {
                "verified": True,
                "story": norm.key,
                "sprint_status": sprint.status,
                "story_file_status": story_status or "unknown",
                "source": "sprint-status.yaml",
            }
        if source == "story-file" and story_status.lower() in done_values:
            payload: dict[str, object] = {
                "verified": True,
                "story": norm.key,
                "sprint_status": sprint.status,
                "story_file_status": story_status,
                "source": "story-file",
            }
            if review_contract["syncSprintStatus"] and not sprint.done:
                payload["note"] = "sprint_status_not_updated"
            return payload
    return {
        "verified": False,
        "story": norm.key,
        "sprint_status": sprint.status,
        "story_file_status": story_status or "unknown",
        "reason": "workflow_not_complete",
    }


def epic_complete(
    *,
    project_root: str,
    story_key: str,
    output_file: str = "",
    contract: dict[str, Any] | None = None,
) -> dict[str, object]:
    norm = normalize_story_key(project_root, story_key)
    if norm is None:
        return {"verified": False, "reason": "could_not_normalize_key", "input": story_key}
    epic = norm.id.split(".", 1)[0]
    stories, done = sprint_status_epic(project_root, epic)
    if not stories:
        return {"verified": False, "epic": epic, "reason": "no_stories_found", "source": "sprint-status.yaml"}
    return {
        "verified": done == len(stories),
        "epic": epic,
        "story": norm.key,
        "totalStories": len(stories),
        "doneStories": done,
        "source": "sprint-status.yaml",
        **({} if done == len(stories) else {"reason": "epic_incomplete"}),
    }


def _success_config(contract: dict[str, Any] | None) -> dict[str, Any]:
    config = (contract or {}).get("config") or {}
    if not isinstance(config, dict):
        raise PolicyError("success.config must be an object")
    return config


def _format_story_pattern(pattern: str, story) -> str:
    return (
        pattern.replace("{story_prefix}", story.prefix)
        .replace("{story_id}", story.id)
        .replace("{story_key}", story.key)
    )


def _story_artifact_path(project_root: str, story_prefix: str) -> Path | None:
    matches = sorted((Path(project_root) / "_bmad-output" / "implementation-artifacts").glob(f"{story_prefix}-*.md"))
    return matches[0] if matches else None


def _load_review_contract(project_root: str, contract: dict[str, Any]) -> dict[str, Any]:
    merged = dict(DEFAULT_REVIEW_CONTRACT)
    contract_path = str(contract.get("contractPath") or "").strip()
    if contract_path:
        path = Path(contract_path)
        if not path.is_absolute():
            path = Path(project_root) / path
        try:
            payload = json.loads(read_text(path))
        except json.JSONDecodeError as exc:
            raise PolicyError(f"review contract json invalid: {path}") from exc
        if not isinstance(payload, dict):
            raise PolicyError(f"review contract must be an object: {path}")
        merged.update(payload)
    inline = _inline_review_contract(contract)
    merged.update(inline)
    _validate_review_contract(merged)
    return {
        "blockingSeverity": [str(value).strip() for value in merged["blockingSeverity"] if str(value).strip()],
        "doneValues": [str(value).strip() for value in merged["doneValues"] if str(value).strip()],
        "inProgressValues": [str(value).strip() for value in merged["inProgressValues"] if str(value).strip()],
        "sourceOrder": [str(value).strip() for value in merged["sourceOrder"] if str(value).strip()],
        "syncSprintStatus": bool(merged["syncSprintStatus"]),
    }


def _inline_review_contract(contract: dict[str, Any]) -> dict[str, Any]:
    inline: dict[str, Any] = {}
    config = contract.get("config")
    if isinstance(config, dict):
        for key in ALLOWED_REVIEW_CONTRACT_KEYS:
            if key in config:
                inline[key] = config[key]
    for key in ALLOWED_REVIEW_CONTRACT_KEYS:
        if key in contract:
            inline[key] = contract[key]
    return inline


def _validate_review_contract(contract: dict[str, Any]) -> None:
    unknown_keys = sorted(set(contract) - ALLOWED_REVIEW_CONTRACT_KEYS)
    if unknown_keys:
        raise PolicyError(f"unknown review contract keys: {', '.join(unknown_keys)}")
    for key in ("blockingSeverity", "doneValues", "inProgressValues", "sourceOrder"):
        values = contract.get(key)
        if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
            raise PolicyError(f"review contract {key} must be a string array")
    if not isinstance(contract.get("syncSprintStatus"), bool):
        raise PolicyError("review contract syncSprintStatus must be a boolean")
    invalid_sources = sorted({value for value in contract["sourceOrder"] if value not in ALLOWED_REVIEW_SOURCES})
    if invalid_sources:
        raise PolicyError(f"review contract sourceOrder contains unknown sources: {', '.join(invalid_sources)}")


VerifierFn = Callable[..., dict[str, object]]

VERIFIERS: dict[str, VerifierFn] = {
    "create_story_artifact": create_story_artifact,
    "session_exit": session_exit,
    "review_completion": review_completion,
    "epic_complete": epic_complete,
}
