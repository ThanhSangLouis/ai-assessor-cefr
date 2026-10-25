# Nguồn tài liệu của đề tài

Cập nhật lưu trữ 08/10/2026: thư mục tham chiếu cũ đã được xóa theo yêu cầu; source, tài liệu và dữ liệu local được giữ tại `../ai-assessor-cefr-runtime/backups/ai-assessor-cefr-thamchie-before-cleanup-2026-10-08` (không gồm `.venv`). Các đường dẫn/lệnh khảo sát cũ bên dưới là lịch sử; checksum và kết quả khảo sát không đổi.

Dự án `ai-assessor-cefr` là sản phẩm chính thức do nhóm phát triển từ đầu theo SDD hiện hành. Thư mục này lưu đề cương, model provenance và hồ sơ kỹ thuật nội bộ do chính nhóm tạo trong quá trình hình thành đề tài. Hai đề cương DOCX được lưu nguyên bản dưới `original-documents/`; báo cáo fine-tune của Thắng nằm dưới `prior-project-reports/`. Mỗi tài liệu quan trọng có checksum để đối chiếu xuất xứ. Requirement, implementation và evidence của dự án được quản lý theo module và revision hiện hành.

| ID | Tài liệu nguồn | Vai trò trong dự án | Trạng thái sử dụng |
| --- | --- | --- | --- |
| SRC-01 | [Đề cương v3.1](original-documents/De_cuong_AI_Assessor_CEFR_v3.1_ALDM-L.docx) · SHA-256 `cc0b81070dc7af37b153a032094216f3805296ff331734edf9d86c068dafdffe` | Nền tảng nghiên cứu, thuật ngữ, câu hỏi và phạm vi dài hạn | Tài liệu gốc của nhóm; các lựa chọn 10 tuần, 6 tiêu chí và chữ “chốt” trong file không tự áp dụng cho MVP 3 tuần |
| SRC-02 | [Đề cương chi tiết](original-documents/De_cuong_chi_tiet_AI_Assessor_CEFR_A2-B2.docx) · SHA-256 `c17b99aa9d1215d2ac5b9b139d6cc3a069a574eb419b0c814366c1137f51e3f1` | Bối cảnh và phương án ban đầu | Tài liệu định hướng trong giai đoạn hình thành đề tài; thiết kế hiện hành theo SDD module |
| SRC-03 | [Báo cáo W1](../reports/week-01/bao-cao-tuan-01.docx) và [tổng kết W1](../reports/week-01/tong-ket-w1.md) | Bằng chứng công việc W1 và hướng MVP 3 tuần do nhóm cung cấp | W1 hoàn thành theo chủ dự án; các claim nội dung chưa được xác minh độc lập |
| SRC-04 | [Rubric đồ án](../rubric/Rubric_Do_An_Mon_Hoc_CNPM_sinhvien.docx.pdf) | Yêu cầu hồ sơ/chấm đồ án | Nguồn chuẩn cho `docs/evidence/`, khác với rubric chấm Speaking cần giảng viên bộ môn duyệt |
| SRC-05 | [CEFR Companion Volume 2020, Appendix 3](https://rm.coe.int/cefr-companion-volume-with-new-descriptors-2020/16809ea0d4) | Nguồn chuẩn để khảo sát qualitative features của spoken language | Đã xác định trên website Council of Europe ngày 25/09/2026; nhóm vẫn cần diễn giải/rubric theo task và review học thuật |
| SRC-06 | [Báo cáo fine-tune DeBERTa do Thắng viết](prior-project-reports/deberta_cefr_finetune_thang.md) · SHA-256 `27b17e3519f5a648d9acff354bf1887493904a00bdbdee6b80d255d5f94c0a46` | Model provenance cho nhánh transcript; xem [kiểm tra chấm điểm](scoring-audit.md) | Kết quả nghiên cứu nội bộ; weight nằm ngoài Git và chưa thuộc pipeline hiện hành |

[Khảo sát nền tảng kỹ thuật nội bộ](code-survey.md) cùng [kiểm tra scorer/model](scoring-audit.md) tập trung provenance và các quan sát kỹ thuật tại một nơi. Test của dự án được đo riêng trên revision hiện hành và lưu trong evidence của module.

Hai DOCX được lưu byte-for-byte từ kho kỹ thuật nội bộ `../ai-assessor-cefr-thamchie/artifacts/source/documents/`. Các tài liệu 10 tuần, ba presentation, SRS/SDD và `markdown/` lịch sử tiếp tục được quản lý tại đó để tránh nhiều bản gần trùng. Khi cần một quyết định cụ thể, owner ghi tài liệu nguồn và cách áp dụng trong SDD của module.

## Quy tắc nguồn và diễn giải

1. Yêu cầu mới nhất của chủ dự án và kết quả W1 quyết định phạm vi hiện hành. Đề cương gốc hỗ trợ giải thích; approval được quản lý tại các checkpoint SDD của từng module.
2. Phân biệt `FACT` (nội dung có trong nguồn), `PROPOSED` (phương án của nhóm), `OPEN` (chưa chốt) và `MEASURED` (kết quả có dữ liệu/lệnh kiểm tra của repo dự án).
3. Báo cáo kết quả ASR, chấm CEFR, hiệu năng, kiểm thử hoặc nghiên cứu người dùng chỉ xuất hiện sau khi có evidence thực tế tại `docs/sdd/modules/<module>/evidence/` và được dẫn sang `docs/evidence/` theo rubric.
4. Tài liệu và hình W1 được lưu nguyên bản hoặc kèm checksum để bảo toàn provenance và phục vụ báo cáo.

## SCRUM-87 — source tham khảo

Xem [gói handoff SCRUM-87](research-preparation/README.md). Chỉ phục vụ đối chiếu consent; chưa là requirement được duyệt hoặc phiếu consent hoàn chỉnh.

## SCRUM-88 — source tham khảo

Xem [gói handoff SCRUM-88](research-preparation/README.md). Chứa kế hoạch/đề xuất đề bài, rubric và prompt; chưa phải protocol hoặc rubric đã duyệt.
