from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from story_automator.core.runtime_policy import (
    PolicyError,
    load_effective_policy,
    load_policy_snapshot,
    load_runtime_policy,
    snapshot_effective_policy,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


class RuntimePolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.project_root = Path(self.tmp.name)
        self._install_bundle()
        self._install_required_skills()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_bundled_default_loads(self) -> None:
        policy = load_effective_policy(str(self.project_root))
        self.assertEqual(policy["version"], 1)
        self.assertEqual(policy["steps"]["review"]["success"]["verifier"], "review_completion")

    def test_project_override_deep_merges_and_arrays_replace(self) -> None:
        self._write_override(
            {
                "workflow": {"sequence": ["create", "review"]},
                "steps": {"review": {"prompt": {"defaultExtraInstruction": "fix critical issues only"}}},
            }
        )
        policy = load_effective_policy(str(self.project_root))
        self.assertEqual(policy["workflow"]["sequence"], ["create", "review"])
        self.assertEqual(policy["steps"]["review"]["prompt"]["defaultExtraInstruction"], "fix critical issues only")

    def test_invalid_step_name_rejected(self) -> None:
        self._write_override({"steps": {"ship": {"success": {"verifier": "session_exit"}}}})
        with self.assertRaises(PolicyError):
            load_effective_policy(str(self.project_root))

    def test_invalid_verifier_name_rejected(self) -> None:
        self._write_override({"steps": {"review": {"success": {"verifier": "nope"}}}})
        with self.assertRaises(PolicyError):
            load_effective_policy(str(self.project_root))

    def test_required_asset_missing_fails(self) -> None:
        shutil.rmtree(self.project_root / ".claude" / "skills" / "bmad-create-story")
        with self.assertRaises(PolicyError):
            load_effective_policy(str(self.project_root))

    def test_snapshot_hash_stable(self) -> None:
        first = snapshot_effective_policy(str(self.project_root))
        second = snapshot_effective_policy(str(self.project_root))
        self.assertEqual(first["policySnapshotHash"], second["policySnapshotHash"])

    def test_snapshot_bakes_legacy_env_values_for_resume(self) -> None:
        with patch.dict("os.environ", {"MAX_REVIEW_CYCLES": "2", "MAX_CRASH_RETRIES": "4"}, clear=False):
            snapshot = snapshot_effective_policy(str(self.project_root))
        with patch.dict("os.environ", {"MAX_REVIEW_CYCLES": "9", "MAX_CRASH_RETRIES": "9"}, clear=False):
            policy = load_policy_snapshot(
                snapshot["policySnapshotFile"],
                project_root=str(self.project_root),
                expected_hash=snapshot["policySnapshotHash"],
            )
        self.assertEqual(policy["workflow"]["repeat"]["review"]["maxCycles"], 2)
        self.assertEqual(policy["workflow"]["crash"]["maxRetries"], 4)

    def test_invalid_legacy_env_value_raises_policy_error(self) -> None:
        with patch.dict("os.environ", {"MAX_REVIEW_CYCLES": "nope"}, clear=False):
            with self.assertRaisesRegex(PolicyError, "MAX_REVIEW_CYCLES must be an integer"):
                load_effective_policy(str(self.project_root))

    def test_malformed_override_json_raises_policy_error(self) -> None:
        override_dir = self.project_root / "_bmad" / "bmm"
        override_dir.mkdir(parents=True, exist_ok=True)
        (override_dir / "story-automator.policy.json").write_text("{bad json", encoding="utf-8")
        with self.assertRaises(PolicyError):
            load_effective_policy(str(self.project_root))

    def test_invalid_assets_type_rejected(self) -> None:
        self._write_override({"steps": {"review": {"assets": []}}})
        with self.assertRaises(PolicyError):
            load_effective_policy(str(self.project_root))

    def test_invalid_workflow_and_snapshot_types_rejected(self) -> None:
        self._write_override({"workflow": [], "snapshot": []})
        with self.assertRaises(PolicyError):
            load_effective_policy(str(self.project_root))

    def test_invalid_nested_workflow_types_rejected(self) -> None:
        self._write_override({"workflow": {"repeat": [1], "crash": [2]}})
        with self.assertRaises(PolicyError):
            load_effective_policy(str(self.project_root))

    def test_invalid_parser_runtime_rejected(self) -> None:
        self._write_override({"runtime": {"parser": {"provider": "bad", "model": "haiku", "timeoutSeconds": 120}}})
        with self.assertRaisesRegex(PolicyError, "runtime.parser.provider"):
            load_effective_policy(str(self.project_root))

    def test_snapshot_reload_re_resolves_paths_for_new_root(self) -> None:
        snapshot = snapshot_effective_policy(str(self.project_root))
        copied_root = Path(self.tmp.name) / "copied"
        shutil.copytree(self.project_root, copied_root)
        policy = load_runtime_policy(str(copied_root), state_file=str(copied_root / snapshot["policySnapshotFile"]))
        template_path = policy["steps"]["create"]["prompt"]["templatePath"]
        self.assertTrue(str(copied_root) in template_path)

    def test_missing_marker_state_falls_back_to_effective_policy(self) -> None:
        marker = self.project_root / ".claude" / ".story-automator-active"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({"stateFile": "missing.md"}), encoding="utf-8")
        policy = load_runtime_policy(str(self.project_root))
        self.assertEqual(policy["workflow"]["repeat"]["review"]["maxCycles"], 5)

    def test_malformed_marker_falls_back_to_effective_policy(self) -> None:
        marker = self.project_root / ".claude" / ".story-automator-active"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("{bad json", encoding="utf-8")
        policy = load_runtime_policy(str(self.project_root))
        self.assertEqual(policy["workflow"]["repeat"]["review"]["maxCycles"], 5)

    def test_legacy_state_uses_bundled_defaults_without_override_or_env(self) -> None:
        self._write_override({"workflow": {"repeat": {"review": {"maxCycles": 1}}}})
        legacy_state = self.project_root / "legacy.md"
        legacy_state.write_text(
            "---\nepic: \"1\"\nepicName: \"Epic 1\"\nstoryRange: [\"1.1\"]\nstatus: \"READY\"\nlastUpdated: \"2026-04-13T00:00:00Z\"\naiCommand: \"claude\"\n---\n",
            encoding="utf-8",
        )
        with patch.dict("os.environ", {"MAX_REVIEW_CYCLES": "2"}, clear=False):
            policy = load_runtime_policy(str(self.project_root), state_file=str(legacy_state))
        self.assertEqual(policy["workflow"]["repeat"]["review"]["maxCycles"], 5)

    def test_marker_resume_with_missing_snapshot_raises_policy_error(self) -> None:
        state_file = self.project_root / "orchestration.md"
        state_file.write_text(
            "---\npolicySnapshotFile: \"_bmad-output/story-automator/snapshots/missing.json\"\npolicySnapshotHash: \"deadbeef\"\n---\n",
            encoding="utf-8",
        )
        marker = self.project_root / ".claude" / ".story-automator-active"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({"stateFile": str(state_file.relative_to(self.project_root))}), encoding="utf-8")
        with self.assertRaises(PolicyError):
            load_runtime_policy(str(self.project_root))

    def test_new_state_without_snapshot_metadata_is_rejected(self) -> None:
        state_file = self.project_root / "orchestration.md"
        state_file.write_text(
            "---\nepic: \"1\"\nepicName: \"Epic 1\"\nstoryRange: [\"1.1\"]\nstatus: \"READY\"\nlastUpdated: \"2026-04-13T00:00:00Z\"\naiCommand: \"claude\"\npolicyVersion: 1\nlegacyPolicy: false\n---\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(PolicyError, "state policy snapshot missing"):
            load_runtime_policy(str(self.project_root), state_file=str(state_file))

    def test_contradictory_legacy_flag_with_policy_version_is_rejected(self) -> None:
        state_file = self.project_root / "orchestration.md"
        state_file.write_text(
            "---\nepic: \"1\"\nepicName: \"Epic 1\"\nstoryRange: [\"1.1\"]\nstatus: \"READY\"\nlastUpdated: \"2026-04-13T00:00:00Z\"\naiCommand: \"claude\"\npolicyVersion: 1\nlegacyPolicy: true\n---\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(PolicyError, "state policy snapshot missing"):
            load_runtime_policy(str(self.project_root), state_file=str(state_file))

    def test_snapshot_metadata_with_legacy_flag_is_rejected(self) -> None:
        snapshot = snapshot_effective_policy(str(self.project_root))
        state_file = self.project_root / "orchestration.md"
        state_file.write_text(
            f"---\npolicySnapshotFile: \"{snapshot['policySnapshotFile']}\"\npolicySnapshotHash: \"{snapshot['policySnapshotHash']}\"\nlegacyPolicy: true\n---\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(PolicyError, "state policy metadata contradictory"):
            load_runtime_policy(str(self.project_root), state_file=str(state_file))

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

    def _write_override(self, payload: dict[str, object]) -> None:
        override_dir = self.project_root / "_bmad" / "bmm"
        override_dir.mkdir(parents=True, exist_ok=True)
        (override_dir / "story-automator.policy.json").write_text(json.dumps(payload), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
