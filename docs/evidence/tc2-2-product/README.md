# TC2.2 — Mức độ hoàn thiện sản phẩm

**Nguồn tiêu chí:** rubric PDF tại docs/rubric/. Trạng thái của folder: PARTIAL — có source và local evidence, nghiệm thu PENDING.

## Hồ sơ cần có

Source, commit/diff, danh sách chức năng đã cam kết, demo/build trên repo dự án và đối chiếu khối lượng theo phân công.

## Minh chứng hiện có

| Tài liệu | Đường dẫn | Tình trạng |
| --- | --- | --- |
| Roadmap | [Roadmap](../../plan/three-week-roadmap.md) | Tài liệu đầu vào/đã có; cần kiểm tra nội dung trước nghiệm thu |
| Kế hoạch W2 | [Kế hoạch W2](../../plan/week-02.md) | Tài liệu đầu vào/đã có; cần kiểm tra nội dung trước nghiệm thu |
| Kế hoạch W3 | [Kế hoạch W3](../../plan/week-03.md) | Tài liệu đầu vào/đã có; cần kiểm tra nội dung trước nghiệm thu |
| W3 implementation | [W3 Tasks/Status](../../sdd/features/w3-local-integration/07-status.md) | W3-TASK-001–008; local feature branch, user verdict PENDING |
| Demo/local entrypoint | [Local run guide](../../local-run.md) | CLI, fixture accounts, consent, upload/report và teacher review; model/data ngoài Git |
| Inference smoke | [Actual ASR/VAD](../../sdd/features/w3-local-integration/evidence/real-speech-smoke.md) | Codex đo 02/10; Whisper/Silero/Ridge local, không là validation CEFR |
| Revision/test/review | [W3 Evidence](../../sdd/features/w3-local-integration/evidence/evidence-manifest.md) | Dẫn source commits, raw reports và kiểm tra độc lập |
| W5 DoD baseline — SCRUM-83 | [Evidence index](../w5-dod-baseline-2026-10-25.md) | Inventory theo 12 điều kiện; W5 vẫn `PENDING`, chưa có owner verdict |

## Còn thiếu / cần xác minh

User acceptance, rubric học thuật/calibration và validation người học chưa có từ lượt này. Branch W3 chưa push/deploy; không có demo production. Giờ công W1 là ước tính, không là timesheet đo thực; automation W3 cũng không thay giờ công các owner.

Khi có evidence mới, thêm dòng gồm: Evidence ID, nguồn/path hoặc URL, ngày, owner, Prompt/Task/AC nếu áp dụng, revision/checksum và trạng thái xác minh. Chỉ ghi số liệu và trạng thái PASS khi có phép đo cùng evidence tương ứng.
