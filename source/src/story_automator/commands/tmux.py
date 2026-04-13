from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from story_automator.core.runtime_policy import PolicyError, load_runtime_policy, step_contract
from story_automator.core.success_verifiers import resolve_success_contract, run_success_verifier
from story_automator.core.utils import (
    atomic_write,
    command_exists,
    file_exists,
    filter_input_box,
    get_project_root,
    iso_now,
    md5_hex8,
    print_json,
    project_hash,
    project_slug,
    read_text,
    run_cmd,
)


def cmd_tmux_wrapper(args: list[str]) -> int:
    if not args:
        return _usage(1)
    if args[0] in {"--help", "-h"}:
        return _usage(0)
    action = args[0]
    if action == "spawn":
        return _spawn(args[1:])
    if action == "name":
        if len(args) < 4:
            return _usage(1)
        cycle = args[4] if len(args) > 4 else ""
        print(generate_session_name(args[1], args[2], args[3], cycle))
        return 0
    if action == "list":
        sessions, _ = tmux_list_sessions("--project-only" in args[1:])
        print("\n".join(sessions))
        return 0
    if action == "kill":
        if len(args) < 2:
            return _usage(1)
        tmux_kill_session(args[1])
        return 0
    if action == "kill-all":
        sessions, _ = tmux_list_sessions("--project-only" in args[1:])
        for session in sessions:
            tmux_kill_session(session)
        print(f"Killed {len(sessions)} sessions")
        return 0
    if action == "exists":
        if len(args) < 2:
            return _usage(1)
        if tmux_has_session(args[1]):
            print("true")
            return 0
        print("false")
        return 1
    if action == "build-cmd":
        return _build_cmd(args[1:])
    if action == "project-slug":
        print(project_slug())
        return 0
    if action == "project-hash":
        print(project_hash())
        return 0
    if action == "story-suffix":
        if len(args) < 2:
            return _usage(1)
        print(args[1].replace(".", "-"))
        return 0
    if action == "agent-type":
        print(agent_type())
        return 0
    if action == "agent-cli":
        print(agent_cli(agent_type()))
        return 0
    if action == "skill-prefix":
        print(skill_prefix(agent_type()))
        return 0
    return _usage(1)


def _usage(code: int) -> int:
    target = __import__("sys").stderr if code else __import__("sys").stdout
    print("Usage: tmux-wrapper <action> [args...]", file=target)
    print("", file=target)
    print("Actions:", file=target)
    print('  spawn <step> <epic> <story_id> --command "..." [--cycle N] [--agent TYPE]', file=target)
    print("  name <step> <epic> <story_id> [--cycle N]", file=target)
    print("  list [--project-only]", file=target)
    print("  kill <session_name>", file=target)
    print("  kill-all [--project-only]", file=target)
    print("  exists <session_name>", file=target)
    print("  build-cmd <step> <story_id> [--agent TYPE] [extra_instruction]", file=target)
    print("  project-slug", file=target)
    print("  project-hash", file=target)
    print("  story-suffix <story_id>", file=target)
    print("  agent-type", file=target)
    print("  agent-cli", file=target)
    print("  skill-prefix", file=target)
    return code


def _spawn(args: list[str]) -> int:
    if len(args) < 3:
        return _usage(1)
    step, epic, story_id = args[:3]
    command = ""
    cycle = ""
    agent = agent_type()
    tail = args[3:]
    for idx, arg in enumerate(tail):
        if arg == "--command" and idx + 1 < len(tail):
            command = tail[idx + 1]
        elif arg == "--cycle" and idx + 1 < len(tail):
            cycle = tail[idx + 1]
        elif arg == "--agent" and idx + 1 < len(tail):
            agent = tail[idx + 1]
    if not command:
        print("--command is required", file=__import__("sys").stderr)
        return 1
    session = generate_session_name(step, epic, story_id, cycle)
    state_file = Path(f"/tmp/.sa-{project_hash()}-session-{session}-state.json")
    if state_file.exists():
        state_file.unlink()
    if not command_exists("tmux"):
        print("tmux not found", file=__import__("sys").stderr)
        return 1
    root = get_project_root()
    out, code = run_cmd(
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
        root,
        "-e",
        "STORY_AUTOMATOR_CHILD=true",
        "-e",
        f"AI_AGENT={agent}",
        "-e",
        "CLAUDECODE=",
    )
    if code != 0:
        print(out.strip(), file=__import__("sys").stderr)
        return 1
    if command:
        if len(command) > 500:
            script = Path(f"/tmp/sa-cmd-{session}.sh")
            script.write_text("#!/bin/bash\n" + command + "\n", encoding="utf-8")
            script.chmod(0o755)
            run_cmd("tmux", "send-keys", "-t", session, f"bash {script}", "Enter")
        else:
            run_cmd("tmux", "send-keys", "-t", session, command, "Enter")
    print(session)
    return 0


def _build_cmd(args: list[str]) -> int:
    if len(args) < 2:
        return _usage(1)
    step, story_id = args[:2]
    agent = ""
    extra = ""
    tail = args[2:]
    idx = 0
    state_file = ""
    while idx < len(tail):
        if tail[idx] == "--agent" and idx + 1 < len(tail):
            agent = tail[idx + 1]
            idx += 2
            continue
        if tail[idx] == "--state-file" and idx + 1 < len(tail):
            state_file = tail[idx + 1]
            idx += 2
            continue
        extra = f"{extra} {tail[idx]}".strip()
        idx += 1
    agent = agent or agent_type()
    story_prefix = story_id.replace(".", "-")
    root = get_project_root()
    try:
        policy = load_runtime_policy(root, state_file=state_file)
        contract = step_contract(policy, step)
    except (FileNotFoundError, PolicyError) as exc:
        print(str(exc), file=__import__("sys").stderr)
        return 1
    ai_command = os.environ.get("AI_COMMAND")
    if ai_command and not os.environ.get("AI_AGENT"):
        cli = ai_command
    elif agent != "codex":
        cli = agent_cli(agent)
    else:
        cli = "codex exec"
    prompt = _render_step_prompt(contract, story_id, story_prefix, extra)
    escaped = prompt.replace("\\", "\\\\").replace('"', '\\"')
    if agent == "codex" and not ai_command:
        codex_home = f"/tmp/sa-codex-home-{project_hash(root)}"
        auth_src = os.path.expanduser("~/.codex/auth.json")
        print(
            f'mkdir -p "{codex_home}"'
            + f' && if [ -f "{auth_src}" ]; then ln -sf "{auth_src}" "{codex_home}/auth.json"; fi'
            + f' && CODEX_HOME="{codex_home}" codex exec -s workspace-write -c \'approval_policy="never"\''
            + f' -c \'model_reasoning_effort="high"\''
            + f' --disable plugins --disable sqlite --disable shell_snapshot "{escaped}"'
        )
    else:
        print(f'unset CLAUDECODE && {cli} "{escaped}"')
    return 0


def agent_type() -> str:
    return os.environ.get("AI_AGENT", "claude")


def agent_cli(agent: str) -> str:
    return "codex exec" if agent == "codex" else "claude --dangerously-skip-permissions"


def skill_prefix(agent: str) -> str:
    return "none" if agent == "codex" else "bmad-"


def _render_step_prompt(contract: dict[str, object], story_id: str, story_prefix: str, extra_instruction: str) -> str:
    prompt_cfg = contract.get("prompt") or {}
    assets = (contract.get("assets") or {}).get("files") or {}
    template = read_text(str(prompt_cfg.get("templatePath") or ""))
    replacements = {
        "{{story_id}}": story_id,
        "{{story_prefix}}": story_prefix,
        "{{label}}": str(contract.get("label") or ""),
        "{{skill_line}}": _prompt_line("READ this skill first", str(assets.get("skill") or "")),
        "{{workflow_line}}": _prompt_line("READ this workflow file next", str(assets.get("workflow") or "")),
        "{{instructions_line}}": _prompt_line("Then read", str(assets.get("instructions") or "")),
        "{{checklist_line}}": _prompt_line("Validate with", str(assets.get("checklist") or "")),
        "{{template_line}}": _prompt_line("Use template", str(assets.get("template") or "")),
        "{{extra_instruction}}": extra_instruction.strip() or str(prompt_cfg.get("defaultExtraInstruction") or ""),
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    return template


def _prompt_line(prefix: str, value: str) -> str:
    return f"{prefix}: {value}\n" if value else ""


def generate_session_name(step: str, epic: str, story_id: str, cycle: str = "") -> str:
    stamp = time.strftime("%y%m%d-%H%M%S", time.localtime())
    suffix = story_id.replace(".", "-")
    name = f"sa-{project_slug()}-{stamp}-e{epic}-s{suffix}-{step}"
    if cycle:
        name += f"-r{cycle}"
    return name


def tmux_has_session(session: str) -> bool:
    return command_exists("tmux") and run_cmd("tmux", "has-session", "-t", session)[1] == 0


def tmux_list_sessions(project_only: bool) -> tuple[list[str], int]:
    if not command_exists("tmux"):
        return ([], 1)
    out, code = run_cmd("tmux", "list-sessions", "-F", "#{session_name}")
    if code != 0:
        return ([], code)
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    prefix = f"sa-{project_slug()}-"
    if project_only:
        lines = [line for line in lines if line.startswith(prefix)]
    else:
        lines = [line for line in lines if line.startswith("sa-")]
    return (lines, 0)


def tmux_kill_session(session: str) -> None:
    if command_exists("tmux"):
        run_cmd("tmux", "kill-session", "-t", session)
    for path in (
        Path(f"/tmp/.sa-{project_hash()}-session-{session}-state.json"),
        Path(f"/tmp/sa-{project_hash()}-output-{session}.txt"),
        Path(f"/tmp/sa-cmd-{session}.sh"),
    ):
        if path.exists():
            path.unlink()


def cmd_heartbeat_check(args: list[str]) -> int:
    if not args:
        print("error,0.0,,no_session")
        return 0
    session = args[0]
    agent = "auto"
    tail = args[1:]
    for idx, arg in enumerate(tail):
        if arg == "--agent" and idx + 1 < len(tail):
            agent = tail[idx + 1]
    status, cpu, pid, prompt = heartbeat_check(session, agent)
    print(f"{status},{cpu:.1f},{pid},{prompt}")
    return 0


def heartbeat_check(session: str, agent: str) -> tuple[str, float, str, str]:
    if not session:
        return ("error", 0.0, "", "no_session")
    if not tmux_has_session(session):
        return ("error", 0.0, "", "session_not_found")
    capture = filter_input_box(run_cmd("tmux", "capture-pane", "-t", session, "-p", "-S", "-40")[0])
    prompt = "true" if re.search(r"(❯|\$|#|%)\s*$", capture.splitlines()[-1] if capture.splitlines() else "") else "false"
    pane_pid, code = run_cmd("tmux", "display-message", "-t", session, "-p", "#{pane_pid}")
    if code != 0 or not pane_pid.strip():
        return ("completed" if prompt == "true" else "dead", 0.0, "", prompt)
    pane_pid = pane_pid.strip()
    pattern = "codex" if agent == "codex" else "claude"
    agent_pid = _find_agent_pid(pane_pid, pattern, 0)
    if not agent_pid:
        return ("completed" if prompt == "true" else "dead", 0.0, "", prompt)
    cpu_out, _ = run_cmd("ps", "-o", "%cpu=", "-p", agent_pid)
    cpu = float(cpu_out.strip() or "0")
    if int(cpu) > 0:
        return ("alive", cpu, agent_pid, prompt)
    return ("completed" if prompt == "true" else "idle", cpu, agent_pid, prompt)


def _find_agent_pid(parent: str, pattern: str, depth: int) -> str:
    if depth > 4:
        return ""
    output, code = run_cmd("pgrep", "-P", parent)
    if code != 0:
        return ""
    for child in [line.strip() for line in output.splitlines() if line.strip()]:
        command, _ = run_cmd("ps", "-o", "comm=", "-p", child)
        if pattern.lower() in command.lower():
            return child
        nested = _find_agent_pid(child, pattern, depth + 1)
        if nested:
            return nested
    return ""


def cmd_codex_status_check(args: list[str]) -> int:
    return _status_check(args, codex=True)


def cmd_tmux_status_check(args: list[str]) -> int:
    return _status_check(args, codex=False)


def _status_check(args: list[str], codex: bool) -> int:
    if not args:
        print("error,0,0,no_session,30,error")
        return 0 if codex else 1
    session = args[0]
    full = "--full" in args[1:]
    project_root: str | None = None
    tail = args[1:]
    idx = 0
    while idx < len(tail):
        if tail[idx] == "--project-root" and idx + 1 < len(tail):
            project_root = tail[idx + 1]
            idx += 2
            continue
        idx += 1
    status = session_status(session, full=full, codex=codex, project_root=project_root)
    print(",".join([status["status"], str(status["todos_done"]), str(status["todos_total"]), status["active_task"], str(status["wait_estimate"]), status["session_state"]]))
    return 0 if codex else (0 if status["status"] != "error" else 1)


def session_status(
    session: str,
    *,
    full: bool,
    codex: bool,
    project_root: str | None = None,
) -> dict[str, str | int]:
    if codex:
        return _codex_session_status(session, full=full, project_root=project_root)
    return _claude_session_status(session, full=full, project_root=project_root)


def _codex_session_status(
    session: str,
    *,
    full: bool,
    project_root: str | None = None,
) -> dict[str, str | int]:
    if not session:
        return {"status": "error", "todos_done": 0, "todos_total": 0, "active_task": "no_session", "wait_estimate": 30, "session_state": "error"}
    if not tmux_has_session(session):
        return {"status": "not_found", "todos_done": 0, "todos_total": 0, "active_task": "session_not_found", "wait_estimate": 0, "session_state": "not_found"}
    capture = filter_input_box(run_cmd("tmux", "capture-pane", "-t", session, "-p", "-S", "-120")[0])
    todos_done = capture.count("☒")
    todos_total = todos_done + capture.count("☐")
    if re.search(r"tokens used|❯\s*(\d+[smh]\s*)?\d{1,2}:\d{2}:\d{2}\s*$", capture):
        output = _write_capture(session, capture, project_root=project_root)
        return {"status": "idle", "todos_done": max(1, todos_done), "todos_total": max(1, todos_total or 1), "active_task": output if full else "", "wait_estimate": 0, "session_state": "completed"}
    heartbeat, cpu, _, prompt = heartbeat_check(session, "codex")
    if heartbeat in {"alive", "idle"}:
        active_task = extract_active_task(capture) or ("Codex working" if heartbeat == "alive" else "Codex running")
        wait_estimate = 90 if heartbeat == "alive" else 60
        return {"status": "active", "todos_done": todos_done, "todos_total": todos_total, "active_task": active_task, "wait_estimate": wait_estimate, "session_state": "in_progress"}
    if prompt == "true":
        output = _write_capture(session, capture, project_root=project_root)
        return {"status": "idle", "todos_done": max(1, todos_done), "todos_total": max(1, todos_total or 1), "active_task": output if full else "", "wait_estimate": 0, "session_state": "completed"}
    if todos_done or todos_total:
        output = _write_capture(session, capture, project_root=project_root)
        return {"status": "idle", "todos_done": todos_done, "todos_total": todos_total, "active_task": output if full else "", "wait_estimate": 0, "session_state": "completed"}
    output = _write_capture(session, capture, project_root=project_root)
    return {"status": "idle", "todos_done": 0, "todos_total": 0, "active_task": output if full else "", "wait_estimate": 0, "session_state": "stuck"}


def _claude_session_status(
    session: str,
    *,
    full: bool,
    project_root: str | None = None,
) -> dict[str, str | int]:
    if not session:
        return {"status": "error", "todos_done": 0, "todos_total": 0, "active_task": "no_session", "wait_estimate": 30, "session_state": "error"}

    root = project_root or get_project_root()
    state_path = _state_file(session, root)

    if not tmux_has_session(session):
        state_path.unlink(missing_ok=True)
        return {"status": "not_found", "todos_done": 0, "todos_total": 0, "active_task": "", "wait_estimate": 0, "session_state": "not_found"}

    pane_state = _pane_status(session)
    if pane_state.startswith("crashed:"):
        exit_code = pane_state.removeprefix("crashed:")
        capture = filter_input_box(run_cmd("tmux", "capture-pane", "-t", session, "-p", "-S", "-200")[0])
        output = _write_capture(session, capture, project_root=root, max_lines=150)
        state_path.unlink(missing_ok=True)
        return {
            "status": "crashed",
            "todos_done": 0,
            "todos_total": 0,
            "active_task": output if full else "",
            "wait_estimate": int(exit_code or "1"),
            "session_state": "crashed",
        }

    state = _load_tmux_state(state_path)
    state["poll_count"] = int(state["poll_count"]) + 1

    capture, code = run_cmd("tmux", "capture-pane", "-t", session, "-p", "-S", "-50")
    capture = filter_input_box(capture)
    if code != 0 or not capture:
        return {"status": "error", "todos_done": 0, "todos_total": 0, "active_task": "capture_failed", "wait_estimate": 30, "session_state": "error"}

    current_status_time = _parse_statusline_time(capture)
    todos_done = capture.count("☒")
    todos_total = todos_done + capture.count("☐")

    if re.search(r"for [0-9]+m [0-9]+s", capture):
        _save_tmux_state(
            state_path,
            poll_count=int(state["poll_count"]),
            has_active=True,
            done=int(state["last_todos_done"]),
            total=int(state["last_todos_total"]),
            status_time=current_status_time,
        )
        output = _write_full_capture(session, project_root=root) if full else ""
        return {
            "status": "idle",
            "todos_done": int(state["last_todos_done"]),
            "todos_total": int(state["last_todos_total"]),
            "active_task": output,
            "wait_estimate": 0,
            "session_state": "completed",
        }

    pane_pid, pane_pid_code = run_cmd("tmux", "display-message", "-t", session, "-p", "#{pane_pid}")
    claude_running = False
    if pane_pid_code == 0 and pane_pid.strip():
        claude_running = bool(_find_agent_pid(pane_pid.strip(), "claude", 0))

    activity_detected = bool(
        re.search(
            r"(?i)ctrl\+c to interrupt|Musing|Thinking|Working|Running|Loading|Beaming|Galloping|Razzmatazzing|Creating|⏺|✻|·",
            capture,
        )
    )

    if activity_detected or claude_running:
        active_task = extract_active_task(capture) or "Claude working"
        wait_estimate = 60
        if todos_total > 0:
            progress = 100 * todos_done // todos_total
            if progress < 25:
                wait_estimate = 90
            elif progress >= 75:
                wait_estimate = 30
        _save_tmux_state(
            state_path,
            poll_count=int(state["poll_count"]),
            has_active=True,
            done=todos_done,
            total=todos_total,
            status_time=current_status_time,
        )
        return {
            "status": "active",
            "todos_done": todos_done,
            "todos_total": todos_total,
            "active_task": active_task,
            "wait_estimate": wait_estimate,
            "session_state": "in_progress",
        }

    session_state = "stuck"
    if bool(state["has_ever_been_active"]):
        session_state = "completed"
    elif int(state["poll_count"]) <= 10:
        session_state = "just_started"
    elif current_status_time and str(state["last_statusline_time"]):
        session_state = "just_started" if current_status_time != str(state["last_statusline_time"]) else "stuck"
    elif current_status_time:
        session_state = "just_started"

    output = _write_full_capture(session, project_root=root) if full else ""
    if full and pane_state.startswith("exited:"):
        session_state = "completed"

    _save_tmux_state(
        state_path,
        poll_count=int(state["poll_count"]),
        has_active=bool(state["has_ever_been_active"]),
        done=int(state["last_todos_done"]),
        total=int(state["last_todos_total"]),
        status_time=current_status_time,
    )
    return {
        "status": "idle",
        "todos_done": int(state["last_todos_done"]),
        "todos_total": int(state["last_todos_total"]),
        "active_task": output,
        "wait_estimate": 0,
        "session_state": session_state,
    }


def extract_active_task(capture: str) -> str:
    pattern = re.compile(r"(?i)(Musing|Thinking|Working|Running|Loading|Creating|Galloping|Beaming|Razzmatazzing)")
    active = ""
    for line in capture.splitlines():
        if pattern.search(line):
            active = line.strip()
    active = re.sub(r"[·✳⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏✶✻]", "", active)
    active = re.sub(r"\(ctrl\+c.*", "", active).strip()
    return active[:80]


def _state_file(session: str, project_root: str | None = None) -> Path:
    return Path(f"/tmp/.sa-{project_hash(project_root)}-session-{session}-state.json")


def _load_tmux_state(path: Path) -> dict[str, str | int | bool]:
    state: dict[str, str | int | bool] = {
        "poll_count": 0,
        "has_ever_been_active": False,
        "last_todos_done": 0,
        "last_todos_total": 0,
        "last_statusline_time": "",
    }
    if not path.exists():
        return state
    try:
        raw = json.loads(read_text(path))
    except (OSError, json.JSONDecodeError):
        return state
    state["poll_count"] = int(raw.get("pollCount", 0) or 0)
    state["has_ever_been_active"] = bool(raw.get("hasEverBeenActive", False))
    state["last_todos_done"] = int(raw.get("lastTodosDone", 0) or 0)
    state["last_todos_total"] = int(raw.get("lastTodosTotal", 0) or 0)
    state["last_statusline_time"] = str(raw.get("lastStatuslineTime", "") or "")
    return state


def _save_tmux_state(
    path: Path,
    *,
    poll_count: int,
    has_active: bool,
    done: int,
    total: int,
    status_time: str,
) -> None:
    atomic_write(
        path,
        json.dumps(
            {
                "pollCount": poll_count,
                "hasEverBeenActive": has_active,
                "lastTodosDone": done,
                "lastTodosTotal": total,
                "lastStatuslineTime": status_time,
                "lastPollAt": iso_now(),
            }
        ),
    )


def _pane_status(session: str) -> str:
    pane_dead, _ = run_cmd("tmux", "display-message", "-t", session, "-p", "#{pane_dead}")
    exit_status, _ = run_cmd("tmux", "display-message", "-t", session, "-p", "#{pane_dead_status}")
    if pane_dead.strip() == "1":
        if exit_status.strip() and exit_status.strip() != "0":
            return f"crashed:{exit_status.strip()}"
        return "exited:0"
    return "alive"


def _parse_statusline_time(capture: str) -> str:
    matches = re.findall(r"\| [0-9]{2}:[0-9]{2}:[0-9]{2}", capture)
    if not matches:
        return ""
    return matches[-1].replace("|", "").strip()


def _write_full_capture(session: str, *, project_root: str | None = None) -> str:
    capture = filter_input_box(run_cmd("tmux", "capture-pane", "-t", session, "-p", "-S", "-300")[0])
    return _write_capture(session, capture, project_root=project_root)


def _write_capture(
    session: str,
    capture: str,
    *,
    project_root: str | None = None,
    max_lines: int = 200,
) -> str:
    path = Path(f"/tmp/sa-{project_hash(project_root)}-output-{session}.txt")
    lines = capture.splitlines()[:max_lines]
    atomic_write(path, "\n".join(lines))
    return str(path)


def cmd_monitor_session(args: list[str]) -> int:
    if not args:
        print("Usage: monitor-session <session_name> [options]", file=__import__("sys").stderr)
        return 1
    if args[0] in {"--help", "-h"}:
        print("Usage: monitor-session <session_name> [options]")
        print("Options: --max-polls N --initial-wait N --project-root PATH --timeout MIN --verbose --json --agent TYPE --workflow TYPE --story-key KEY --state-file PATH")
        return 0
    session = args[0]
    max_polls = 30
    initial_wait = 5
    timeout_minutes = 60
    json_output = False
    agent = os.environ.get("AI_AGENT", "claude")
    workflow = "dev"
    story_key = ""
    state_file = ""
    project_root = get_project_root()
    idx = 1
    while idx < len(args):
        arg = args[idx]
        if arg == "--max-polls" and idx + 1 < len(args):
            max_polls = int(args[idx + 1])
            idx += 2
            continue
        if arg == "--initial-wait" and idx + 1 < len(args):
            initial_wait = int(args[idx + 1])
            idx += 2
            continue
        if arg == "--timeout" and idx + 1 < len(args):
            timeout_minutes = int(args[idx + 1])
            idx += 2
            continue
        if arg == "--json":
            json_output = True
        elif arg == "--agent" and idx + 1 < len(args):
            agent = args[idx + 1]
            idx += 2
            continue
        elif arg == "--workflow" and idx + 1 < len(args):
            workflow = args[idx + 1]
            idx += 2
            continue
        elif arg == "--story-key" and idx + 1 < len(args):
            story_key = args[idx + 1]
            idx += 2
            continue
        elif arg == "--state-file" and idx + 1 < len(args):
            state_file = args[idx + 1]
            idx += 2
            continue
        elif arg == "--project-root" and idx + 1 < len(args):
            project_root = args[idx + 1]
            idx += 2
            continue
        idx += 1
    if agent == "codex":
        timeout_minutes = timeout_minutes * 3 // 2
    time.sleep(max(0, initial_wait))
    start = time.time()
    last_done = 0
    last_total = 0
    for _poll in range(1, max_polls + 1):
        if time.time() - start >= timeout_minutes * 60:
            return _emit_monitor(json_output, "timeout", last_done, last_total, "", f"exceeded_{timeout_minutes}m")
        status = session_status(session, full=False, codex=agent == "codex", project_root=project_root)
        if int(status["todos_done"]) or int(status["todos_total"]):
            last_done = int(status["todos_done"])
            last_total = int(status["todos_total"])
        state = str(status["session_state"])
        if state == "completed":
            output = session_status(session, full=True, codex=agent == "codex", project_root=project_root)["active_task"]
            verification = _verify_monitor_completion(
                workflow,
                project_root=project_root,
                story_key=story_key,
                output_file=str(output),
                state_file=state_file or None,
            )
            if verification is not None:
                verified, verifier_name = verification
                if bool(verified.get("verified")):
                    reason = "normal_completion" if verifier_name == "session_exit" else "verified_complete"
                    return _emit_monitor(json_output, "completed", last_done, last_total, str(output), reason)
                return _emit_monitor(
                    json_output,
                    "incomplete",
                    last_done,
                    last_total,
                    str(output),
                    str(verified.get("reason") or "workflow_not_verified"),
                )
            return _emit_monitor(json_output, "completed", last_done, last_total, str(output), "normal_completion")
        if state == "crashed":
            crashed = session_status(session, full=True, codex=agent == "codex", project_root=project_root)
            return _emit_monitor(
                json_output,
                "crashed",
                last_done,
                last_total,
                str(crashed["active_task"]),
                f"exit_code_{int(crashed['wait_estimate'])}",
            )
        if state == "stuck":
            output = session_status(session, full=True, codex=agent == "codex", project_root=project_root)["active_task"]
            return _emit_monitor(json_output, "stuck", 0, 0, str(output), "never_active")
        if state == "not_found":
            return _emit_monitor(json_output, "not_found", last_done, last_total, "", "session_gone")
        time.sleep(min(180 if agent == "codex" else 120, max(5, int(status["wait_estimate"]))))
    output = session_status(session, full=True, codex=agent == "codex", project_root=project_root)["active_task"]
    return _emit_monitor(json_output, "timeout", last_done, last_total, str(output), "max_polls_exceeded")


def _emit_monitor(json_output: bool, state: str, done: int, total: int, output_file: str, reason: str) -> int:
    if json_output:
        print_json({"final_state": state, "todos_done": done, "todos_total": total, "output_file": output_file, "exit_reason": reason, "output_verified": bool(output_file)})
    else:
        print(f"{state},{done},{total},{output_file},{reason}")
    return 0


def _verify_monitor_completion(
    workflow: str,
    *,
    project_root: str,
    story_key: str,
    output_file: str,
    state_file: str | Path | None = None,
) -> tuple[dict[str, object], str] | None:
    try:
        contract = resolve_success_contract(project_root, workflow, state_file=state_file)
    except (FileNotFoundError, PolicyError):
        return ({"verified": False, "reason": "verifier_contract_invalid"}, "")
    verifier_name = str(contract.get("verifier") or "").strip()
    if not verifier_name:
        return None
    try:
        result = run_success_verifier(
            verifier_name,
            project_root=project_root,
            story_key=story_key,
            output_file=output_file,
            contract=contract,
        )
    except PolicyError:
        return ({"verified": False, "reason": "verifier_contract_invalid"}, verifier_name)
    return (result, verifier_name)
