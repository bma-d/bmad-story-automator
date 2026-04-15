from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from story_automator.commands.orchestrator import cmd_orchestrator_helper
from story_automator.commands.state import cmd_build_state_doc, cmd_validate_state
from story_automator.commands.tmux import _build_cmd


REPO_ROOT = Path(__file__).resolve().parents[2]


class StatePolicyMetadataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.project_root = Path(self.tmp.name)
        self.output_dir = self.project_root / "_bmad-output" / "story-automator"
        self._install_bundle()
        self._install_required_skills()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_state_doc_writes_policy_metadata(self) -> None:
        stdout = io.StringIO()
        template = self.project_root / ".claude" / "skills" / "bmad-story-automator" / "templates" / "state-document.md"
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_build_state_doc(
                [
                    "--template",
                    str(template),
                    "--output-folder",
                    str(self.output_dir),
                    "--config-json",
                    json.dumps(self._config()),
                ]
            )
        self.assertEqual(code, 0)
        state_file = Path(json.loads(stdout.getvalue())["path"])
        text = state_file.read_text(encoding="utf-8")
        self.assertIn("policySnapshotFile:", text)
        self.assertIn("policySnapshotHash:", text)

    def test_summary_surfaces_policy_metadata(self) -> None:
        state_file = self._build_state()
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_orchestrator_helper(["state-summary", str(state_file)])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["policySnapshotFile"])
        self.assertTrue(payload["policySnapshotHash"])

    def test_legacy_state_without_policy_metadata_remains_valid(self) -> None:
        legacy = self.project_root / "legacy.md"
        legacy.write_text(
            "---\nepic: \"1\"\nepicName: \"Epic 1\"\nstoryRange: [\"1.1\"]\nstatus: \"READY\"\nlastUpdated: \"2026-04-13T00:00:00Z\"\naiCommand: \"claude\"\n---\n",
            encoding="utf-8",
        )
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_validate_state(["--state", str(legacy)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["structure"], "ok")

    def test_summary_infers_legacy_policy_for_old_state(self) -> None:
        legacy = self.project_root / "legacy.md"
        legacy.write_text(
            "---\nepic: \"1\"\nepicName: \"Epic 1\"\nstoryRange: [\"1.1\"]\nstatus: \"READY\"\nlastUpdated: \"2026-04-13T00:00:00Z\"\naiCommand: \"claude\"\n---\n",
            encoding="utf-8",
        )
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_orchestrator_helper(["state-summary", str(legacy)])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["policySnapshotFile"], "")
        self.assertEqual(payload["policySnapshotHash"], "")
        self.assertEqual(payload["legacyPolicy"], "true")

    def test_validate_state_rejects_new_state_with_missing_snapshot(self) -> None:
        state_file = self.project_root / "orchestration.md"
        state_file.write_text(
            "---\nepic: \"1\"\nepicName: \"Epic 1\"\nstoryRange: [\"1.1\"]\nstatus: \"READY\"\nlastUpdated: \"2026-04-13T00:00:00Z\"\naiCommand: \"claude\"\npolicySnapshotFile: \"_bmad-output/story-automator/snapshots/missing.json\"\npolicySnapshotHash: \"deadbeef\"\n---\n",
            encoding="utf-8",
        )
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_validate_state(["--state", str(state_file)])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["structure"], "issues")
        self.assertTrue(any("policy snapshot missing" in issue for issue in payload["issues"]))

    def test_validate_state_rejects_new_state_missing_snapshot_metadata(self) -> None:
        state_file = self.project_root / "orchestration.md"
        state_file.write_text(
            "---\nepic: \"1\"\nepicName: \"Epic 1\"\nstoryRange: [\"1.1\"]\nstatus: \"READY\"\nlastUpdated: \"2026-04-13T00:00:00Z\"\naiCommand: \"claude\"\npolicyVersion: 1\nlegacyPolicy: false\n---\n",
            encoding="utf-8",
        )
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_validate_state(["--state", str(state_file)])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["structure"], "issues")
        self.assertTrue(any("state policy snapshot missing" in issue for issue in payload["issues"]))

    def test_summary_does_not_infer_legacy_for_new_state_missing_snapshot_metadata(self) -> None:
        state_file = self.project_root / "orchestration.md"
        state_file.write_text(
            "---\nepic: \"1\"\nepicName: \"Epic 1\"\nstoryRange: [\"1.1\"]\nstatus: \"READY\"\nlastUpdated: \"2026-04-13T00:00:00Z\"\naiCommand: \"claude\"\npolicyVersion: 1\n---\n",
            encoding="utf-8",
        )
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_orchestrator_helper(["state-summary", str(state_file)])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["legacyPolicy"], "false")

    def test_summary_does_not_mark_contradictory_legacy_flag_as_legacy(self) -> None:
        state_file = self.project_root / "orchestration.md"
        state_file.write_text(
            "---\nepic: \"1\"\nepicName: \"Epic 1\"\nstoryRange: [\"1.1\"]\nstatus: \"READY\"\nlastUpdated: \"2026-04-13T00:00:00Z\"\naiCommand: \"claude\"\npolicyVersion: 1\nlegacyPolicy: true\n---\n",
            encoding="utf-8",
        )
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_orchestrator_helper(["state-summary", str(state_file)])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["legacyPolicy"], "false")
        self.assertEqual(payload["policyError"], "state policy snapshot missing")

    def test_summary_clears_contradictory_snapshot_metadata(self) -> None:
        state_file = self.project_root / "orchestration.md"
        state_file.write_text(
            "---\npolicySnapshotFile: \"snap.json\"\npolicySnapshotHash: \"deadbeef\"\nlegacyPolicy: true\n---\n",
            encoding="utf-8",
        )
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_orchestrator_helper(["state-summary", str(state_file)])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["policySnapshotFile"], "")
        self.assertEqual(payload["policySnapshotHash"], "")
        self.assertEqual(payload["legacyPolicy"], "false")
        self.assertEqual(payload["policyError"], "state policy metadata contradictory")

    def test_summary_clears_incomplete_snapshot_metadata(self) -> None:
        state_file = self.project_root / "orchestration.md"
        state_file.write_text(
            "---\npolicySnapshotFile: \"snap.json\"\n---\n",
            encoding="utf-8",
        )
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_orchestrator_helper(["state-summary", str(state_file)])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["policySnapshotFile"], "")
        self.assertEqual(payload["policySnapshotHash"], "")
        self.assertEqual(payload["legacyPolicy"], "false")
        self.assertEqual(payload["policyError"], "state policy metadata incomplete")

    def test_summary_reports_missing_snapshot_reference(self) -> None:
        state_file = self.project_root / "orchestration.md"
        state_file.write_text(
            "---\npolicySnapshotFile: \"missing.json\"\npolicySnapshotHash: \"deadbeef\"\n---\n",
            encoding="utf-8",
        )
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_orchestrator_helper(["state-summary", str(state_file)])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["policySnapshotFile"], "")
        self.assertEqual(payload["policySnapshotHash"], "")
        self.assertIn("policy snapshot missing", payload["policyError"])

    def test_summary_reports_snapshot_hash_mismatch(self) -> None:
        state_file = self._build_state()
        lines = []
        for line in state_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("policySnapshotHash: "):
                lines.append('policySnapshotHash: "deadbeef"')
            else:
                lines.append(line)
        state_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_orchestrator_helper(["state-summary", str(state_file)])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["policySnapshotFile"], "")
        self.assertEqual(payload["policySnapshotHash"], "")
        self.assertIn("policy snapshot hash mismatch", payload["policyError"])

    def test_summary_uses_runtime_root_for_relative_snapshot_validation(self) -> None:
        outside = self.project_root.parent / "outside-state"
        outside.mkdir(parents=True, exist_ok=True)
        shadow = outside / "snap.json"
        shadow.write_text("{}", encoding="utf-8")
        state_file = outside / "orchestration.md"
        state_file.write_text(
            "---\npolicySnapshotFile: \"snap.json\"\npolicySnapshotHash: \"99999999\"\n---\n",
            encoding="utf-8",
        )
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_orchestrator_helper(["state-summary", str(state_file)])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["policySnapshotFile"], "")
        self.assertEqual(payload["policySnapshotHash"], "")
        self.assertIn("policy snapshot missing", payload["policyError"])

    def test_escalate_uses_pinned_snapshot_when_state_file_provided(self) -> None:
        state_file = self._build_state()
        override_dir = self.project_root / "_bmad" / "bmm"
        override_dir.mkdir(parents=True, exist_ok=True)
        (override_dir / "story-automator.policy.json").write_text(
            json.dumps({"workflow": {"repeat": {"review": {"maxCycles": 1}}}}),
            encoding="utf-8",
        )
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_orchestrator_helper(["escalate", "review-loop", "cycles=2", "--state-file", str(state_file)])
        self.assertEqual(code, 0)
        self.assertFalse(json.loads(stdout.getvalue())["escalate"])

    def test_escalate_returns_json_when_state_snapshot_is_invalid(self) -> None:
        state_file = self.project_root / "orchestration.md"
        state_file.write_text(
            "---\npolicySnapshotFile: \"missing.json\"\npolicySnapshotHash: \"deadbeef\"\n---\n",
            encoding="utf-8",
        )
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_orchestrator_helper(["escalate", "review-loop", "cycles=1", "--state-file", str(state_file)])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["escalate"])
        self.assertIn("policy snapshot missing", payload["reason"])

    def test_build_cmd_does_not_treat_state_file_flag_as_prompt_text(self) -> None:
        state_file = self._build_state()
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = _build_cmd(["review", "1.1", "--state-file", str(state_file)])
        self.assertEqual(code, 0)
        rendered = stdout.getvalue()
        self.assertNotIn("--state-file", rendered)
        self.assertNotIn(str(state_file), rendered)

    def test_build_state_doc_returns_json_on_policy_snapshot_failure(self) -> None:
        override_dir = self.project_root / "_bmad" / "bmm"
        override_dir.mkdir(parents=True, exist_ok=True)
        (override_dir / "story-automator.policy.json").write_text(
            json.dumps({"snapshot": {"relativeDir": "../outside"}}),
            encoding="utf-8",
        )
        stdout = io.StringIO()
        template = self.project_root / ".claude" / "skills" / "bmad-story-automator" / "templates" / "state-document.md"
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_build_state_doc(
                [
                    "--template",
                    str(template),
                    "--output-folder",
                    str(self.output_dir),
                    "--config-json",
                    json.dumps(self._config()),
                ]
            )
        self.assertEqual(code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"], "policy_snapshot_failed")

    def test_build_cmd_rejects_unknown_step_via_policy(self) -> None:
        stderr = io.StringIO()
        with patch_env(self.project_root), redirect_stderr(stderr):
            code = _build_cmd(["ship", "1.1"])
        self.assertEqual(code, 1)
        self.assertIn("unknown step: ship", stderr.getvalue())

    def _build_state(self) -> Path:
        stdout = io.StringIO()
        template = self.project_root / ".claude" / "skills" / "bmad-story-automator" / "templates" / "state-document.md"
        with patch_env(self.project_root), redirect_stdout(stdout):
            cmd_build_state_doc(
                [
                    "--template",
                    str(template),
                    "--output-folder",
                    str(self.output_dir),
                    "--config-json",
                    json.dumps(self._config()),
                ]
            )
        return Path(json.loads(stdout.getvalue())["path"])

    def _config(self) -> dict[str, object]:
        return {
            "epic": "1",
            "epicName": "Epic 1",
            "storyRange": ["1.1"],
            "status": "READY",
            "aiCommand": "claude --dangerously-skip-permissions",
        }

    def _install_bundle(self) -> None:
        source_skill = REPO_ROOT / "payload" / ".claude" / "skills" / "bmad-story-automator"
        source_review = REPO_ROOT / "payload" / ".claude" / "skills" / "bmad-story-automator-review"
        target_root = self.project_root / ".claude" / "skills"
        target_root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_skill, target_root / "bmad-story-automator")
        shutil.copytree(source_review, target_root / "bmad-story-automator-review")

    def _install_required_skills(self) -> None:
        for name in ("bmad-create-story", "bmad-dev-story", "bmad-retrospective", "bmad-qa-generate-e2e-tests"):
            skill_dir = self.project_root / ".claude" / "skills" / name
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")
            (skill_dir / "workflow.md").write_text(f"# {name}\n", encoding="utf-8")
        (self.project_root / ".claude" / "skills" / "bmad-create-story" / "discover-inputs.md").write_text("# discover\n", encoding="utf-8")
        (self.project_root / ".claude" / "skills" / "bmad-create-story" / "checklist.md").write_text("# checklist\n", encoding="utf-8")
        (self.project_root / ".claude" / "skills" / "bmad-create-story" / "template.md").write_text("# template\n", encoding="utf-8")
        (self.project_root / ".claude" / "skills" / "bmad-dev-story" / "checklist.md").write_text("# checklist\n", encoding="utf-8")
        (self.project_root / ".claude" / "skills" / "bmad-qa-generate-e2e-tests" / "checklist.md").write_text("# checklist\n", encoding="utf-8")


class patch_env:
    def __init__(self, project_root: Path) -> None:
        self.project_root = str(project_root)
        self.previous = None

    def __enter__(self) -> None:
        import os

        self.previous = os.environ.get("PROJECT_ROOT")
        os.environ["PROJECT_ROOT"] = self.project_root

    def __exit__(self, exc_type, exc, tb) -> None:
        import os

        if self.previous is None:
            os.environ.pop("PROJECT_ROOT", None)
        else:
            os.environ["PROJECT_ROOT"] = self.previous


if __name__ == "__main__":
    unittest.main()
