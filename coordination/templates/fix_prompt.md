# Locked fix prompt

| Field | Value |
| --- | --- |
| `work_id` | `[required]` |
| `status` | `FIX_PROMPT_LOCKED` |
| `fix_version` | `F1` |
| `review_ref` | `[Codex review path/hash]` |
| `starting_commit` | `[failed head commit]` |
| `allowed_findings` | `[F001, ...]` |
| `prompt_hash` | `[sha256 after lock]` |

## Objective

Fix only the listed findings without changing approved V3 scope.

## Findings to fix

| Finding ID | Required correction | Verification |
| --- | --- | --- |
| F001 | [verbatim from review] | [exact test/check] |

## Allowed files

- [Exact paths]

## Forbidden changes

- Do not rewrite Git history.
- Do not modify approved package or unrelated code.
- Do not suppress/delete a failing test unless explicitly required by the finding.
- Do not introduce new dependency/service/data access outside V3.

## Report

Append a new fix section to the Antigravity raw report with new head commit, actual diff, commands, exit codes and raw results.

