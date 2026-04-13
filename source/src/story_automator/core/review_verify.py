from __future__ import annotations

from pathlib import Path
from typing import Any

from .success_verifiers import resolve_success_contract, review_completion


def verify_code_review_completion(
    project_root: str,
    story_key: str,
    *,
    success_contract: dict[str, Any] | None = None,
    state_file: str | Path | None = None,
) -> dict[str, object]:
    try:
        contract = success_contract or resolve_success_contract(project_root, "review", state_file=state_file)
        return review_completion(project_root=project_root, story_key=story_key, contract=contract)
    except (FileNotFoundError, ValueError) as exc:
        return {"verified": False, "reason": "review_contract_invalid", "input": story_key, "error": str(exc)}
