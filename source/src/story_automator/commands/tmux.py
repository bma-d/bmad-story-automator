from __future__ import annotations

import os
import re
import time

from story_automator.core.tmux_runtime import (
    agent_cli,
    agent_type,
    generate_session_name,
    heartbeat_check,
    runtime_mode,
    session_status,
    skill_prefix,
    spawn_session,
    tmux_has_session,
    tmux_kill_session,
    tmux_list_sessions,
)
from story_automator.core.review_verify import verify_code_review_completion
from story_automator.core.utils import (
    get_project_root,
    print_json,
    project_hash,
    project_slug,
)
from story_automator.core.workflow_paths import (
    create_story_workflow_paths,
    dev_story_workflow_paths,
    retrospective_workflow_paths,
    review_workflow_paths,
    testarch_automate_workflow_paths,
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
    root = get_project_root()
    out, code = spawn_session(session, command, agent, root, mode=runtime_mode())
    if code != 0:
        print(out.strip(), file=__import__("sys").stderr)
        return 1
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
    while idx < len(tail):
        if tail[idx] == "--agent" and idx + 1 < len(tail):
            agent = tail[idx + 1]
            idx += 2
            continue
        extra = f"{extra} {tail[idx]}".strip()
        idx += 1
    agent = agent or agent_type()
    if step == "retro" and agent != "codex":
        prompt = (
            f"/bmad-bmm-retrospective {story_id}\n\n"
            "Run the retrospective in #YOLO mode.\n"
            "Assume the user will NOT provide any input to the retrospective directly.\n"
            "Skip all WAIT for user instructions and continue autonomously."
        )
        prompt = prompt.replace('"', '\\"').replace("\n", " ")
        print(f'unset CLAUDECODE && claude --dangerously-skip-permissions "{prompt}"')
        return 0
    story_prefix = story_id.replace(".", "-")
    root = get_project_root()
    create_paths = create_story_workflow_paths(root)
    dev_paths = dev_story_workflow_paths(root)
    auto_paths = testarch_automate_workflow_paths(root)
    review_paths = review_workflow_paths(root)
    retro_paths = retrospective_workflow_paths(root)
    auto_label = _automate_workflow_label(auto_paths.workflow)
    auto_command = _automate_command(auto_paths.workflow, story_id)
    ai_command = os.environ.get("AI_COMMAND")
    if ai_command and not os.environ.get("AI_AGENT"):
        cli = ai_command
    elif agent != "codex":
        cli = agent_cli(agent)
    else:
        cli = "codex exec"
    workflow = {
        "create": f"/bmad-bmm-create-story {story_id} #YOLO",
        "dev": f"/bmad-bmm-dev-story {story_id} #YOLO",
        "auto": auto_command,
        "review": f"/bmad-bmm-story-automator-review {story_id} {extra or 'auto-fix all issues without prompting'}",
        "retro": f"/bmad-bmm-retrospective {story_id} #YOLO",
    }
    if step not in workflow:
        print(f"Unknown step type: {step}", file=__import__("sys").stderr)
        return 1
    if agent != "codex" or ai_command:
        print(f'unset CLAUDECODE && {cli} "{workflow[step]}"')
        return 0
    create_extra = ""
    if create_paths.instructions:
        create_extra += f"Then read: {create_paths.instructions}\n"
    if create_paths.template:
        create_extra += f"Use template: {create_paths.template}\n"
    if create_paths.checklist:
        create_extra += f"Validate with: {create_paths.checklist}\n"

    dev_extra = ""
    if dev_paths.instructions:
        dev_extra += f"Then read: {dev_paths.instructions}\n"
    if dev_paths.checklist:
        dev_extra += f"Validate with: {dev_paths.checklist}\n"

    auto_extra = ""
    if auto_paths.skill:
        auto_extra += f"READ this skill first: {auto_paths.skill}\n"
    if auto_paths.instructions:
        auto_extra += f"Then read: {auto_paths.instructions}\n"
    if auto_paths.checklist:
        auto_extra += f"Validate with: {auto_paths.checklist}\n"

    review_extra = ""
    if review_paths.instructions:
        review_extra += f"Then read: {review_paths.instructions}\n"
    if review_paths.checklist:
        review_extra += f"Validate with: {review_paths.checklist}\n"

    retro_extra = ""
    if retro_paths.instructions:
        retro_extra += f"Then read: {retro_paths.instructions}\n"

    prompt = {
        "create": (
            (
                f"Execute the BMAD create-story workflow for story {story_id}.\n\n"
                f"READ this skill first: {create_paths.skill}\n"
                f"READ this workflow file next: {create_paths.workflow}\n"
            )
            + create_extra
            + (
            f"Create story file at: _bmad-output/implementation-artifacts/{story_prefix}-*.md\n\n"
            f"Story ID: {story_id}\n\n#YOLO - Do NOT wait for user input."
            )
        ),
        "dev": (
            (
                f"Execute the BMAD dev-story workflow for story {story_id}.\n\n"
                f"READ this skill first: {dev_paths.skill}\n"
                f"READ this workflow file next: {dev_paths.workflow}\n"
            )
            + dev_extra
            + (
            f"Story file: _bmad-output/implementation-artifacts/{story_prefix}-*.md\n"
            "Implement all tasks marked [ ]. Run tests. Update checkboxes."
            )
        ),
        "auto": (
            (
                f"Execute the BMAD {auto_label} workflow for story {story_id}.\n\n"
                f"READ this workflow file first: {auto_paths.workflow}\n"
            )
            + auto_extra
            + (
            f"Story file: _bmad-output/implementation-artifacts/{story_prefix}-*.md\n"
            "Auto-apply all discovered gaps in tests."
            )
        ),
        "review": (
            (
                f"Execute the story-automator review workflow for story {story_id}.\n\n"
                f"READ this skill first: {review_paths.skill}\n"
                f"READ this workflow file next: {review_paths.workflow}\n"
            )
            + review_extra
            + (
            f"Story file: _bmad-output/implementation-artifacts/{story_prefix}-*.md\n"
            f"Review implementation, find issues, fix them automatically. {extra or 'auto-fix all issues without prompting'}"
            )
        ),
        "retro": (
            (
                f"Execute the BMAD retrospective workflow for epic {story_id}.\n\n"
                f"READ this skill first: {retro_paths.skill}\n"
                f"READ this workflow file next: {retro_paths.workflow}\n"
            )
            + retro_extra
            + "Run the retrospective in #YOLO mode and assume the user will NOT provide input."
        ),
    }[step]
    escaped = prompt.replace("\\", "\\\\").replace('"', '\\"')
    print(f'codex exec --full-auto "{escaped}"')
    return 0


def _automate_workflow_label(workflow_path: str) -> str:
    return "qa-generate-e2e-tests" if "qa-generate-e2e-tests" in workflow_path else "testarch-automate"


def _automate_command(workflow_path: str, story_id: str) -> str:
    if "qa-generate-e2e-tests" in workflow_path:
        return f"/bmad-bmm-qa-generate-e2e-tests {story_id} auto-apply all discovered gaps in tests"
    return f"/bmad-tea-testarch-automate {story_id} auto-apply all discovered gaps in tests"


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
    status, cpu, pid, prompt = heartbeat_check(session, agent, project_root=get_project_root(), mode=runtime_mode())
    print(f"{status},{cpu:.1f},{pid},{prompt}")
    return 0


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
    status = session_status(session, full=full, codex=codex, project_root=project_root, mode=runtime_mode())
    print(",".join([status["status"], str(status["todos_done"]), str(status["todos_total"]), status["active_task"], str(status["wait_estimate"]), status["session_state"]]))
    return 0 if codex else (0 if status["status"] != "error" else 1)


def cmd_monitor_session(args: list[str]) -> int:
    if not args:
        print("Usage: monitor-session <session_name> [options]", file=__import__("sys").stderr)
        return 1
    if args[0] in {"--help", "-h"}:
        print("Usage: monitor-session <session_name> [options]")
        print("Options: --max-polls N --initial-wait N --project-root PATH --timeout MIN --verbose --json --agent TYPE --workflow TYPE --story-key KEY")
        return 0
    session = args[0]
    max_polls = 30
    initial_wait = 5
    timeout_minutes = 60
    json_output = False
    agent = os.environ.get("AI_AGENT", "claude")
    workflow = "dev"
    story_key = ""
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
        status = session_status(session, full=False, codex=agent == "codex", project_root=project_root, mode=runtime_mode())
        if int(status["todos_done"]) or int(status["todos_total"]):
            last_done = int(status["todos_done"])
            last_total = int(status["todos_total"])
        state = str(status["session_state"])
        if state == "completed":
            output = session_status(session, full=True, codex=agent == "codex", project_root=project_root, mode=runtime_mode())["active_task"]
            if workflow == "review" and story_key:
                verified = verify_code_review_completion(project_root, story_key)
                if bool(verified.get("verified")):
                    return _emit_monitor(json_output, "completed", last_done, last_total, str(output), "verified_complete")
                return _emit_monitor(json_output, "incomplete", last_done, last_total, str(output), "workflow_not_verified")
            return _emit_monitor(json_output, "completed", last_done, last_total, str(output), "normal_completion")
        if state == "crashed":
            crashed = session_status(session, full=True, codex=agent == "codex", project_root=project_root, mode=runtime_mode())
            return _emit_monitor(
                json_output,
                "crashed",
                last_done,
                last_total,
                str(crashed["active_task"]),
                f"exit_code_{int(crashed['wait_estimate'])}",
            )
        if state == "stuck":
            output = session_status(session, full=True, codex=agent == "codex", project_root=project_root, mode=runtime_mode())["active_task"]
            return _emit_monitor(json_output, "stuck", 0, 0, str(output), "never_active")
        if state == "not_found":
            return _emit_monitor(json_output, "not_found", last_done, last_total, "", "session_gone")
        time.sleep(min(180 if agent == "codex" else 120, max(5, int(status["wait_estimate"]))))
    output = session_status(session, full=True, codex=agent == "codex", project_root=project_root, mode=runtime_mode())["active_task"]
    return _emit_monitor(json_output, "timeout", last_done, last_total, str(output), "max_polls_exceeded")


def _emit_monitor(json_output: bool, state: str, done: int, total: int, output_file: str, reason: str) -> int:
    if json_output:
        print_json({"final_state": state, "todos_done": done, "todos_total": total, "output_file": output_file, "exit_reason": reason, "output_verified": bool(output_file)})
    else:
        print(f"{state},{done},{total},{output_file},{reason}")
    return 0
