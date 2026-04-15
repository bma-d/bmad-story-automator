from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from story_automator.commands.state import cmd_build_state_doc
from story_automator.commands.orchestrator_parse import parse_output_action
from story_automator.core.utils import CommandResult


REPO_ROOT = Path(__file__).resolve().parents[2]


class OrchestratorParseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.project_root = Path(self.tmp.name)
        self._install_bundle()
        self._install_required_skills()
        self.output_file = self.project_root / "session.txt"
        self.output_file.write_text("session output\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_parse_schema_loads_from_step_contract(self) -> None:
        stdout = io.StringIO()
        with patch.dict("os.environ", {"PROJECT_ROOT": str(self.project_root)}), patch(
            "story_automator.commands.orchestrator_parse.run_cmd",
            return_value=CommandResult('{"status":"SUCCESS","story_created":true,"story_file":"x","summary":"ok","next_action":"proceed"}', 0),
        ), redirect_stdout(stdout):
            code = parse_output_action([str(self.output_file), "create"])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["story_created"])

    def test_invalid_schema_file_rejected(self) -> None:
        override_dir = self.project_root / "_bmad" / "bmm"
        override_dir.mkdir(parents=True)
        (override_dir / "story-automator.policy.json").write_text(
            json.dumps({"steps": {"create": {"parse": {"schemaFile": "missing.json"}}}}),
            encoding="utf-8",
        )
        stdout = io.StringIO()
        with patch.dict("os.environ", {"PROJECT_ROOT": str(self.project_root)}), redirect_stdout(stdout):
            code = parse_output_action([str(self.output_file), "create"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(stdout.getvalue())["reason"], "parse_contract_invalid")

    def test_missing_state_file_flag_value_rejected(self) -> None:
        stdout = io.StringIO()
        with patch.dict("os.environ", {"PROJECT_ROOT": str(self.project_root)}), redirect_stdout(stdout):
            code = parse_output_action([str(self.output_file), "create", "--state-file"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(stdout.getvalue())["reason"], "parse_contract_invalid")

    def test_non_string_required_key_rejected(self) -> None:
        schema = self.project_root / ".claude" / "skills" / "bmad-story-automator" / "data" / "parse" / "create.json"
        schema.write_text(json.dumps({"requiredKeys": [True], "schema": {}}), encoding="utf-8")
        stdout = io.StringIO()
        with patch.dict("os.environ", {"PROJECT_ROOT": str(self.project_root)}), redirect_stdout(stdout):
            code = parse_output_action([str(self.output_file), "create"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(stdout.getvalue())["reason"], "parse_contract_invalid")

    def test_invalid_child_json_rejected(self) -> None:
        stdout = io.StringIO()
        with patch.dict("os.environ", {"PROJECT_ROOT": str(self.project_root)}), patch(
            "story_automator.commands.orchestrator_parse.run_cmd",
            return_value=CommandResult("not json", 0),
        ), redirect_stdout(stdout):
            code = parse_output_action([str(self.output_file), "create"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(stdout.getvalue())["reason"], "sub-agent returned invalid json")

    def test_output_shape_remains_compatible(self) -> None:
        stdout = io.StringIO()
        with patch.dict("os.environ", {"PROJECT_ROOT": str(self.project_root)}), patch(
            "story_automator.commands.orchestrator_parse.run_cmd",
            return_value=CommandResult('{"status":"SUCCESS","issues_found":{"critical":0,"high":0,"medium":1,"low":0},"all_fixed":true,"summary":"ok","next_action":"proceed"}', 0),
        ), redirect_stdout(stdout):
            code = parse_output_action([str(self.output_file), "review"])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertIn("issues_found", payload)
        self.assertIn("all_fixed", payload)

    def test_review_output_rejects_invalid_nested_shape(self) -> None:
        stdout = io.StringIO()
        with patch.dict("os.environ", {"PROJECT_ROOT": str(self.project_root)}), patch(
            "story_automator.commands.orchestrator_parse.run_cmd",
            return_value=CommandResult('{"status":"SUCCESS","issues_found":{"critical":"0","high":0,"medium":1,"low":0},"all_fixed":true,"summary":"ok","next_action":"proceed"}', 0),
        ), redirect_stdout(stdout):
            code = parse_output_action([str(self.output_file), "review"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(stdout.getvalue())["reason"], "sub-agent returned invalid json")

    def test_review_output_rejects_invalid_enum_value(self) -> None:
        stdout = io.StringIO()
        with patch.dict("os.environ", {"PROJECT_ROOT": str(self.project_root)}), patch(
            "story_automator.commands.orchestrator_parse.run_cmd",
            return_value=CommandResult('{"status":"BROKEN","issues_found":{"critical":0,"high":0,"medium":1,"low":0},"all_fixed":true,"summary":"ok","next_action":"proceed"}', 0),
        ), redirect_stdout(stdout):
            code = parse_output_action([str(self.output_file), "review"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(stdout.getvalue())["reason"], "sub-agent returned invalid json")

    def test_state_file_keeps_pinned_parse_contract_after_override_changes(self) -> None:
        state_file = self._build_state()
        override_dir = self.project_root / "_bmad" / "bmm"
        override_dir.mkdir(parents=True, exist_ok=True)
        (override_dir / "story-automator.policy.json").write_text(
            json.dumps({"steps": {"create": {"parse": {"schemaFile": "missing.json"}}}}),
            encoding="utf-8",
        )
        stdout = io.StringIO()
        with patch.dict("os.environ", {"PROJECT_ROOT": str(self.project_root)}), patch(
            "story_automator.commands.orchestrator_parse.run_cmd",
            return_value=CommandResult('{"status":"SUCCESS","story_created":true,"story_file":"x","summary":"ok","next_action":"proceed"}', 0),
        ), redirect_stdout(stdout):
            code = parse_output_action([str(self.output_file), "create", "--state-file", str(state_file)])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(stdout.getvalue())["story_created"])

    def test_parser_runtime_uses_policy_settings(self) -> None:
        override_dir = self.project_root / "_bmad" / "bmm"
        override_dir.mkdir(parents=True, exist_ok=True)
        (override_dir / "story-automator.policy.json").write_text(
            json.dumps({"runtime": {"parser": {"provider": "claude", "model": "sonnet", "timeoutSeconds": 33}}}),
            encoding="utf-8",
        )
        stdout = io.StringIO()
        with patch.dict("os.environ", {"PROJECT_ROOT": str(self.project_root)}), patch(
            "story_automator.commands.orchestrator_parse.run_cmd",
            return_value=CommandResult('{"status":"SUCCESS","story_created":true,"story_file":"x","summary":"ok","next_action":"proceed"}', 0),
        ) as mock_run, redirect_stdout(stdout):
            code = parse_output_action([str(self.output_file), "create"])
        self.assertEqual(code, 0)
        self.assertEqual(mock_run.call_args.args[:4], ("claude", "-p", "--model", "sonnet"))
        self.assertEqual(mock_run.call_args.kwargs["timeout"], 33)

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

    def _build_state(self) -> Path:
        output_dir = self.project_root / "_bmad-output" / "story-automator"
        output_dir.mkdir(parents=True, exist_ok=True)
        stdout = io.StringIO()
        template = self.project_root / ".claude" / "skills" / "bmad-story-automator" / "templates" / "state-document.md"
        with patch.dict("os.environ", {"PROJECT_ROOT": str(self.project_root)}), redirect_stdout(stdout):
            cmd_build_state_doc(
                [
                    "--template",
                    str(template),
                    "--output-folder",
                    str(output_dir),
                    "--config-json",
                    json.dumps(
                        {
                            "epic": "1",
                            "epicName": "Epic 1",
                            "storyRange": ["1.1"],
                            "status": "READY",
                            "aiCommand": "claude --dangerously-skip-permissions",
                        }
                    ),
                ]
            )
        return Path(json.loads(stdout.getvalue())["path"])


if __name__ == "__main__":
    unittest.main()
