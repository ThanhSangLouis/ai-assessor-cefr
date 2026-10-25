# SCRUM-87 — đối chiếu nguồn cho phiếu đồng thuận giấy

**Nguồn:** `D:\LAPTRINH\TLCN\AI\ai-assessor-cefr`, HEAD `7614f3d9eec3b2673614b3ca6c4de8d3097221d3` (24/10/2026). **Disposition:** `REFERENCE_ONLY`; chưa có phiếu đã duyệt.

Đã đối chiếu thêm `origin/main` `09b4e8d` (nhánh nguồn đi trước 7 commit): các file consent liên quan không đổi và không có đầu ra consent mới.

| File được chuyển nguyên trạng | SHA-256 | Phần liên quan |
|---|---|---|
| `KE_HOACH_KHAO_SAT.md` ← `docs/plan/KE_HOACH_KHAO_SAT.md` | `AF4787121BC0228C69D8FB4BF7CBB63D4DF8D3DBBEB85ACBAC955C896BB66964` | Phụ lục A là nội dung consent rút gọn; §11 ghi phiếu ký duyệt là đầu ra dự kiến. |
| `17_consent_requirements.md` ← `markdown/week_01/17_consent_requirements.md` | `BE483730FFDE5F1057887D16D8153BE6E50D754096E74A32D4EBDF5096689A96` | Checklist nội dung; trạng thái `DRAFT`, không thay mẫu của trường. |
| `16_data_management_plan.md` ← `markdown/week_01/16_data_management_plan.md` | `15013EE57FC59D6D331BD3A96A2284B567CAF6D2D646BB1A47E6009FFE0C50DE` | Retention, quyền truy cập và xóa còn chờ duyệt; 12 tháng chỉ là đề xuất. |

## Kết quả đối chiếu

Không tìm thấy biểu mẫu giấy hoàn chỉnh, chữ ký hay phê duyệt ethics/GVHD trong repo nguồn. Không chuyển báo cáo test synthetic hoặc runbook vì chúng không phải nội dung cần có trong phiếu. Source plan ghi phiếu ký duyệt là việc sẽ làm ở W6, không phải kết quả đã có.

Target UI hiện có consent bắt buộc và lựa chọn nghiên cứu tùy chọn, nhưng chưa có lựa chọn lưu audio riêng. Browser QA trước đó trên revision `82fe708` ghi nhận trạng thái này; đây là đối chiếu giao diện, không phải phê duyệt consent.

Còn thiếu mẫu được trường/GVHD/ethics duyệt; câu chữ và phiên bản ánh xạ với UI; mục đích lưu/xử lý audio cho bài hiện tại so với tái sử dụng nghiên cứu; retention/xóa, chủ sở hữu và quyền truy cập; contact/khiếu nại; và bằng chứng sign-off. Không dùng tài liệu này để bắt đầu thu dữ liệu hoặc ghi nhận consent thật.

## Recheck code-level source (HEAD `09b4e8d68d46b87a7219bfb009118d29b515c6c7`)

Repo nguồn hiện đồng bộ với `origin/main`; working tree chỉ còn thay đổi local ở file model không liên quan. Nguồn có code consent tách hai lựa chọn, ngoài các tài liệu reference ở trên:

| File nguồn được kiểm tra | SHA-256 | Chức năng |
|---|---|---|
| `src/aicefr/api/templates/consent.html` | `3AA6EEBEE1EC0AC0EE7E4C774E96B1DBBF1EE5133F438BA28176974C48F02E97` | Hiển thị checkbox riêng cho lưu audio và tái sử dụng nghiên cứu. |
| `src/aicefr/api/static/consent.js` | `BE32F3947BD82CBDBB7EAED67E1102FBFC5FA70F00FFF987DF2839BF162DD686` | Gửi hai lựa chọn riêng lên API. |
| `src/aicefr/storage/consent_repository.py` | `185B423277B0FD021AF970E473DBFE0101AA33198F1A9E504046AC05F770ABFB` | Lưu/version hóa hai consent; `may_submit` phụ thuộc audio consent còn hiệu lực. |
| `tests/test_consent.py` | `9713A1B5B92F0E940BF57C93356EC0E2397B5A5E4EABEDBEBAF06666844A2369` | Test consent bằng test data. |

Đối chiếu target hiện tại: M08/M11 và WSGI consent chỉ có `research_allowed`, chưa có `audio_storage_allowed`. Source consent dùng FastAPI/Mongo; target dùng WSGI/SQLite và contract khác. Chưa chuyển code vì ticket hiện là phiếu giấy khớp implementation target, còn thêm lựa chọn audio vào target sẽ đổi consent contract/schema/API và cần scope/SDD owner review. Source UI là bằng chứng về lựa chọn ở **repo nguồn**, không phải trạng thái giao diện target.

Kết luận về biểu mẫu giữ nguyên: source code có hai lựa chọn, nhưng source vẫn không có phiếu giấy đã ký/được duyệt; phụ lục consent trong kế hoạch còn là đề xuất.

## Target branch follow-up — SCRUM-87 (25/10/2026)

The comparison above records the target state at its audit revision. The SCRUM-87
task branch subsequently added a target-side `audio_storage_allowed` consent
choice and linked a printable `consent-v2` form. No source-repository code was
copied into the target; the target contract and SQLite migration were implemented
for its WSGI/storage architecture. The current implementation and test/browser
evidence are recorded at
`docs/sdd/modules/m08-identity-storage-admin/evidence/scrum-87-implementation.md`.

The retention section remains explicit: the tracked data-management plan calls
12 months a proposal, and the app does not automatically erase stored audio.
This branch does not claim an approved retention policy or real-data collection.
