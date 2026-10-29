# Locked implementation prompt

| Field | Value |
| --- | --- |
| `work_id` | `[required]` |
| `status` | `PROMPT_LOCKED` |
| `approved_package_version` | `V3` |
| `approval_ref` | `[required actual user approval]` |
| `base_commit` | `[required resolvable commit]` |
| `branch` | `work/<work-id>-antigravity` |
| `prompt_version` | `P1` |
| `prompt_hash` | `[sha256 after lock]` |

## Objective

[One concrete implementation objective]

## Read first

1. `AGENTS.md`
2. `ANTIGRAVITY.md`
3. Approved V3 package files for this work item

## Allowed files/modules

- [Exact path or bounded directory]

## Forbidden changes

- Do not change requirement/spec/acceptance.
- Do not modify unrelated files or reformat broadly.
- Do not add external service/production dependency without explicit approval.
- Do not access or commit real participant data, audio, transcript, PII or secrets.
- [Work-item-specific exclusions]

## Implementation tasks

1. [Atomic task]

## Required tests

```text
[Exact commands copied from approved Test Plan]
```

## Acceptance criteria

- [Verbatim criteria from V3]

## Report contract

Create/update `05_antigravity_raw_report.md` using the repository template. Include actual base/head, changed files, commands, exit codes, raw outputs/artifact refs, failures, deviations and known issues. Do not declare Codex review or user acceptance.

## Stop and report BLOCKED when

- base commit/branch cannot be verified;
- instructions conflict;
- required data/credential/approval is missing;
- a necessary change falls outside allowed scope;
- a test cannot run without materially expanding authority.

