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


def _skill_file(skill_name: str) -> str:
    return f".claude/skills/{skill_name}/SKILL.md"


def _workflow_file(skill_name: str, *names: str, project_root: str | None = None) -> str:
    return _first_existing_relative_path(
        *(f".claude/skills/{skill_name}/{name}" for name in names),
        project_root=project_root,
    )


def _optional_file(skill_name: str, *names: str, project_root: str | None = None) -> str:
    return _existing_relative_path_or_empty(
        *(f".claude/skills/{skill_name}/{name}" for name in names),
        project_root=project_root,
    )


def _paired_optional_workflow_paths(
    skill_name: str,
    *,
    workflow_names: tuple[str, ...],
    checklist_names: tuple[str, ...] = (),
    project_root: str | None = None,
) -> WorkflowPaths:
    skill = _existing_relative_path_or_empty(_skill_file(skill_name), project_root=project_root)
    workflow = _existing_relative_path_or_empty(
        *(f".claude/skills/{skill_name}/{name}" for name in workflow_names),
        project_root=project_root,
    )
    if not skill or not workflow:
        return WorkflowPaths()
    return WorkflowPaths(
        skill=skill,
        workflow=workflow,
        checklist=_existing_relative_path_or_empty(
            *(f".claude/skills/{skill_name}/{name}" for name in checklist_names),
            project_root=project_root,
        ),
    )


def create_story_workflow_paths(project_root: str | None = None) -> WorkflowPaths:
    return WorkflowPaths(
        skill=_first_existing_relative_path(_skill_file("bmad-create-story"), project_root=project_root),
        workflow=_workflow_file("bmad-create-story", "workflow.md", "workflow.yaml", project_root=project_root),
        instructions=_optional_file("bmad-create-story", "discover-inputs.md", project_root=project_root),
        checklist=_optional_file("bmad-create-story", "checklist.md", project_root=project_root),
        template=_optional_file("bmad-create-story", "template.md", project_root=project_root),
    )


def dev_story_workflow_paths(project_root: str | None = None) -> WorkflowPaths:
    return WorkflowPaths(
        skill=_first_existing_relative_path(_skill_file("bmad-dev-story"), project_root=project_root),
        workflow=_workflow_file("bmad-dev-story", "workflow.md", "workflow.yaml", project_root=project_root),
        instructions="",
        checklist=_optional_file("bmad-dev-story", "checklist.md", project_root=project_root),
    )


def retrospective_workflow_paths(project_root: str | None = None) -> WorkflowPaths:
    return WorkflowPaths(
        skill=_first_existing_relative_path(_skill_file("bmad-retrospective"), project_root=project_root),
        workflow=_workflow_file("bmad-retrospective", "workflow.md", "workflow.yaml", project_root=project_root),
        instructions="",
    )


def review_workflow_paths(project_root: str | None = None) -> WorkflowPaths:
    return WorkflowPaths(
        skill=_first_existing_relative_path(
            _skill_file("bmad-story-automator-review"),
            project_root=project_root,
        ),
        workflow=_workflow_file(
            "bmad-story-automator-review",
            "workflow.yaml",
            "workflow.md",
            project_root=project_root,
        ),
        instructions=_optional_file(
            "bmad-story-automator-review",
            "instructions.xml",
            project_root=project_root,
        ),
        checklist=_optional_file(
            "bmad-story-automator-review",
            "checklist.md",
            project_root=project_root,
        ),
    )


def testarch_automate_workflow_paths(project_root: str | None = None) -> WorkflowPaths:
    return _paired_optional_workflow_paths(
        "bmad-qa-generate-e2e-tests",
        workflow_names=("workflow.md", "workflow.yaml"),
        checklist_names=("checklist.md",),
        project_root=project_root,
    )
