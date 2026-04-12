from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

from ..core.common import (
    clamp_int,
    command_exists,
    ensure_dir,
    file_exists,
    filter_input_box,
    iso_now,
    md5_hex8,
    project_root,
    read_text,
    run_cmd,
    safe_int,
    trim_lines,
    write_atomic,
)


@dataclass
class TmuxStatus:
    status: str
    todos_done: int
    todos_total: int
    active_task: str
    wait_estimate: int
    session_state: str


def project_slug() -> str:
    base = project_root().name.lower()
    slug = "".join(ch for ch in base if ch.isalnum())[:8]
    return slug or "project"


def project_hash(root: str | Path | None = None) -> str:
    resolved = Path(root) if root else project_root()
    return md5_hex8(str(Path(resolved).resolve()))


def generate_session_name(step: str, epic: str, story_id: str, cycle: str = "") -> str:
    stamp = time.strftime("%y%m%d-%H%M%S", time.localtime())
    suffix = story_id.replace(".", "-")
    name = f"sa-{project_slug()}-{stamp}-e{epic}-s{suffix}-{step}"
    if cycle:
        name += f"-r{cycle}"
    return name


def agent_type() -> str:
    return os.environ.get("AI_AGENT", "claude")


def agent_cli(agent: str) -> str:
    return "codex exec" if agent == "codex" else "claude --dangerously-skip-permissions"


def skill_prefix(agent: str) -> str:
    return "none" if agent == "codex" else "bmad-"


def tmux_has_session(session: str) -> bool:
    _, code = run_cmd("tmux", "has-session", "-t", session)
    return code == 0


def tmux_display(session: str, fmt: str) -> str:
    output, _ = run_cmd("tmux", "display-message", "-t", session, "-p", fmt)
    return output.strip()


def tmux_show_environment(session: str, key: str) -> str:
    output, code = run_cmd("tmux", "show-environment", "-t", session, key)
    if code != 0:
        return ""
    parts = output.strip().split("=", 1)
    return parts[1] if len(parts) == 2 else ""


def tmux_new_session(session: str, root: str | Path, selected_agent: str) -> tuple[str, int]:
    return run_cmd(
        "tmux",
        "new-session",
        "-d",
        "-s",
        session,
        "-x",
        "200",
        "-y",
        "50",
        "-c",
        str(root),
        "-e",
        "STORY_AUTOMATOR_CHILD=true",
        "-e",
        f"AI_AGENT={selected_agent}",
        "-e",
        "CLAUDECODE=",
    )


def tmux_send_keys(session: str, command: str, enter: bool = True) -> tuple[str, int]:
    args = ["tmux", "send-keys", "-t", session, command]
    if enter:
        args.append("Enter")
    return run_cmd(*args)


def tmux_list_sessions(project_only: bool = False) -> list[str]:
    if not command_exists("tmux"):
        return []
    output, code = run_cmd("tmux", "list-sessions", "-F", "#{session_name}")
    if code != 0:
        return []
    sessions = [line for line in trim_lines(output) if line.startswith("sa-")]
    if project_only:
        prefix = f"sa-{project_slug()}-"
        sessions = [line for line in sessions if line.startswith(prefix)]
    return sessions


def tmux_kill_session(session: str) -> None:
    run_cmd("tmux", "kill-session", "-t", session)
    hash_value = project_hash()
    for file_name in (
        f"/tmp/.sa-{hash_value}-session-{session}-state.json",
        f"/tmp/sa-{hash_value}-output-{session}.txt",
        f"/tmp/sa-cmd-{session}.sh",
    ):
        Path(file_name).unlink(missing_ok=True)


def pane_status(session: str) -> str:
    pane_dead = tmux_display(session, "#{pane_dead}")
    exit_status = tmux_display(session, "#{pane_dead_status}")
    if pane_dead == "1":
        if exit_status and exit_status != "0":
            return f"crashed:{exit_status}"
        return "exited:0"
    return "alive"


def detect_codex_session(session: str, capture: str) -> str:
    if tmux_show_environment(session, "AI_AGENT") == "codex":
        return "codex"
    if re.search(r"(?i)OpenAI Codex|codex exec|gpt-[0-9]+-codex|tokens used|codex-cli", capture):
        return "codex"
    return "claude"


def estimate_wait(task: str, done: int, total: int) -> int:
    lower = task.lower()
    if re.search(r"loading|reading|searching|parsing", lower):
        return 30
    if re.search(r"presenting|waiting|menu|select|choose", lower):
        return 15
    if re.search(r"running tests|testing|building|compiling|installing", lower):
        return 120
    if re.search(r"writing|editing|updating|creating|fixing", lower):
        return 60
    if total > 0:
        progress = 100 * done // total
        if progress < 25:
            return 90
        if progress < 50:
            return 75
        if progress < 75:
            return 60
        return 30
    return 60


def extract_active_task(capture: str) -> str:
    pattern = re.compile(r"(?i)(·|✳|⠋|⠙|⠹|⠸|⠼|⠴|⠦|⠧|⠇|⠏|✶|✻|Galloping|Working|Running|Beaming|Razzmatazzing|Creating)")
    active = ""
    for line in trim_lines(capture):
        if pattern.search(line):
            active = line
    if not active:
        return ""
    active = re.sub(r"[·✳⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏✶✻]", "", active)
    active = re.sub(r"\(ctrl\+c.*", "", active).strip()
    return active[:80]


def parse_statusline_time(capture: str) -> str:
    pattern = re.compile(r"\| [0-9]{2}:[0-9]{2}:[0-9]{2}")
    last = ""
    for line in trim_lines(capture):
        matches = pattern.findall(line)
        if matches:
            last = matches[-1].replace("|", "").strip()
    return last


def load_json_state(path: str | Path) -> dict[str, object]:
    if not file_exists(path):
        return {}
    return json.loads(read_text(path))


def save_json_state(path: str | Path, payload: dict[str, object]) -> None:
    ensure_dir(Path(path).parent)
    write_atomic(path, json.dumps(payload))


def count_rune(text: str, target: str) -> int:
    return sum(1 for char in text if char == target)


def find_first_todo_line(capture: str) -> int:
    for index, line in enumerate(trim_lines(capture), start=1):
        if "☒" in line or "☐" in line:
            return index
    return 999


def verify_or_create_output(output_file: str, session_name: str, hash_value: str) -> str:
    if output_file and file_exists(output_file) and Path(output_file).stat().st_size > 0:
        return output_file
    fallback = Path(f"/tmp/sa-{hash_value}-output-{session_name}-fallback.txt")
    if tmux_has_session(session_name):
        capture, _ = run_cmd("tmux", "capture-pane", "-t", session_name, "-p", "-S", "-300")
        lines = trim_lines(capture)[:200]
        fallback.write_text("\n".join(lines), encoding="utf-8")
        if fallback.exists() and fallback.stat().st_size > 0:
            return str(fallback)
    expected = Path(f"/tmp/sa-{hash_value}-output-{session_name}.txt")
    if expected.exists() and expected.stat().st_size > 0:
        return str(expected)
    return ""


def heartbeat_check(session: str, selected_agent: str) -> tuple[str, float, str, str]:
    if not session:
        return "error", 0.0, "", "no_session"
    if not tmux_has_session(session):
        return "error", 0.0, "", "session_not_found"
    pane_pid = tmux_display(session, "#{pane_pid}")
    if not pane_pid:
        return "error", 0.0, "", "no_pane_pid"
    pattern = "codex" if selected_agent == "codex" else "claude"
    agent_pid = _find_agent_pid(pane_pid, pattern, 0)
    prompt = _check_prompt_visible(session)
    if not agent_pid:
        return ("completed" if prompt == "true" else "dead"), 0.0, "", prompt
    cpu_output, _ = run_cmd("ps", "-o", "%cpu=", "-p", agent_pid)
    cpu = float(cpu_output.strip() or 0.0)
    status = "alive" if int(cpu) > 0 else "idle"
    if prompt == "true":
        status = "completed"
    return status, cpu, agent_pid, prompt


def _find_agent_pid(parent: str, pattern: str, depth: int) -> str:
    if depth > 4:
        return ""
    output, code = run_cmd("pgrep", "-P", parent)
    if code != 0:
        return ""
    for child in trim_lines(output):
        child = child.strip()
        if not child:
            continue
        command, _ = run_cmd("ps", "-o", "comm=", "-p", child)
        if pattern.lower() in command.lower():
            return child
        nested = _find_agent_pid(child, pattern, depth + 1)
        if nested:
            return nested
    return ""


def _check_prompt_visible(session: str) -> str:
    capture, _ = run_cmd("tmux", "capture-pane", "-t", session, "-p")
    lines = trim_lines(capture)[-3:]
    last = lines[-1].rstrip() if lines else ""
    if re.search(r"❯\s*([0-9]+[smh]\s*)?[0-9]{1,2}:[0-9]{2}:[0-9]{2}\s*$", last):
        return "true"
    if re.search(r"(❯|\$|#|%)\s*$", last):
        return "true"
    return "false"
