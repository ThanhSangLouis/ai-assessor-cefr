# M02 — 06 Tasks (W2 task breakdown)

> **W2 v0.2 · 28/09/2026 · Phase 05 APPROVED by Thắng for implementation.** Sang’s M03/M04 review remains pending and must be disclosed before PR merge. M02-PROMPT-001 issued to Codex for SCRUM-46; Antigravity unavailable in this session.

| Jira / Task ID | FR/AC · Test IDs | Branch | Dependencies | Planned scope | Exit evidence |
| --- | --- | --- | --- | --- | --- |
| SCRUM-46 · M02-TASK-001 — Audio decoder, QC measurements và unit tests | M02-FR-001/002 / M02-AC-001/002 · M02-TEST-001–006 | `feat/SCRUM-46-M02-TASK-001-Audio-decoder-QC-va-unit-tests` | No source predecessor; Sang shared-contract review pending under Thắng Phase 05 override | Approved SoundFile/SoXR decoder, whitelist/channel policy, 16 kHz PCM output, explicit measurements/config; files from SCRUM-46 row in 05-plan | Test IDs PASS, coverage report, `ruff` if configured, privacy-safe diff, evidence with revision/fingerprint |
| SCRUM-47 · M02-TASK-002 — QC policy và pipeline boundary tests | M02-FR-001/002 / M02-AC-001/002 · M02-TEST-007, 008 | `feat/SCRUM-47-M02-TASK-002-QC-policy-va-pipeline-boundary-tests` | SCRUM-46 implementation committed; Sang boundary review pending under Thắng Phase 05 override | Versioned PASS/REVIEW/REJECT policy and M02 pipeline gate; no edit to M03 service | Test IDs PASS; PASS-only dispatch proven with ASR spy; REJECT/REVIEW create no transcript/score; evidence with revision/fingerprint |

## Shared gates and completion

- Sang (M03/M04 owner) must review `QCMeasurement`, the `QCResult` extension and 16 kHz output contract; M03 must review PASS-only dispatch. Record comments/approval before recommending PR merge; Thắng explicitly deferred this review until tasks are implemented.
- Each task gets its own prompt ID/file under the approved Phase 05 artifact and a fresh branch fingerprint. Prompt status records the actual executor and evidence; M02-PROMPT-001 was issued to Codex.
- Branch/PR order across tasks: SCRUM-46 → SCRUM-47 → SCRUM-48 → SCRUM-49. M02 order is SCRUM-46 → SCRUM-47. SCRUM-47 starts from the SCRUM-46 implementation commit; after SCRUM-46 merges, update SCRUM-47 against current `main` if the PR merge method requires it.
- No task may commit audio, transcript, model, secret or actual participant data. No production QC defaults are added.

**Trạng thái:** SCRUM-46 and SCRUM-47 IMPLEMENTED / CHECKS PASS; Sang review PENDING. **Phase 05 verdict:** APPROVED by Thắng · 28/09/2026; Sang review PENDING.

## W7 — Chuyển M02 từ repo gốc (W7-T02, SCRUM-99)

| Task | Deliverable | Tests | Status |
| --- | --- | --- | --- |
| W7-T02 (M02) | `src/aicefr/audio/` (`decoder.py`, `config.py`, `recordings.py`, `pipeline.py`), `src/aicefr/qc/` (`audio_qc.py`, `policy.py`) | `test_audio_qc.py`, `test_decoder.py`, `test_pipeline.py` | IN_REVIEW — Chuyển từ ThanhSangLouis/ai-assessor-cefr@0853c95 vào nhánh tích hợp |
