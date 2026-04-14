from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from story_automator.core.utils import get_project_root


@dataclass(frozen=True)
class WorkflowPaths:
    skill: str = ""
    workflow: str = ""
    instructions: str = ""
    checklist: str = ""
    template: str = ""


def _preferred_skill_roots(agent: str | None = None) -> tuple[str, ...]:
    normalized = (agent or "").strip().lower()
    if normalized == "claude":
        return (".claude/skills", ".agents/skills")
    if normalized == "codex":
        return (".agents/skills", ".claude/skills")
    return (".agents/skills", ".claude/skills")


def _skill_candidates(skill_name: str, *file_names: str, agent: str | None = None) -> tuple[str, ...]:
    candidates: list[str] = []
    for root in _preferred_skill_roots(agent):
        for file_name in file_names:
            candidates.append(f"{root}/{skill_name}/{file_name}")
    return tuple(candidates)


def _first_existing_relative_path(*candidates: str, project_root: str | None = None) -> str:
    root = Path(project_root or get_project_root())
    for rel in candidates:
        if rel and (root / rel).exists():
            return rel
    for rel in candidates:
        if rel:
            return rel
    return ""


def _existing_relative_path_or_empty(*candidates: str, project_root: str | None = None) -> str:
    root = Path(project_root or get_project_root())
    for rel in candidates:
        if rel and (root / rel).exists():
            return rel
    return ""


def create_story_workflow_paths(project_root: str | None = None, agent: str | None = None) -> WorkflowPaths:
    return WorkflowPaths(
        skill=_first_existing_relative_path(
            *_skill_candidates("bmad-create-story", "SKILL.md", agent=agent),
            "_bmad/bmm/4-implementation/bmad-create-story/SKILL.md",
            "_bmad/bmm/4-implementation/create-story/SKILL.md",
            "_bmad/bmm/workflows/4-implementation/create-story/SKILL.md",
            project_root=project_root,
        ),
        workflow=_first_existing_relative_path(
            *_skill_candidates("bmad-create-story", "workflow.md", "workflow.yaml", agent=agent),
            "_bmad/bmm/4-implementation/bmad-create-story/workflow.md",
            "_bmad/bmm/4-implementation/create-story/workflow.md",
            "_bmad/bmm/4-implementation/bmad-create-story/workflow.yaml",
            "_bmad/bmm/4-implementation/create-story/workflow.yaml",
            "_bmad/bmm/workflows/4-implementation/create-story/workflow.md",
            "_bmad/bmm/workflows/4-implementation/create-story/workflow.yaml",
            project_root=project_root,
        ),
        instructions=_first_existing_relative_path(
            *_skill_candidates("bmad-create-story", "discover-inputs.md", agent=agent),
            "_bmad/bmm/4-implementation/bmad-create-story/discover-inputs.md",
            "_bmad/bmm/workflows/4-implementation/create-story/discover-inputs.md",
            project_root=project_root,
        ),
        checklist=_first_existing_relative_path(
            *_skill_candidates("bmad-create-story", "checklist.md", agent=agent),
            "_bmad/bmm/4-implementation/bmad-create-story/checklist.md",
            "_bmad/bmm/4-implementation/create-story/checklist.md",
            "_bmad/bmm/workflows/4-implementation/create-story/checklist.md",
            project_root=project_root,
        ),
        template=_first_existing_relative_path(
            *_skill_candidates("bmad-create-story", "template.md", agent=agent),
            "_bmad/bmm/4-implementation/bmad-create-story/template.md",
            "_bmad/bmm/4-implementation/create-story/template.md",
            "_bmad/bmm/workflows/4-implementation/create-story/template.md",
            project_root=project_root,
        ),
    )


def dev_story_workflow_paths(project_root: str | None = None, agent: str | None = None) -> WorkflowPaths:
    return WorkflowPaths(
        skill=_first_existing_relative_path(
            *_skill_candidates("bmad-dev-story", "SKILL.md", agent=agent),
            "_bmad/bmm/4-implementation/bmad-dev-story/SKILL.md",
            "_bmad/bmm/4-implementation/dev-story/SKILL.md",
            "_bmad/bmm/workflows/4-implementation/dev-story/SKILL.md",
            project_root=project_root,
        ),
        workflow=_first_existing_relative_path(
            *_skill_candidates("bmad-dev-story", "workflow.md", "workflow.yaml", agent=agent),
            "_bmad/bmm/4-implementation/bmad-dev-story/workflow.md",
            "_bmad/bmm/4-implementation/dev-story/workflow.md",
            "_bmad/bmm/4-implementation/bmad-dev-story/workflow.yaml",
            "_bmad/bmm/4-implementation/dev-story/workflow.yaml",
            "_bmad/bmm/workflows/4-implementation/dev-story/workflow.md",
            "_bmad/bmm/workflows/4-implementation/dev-story/workflow.yaml",
            project_root=project_root,
        ),
        instructions="",
        checklist=_first_existing_relative_path(
            *_skill_candidates("bmad-dev-story", "checklist.md", agent=agent),
            "_bmad/bmm/4-implementation/bmad-dev-story/checklist.md",
            "_bmad/bmm/4-implementation/dev-story/checklist.md",
            "_bmad/bmm/workflows/4-implementation/dev-story/checklist.md",
            project_root=project_root,
        ),
    )


def retrospective_workflow_paths(project_root: str | None = None, agent: str | None = None) -> WorkflowPaths:
    return WorkflowPaths(
        skill=_first_existing_relative_path(
            *_skill_candidates("bmad-retrospective", "SKILL.md", agent=agent),
            "_bmad/bmm/4-implementation/bmad-retrospective/SKILL.md",
            "_bmad/bmm/4-implementation/retrospective/SKILL.md",
            "_bmad/bmm/workflows/4-implementation/retrospective/SKILL.md",
            project_root=project_root,
        ),
        workflow=_first_existing_relative_path(
            *_skill_candidates("bmad-retrospective", "workflow.md", "workflow.yaml", agent=agent),
            "_bmad/bmm/4-implementation/bmad-retrospective/workflow.md",
            "_bmad/bmm/4-implementation/retrospective/workflow.md",
            "_bmad/bmm/4-implementation/bmad-retrospective/workflow.yaml",
            "_bmad/bmm/4-implementation/retrospective/workflow.yaml",
            "_bmad/bmm/workflows/4-implementation/retrospective/workflow.md",
            "_bmad/bmm/workflows/4-implementation/retrospective/workflow.yaml",
            project_root=project_root,
        ),
        instructions="",
    )


def review_workflow_paths(project_root: str | None = None, agent: str | None = None) -> WorkflowPaths:
    return WorkflowPaths(
        skill=_first_existing_relative_path(
            "_bmad/bmm/4-implementation/bmad-story-automator-review/SKILL.md",
            "_bmad/bmm/4-implementation/story-automator-review/SKILL.md",
            "_bmad/bmm/workflows/4-implementation/story-automator-review/SKILL.md",
            project_root=project_root,
        ),
        workflow=_first_existing_relative_path(
            "_bmad/bmm/4-implementation/bmad-story-automator-review/workflow.yaml",
            "_bmad/bmm/4-implementation/story-automator-review/workflow.yaml",
            "_bmad/bmm/workflows/4-implementation/story-automator-review/workflow.yaml",
            project_root=project_root,
        ),
        instructions=_first_existing_relative_path(
            "_bmad/bmm/4-implementation/bmad-story-automator-review/instructions.xml",
            "_bmad/bmm/4-implementation/story-automator-review/instructions.xml",
            "_bmad/bmm/workflows/4-implementation/story-automator-review/instructions.xml",
            project_root=project_root,
        ),
        checklist=_first_existing_relative_path(
            "_bmad/bmm/4-implementation/bmad-story-automator-review/checklist.md",
            "_bmad/bmm/4-implementation/story-automator-review/checklist.md",
            "_bmad/bmm/workflows/4-implementation/story-automator-review/checklist.md",
            project_root=project_root,
        ),
    )


def testarch_automate_workflow_paths(project_root: str | None = None, agent: str | None = None) -> WorkflowPaths:
    return WorkflowPaths(
        skill=_existing_relative_path_or_empty(
            *_skill_candidates("bmad-qa-generate-e2e-tests", "SKILL.md", agent=agent),
            "_bmad/bmm/4-implementation/bmad-qa-generate-e2e-tests/SKILL.md",
            "_bmad/bmm/4-implementation/qa-generate-e2e-tests/SKILL.md",
            "_bmad/bmm/workflows/4-implementation/bmad-qa-generate-e2e-tests/SKILL.md",
            "_bmad/bmm/workflows/4-implementation/qa-generate-e2e-tests/SKILL.md",
            project_root=project_root,
        ),
        workflow=_existing_relative_path_or_empty(
            *_skill_candidates("bmad-qa-generate-e2e-tests", "workflow.md", "workflow.yaml", agent=agent),
            "_bmad/tea/4-implementation/bmad-testarch-automate/workflow.md",
            "_bmad/tea/4-implementation/bmad-testarch-automate/workflow.yaml",
            "_bmad/tea/4-implementation/testarch-automate/workflow.md",
            "_bmad/tea/4-implementation/testarch-automate/workflow.yaml",
            "_bmad/bmm/4-implementation/bmad-testarch-automate/workflow.md",
            "_bmad/bmm/4-implementation/bmad-testarch-automate/workflow.yaml",
            "_bmad/bmm/4-implementation/testarch-automate/workflow.md",
            "_bmad/bmm/4-implementation/testarch-automate/workflow.yaml",
            "_bmad/bmm/4-implementation/bmad-qa-generate-e2e-tests/workflow.md",
            "_bmad/bmm/4-implementation/bmad-qa-generate-e2e-tests/workflow.yaml",
            "_bmad/bmm/4-implementation/qa-generate-e2e-tests/workflow.md",
            "_bmad/bmm/4-implementation/qa-generate-e2e-tests/workflow.yaml",
            "_bmad/tea/workflows/testarch/automate/workflow.md",
            "_bmad/tea/workflows/testarch/automate/workflow.yaml",
            "_bmad/bmm/workflows/4-implementation/bmad-qa-generate-e2e-tests/workflow.md",
            "_bmad/bmm/workflows/4-implementation/bmad-qa-generate-e2e-tests/workflow.yaml",
            "_bmad/bmm/workflows/4-implementation/qa-generate-e2e-tests/workflow.md",
            "_bmad/bmm/workflows/4-implementation/qa-generate-e2e-tests/workflow.yaml",
            "_bmad/bmm/workflows/testarch/automate/workflow.md",
            "_bmad/bmm/workflows/testarch/automate/workflow.yaml",
            project_root=project_root,
        ),
        instructions=_existing_relative_path_or_empty(
            "_bmad/tea/4-implementation/bmad-testarch-automate/instructions.md",
            "_bmad/tea/4-implementation/testarch-automate/instructions.md",
            "_bmad/tea/workflows/testarch/automate/instructions.md",
            "_bmad/bmm/workflows/testarch/automate/instructions.md",
            project_root=project_root,
        ),
        checklist=_existing_relative_path_or_empty(
            *_skill_candidates("bmad-qa-generate-e2e-tests", "checklist.md", agent=agent),
            "_bmad/tea/4-implementation/bmad-testarch-automate/checklist.md",
            "_bmad/tea/4-implementation/testarch-automate/checklist.md",
            "_bmad/bmm/4-implementation/bmad-qa-generate-e2e-tests/checklist.md",
            "_bmad/bmm/4-implementation/qa-generate-e2e-tests/checklist.md",
            "_bmad/bmm/workflows/4-implementation/bmad-qa-generate-e2e-tests/checklist.md",
            "_bmad/bmm/workflows/4-implementation/qa-generate-e2e-tests/checklist.md",
            "_bmad/tea/workflows/testarch/automate/checklist.md",
            "_bmad/bmm/workflows/testarch/automate/checklist.md",
            project_root=project_root,
        ),
    )
