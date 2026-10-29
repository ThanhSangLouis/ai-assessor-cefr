# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

## 23. Backlog tuần 2

| Thuộc tính | Giá trị |
| --- | --- |
| Tuần | W1 - Nền tảng đo lường, phạm vi và điều kiện nghiên cứu |
| Trạng thái | DRAFT - cần thực hiện và xác nhận |
| Người phụ trách | SV2 điều phối |
| Người duyệt | GVHD |
| Phiên bản | 1.1 |
| Ngày cập nhật | 02/09/2026 |
| Trạng thái thực thi | BLOCKED BY G1 - chỉ là proposed backlog |

## 1. Mục tiêu W2

Khóa rubric A2/B1/B2, task blueprint, prompt bank, rating form, reason codes, anchor protocol và thiết kế Task C đủ để bắt đầu vertical slice W3.

Không bắt đầu implementation W2 từ file này cho đến khi G1 `PASS` hoặc `CONDITIONAL PASS` có owner/deadline và không còn blocker ảnh hưởng trực tiếp.

### 1.1. Phần chuẩn bị được thực hiện trước G1

Ngày 02/09/2026 đã hoàn thành desk survey cho W2-11/W2-14 mà không tải corpus hoặc khóa thiết kế: xem `../week_02/01_public_data_source_register.md`, `02_data_acquisition_plan.md` và `03_dataset_manifest_spec.md`. Đây là `PRE-G1 PREPARATION`, không thay đổi trạng thái `BLOCKED BY G1` của backlog.

## 2. Backlog ưu tiên

| ID | Hạng mục | Ưu tiên | Owner | Phụ thuộc | Acceptance |
| --- | --- | --- | --- | --- | --- |
| W2-01 | Rubric v0.1 cho 6 criteria | P0 | SV2 + GV | G1 construct | Có A2/B1/B2 và insufficient evidence |
| W2-02 | Rating manual | P0 | SV2 | W2-01 | Ví dụ, boundary, error rules |
| W2-03 | Task A blueprint | P0 | Pedagogy | G1 | Purpose, duration, coverage, prompts |
| W2-04 | Task B blueprint | P0 | Pedagogy | G1 | Kiểm tra floor A2 |
| W2-05 | Chọn và đặc tả phương thức Task C | P0 | Pedagogy + SV3 | D004, D013 | Có contingent interaction, timing, clarification paths và missing-evidence rule |
| W2-06 | Prompt equivalence/reliability design | P0 | SV2 | W2-03/04, D014 | Topic/difficulty/function balanced; xác định rõ within-speaker hay between-speaker estimand |
| W2-07 | Rating form | P0 | SV2/SV3 | W2-01 | Blind independent rating + confidence |
| W2-08 | Reason code schema | P1 | SV1/SV2 | Evidence matrix | Codes cho quality/evidence/review |
| W2-09 | speaking_profile schema | P1 | SV3 | Scope/output | Versioned JSON example |
| W2-10 | Latency measurement protocol | P0 | SV1/SV3 | Task C | Client/system latency tách riêng |
| W2-11 | Anchor sourcing plan | P1 | GV + SV2 | Rubric | Quyền sử dụng và level coverage |
| W2-12 | Rater calibration plan | P1 | SV2 | Rubric/anchor | Session, materials, record forms |
| W2-13 | Data schema/database draft | P1 | SV3 | DMP | PII separation and keys |
| W2-14 | Test fixtures/audio samples | P2 | SV1 | Task specs | 3-5 non-sensitive samples |
| W2-15 | Precision-analysis artifact | P0 | SV2 | D015 | Script/config/seed/output tái lập; không chứa dữ liệu thật |
| W2-16 | Contract/invariant tests | P0 | SV1 + SV2 + SV3 | Schema/RQ/DMP | Speaker leakage, evidence refs, missing Interaction, `teacher_verified=false`, no PII logs |

## 3. Lịch gợi ý

| Ngày | Trọng tâm |
| --- | --- |
| W2-D1 | Rubric workshop và boundary A2/B1/B2 |
| W2-D2 | Task A/B, prompt bank và equivalence |
| W2-D3 | Task C, prompt tree và latency protocol |
| W2-D4 | Rating form, reason codes, schema |
| W2-D5 | Dry run rater, sửa và review G2 |

## 4. G2 draft checklist

- [ ] Rater giải thích được điểm theo evidence.
- [ ] Mỗi criterion có task tạo evidence.
- [ ] Interaction missing rule hoạt động.
- [ ] Task C timing/latency đã test.
- [ ] Prompt instructions không vượt target.
- [ ] Rubric/prompt/schema có version.

## 5. Cut rules

- Nếu Task C không ổn cuối W2: cắt Task C/Interaction khỏi MVP.
- Nếu rubric chưa đạt đồng thuận: không code scoring logic cố định.
- Nếu anchor chưa có: dùng sample nội bộ chỉ cho dry run, không coi là benchmark chính thức.
