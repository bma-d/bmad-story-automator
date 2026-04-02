# Contributing

## Scope

This repository packages the BMAD story-automator workflow payload plus the Python runtime used by the installed workflow.

## Before Opening A PR

- keep changes scoped; avoid unrelated cleanup
- keep files under roughly 500 LOC when practical
- preserve current and legacy BMAD layout support
- avoid adding dependencies unless clearly justified
- run:
  - `npm run pack:dry-run`
  - `npm run test:smoke`
  - `PYTHONPATH=source/src python3 -m story_automator --help`

## PR Notes

- use Conventional Commits
- describe user-facing behavior changes
- mention install-path or workflow-path changes explicitly
- call out any payload files copied from upstream BMAD sources

## Reporting Bugs

Include:
- OS
- Python version
- Node version
- BMAD layout: current or legacy
- exact command run
- exact error output
