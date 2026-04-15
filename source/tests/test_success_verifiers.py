from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from story_automator.commands.orchestrator import cmd_orchestrator_helper
from story_automator.commands.state import cmd_build_state_doc
from story_automator.commands.tmux import _verify_monitor_completion
from story_automator.commands.validate_story_creation import cmd_validate_story_creation
from story_automator.core.review_verify import verify_code_review_completion
from story_automator.core.runtime_policy import PolicyError
from story_automator.core.success_verifiers import create_story_artifact, epic_complete, review_completion


REPO_ROOT = Path(__file__).resolve().parents[2]


class SuccessVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.project_root = Path(self.tmp.name)
        self.output_dir = self.project_root / "_bmad-output" / "story-automator"
        self.artifacts_dir = self.project_root / "_bmad-output" / "implementation-artifacts"
        self._install_bundle()
        self._install_required_skills()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_create_story_artifact_matches_configured_glob(self) -> None:
        self._write_story("1-2-example", status="draft")
        payload = create_story_artifact(
            project_root=str(self.project_root),
            story_key="1.2",
            contract={"config": {"glob": "_bmad-output/implementation-artifacts/{story_prefix}-*.md", "expectedMatches": 1}},
        )
        self.assertTrue(payload["verified"])
        self.assertEqual(payload["actualMatches"], 1)

    def test_review_completion_uses_contract_done_values(self) -> None:
        self._write_story("1-2-example", status="approved")
        contract = self._write_review_contract(
            {"doneValues": ["approved"], "sourceOrder": ["story-file"], "syncSprintStatus": False}
        )
        payload = review_completion(
            project_root=str(self.project_root),
            story_key="1.2",
            contract={"contractPath": str(contract)},
        )
        self.assertTrue(payload["verified"])
        self.assertEqual(payload["source"], "story-file")
        self.assertNotIn("note", payload)

    def test_review_completion_rejects_invalid_contract(self) -> None:
        contract = self._write_review_contract({"sourceOrder": ["bad-source"]})
        with self.assertRaises(PolicyError):
            review_completion(
                project_root=str(self.project_root),
                story_key="1.2",
                contract={"contractPath": str(contract)},
            )

    def test_review_completion_rejects_empty_contract_lists(self) -> None:
        with self.assertRaises(PolicyError):
            review_completion(
                project_root=str(self.project_root),
                story_key="1.2",
                contract={"doneValues": [], "sourceOrder": []},
            )

    def test_review_completion_rejects_whitespace_only_done_values(self) -> None:
        with self.assertRaises(PolicyError):
            review_completion(
                project_root=str(self.project_root),
                story_key="1.2",
                contract={"doneValues": ["   "], "sourceOrder": ["story-file"]},
            )

    def test_epic_complete_checks_sprint_status(self) -> None:
        self._write_sprint_status("1-1-story-one: done\n1-2-story-two: done\n")
        payload = epic_complete(project_root=str(self.project_root), story_key="1.2")
        self.assertTrue(payload["verified"])
        self.assertEqual(payload["doneStories"], 2)

    def test_epic_complete_accepts_bare_epic_id(self) -> None:
        self._write_sprint_status("1-1-story-one: done\n1-2-story-two: done\n")
        payload = epic_complete(project_root=str(self.project_root), story_key="1")
        self.assertTrue(payload["verified"])
        self.assertEqual(payload["epic"], "1")

    def test_review_wrapper_uses_pinned_state_snapshot(self) -> None:
        self._write_story("1-2-example", status="approved")
        state_file = self._build_state()
        self._write_override(
            {
                "steps": {
                    "review": {
                        "success": {
                            "config": {"doneValues": ["approved"], "sourceOrder": ["story-file"], "syncSprintStatus": False}
                        }
                    }
                }
            }
        )
        payload = verify_code_review_completion(str(self.project_root), "1.2", state_file=state_file)
        self.assertFalse(payload["verified"])
        self.assertEqual(payload["reason"], "workflow_not_complete")

    def test_review_wrapper_ignores_unrelated_missing_assets(self) -> None:
        shutil.rmtree(self.project_root / ".claude" / "skills" / "bmad-create-story")
        self._write_story("1-2-example", status="done")
        payload = verify_code_review_completion(str(self.project_root), "1.2")
        self.assertTrue(payload["verified"])
        self.assertEqual(payload["source"], "story-file")

    def test_monitor_dispatch_uses_review_verifier_from_contract(self) -> None:
        self._write_story("1-2-example", status="done")
        result = _verify_monitor_completion(
            "review",
            project_root=str(self.project_root),
            story_key="1.2",
            output_file="/tmp/session.txt",
        )
        self.assertIsNotNone(result)
        payload, verifier = result or ({}, "")
        self.assertEqual(verifier, "review_completion")
        self.assertTrue(payload["verified"])

    def test_monitor_dispatch_skips_story_keyed_verifier_without_story_key(self) -> None:
        result = _verify_monitor_completion(
            "review",
            project_root=str(self.project_root),
            story_key="",
            output_file="/tmp/session.txt",
        )
        self.assertIsNotNone(result)
        payload, verifier = result or ({}, "")
        self.assertEqual(verifier, "review_completion")
        self.assertFalse(payload["verified"])
        self.assertEqual(payload["reason"], "story_key_required")

    def test_monitor_dispatch_allows_session_exit_without_story_key(self) -> None:
        result = _verify_monitor_completion(
            "dev",
            project_root=str(self.project_root),
            story_key="",
            output_file="/tmp/session.txt",
        )
        self.assertIsNotNone(result)
        payload, verifier = result or ({}, "")
        self.assertEqual(verifier, "session_exit")
        self.assertTrue(payload["verified"])

    def test_verify_step_create_uses_shared_verifier(self) -> None:
        self._write_story("1-2-example", status="draft")
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_orchestrator_helper(["verify-step", "create", "1.2"])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["verified"])
        self.assertEqual(payload["source"], "artifact_glob")

    def test_verify_step_create_uses_pinned_snapshot(self) -> None:
        self._write_story("1-2-example", status="draft")
        state_file = self._build_state()
        self._write_override({"steps": {"create": {"success": {"config": {"expectedMatches": 2}}}}})
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_orchestrator_helper(["verify-step", "create", "1.2", "--state-file", str(state_file)])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["verified"])
        self.assertEqual(payload["expectedMatches"], 1)

    def test_verify_step_create_returns_json_on_verification_failure(self) -> None:
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_orchestrator_helper(["verify-step", "create", "1.2"])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["verified"])
        self.assertEqual(payload["reason"], "unexpected_story_artifact_count")

    def test_validate_story_creation_check_uses_shared_verifier(self) -> None:
        self._write_story("1-2-example", status="draft")
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_validate_story_creation(["check", "1.2"])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["valid"])
        self.assertTrue(payload["verified"])
        self.assertEqual(payload["created_count"], 1)
        self.assertEqual(payload["expected"], 1)

    def test_validate_story_creation_check_uses_pinned_snapshot(self) -> None:
        self._write_story("1-2-example", status="draft")
        state_file = self._build_state()
        self._write_override({"steps": {"create": {"success": {"config": {"expectedMatches": 2}}}}})
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_validate_story_creation(["check", "1.2", "--state-file", str(state_file)])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["expected"], 1)

    def test_validate_story_creation_check_uses_before_after_delta(self) -> None:
        self._write_story("1-2-existing", status="draft")
        self._write_story("1-2-new", status="draft")
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_validate_story_creation(["check", "1.2", "--before", "1", "--after", "2"])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["created_count"], 1)
        self.assertEqual(payload["before"], 1)
        self.assertEqual(payload["after"], 2)

    def test_validate_story_creation_positional_mode_forwards_state_file(self) -> None:
        self._write_story("1-2-example", status="draft")
        state_file = self._build_state()
        self._write_override({"steps": {"create": {"success": {"config": {"expectedMatches": 2}}}}})
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_validate_story_creation(["1.2", "0", "1", "--state-file", str(state_file)])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["expected"], 1)
        self.assertEqual(payload["created_count"], 1)

    def test_validate_story_creation_check_returns_compat_schema_on_policy_error(self) -> None:
        self._write_override({"steps": {"create": {"success": {"config": {"expectedMatches": "abc"}}}}})
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_validate_story_creation(["check", "1.2"])
        self.assertEqual(code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["valid"])
        self.assertEqual(payload["expected"], 1)
        self.assertEqual(payload["created_count"], 0)
        self.assertEqual(payload["prefix"], "1-2")
        self.assertEqual(payload["source"], "")
        self.assertEqual(payload["pattern"], "")
        self.assertEqual(payload["matches"], [])

    def test_validate_story_creation_check_returns_compat_schema_on_missing_state_file(self) -> None:
        stdout = io.StringIO()
        missing = self.project_root / "missing-state.md"
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_validate_story_creation(["check", "1.2", "--state-file", str(missing)])
        self.assertEqual(code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["valid"])
        self.assertIn("missing-state.md", payload["reason"])

    def test_review_wrapper_honors_empty_injected_contract(self) -> None:
        self._write_story("1-2-example", status="done")
        self._write_override(
            {
                "steps": {
                    "review": {
                        "success": {
                            "config": {"doneValues": ["approved"], "sourceOrder": ["story-file"], "syncSprintStatus": False}
                        }
                    }
                }
            }
        )
        payload = verify_code_review_completion(str(self.project_root), "1.2", success_contract={})
        self.assertTrue(payload["verified"])
        self.assertEqual(payload["source"], "story-file")

    def test_review_wrapper_normalizes_policy_error(self) -> None:
        payload = verify_code_review_completion(
            str(self.project_root),
            "1.2",
            success_contract={"doneValues": [], "sourceOrder": ["story-file"]},
        )
        self.assertFalse(payload["verified"])
        self.assertEqual(payload["reason"], "review_contract_invalid")

    def test_verify_step_rejects_incomplete_state_file_flag(self) -> None:
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_orchestrator_helper(["verify-step", "create", "1.2", "--state-file"])
        self.assertEqual(code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["verified"])
        self.assertEqual(payload["reason"], "verifier_contract_invalid")
        self.assertEqual(payload["error"], "--state-file requires a value")

    def test_validate_story_creation_check_returns_compat_schema_on_bad_counts(self) -> None:
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_validate_story_creation(["check", "1.2", "--before", "x", "--after", "1"])
        self.assertEqual(code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["valid"])
        self.assertEqual(payload["reason"], "before/after must be integers")
        self.assertEqual(payload["expected"], 1)
        self.assertEqual(payload["created_count"], 0)

    def test_validate_story_creation_check_returns_compat_schema_on_partial_counts(self) -> None:
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_validate_story_creation(["check", "1.2", "--before", "1"])
        self.assertEqual(code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["valid"])
        self.assertEqual(payload["reason"], "both --before and --after are required together")
        self.assertEqual(payload["prefix"], "1-2")

    def test_validate_story_creation_check_returns_compat_schema_on_trailing_before_flag(self) -> None:
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_validate_story_creation(["check", "1.2", "--before"])
        self.assertEqual(code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["valid"])
        self.assertEqual(payload["reason"], "--before requires a value")

    def test_validate_story_creation_check_returns_compat_schema_on_empty_counts(self) -> None:
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_validate_story_creation(["check", "1.2", "--before", "", "--after", ""])
        self.assertEqual(code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["valid"])
        self.assertEqual(payload["reason"], "before/after must be integers")

    def test_validate_story_creation_check_returns_compat_schema_on_unsupported_artifacts_dir(self) -> None:
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_validate_story_creation(["check", "1.2", "--artifacts-dir", str(self.project_root / "tmp")])
        self.assertEqual(code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["valid"])
        self.assertIn("no longer supports --artifacts-dir overrides", payload["reason"])

    def test_validate_story_creation_check_rejects_artifacts_dir_in_delta_mode(self) -> None:
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_validate_story_creation(["check", "1.2", "--before", "0", "--after", "1", "--artifacts-dir", str(self.project_root / "tmp")])
        self.assertEqual(code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["valid"])
        self.assertIn("no longer supports --artifacts-dir overrides", payload["reason"])
        self.assertEqual(payload["created_count"], 1)
        self.assertEqual(payload["before"], 0)
        self.assertEqual(payload["after"], 1)

    def test_validate_story_creation_positional_mode_rejects_artifacts_dir_with_delta_fields(self) -> None:
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_validate_story_creation(["1.2", "0", "1", "--artifacts-dir", str(self.project_root / "tmp")])
        self.assertEqual(code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["valid"])
        self.assertIn("no longer supports --artifacts-dir overrides", payload["reason"])
        self.assertEqual(payload["created_count"], 1)
        self.assertEqual(payload["before"], 0)
        self.assertEqual(payload["after"], 1)

    def test_validate_story_creation_positional_mode_returns_compat_schema_on_bad_counts(self) -> None:
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_validate_story_creation(["1.2", "x", "1"])
        self.assertEqual(code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["valid"])
        self.assertEqual(payload["reason"], "before/after must be integers")

    def test_validate_story_creation_positional_mode_returns_compat_schema_on_missing_after(self) -> None:
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_validate_story_creation(["1.2", "0"])
        self.assertEqual(code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["valid"])
        self.assertEqual(payload["reason"], "both --before and --after are required together")

    def test_validate_story_creation_positional_mode_returns_compat_schema_on_missing_counts(self) -> None:
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_validate_story_creation(["1.2"])
        self.assertEqual(code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["valid"])
        self.assertEqual(payload["reason"], "both --before and --after are required together")

    def test_validate_story_creation_positional_mode_returns_compat_schema_on_extra_token(self) -> None:
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_validate_story_creation(["1.2", "0", "1", "junk"])
        self.assertEqual(code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["valid"])
        self.assertEqual(payload["reason"], "unsupported check argument: junk")
        self.assertEqual(payload["created_count"], 1)
        self.assertEqual(payload["before"], 0)
        self.assertEqual(payload["after"], 1)

    def test_validate_story_creation_positional_mode_returns_compat_schema_on_incomplete_state_file(self) -> None:
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_validate_story_creation(["1.2", "0", "1", "--state-file"])
        self.assertEqual(code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["valid"])
        self.assertEqual(payload["reason"], "--state-file requires a value")
        self.assertEqual(payload["created_count"], 1)
        self.assertEqual(payload["before"], 0)
        self.assertEqual(payload["after"], 1)

    def test_validate_story_creation_check_preserves_delta_on_incomplete_state_file(self) -> None:
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_validate_story_creation(["check", "1.2", "--before", "0", "--after", "1", "--state-file"])
        self.assertEqual(code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["valid"])
        self.assertEqual(payload["reason"], "--state-file requires a value")
        self.assertEqual(payload["created_count"], 1)
        self.assertEqual(payload["before"], 0)
        self.assertEqual(payload["after"], 1)

    def test_validate_story_creation_check_preserves_delta_on_trailing_before_flag(self) -> None:
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_validate_story_creation(["check", "1.2", "--before", "0", "--after", "1", "--before"])
        self.assertEqual(code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["valid"])
        self.assertEqual(payload["reason"], "--before requires a value")
        self.assertEqual(payload["created_count"], 1)
        self.assertEqual(payload["before"], 0)
        self.assertEqual(payload["after"], 1)

    def test_validate_story_creation_positional_mode_preserves_delta_on_trailing_before_flag(self) -> None:
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_validate_story_creation(["1.2", "0", "1", "--before"])
        self.assertEqual(code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["valid"])
        self.assertEqual(payload["reason"], "--before requires a value")
        self.assertEqual(payload["created_count"], 1)
        self.assertEqual(payload["before"], 0)
        self.assertEqual(payload["after"], 1)

    def test_validate_story_creation_check_returns_compat_failure_without_exception(self) -> None:
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_validate_story_creation(["check", "1.2"])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["valid"])
        self.assertEqual(payload["created_count"], 0)
        self.assertEqual(payload["reason"], "No story file created - session may have failed")

    def test_validate_story_creation_positional_mode_returns_delta_failure_without_exception(self) -> None:
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_validate_story_creation(["1.2", "1", "3"])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["valid"])
        self.assertEqual(payload["created_count"], 2)
        self.assertEqual(payload["reason"], "RUNAWAY CREATION: 2 files created instead of 1")

    def test_validate_story_creation_check_preserves_zero_expected_matches(self) -> None:
        self._write_override({"steps": {"create": {"success": {"config": {"expectedMatches": 0}}}}})
        stdout = io.StringIO()
        with patch_env(self.project_root), redirect_stdout(stdout):
            code = cmd_validate_story_creation(["check", "1.2"])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["expected"], 0)
        self.assertEqual(payload["created_count"], 0)

    def test_create_story_artifact_rejects_invalid_expected_matches(self) -> None:
        with self.assertRaises(PolicyError):
            create_story_artifact(
                project_root=str(self.project_root),
                story_key="1.2",
                contract={"config": {"expectedMatches": "abc"}},
            )

    def test_create_story_artifact_rejects_boolean_expected_matches(self) -> None:
        with self.assertRaises(PolicyError):
            create_story_artifact(
                project_root=str(self.project_root),
                story_key="1.2",
                contract={"config": {"expectedMatches": False}},
            )

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
                    json.dumps(
                        {
                            "epic": "1",
                            "epicName": "Epic 1",
                            "storyRange": ["1.2"],
                            "status": "READY",
                            "aiCommand": "claude --dangerously-skip-permissions",
                        }
                    ),
                ]
            )
        return Path(json.loads(stdout.getvalue())["path"])

    def _install_bundle(self) -> None:
        source_skill = REPO_ROOT / "payload" / ".claude" / "skills" / "bmad-story-automator"
        source_review = REPO_ROOT / "payload" / ".claude" / "skills" / "bmad-story-automator-review"
        target_root = self.project_root / ".claude" / "skills"
        target_root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_skill, target_root / "bmad-story-automator")
        shutil.copytree(source_review, target_root / "bmad-story-automator-review")

    def _install_required_skills(self) -> None:
        self._make_skill(
            "bmad-create-story",
            extras={"discover-inputs.md": "# discover\n", "checklist.md": "# checklist\n", "template.md": "# template\n"},
        )
        self._make_skill("bmad-dev-story", extras={"checklist.md": "# checklist\n"})
        self._make_skill("bmad-retrospective")
        self._make_skill("bmad-qa-generate-e2e-tests", extras={"checklist.md": "# checklist\n"})

    def _make_skill(self, name: str, *, extras: dict[str, str] | None = None) -> None:
        skill_dir = self.project_root / ".claude" / "skills" / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")
        (skill_dir / "workflow.md").write_text(f"# {name}\n", encoding="utf-8")
        for rel, content in (extras or {}).items():
            (skill_dir / rel).write_text(content, encoding="utf-8")

    def _write_story(self, stem: str, *, status: str) -> Path:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        path = self.artifacts_dir / f"{stem}.md"
        path.write_text(f"---\nStatus: {status}\nTitle: Story\n---\n", encoding="utf-8")
        return path

    def _write_sprint_status(self, content: str) -> None:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        (self.artifacts_dir / "sprint-status.yaml").write_text(content, encoding="utf-8")

    def _write_review_contract(self, payload: dict[str, object]) -> Path:
        path = self.project_root / "review-contract.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def _write_override(self, payload: dict[str, object]) -> None:
        override_dir = self.project_root / "_bmad" / "bmm"
        override_dir.mkdir(parents=True, exist_ok=True)
        (override_dir / "story-automator.policy.json").write_text(json.dumps(payload), encoding="utf-8")


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
