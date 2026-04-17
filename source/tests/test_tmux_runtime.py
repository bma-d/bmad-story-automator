from __future__ import annotations

import os
import stat
import tempfile
import time
import unittest
from unittest import mock
from pathlib import Path

from story_automator.core.tmux_runtime import (
    PaneSnapshot,
    _check_prompt_visible,
    _claude_completion_marker_present,
    _legacy_heartbeat_check,
    _reconcile_runner_state,
    _runner_file_content,
    cleanup_stale_terminal_artifacts,
    command_exists,
    heartbeat_check,
    load_session_state,
    pane_status,
    resolve_command_shell,
    skill_prefix,
    save_session_state,
    session_paths,
    session_status,
    spawn_session,
    tmux_kill_session,
    _runner_session_status,
    _terminal_runner_status,
    update_session_state,
)


@unittest.skipUnless(command_exists("tmux"), "tmux not available")
class TmuxRuntimeIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = self.temp_dir.name
        self.sessions: list[str] = []

    def tearDown(self) -> None:
        for session in self.sessions:
            tmux_kill_session(session, self.project_root)
        self.temp_dir.cleanup()

    def _session_name(self, suffix: str) -> str:
        session = f"sa-test-{suffix}-{int(time.time() * 1000)}"
        self.sessions.append(session)
        return session

    def _wait_for_terminal(self, session: str, *, codex: bool) -> dict[str, str | int]:
        timeout_seconds = float(os.environ.get("TMUX_TEST_TIMEOUT_SECONDS", "15"))
        deadline = time.time() + timeout_seconds
        last = session_status(session, full=False, codex=codex, project_root=self.project_root, mode="runner")
        while time.time() < deadline:
            last = session_status(session, full=False, codex=codex, project_root=self.project_root, mode="runner")
            if str(last["session_state"]) in {"completed", "crashed", "stuck"}:
                return last
            time.sleep(0.1)
        self.fail(f"session {session} did not reach terminal state, last={last}")

    def test_runner_spawn_success_records_state_and_keeps_dead_pane(self) -> None:
        session = self._session_name("success")
        output, code = spawn_session(session, "printf hello", "codex", self.project_root, mode="runner")
        self.assertEqual((output, code), ("", 0))

        status = self._wait_for_terminal(session, codex=True)
        self.assertEqual(status["session_state"], "completed")
        self.assertEqual(status["status"], "idle")
        self.assertEqual(pane_status(session), "exited:0")

        paths = session_paths(session, self.project_root)
        state = load_session_state(paths.state)
        self.assertEqual(state["schemaVersion"], 1)
        self.assertEqual(state["lifecycle"], "finished")
        self.assertEqual(state["result"], "success")
        self.assertEqual(state["exitCode"], 0)
        self.assertEqual(stat.S_IMODE(paths.state.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(paths.command.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(paths.runner.stat().st_mode), 0o700)

        full_status = session_status(session, full=True, codex=True, project_root=self.project_root, mode="runner")
        output_path = Path(str(full_status["active_task"]))
        self.assertTrue(output_path.exists())
        self.assertIn("hello", output_path.read_text(encoding="utf-8"))

    def test_runner_spawn_nonzero_exit_maps_to_crashed(self) -> None:
        session = self._session_name("failure")
        output, code = spawn_session(session, "printf boom && exit 9", "codex", self.project_root, mode="runner")
        self.assertEqual((output, code), ("", 0))

        status = self._wait_for_terminal(session, codex=True)
        self.assertEqual(status["session_state"], "crashed")
        self.assertEqual(status["status"], "crashed")
        self.assertEqual(status["wait_estimate"], 9)

        paths = session_paths(session, self.project_root)
        state = load_session_state(paths.state)
        self.assertEqual(state["result"], "failure")
        self.assertEqual(state["exitCode"], 9)


class TmuxRuntimeStateTests(unittest.TestCase):
    def test_skill_prefix_matches_pure_skill_layout(self) -> None:
        self.assertEqual(skill_prefix("claude"), "bmad-")
        self.assertEqual(skill_prefix("codex"), "none")

    def test_resolve_command_shell_prefers_tmux_default_shell(self) -> None:
        with (
            mock.patch("story_automator.core.tmux_runtime.command_exists", return_value=True),
            mock.patch("story_automator.core.tmux_runtime.run_cmd", return_value=("/bin/zsh\n", 0)),
            mock.patch("story_automator.core.tmux_runtime.os.path.isfile", return_value=True),
            mock.patch("story_automator.core.tmux_runtime.os.access", return_value=True),
        ):
            self.assertEqual(resolve_command_shell(), "/bin/zsh")

    def test_runner_file_content_uses_interactive_shell_for_zsh_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = session_paths("sa-test-shell", temp_dir)
            content = _runner_file_content(paths, "/bin/bash", "/bin/zsh", temp_dir)
        self.assertIn('COMMAND_SHELL=/bin/zsh', content)
        self.assertIn('"$COMMAND_SHELL" "$COMMAND_FILE"', content)
        self.assertIn('"$exit_code" -eq 131', content)

    def test_session_paths_rejects_unsafe_session_names(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                session_paths("../escape", temp_dir)

    def test_update_session_state_refreshes_updated_at(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "state.json"
            save_session_state(
                state_path,
                {
                    "updatedAt": "2026-04-14T18:44:00Z",
                    "lifecycle": "created",
                },
            )
            with mock.patch("story_automator.core.tmux_runtime.iso_now", return_value="2026-04-14T18:45:00Z"):
                state = update_session_state(state_path, lifecycle="running")
            self.assertEqual(state["updatedAt"], "2026-04-14T18:45:00Z")
            self.assertEqual(load_session_state(state_path)["updatedAt"], "2026-04-14T18:45:00Z")

    def test_check_prompt_visible_accepts_claude_prompt_before_status_panel(self) -> None:
        capture = "\n".join(
            [
                "",
                "✻ Baked for 4m 55s",
                "",
                "────────────────────────────────────────",
                "❯ ",
                "────────────────────────────────────────",
                "  Model: Sonnet 4.6",
                "  Session: 4m",
                "  bypass permissions on",
            ]
        )
        with mock.patch("story_automator.core.tmux_runtime._capture_text", return_value=capture):
            self.assertEqual(_check_prompt_visible("sa-test"), "true")

    def test_runner_claude_prompt_completion_maps_to_completed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            session = "sa-test-claude-complete"
            paths = session_paths(session, temp_dir)
            save_session_state(
                paths.state,
                {
                    "schemaVersion": 1,
                    "session": session,
                    "agent": "claude",
                    "projectRoot": temp_dir,
                    "paneId": "%1",
                    "panePid": 1,
                    "runnerPid": 1,
                    "childPid": 2,
                    "commandFile": str(paths.command),
                    "outputHint": str(paths.output),
                    "createdAt": "2026-04-14T18:43:59Z",
                    "startedAt": "2026-04-14T18:43:59Z",
                    "finishedAt": "",
                    "updatedAt": "2026-04-14T18:44:00Z",
                    "lifecycle": "running",
                    "result": "",
                    "exitCode": "",
                    "failureReason": "",
                },
            )
            capture = "Story created.\n\nBaked for 4m 55s\n\n❯ "
            with (
                mock.patch("story_automator.core.tmux_runtime._capture_text", return_value=capture),
                mock.patch("story_automator.core.tmux_runtime._check_prompt_visible", return_value="true"),
                mock.patch(
                    "story_automator.core.tmux_runtime._pane_snapshot",
                    return_value=PaneSnapshot(exists=True, pane_id="%1", pane_pid=1, dead=False, dead_status=None),
                ),
                mock.patch("story_automator.core.tmux_runtime._pid_alive", side_effect=lambda pid: pid in {1, 2}),
            ):
                status = _runner_session_status(session, full=False, codex=False, project_root=temp_dir)

            self.assertEqual(status["session_state"], "completed")
            self.assertEqual(status["status"], "idle")

            state = load_session_state(paths.state)
            self.assertEqual(state["lifecycle"], "finished")
            self.assertEqual(state["result"], "success")
            self.assertEqual(state["exitCode"], 0)
            self.assertEqual(state["failureReason"], "")

    def test_claude_completion_marker_ignores_generic_duration_text(self) -> None:
        capture = "all tests passed for 3m 10s\n\n❯ "
        self.assertFalse(_claude_completion_marker_present(capture))

    def test_reconcile_dead_pane_without_status_maps_to_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            session = "sa-test-pane-dead-unknown"
            paths = session_paths(session, temp_dir)
            save_session_state(
                paths.state,
                {
                    "schemaVersion": 1,
                    "session": session,
                    "agent": "codex",
                    "projectRoot": temp_dir,
                    "paneId": "%1",
                    "panePid": 1,
                    "runnerPid": 1,
                    "childPid": 2,
                    "commandFile": str(paths.command),
                    "outputHint": str(paths.output),
                    "createdAt": "2026-04-14T18:43:59Z",
                    "startedAt": "2026-04-14T18:43:59Z",
                    "finishedAt": "",
                    "updatedAt": "2026-04-14T18:44:00Z",
                    "lifecycle": "running",
                    "result": "",
                    "exitCode": "",
                    "failureReason": "",
                },
            )

            reconciled = _reconcile_runner_state(
                paths,
                load_session_state(paths.state),
                PaneSnapshot(exists=True, pane_id="%1", pane_pid=1, dead=True, dead_status=None),
            )

            self.assertEqual(reconciled["lifecycle"], "finished")
            self.assertEqual(reconciled["result"], "unknown")
            self.assertEqual(reconciled["exitCode"], "")
            self.assertEqual(reconciled["failureReason"], "pane_dead_unknown_status")

    def test_launch_never_succeeded_maps_to_stuck(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            session = "sa-test-launch-stuck"
            paths = session_paths(session, temp_dir)
            save_session_state(
                paths.state,
                {
                    "schemaVersion": 1,
                    "session": session,
                    "agent": "codex",
                    "projectRoot": temp_dir,
                    "paneId": "%1",
                    "panePid": "",
                    "runnerPid": "",
                    "childPid": "",
                    "commandFile": str(paths.command),
                    "outputHint": str(paths.output),
                    "createdAt": "2026-04-13T00:00:00Z",
                    "startedAt": "",
                    "finishedAt": "2026-04-13T00:00:01Z",
                    "updatedAt": "2026-04-13T00:00:01Z",
                    "lifecycle": "finished",
                    "result": "unknown",
                    "exitCode": "",
                    "failureReason": "launch_never_succeeded",
                },
            )
            status = _terminal_runner_status(session, load_session_state(paths.state), full=False, project_root=temp_dir)
            self.assertEqual(status["session_state"], "stuck")
            self.assertEqual(status["status"], "idle")

    def test_cleanup_stale_terminal_artifacts_removes_old_terminal_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            session = "sa-test-cleanup"
            paths = session_paths(session, temp_dir)
            save_session_state(
                paths.state,
                {
                    "schemaVersion": 1,
                    "session": session,
                    "agent": "codex",
                    "projectRoot": temp_dir,
                    "paneId": "%1",
                    "panePid": 1,
                    "runnerPid": 2,
                    "childPid": 3,
                    "commandFile": str(paths.command),
                    "outputHint": str(paths.output),
                    "createdAt": "2026-04-13T00:00:00Z",
                    "startedAt": "2026-04-13T00:00:01Z",
                    "finishedAt": "2026-04-13T00:00:02Z",
                    "updatedAt": "2026-04-13T00:00:02Z",
                    "lifecycle": "finished",
                    "result": "success",
                    "exitCode": 0,
                    "failureReason": "",
                },
            )
            for path in (paths.command, paths.runner, paths.output):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("x", encoding="utf-8")
            stale_time = time.time() - (25 * 60 * 60)
            for path in (paths.state, paths.command, paths.runner, paths.output):
                os.utime(path, (stale_time, stale_time))

            cleanup_stale_terminal_artifacts(temp_dir)

            for path in (paths.state, paths.command, paths.runner, paths.output):
                self.assertFalse(path.exists(), f"expected stale artifact removal for {path}")

    def test_cleanup_stale_terminal_artifacts_keeps_old_running_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            session = "sa-test-active-cleanup"
            paths = session_paths(session, temp_dir)
            save_session_state(
                paths.state,
                {
                    "schemaVersion": 1,
                    "session": session,
                    "agent": "codex",
                    "projectRoot": temp_dir,
                    "paneId": "%1",
                    "panePid": 1,
                    "runnerPid": 2,
                    "childPid": 3,
                    "commandFile": str(paths.command),
                    "outputHint": str(paths.output),
                    "createdAt": "2026-04-13T00:00:00Z",
                    "startedAt": "2026-04-13T00:00:01Z",
                    "finishedAt": "",
                    "updatedAt": "2026-04-13T00:00:02Z",
                    "lifecycle": "running",
                    "result": "",
                    "exitCode": "",
                    "failureReason": "",
                },
            )
            for path in (paths.command, paths.runner, paths.output):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("x", encoding="utf-8")
            stale_time = time.time() - (25 * 60 * 60)
            for path in (paths.state, paths.command, paths.runner, paths.output):
                os.utime(path, (stale_time, stale_time))

            cleanup_stale_terminal_artifacts(temp_dir)

            for path in (paths.state, paths.command, paths.runner, paths.output):
                self.assertTrue(path.exists(), f"expected active artifact preservation for {path}")

    def test_pane_status_treats_fractional_cpu_as_alive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            session = "sa-test-fractional-cpu"
            paths = session_paths(session, temp_dir)
            save_session_state(
                paths.state,
                {
                    "schemaVersion": 1,
                    "session": session,
                    "agent": "codex",
                    "projectRoot": temp_dir,
                    "paneId": "%1",
                    "panePid": 10,
                    "runnerPid": 11,
                    "childPid": 12,
                    "commandFile": str(paths.command),
                    "outputHint": str(paths.output),
                    "createdAt": "2026-04-14T18:43:59Z",
                    "startedAt": "2026-04-14T18:43:59Z",
                    "finishedAt": "",
                    "updatedAt": "2026-04-14T18:44:00Z",
                    "lifecycle": "running",
                    "result": "",
                    "exitCode": "",
                    "failureReason": "",
                },
            )
            with (
                mock.patch("story_automator.core.tmux_runtime._process_cpu", return_value=0.5),
                mock.patch("story_automator.core.tmux_runtime._pid_alive", return_value=True),
                mock.patch("story_automator.core.tmux_runtime._check_prompt_visible", return_value="false"),
                mock.patch("story_automator.core.tmux_runtime.tmux_has_session", return_value=True),
            ):
                status, cpu, pid, prompt = heartbeat_check(session, "codex", project_root=temp_dir, mode="runner")

            self.assertEqual(status, "alive")
            self.assertEqual(cpu, 0.5)
            self.assertEqual(pid, "12")
            self.assertEqual(prompt, "false")

    def test_legacy_heartbeat_treats_fractional_cpu_as_alive(self) -> None:
        with (
            mock.patch("story_automator.core.tmux_runtime.tmux_has_session", return_value=True),
            mock.patch("story_automator.core.tmux_runtime._capture_text", return_value="working"),
            mock.patch("story_automator.core.tmux_runtime.tmux_display", return_value="10"),
            mock.patch("story_automator.core.tmux_runtime._find_agent_pid", return_value="12"),
            mock.patch("story_automator.core.tmux_runtime._process_cpu", return_value=0.5),
        ):
            status, cpu, pid, prompt = _legacy_heartbeat_check("sa-test-legacy-cpu", "codex")

        self.assertEqual(status, "alive")
        self.assertEqual(cpu, 0.5)
        self.assertEqual(pid, "12")
        self.assertEqual(prompt, "false")


if __name__ == "__main__":
    unittest.main()
