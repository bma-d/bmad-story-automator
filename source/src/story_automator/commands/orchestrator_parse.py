from __future__ import annotations

import json

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
    prompt = _build_parse_prompt(step, "\n".join(lines))
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
        json.loads(json_line)
    except json.JSONDecodeError:
        print_json({"status": "error", "reason": "sub-agent returned invalid json"})
        return 1
    print(json_line)
    return 0


def _build_parse_prompt(step: str, content: str) -> str:
    if step == "create":
        schema = '{"status":"SUCCESS|FAILURE|AMBIGUOUS","story_created":true/false,"story_file":"path or null","summary":"brief description","next_action":"proceed|retry|escalate"}'
        label = "create-story"
    elif step == "dev":
        schema = '{"status":"SUCCESS|FAILURE|AMBIGUOUS","tests_passed":true/false,"build_passed":true/false,"summary":"brief description","next_action":"proceed|retry|escalate"}'
        label = "dev-story"
    elif step == "auto":
        schema = '{"status":"SUCCESS|FAILURE|AMBIGUOUS","tests_added":N,"coverage_improved":true/false,"summary":"brief description","next_action":"proceed|retry|escalate"}'
        label = "automate-tests"
    elif step == "review":
        schema = '{"status":"SUCCESS|FAILURE|AMBIGUOUS","issues_found":{"critical":N,"high":N,"medium":N,"low":N},"all_fixed":true/false,"summary":"brief description","next_action":"proceed|retry|escalate"}'
        label = "code-review"
    else:
        schema = '{"status":"SUCCESS|FAILURE|AMBIGUOUS","summary":"brief description","next_action":"proceed|retry|escalate"}'
        label = "session"
    return f"Analyze this {label} session output. Return JSON only:\n{schema}\n\nSession output:\n---\n{content}\n---"
