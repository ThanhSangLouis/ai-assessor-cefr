# M09 — Research và Adaptation Map

**Version:** v0.1 · **STATUS:** DRAFT · review cùng Phase 03.
**Reference baseline:** repo Sang `40907cc35b3d04408f9a8713f16d9be99f4cd6c7` (read-only).
**Target baseline:** repo dự án `3b2d2b78ba5bb35bd162b8f3e5de21ade946d237`.

## Hợp đồng tham khảo

- Phạm vi: `asr`, `features/relevance.py`, `scoring/conformal.py`, pipeline/report, calibration/refusal tools và test liên quan.
- Mức sử dụng: `ADAPT`; target giữ contract M03–M07, không sao chép kiến trúc router/storage của nguồn nếu xung đột.
- Không mang sang: secret, model JSON không rõ provenance, số liệu hiệu năng, branding, hard-coded path và mọi phần D043.

## Findings

- Target đã có ASR validation, feature/scorer provenance, window policy, report persistence và review routing; nên mở rộng contract thay vì tạo pipeline thứ hai.
- Nguồn chứng minh tính khả thi của conformal set, relevance guard và refusal benchmark nhưng không tự là requirement.
- Rủi ro lớn nhất là biến guard thành penalty ẩn, làm criterion indicator giống điểm, hoặc fallback im lặng khi artifact thiếu.
- Công cụ benchmark cần ranh giới rõ giữa calibration/dev/confirmation set để tránh leakage.

## Adaptation Map

| REF-ID | Nguồn | Giá trị giữ | Áp dụng vào target | Quyết định |
| --- | --- | --- | --- | --- |
| M09-REF-01 | `scoring/conformal.py` | deterministic prediction set | adapter theo artifact contract M05, hash bắt buộc | ADAPT |
| M09-REF-02 | `features/relevance.py` | evidence cho off-topic/prompt-reading | dùng FeatureSet/version hiện hành, chỉ route review | ADAPT |
| M09-REF-03 | `tools/calibrate_conformal.py` | CLI reproducible | thêm manifest/seed/output hash và no-leakage check | ADAPT |
| M09-REF-04 | `tools/refusal_benchmark.py` | refusal matrix | đo trên fixture/manifest được phép, không claim thực nghiệm | ADAPT |
| M09-REF-05 | source report/UI wording | giải thích uncertainty | viết lại theo contract/thuật ngữ target | INSPIRE |

## Kết luận nghiên cứu

Giữ modular monolith, triển khai M09 như domain service thuần được `PipelineCoordinator` gọi. Không thêm network boundary. Các quyết định sản phẩm ở Requirement vẫn `PENDING` cho tới user verdict.
