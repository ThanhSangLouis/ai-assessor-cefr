# SCRUM-70 / W5-S02 — Domain, alignment và mission rules

Historical target `3b2d2b78ba5bb35bd162b8f3e5de21ade946d237`; reference Sang `40907cc35b3d04408f9a8713f16d9be99f4cd6c7`. Actual branch/source base do root ghi trong authority.md. User đã chỉ định Luna implement, root review và tạo PR; chỉ là quyền task-local, không tự APPROVED các phase DRAFT. Đọc AGENTS.md, AI_CONTEXT.md, module M10 01/03/04/05/06/07, week-05 mục S02/9.4 và `/tmp/s02-reference-prep.md`.

## Owner
Chỉ sửa `src/aicefr/practice/{__init__,contracts,bank,missions,recommend}.py`, `src/aicefr/lessons/{__init__,model,align,text,checks,lint,review,progress}.py` và test unit tương ứng `tests/practice/`, `tests/lessons/` (không test repository/API). Không sửa storage, service runtime, local/app, API, pyproject, migration, workbook. Không commit/push. Assert cwd và branch scrum-70 trước mỗi mutation; main checkout chỉ root sửa log.

## Kết quả bắt buộc
- Frozen typed allowlist models; practice results không field overall_score/band/teacher_verified. Purpose PRACTICE/LEARNING riêng, không dùng Assessment. Mission metadata có criterion và target_band để chọn nhiệm vụ, nhưng result không band.
- Catalogue15 deterministic 5×A2/B1/B2 với đúng IDs PR-FLU/COH/RAN/ACC/PHO-{band}, bảy MissionKind từ pinned reference. Rule fixed/versioned, evidence span/index có bounds; no speech UNMEASURED, ASR confidence thiếu/low UNSURE, không suy diễn sai.
- Nine StepKind và bốn stage đúng mapping pinned; published full lesson có đủ stages, free2–3rounds với time budget giảm. Lint phải validate nội dung/kind/payload và version/reference; teacher draft có thể chưa đầy đủ nhưng publish phải lint sạch.
- Alignment Levenshtein deterministic; contractions/number/ordinal/USUK normalization; lemma simplemma tiếng Anh (runtime dep root/integration pin `simplemma==1.1.2`, official API https://github.com/adbar/simplemma `lemmatize(token,lang='en')`). Irregularfallback versioned, không coi lemma-equivalent hoặc lowconfidence là sai; tokens ngoài VAD±0.3 bỏ; thiếu speech UNMEASURED.
- Recommendation dùng assessment mới nhất đủ điều kiện, criterion coverage/evidence yếu nhất (không giả criterion score), stableties, nearestband; fallback A2 có reason/explanation; không nhận practice result làmassessment.
- Review date VN timezone aware, firstdue+1day, passbox1→2+3days,2→3+7days,3→4done; failreset1+1day. Pure function clock injected, deterministic boundary.
- Progress completion threshold rõ +free step, retry không doublecount; S03 reward chưa implement ở đây.

## Contract handoff và test
Trong bước đầu tiên, ghi model/field/method signatures vào docs evidence lane để storage/integration agents có contract dùng chung; gửi root khi contract sẵn, rồi freeze shape hoặc phối hợp trước thay đổi. Có thể đọc pinned `git show 40907cc:path` nhưng không fetch/update reference hoặc bê source mutable; adaptation tuân thủ target contracts, no-band và quyền. Dùng meaningful unit tests cho7rules/9types/alignment/lemma/VAD/silence/multiround/recommend/review timezone; new pure logic line≥90%,branch≥85%. Shared .venv test `PYTHONPATH=src AICEFR_MODEL_DIR=<runtime>/models`; COVERAGE_FILE lane riêng. Ruffcheck/format toàn ownedfiles, không sửa scope khác. Ghi Vietnamese report actual commands/counts/coverage/limits; không claim browser hay external approval.
