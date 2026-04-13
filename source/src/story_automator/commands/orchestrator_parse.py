from __future__ import annotations

import json

from story_automator.core.runtime_policy import load_effective_policy, step_contract
from story_automator.core.utils import COMMAND_TIMEOUT_EXIT, extract_json_line, print_json, read_text, run_cmd, trim_lines


PARSE_OUTPUT_TIMEOUT = 120


def parse_output_action(args: list[str]) -> int:
    if len(args) < 2:
        print('{"status":"error","reason":"output file not found or empty"}')
        return 1
    output_file, step = args[:2]
    try:
        content = read_text(output_file)
    except FileNotFoundError:
        print('{"status":"error","reason":"output file not found or empty"}')
        return 1
    if not content.strip():
        print('{"status":"error","reason":"output file not found or empty"}')
        return 1
    lines = trim_lines(content)[:150]
    try:
        contract = step_contract(load_effective_policy(), step)
        parse_contract = _load_parse_contract(contract)
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        print_json({"status": "error", "reason": "parse_contract_invalid"})
        return 1
    prompt = _build_parse_prompt(contract, parse_contract, "\n".join(lines))
    result = run_cmd(
        "claude",
        "-p",
        "--model",
        "haiku",
        prompt,
        env={"STORY_AUTOMATOR_CHILD": "true", "CLAUDECODE": ""},
        timeout=PARSE_OUTPUT_TIMEOUT,
    )
    if result.exit_code != 0:
        reason = "sub-agent call timed out" if result.exit_code == COMMAND_TIMEOUT_EXIT else "sub-agent call failed"
        print_json({"status": "error", "reason": reason})
        return 1
    json_line = extract_json_line(result.output)
    if not json_line:
        print_json({"status": "error", "reason": "sub-agent returned invalid json"})
        return 1
    try:
        payload = json.loads(json_line)
    except json.JSONDecodeError:
        print_json({"status": "error", "reason": "sub-agent returned invalid json"})
        return 1
    if not _has_required_keys(payload, parse_contract.get("requiredKeys") or []):
        print_json({"status": "error", "reason": "sub-agent returned invalid json"})
        return 1
    print(json.dumps(payload, separators=(",", ":")))
    return 0


def _load_parse_contract(contract: dict[str, object]) -> dict[str, object]:
    parse = contract.get("parse") or {}
    payload = json.loads(read_text(str(parse.get("schemaPath") or "")))
    if not isinstance(payload, dict):
        raise ValueError("invalid parse schema")
    if not isinstance(payload.get("requiredKeys"), list):
        raise ValueError("invalid parse schema")
    if not isinstance(payload.get("schema"), dict):
        raise ValueError("invalid parse schema")
    return payload


def _build_parse_prompt(contract: dict[str, object], parse_contract: dict[str, object], content: str) -> str:
    label = str(contract.get("label") or "session")
    schema = json.dumps(parse_contract.get("schema") or {}, separators=(",", ":"))
    return f"Analyze this {label} session output. Return JSON only:\n{schema}\n\nSession output:\n---\n{content}\n---"


def _has_required_keys(payload: object, required_keys: list[object]) -> bool:
    if not isinstance(payload, dict):
        return False
    return all(isinstance(key, str) and key in payload for key in required_keys)
