from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from story_automator.core.runtime_policy import PolicyError, load_effective_policy, snapshot_effective_policy


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
