from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .frontmatter import parse_simple_frontmatter
from .utils import ensure_dir, get_project_root, iso_now, md5_hex8, read_text, write_atomic

VALID_TOP_LEVEL_KEYS = {"version", "snapshot", "runtime", "workflow", "steps"}
VALID_STEP_NAMES = {"create", "dev", "auto", "review", "retro"}
VALID_VERIFIERS = {"create_story_artifact", "session_exit", "review_completion", "epic_complete"}
VALID_ASSET_NAMES = {"skill", "workflow", "instructions", "checklist", "template"}


class PolicyError(ValueError):
    pass


def load_effective_policy(project_root: str | None = None, *, resolve_assets: bool = True) -> dict[str, Any]:
    root = Path(project_root or get_project_root()).resolve()
    bundle_root = bundled_skill_root(root)
    bundled = _read_json(bundle_root / "data" / "orchestration-policy.json")
    override_path = root / "_bmad" / "bmm" / "story-automator.policy.json"
    override = _read_json(override_path) if override_path.is_file() else {}
    policy = _deep_merge(bundled, override)
    _apply_legacy_env(policy)
    _validate_policy_shape(policy)
    if resolve_assets:
        _resolve_policy_paths(policy, project_root=root, bundle_root=bundle_root)
    else:
        _resolve_success_paths(policy, project_root=root, bundle_root=bundle_root)
    return policy


def load_runtime_policy(
    project_root: str | None = None,
    state_file: str | Path | None = None,
    *,
    resolve_assets: bool = True,
) -> dict[str, Any]:
    root = Path(project_root or get_project_root()).resolve()
    resolved_state, source = resolve_policy_state_file(root, state_file)
    if resolved_state:
        try:
            return load_policy_for_state(resolved_state, project_root=str(root), resolve_assets=resolve_assets)
        except (FileNotFoundError, PolicyError):
            if source == "explicit":
                raise
    return load_effective_policy(str(root), resolve_assets=resolve_assets)


def snapshot_effective_policy(project_root: str | None = None) -> dict[str, Any]:
    root = Path(project_root or get_project_root()).resolve()
    policy = load_effective_policy(str(root))
    snapshot_dir = root / _snapshot_relative_dir(policy)
    ensure_dir(snapshot_dir)
    stable_json = _stable_policy_json(policy)
    snapshot_hash = md5_hex8(stable_json)
    stamp = iso_now().replace("-", "").replace(":", "").replace("T", "-").replace("Z", "")
    snapshot_path = snapshot_dir / f"{stamp}-{snapshot_hash}.json"
    write_atomic(snapshot_path, stable_json)
    return {
        "policy": policy,
        "policyVersion": policy.get("version", 1),
        "policySnapshotHash": snapshot_hash,
        "policySnapshotFile": _display_path(snapshot_path, root),
    }


def load_policy_snapshot(
    snapshot_file: str,
    *,
    project_root: str | None = None,
    expected_hash: str = "",
    resolve_assets: bool = True,
) -> dict[str, Any]:
    root = Path(project_root or get_project_root()).resolve()
    path = Path(snapshot_file)
    if not path.is_absolute():
        path = root / path
    if not path.is_file():
        raise PolicyError(f"policy snapshot missing: {path}")
    raw = read_text(path)
    actual_hash = md5_hex8(raw)
    if expected_hash and actual_hash != expected_hash:
        raise PolicyError(f"policy snapshot hash mismatch: expected {expected_hash}, got {actual_hash}")
    try:
        policy = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PolicyError(f"policy json invalid: {path}") from exc
    _validate_policy_shape(policy)
    if resolve_assets:
        _resolve_policy_paths(policy, project_root=root, bundle_root=bundled_skill_root(root))
    else:
        _resolve_success_paths(policy, project_root=root, bundle_root=bundled_skill_root(root))
    return policy


def load_policy_for_state(
    state_file: str | Path,
    project_root: str | None = None,
    *,
    resolve_assets: bool = True,
) -> dict[str, Any]:
    root = Path(project_root or get_project_root()).resolve()
    fields = parse_simple_frontmatter(read_text(state_file))
    snapshot_file = str(fields.get("policySnapshotFile") or "").strip()
    snapshot_hash = str(fields.get("policySnapshotHash") or "").strip()
    if snapshot_file or snapshot_hash:
        if not snapshot_file or not snapshot_hash:
            raise PolicyError("state policy metadata incomplete")
        return load_policy_snapshot(
            snapshot_file,
            project_root=str(root),
            expected_hash=snapshot_hash,
            resolve_assets=resolve_assets,
        )
    return load_effective_policy(str(root), resolve_assets=resolve_assets)


def resolve_policy_state_file(project_root: str | Path | None = None, state_file: str | Path | None = None) -> tuple[str, str]:
    root = Path(project_root or get_project_root()).resolve()
    explicit = Path(state_file).expanduser() if state_file else None
    if explicit:
        return str(_resolve_state_path(root, explicit)), "explicit"
    env_state = os.environ.get("STORY_AUTOMATOR_STATE_FILE", "").strip()
    if env_state:
        return str(_resolve_state_path(root, Path(env_state).expanduser())), "env"
    marker = root / ".claude" / ".story-automator-active"
    if marker.is_file():
        try:
            payload = _read_json(marker)
        except PolicyError:
            return "", ""
        marker_state = str(payload.get("stateFile") or "").strip()
        if marker_state:
            return str(_resolve_state_path(root, Path(marker_state).expanduser())), "marker"
    return "", ""


def step_contract(policy: dict[str, Any], step: str) -> dict[str, Any]:
    contract = (policy.get("steps") or {}).get(step)
    if not isinstance(contract, dict):
        raise PolicyError(f"unknown step: {step}")
    return contract


def review_max_cycles(policy: dict[str, Any]) -> int:
    repeat = ((policy.get("workflow") or {}).get("repeat") or {}).get("review") or {}
    return int(repeat.get("maxCycles", 5))


def crash_max_retries(policy: dict[str, Any]) -> int:
    crash = ((policy.get("workflow") or {}).get("crash")) or {}
    return int(crash.get("maxRetries", 2))


def bundled_skill_root(project_root: str | Path | None = None) -> Path:
    root = Path(project_root or get_project_root()).resolve()
    installed = root / ".claude" / "skills" / "bmad-story-automator"
    if (installed / "data" / "orchestration-policy.json").is_file():
        return installed
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "payload" / ".claude" / "skills" / "bmad-story-automator"
        if (candidate / "data" / "orchestration-policy.json").is_file():
            return candidate
    raise PolicyError("bundled policy not found")


def _read_json(path: str | Path) -> dict[str, Any]:
    try:
        payload = json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        raise PolicyError(f"policy json invalid: {path}") from exc
    if not isinstance(payload, dict):
        raise PolicyError(f"policy json must be an object: {path}")
    return payload


def _deep_merge(base: Any, override: Any) -> Any:
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for key, value in override.items():
            merged[key] = _deep_merge(merged[key], value) if key in merged else value
        return merged
    if isinstance(override, list):
        return list(override)
    return override


def _apply_legacy_env(policy: dict[str, Any]) -> None:
    review_cycles = os.environ.get("MAX_REVIEW_CYCLES")
    crash_retries = os.environ.get("MAX_CRASH_RETRIES")
    if review_cycles:
        policy.setdefault("workflow", {}).setdefault("repeat", {}).setdefault("review", {})["maxCycles"] = int(review_cycles)
    if crash_retries:
        policy.setdefault("workflow", {}).setdefault("crash", {})["maxRetries"] = int(crash_retries)


def _validate_policy_shape(policy: dict[str, Any]) -> None:
    unknown_keys = sorted(set(policy) - VALID_TOP_LEVEL_KEYS)
    if unknown_keys:
        raise PolicyError(f"unknown top-level policy keys: {', '.join(unknown_keys)}")
    snapshot = _expect_optional_dict(policy, "snapshot")
    if "snapshot" in policy and "relativeDir" in snapshot and not isinstance(snapshot.get("relativeDir"), str):
        raise PolicyError("snapshot.relativeDir must be a string")
    workflow = _expect_optional_dict(policy, "workflow")
    repeat = _expect_optional_nested_dict(workflow, "repeat", "workflow")
    review = _expect_optional_nested_dict(repeat, "review", "workflow.repeat")
    crash = _expect_optional_nested_dict(workflow, "crash", "workflow")
    steps = policy.get("steps")
    if not isinstance(steps, dict):
        raise PolicyError("steps must be an object")
    unknown_steps = sorted(set(steps) - VALID_STEP_NAMES)
    if unknown_steps:
        raise PolicyError(f"unknown step names: {', '.join(unknown_steps)}")
    sequence = (workflow.get("sequence")) or []
    if not isinstance(sequence, list) or not all(isinstance(item, str) for item in sequence):
        raise PolicyError("workflow.sequence must be a string array")
    if "maxCycles" in review and not isinstance(review.get("maxCycles"), int):
        raise PolicyError("workflow.repeat.review.maxCycles must be an integer")
    if "maxRetries" in crash and not isinstance(crash.get("maxRetries"), int):
        raise PolicyError("workflow.crash.maxRetries must be an integer")
    for step in sequence:
        if step not in steps:
            raise PolicyError(f"workflow.sequence references missing step: {step}")
    for name, contract in steps.items():
        if not isinstance(contract, dict):
            raise PolicyError(f"step contract must be an object: {name}")
        assets = _expect_step_dict(contract, "assets", name)
        _expect_step_dict(contract, "prompt", name)
        _expect_step_dict(contract, "parse", name)
        _expect_step_dict(contract, "success", name)
        verifier = str(((contract.get("success") or {}).get("verifier")) or "")
        if verifier not in VALID_VERIFIERS:
            raise PolicyError(f"invalid verifier for {name}: {verifier}")
        required = (assets.get("required")) or []
        if not isinstance(required, list) or any(item not in VALID_ASSET_NAMES for item in required):
            raise PolicyError(f"invalid required assets for {name}")


def _resolve_policy_paths(policy: dict[str, Any], *, project_root: Path, bundle_root: Path) -> None:
    for name, contract in (policy.get("steps") or {}).items():
        assets = contract.setdefault("assets", {})
        assets["files"] = _resolve_step_assets(name, assets, project_root)
        prompt = contract.setdefault("prompt", {})
        template_file = str(prompt.get("templateFile") or "").strip()
        if not template_file:
            raise PolicyError(f"missing prompt template for {name}")
        prompt["templatePath"] = _resolve_data_path(template_file, project_root=project_root, bundle_root=bundle_root)
        parse = contract.setdefault("parse", {})
        schema_file = str(parse.get("schemaFile") or "").strip()
        if not schema_file:
            raise PolicyError(f"missing parse schema for {name}")
        parse["schemaPath"] = _resolve_data_path(schema_file, project_root=project_root, bundle_root=bundle_root)
        success = contract.setdefault("success", {})
        contract_file = str(success.get("contractFile") or "").strip()
        if contract_file:
            success["contractPath"] = _resolve_data_path(contract_file, project_root=project_root, bundle_root=bundle_root)


def _resolve_success_paths(policy: dict[str, Any], *, project_root: Path, bundle_root: Path) -> None:
    for contract in (policy.get("steps") or {}).values():
        success = contract.setdefault("success", {})
        contract_file = str(success.get("contractFile") or "").strip()
        if contract_file:
            success["contractPath"] = _resolve_data_path(contract_file, project_root=project_root, bundle_root=bundle_root)


def _resolve_step_assets(step: str, assets: dict[str, Any], project_root: Path) -> dict[str, str]:
    skill_name = str(assets.get("skillName") or "").strip()
    if not skill_name:
        raise PolicyError(f"missing skillName for {step}")
    skill_dir = project_root / ".claude" / "skills" / skill_name
    required = set(assets.get("required") or [])
    files = {
        "skill": _resolve_required_file(skill_dir / "SKILL.md", project_root, required, "skill", step),
        "workflow": _resolve_candidate_file(skill_dir, assets.get("workflowCandidates"), project_root, required, "workflow", step),
        "instructions": _resolve_candidate_file(skill_dir, assets.get("instructionsCandidates"), project_root, required, "instructions", step),
        "checklist": _resolve_candidate_file(skill_dir, assets.get("checklistCandidates"), project_root, required, "checklist", step),
        "template": _resolve_candidate_file(skill_dir, assets.get("templateCandidates"), project_root, required, "template", step),
    }
    if ("skill" not in required and "workflow" not in required) and bool(files["skill"]) != bool(files["workflow"]):
        files["skill"] = ""
        files["workflow"] = ""
    return files


def _resolve_required_file(path: Path, project_root: Path, required: set[str], asset: str, step: str) -> str:
    if path.is_file():
        return _display_path(path, project_root)
    if asset in required:
        raise PolicyError(f"missing required {asset} asset for {step}: {path}")
    return ""


def _resolve_candidate_file(
    skill_dir: Path,
    candidates: Any,
    project_root: Path,
    required: set[str],
    asset: str,
    step: str,
) -> str:
    if not isinstance(candidates, list):
        candidates = []
    for name in candidates:
        if not isinstance(name, str) or not name:
            continue
        path = skill_dir / name
        if path.is_file():
            return _display_path(path, project_root)
    if asset in required:
        searched = ", ".join(str(skill_dir / str(name)) for name in candidates if isinstance(name, str) and name)
        raise PolicyError(f"missing required {asset} asset for {step}: {searched}")
    return ""


def _resolve_data_path(path_value: str, *, project_root: Path, bundle_root: Path) -> str:
    raw = Path(path_value)
    if raw.is_absolute():
        if not raw.is_file():
            raise PolicyError(f"policy data file missing: {raw}")
        return str(raw)
    for base in (bundle_root, project_root):
        candidate = (base / raw).resolve()
        if candidate.is_file():
            return str(candidate)
    raise PolicyError(f"policy data file missing: {path_value}")


def _snapshot_relative_dir(policy: dict[str, Any]) -> str:
    snapshot = _expect_optional_dict(policy, "snapshot")
    relative_dir = str(snapshot.get("relativeDir") or "").strip()
    if not relative_dir:
        raise PolicyError("snapshot.relativeDir missing")
    return relative_dir


def _stable_policy_json(policy: dict[str, Any]) -> str:
    return json.dumps(policy, indent=2, sort_keys=True) + "\n"


def _display_path(path: Path, project_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(project_root.resolve()))
    except ValueError:
        return str(path.resolve())


def _resolve_state_path(project_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else project_root / path


def _expect_optional_dict(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise PolicyError(f"{key} must be an object")
    return value


def _expect_step_dict(contract: dict[str, Any], key: str, step: str) -> dict[str, Any]:
    value = contract.get(key)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise PolicyError(f"{step}.{key} must be an object")
    return value


def _expect_optional_nested_dict(payload: dict[str, Any], key: str, label: str) -> dict[str, Any]:
    value = payload.get(key)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise PolicyError(f"{label}.{key} must be an object")
    return value
