# SCRUM-86 — Báo cáo xử lý backlog Jira nền tảng

**Evidence ID:** `SCRUM-86-JIRA-BACKLOG-DISPOSITION`  
**Ngày rà:** 25/10/2026  
**Baseline mã nguồn:** `main` `f540cb88643214cd1d4444f2dd0d81f4463119fa`  
**Issue điều phối:** [SCRUM-86](https://vothanhsangdev.atlassian.net/browse/SCRUM-86)

## Kết quả

Sáu ticket W3 được đối chiếu với trạng thái Jira, PR đã merge và evidence trong repo. Năm ticket được đóng hoặc gộp vào ticket đang theo dõi; SCRUM-34 được chuyển sang W7 vì policy dữ liệu thật và retention chưa được chốt. Không có dữ liệu người học thật hoặc thay đổi policy trong lượt này.

| Ticket | Trạng thái trước | Quyết định | Lý do và bằng chứng |
| --- | --- | --- | --- |
| [SCRUM-15](https://vothanhsangdev.atlassian.net/browse/SCRUM-15) | In Review | Đóng | Contract M03–M05, CI và unit/coverage đã merge ở [PR #6](https://github.com/thanglb2005/ai-assessor-cefr/pull/6), merge `a92fafe`; hai check CI thành công. Sang đã xác nhận 8 tests và coverage 96% trong comment Jira. Chủ dự án xác nhận đang đảm nhiệm vai trò Nguyên và được ủy quyền review; việc đóng ticket chỉ phản ánh contract hiện hành, không duyệt phase M08 hay thay đổi SDD. |
| [SCRUM-16](https://vothanhsangdev.atlassian.net/browse/SCRUM-16) | To Do | Đóng | Decoder M02 đã merge ở [PR #11](https://github.com/thanglb2005/ai-assessor-cefr/pull/11), merge `8419533`; CI thành công ở lượt cuối. Test `tests/audio/test_decoder.py::test_pcm_16k_mono_deterministic_resample` nằm trong scoped regression SCRUM-83 và đạt. Định dạng đầu ra được kiểm là 16 kHz, mono, float32. |
| [SCRUM-34](https://vothanhsangdev.atlassian.net/browse/SCRUM-34) | To Do | Chuyển sang W7 | M08 W2 chỉ cho phép fixture; Requirement/Status giữ export/xóa dữ liệu thật và retention ngoài scope cho tới khi có policy/data-plan approval. UI hiện vẫn hiển thị retention chưa chốt; mốc 12 tháng chỉ là đề xuất. W5 data-operations chỉ kiểm fixture, không thay approval policy. Chuyển vào sprint **W7 — 26/10–01/11** (sprint ID `36`) để chốt phạm vi/policy trước khi vận hành dữ liệu thật. |
| [SCRUM-43](https://vothanhsangdev.atlassian.net/browse/SCRUM-43) | To Do | Đóng | Báo cáo [W3 Final Verification](../../sdd/features/w3-local-integration/08-final-verification.md) đã tổng hợp lệnh, revision, test count, coverage theo module, defect/review state và evidence. Nó đo source `ffb325c`; report nói rõ verdict Phase 09 vẫn `PENDING` và regression tại merge head chưa được khẳng định. Ticket này yêu cầu lập báo cáo W3, không thay verdict nghiệm thu W3. |
| [SCRUM-44](https://vothanhsangdev.atlassian.net/browse/SCRUM-44) | To Do | Gộp vào SCRUM-68 và đóng ticket cũ | Hướng dẫn local và W3 fixture journey được lưu trong repo/W3 evidence; các yêu cầu build/run guide, final clean install và end-to-end gate hiện được theo dõi trong [SCRUM-68](https://vothanhsangdev.atlassian.net/browse/SCRUM-68). SCRUM-68 vẫn `In Review`; chưa claim full W5 E2E hoặc owner verdict đã đạt. |
| [SCRUM-45](https://vothanhsangdev.atlassian.net/browse/SCRUM-45) | To Do | Đóng | Reason code QC được chuyển tới scorer trong [PR #9](https://github.com/thanglb2005/ai-assessor-cefr/pull/9), merge `74afca9`; CI thành công. Regression `tests/asr/test_service.py::test_qc_reject_reasons_reach_the_scorer` có trong scoped regression SCRUM-83 và đạt. |

## Trạng thái sau cập nhật Jira

| Ticket | Trạng thái sau | Jira comment / sprint |
| --- | --- | --- |
| SCRUM-15 | `DONE` | Ghi nhận evidence PR #6 và xác nhận owner |
| SCRUM-16 | `DONE` | Ghi nhận decoder contract và PR #11 |
| SCRUM-34 | `TO_DO` | Sprint W7, ID `36`; policy và human-data operation vẫn pending |
| SCRUM-43 | `DONE` | Liên kết W3 report; không thay verdict Phase 09 |
| SCRUM-44 | `DONE` | Đóng dạng superseded; carry-forward tại SCRUM-68 |
| SCRUM-45 | `DONE` | Ghi nhận PR #9 và regression test |

Đóng các ticket chỉ xác nhận disposition phù hợp với từng DoD/evidence; không có kết luận rằng toàn bộ W3/W5 đã được nghiệm thu.
