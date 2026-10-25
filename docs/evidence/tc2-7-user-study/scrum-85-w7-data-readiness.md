# SCRUM-85 — Readiness dữ liệu pilot W7

**Evidence ID:** `SCRUM-85-W7-DATA-READINESS`  
**Ngày rà:** 25/10/2026 · **Owner theo nhánh:** Thắng  
**Baseline:** `82fe708af80f0b50eb540c65b5c583f64868d2c8`  
**Trạng thái:** `BLOCKED` — chưa chuẩn bị hoặc thu dữ liệu người học; chỉ lập readiness record.

## Phạm vi

Ảnh Jira chỉ có tiêu đề SCRUM-85, không có Acceptance Criteria hoặc định nghĩa loại dữ liệu. Repo không có kế hoạch `week-07`, protocol pilot đã duyệt, participant manifest hay dữ liệu tại hồ sơ TC2.7. Vì vậy record này chỉ xác định readiness và điều kiện mở; không tạo dataset, audio, participant giả hoặc số liệu pilot.

## Evidence hiện có

| Nguồn | Trạng thái thực tế | Ý nghĩa đối với SCRUM-85 |
| --- | --- | --- |
| [M13 Requirement](../../sdd/modules/m13-learning-evidence/01-requirement.md), [Research](../../sdd/modules/m13-learning-evidence/02-research.md), [Specification](../../sdd/modules/m13-learning-evidence/03-specification.md), [Test Plan](../../sdd/modules/m13-learning-evidence/04-test-plan.md), [Plan](../../sdd/modules/m13-learning-evidence/05-plan.md) | Các artifact trên baseline `82fe708` là `DRAFT`; Phase 01 và Research decision `PENDING`. SCRUM-88 có protocol/prompt/rubric trên branch đã push `0998deb`, chưa merge vào baseline và task acceptance còn chờ review. | Không lấy M13-FR-003 (tối thiểu 4 trong bản nháp) làm cỡ mẫu được duyệt. Trước collection cần review protocol SCRUM-88 theo quyền duyệt đã xác nhận và chốt mapping vào revision sẽ chạy. |
| [M13 Status](../../sdd/modules/m13-learning-evidence/07-status.md) | Phase 01 `PENDING`; implementation `CODE_MERGED` một phần; review/acceptance `PENDING`; study outcomes `NOT_EVALUATED` | Code/test evidence không chứng minh đã có pilot data hoặc được phép thu dữ liệu. |
| [M12 Status](../../sdd/modules/m12-blind-evaluation/07-status.md) | Requirement/Research `DRAFT/PENDING`; implementation một phần; review/acceptance `PENDING`. Branch SCRUM-89 local `5901e04` có tài liệu training reference, chưa push. | Chưa có roster hai rater, lượt tập huấn/calibration thực tế hoặc assignment đủ điều kiện trên target để tạo bộ bài chấm thật. |
| [TC2.7 hồ sơ](README.md) | Ghi chưa có thực nghiệm người dùng; fixture không thay thế user-study evidence | Chưa có artifact participant, dataset, metric hoặc thay đổi sau phản hồi. |
| [W6-S03 technical smoke](../../sdd/modules/m09-trust-layer/evidence/w6-s03-real-pipeline.md) | Một audio TTS được dùng cho pipeline smoke; không phải giọng người học | Chỉ chứng minh một đường chạy kỹ thuật; không phải dữ liệu pilot, rater calibration hay CEFR validation. |

## Điều kiện cần chốt trước khi tạo dữ liệu pilot

1. SCRUM-88/M13: review protocol đã push tại `0998deb`, xác nhận prompt ID/version, rubric theo M05, population/eligibility, phương pháp/cỡ mẫu, lịch W7, metric và xử lý bài thiếu/lỗi trên revision sẽ chạy.
2. SCRUM-87: hoàn tất nội dung phiếu consent và mapping với target, gồm mục đích, lựa chọn lưu audio riêng, tái sử dụng nghiên cứu, withdrawal, retention/xóa, quyền truy cập và người giữ mapping pseudonym. Theo xác nhận của chủ dự án, không cần GV ngoại ngữ hoặc biên bản họp riêng.
3. SCRUM-81/SCRUM-89: chốt quy trình chấm mù, roster hai rater, anchor/bài tập, version rubric, tập huấn và calibration thực tế. Tài liệu training reference trên branch chưa thay cho hoạt động này.
4. M13 owner/project owner: verdict các phase SDD áp dụng và quyền bắt đầu thu dữ liệu thật; xác nhận nơi lưu được kiểm soát ngoài Git và người được cấp quyền.
5. Sau khi được phép: manifest dữ liệu phải ghi protocol/version, consent version, pseudonymous record ID, eligibility, source/collection date, custodian, secure storage reference, checksum và withdrawal/erasure state. Không ghi tên, email, audio hoặc mapping nhận dạng vào Git.

## Blocker và next action

`SCRUM-85` giữ `BLOCKED`. SCRUM-88 đã push protocol/prompt/rubric nhưng chưa merge vào baseline; SCRUM-87 chưa có phiếu consent khớp target; SCRUM-89 chưa có hoạt động hai rater/calibration ghi nhận. Chốt các artifact và blind-rating readiness SCRUM-81 trước khi lập collection batch. Sau khi owner review/cho phép trên revision sẽ chạy, có thể tạo manifest và thu theo protocol; đến lúc đó pilot vẫn `NOT_RUN`/`NOT_EVALUATED`. Fixture tổng hợp chỉ được tạo theo task kiểm thử riêng và phải được ghi là fixture, không thay cho pilot data.

Không chỉnh M12/M13 SDD trong task này vì đây là scope do Sang sở hữu và chưa có verdict Phase 01–05. Không thay Jira status; report này là readiness finding, không phải task acceptance.
