# Security Policy

## Reporting

Do not open public issues for credential leaks or security-sensitive problems.

Report privately to:
- `bmad.directory@gmail.com`

Include:
- affected version or commit
- reproduction steps
- impact summary
- whether the issue affects install-time behavior, generated command wrappers, or runtime orchestration

## Scope Notes

This project ships workflow payload plus a Python helper runtime. Security review should cover:
- installer path handling
- copied workflow payload contents
- command-wrapper generation
- subprocess and tmux execution paths
- any file writes into target projects
