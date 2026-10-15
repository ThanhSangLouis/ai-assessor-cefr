# Báo cáo tích hợp SCRUM-69 — Trust, pipeline, report và API

Ngày kiểm tra: 15/10/2026. Nhánh được dựng trên G1 `9748814`; nguồn module trước tích hợp `d60e8a4`. Worktree được yêu cầu không commit/push; chấp thuận nghiệp vụ/reviewer toàn cục vẫn đang chờ.

## Tích hợp runtime

`create_runtime` ghép `RuntimeTrustEvaluator` với scorer đang hoạt động, cấu hình Trust và `TaskRepository` của cùng runtime SQLite. Worker dùng composition path hiện có. Thiếu artifact hoặc artifact không khớp pin SHA/model/feature order/band thresholds làm readiness thất bại và mọi bài không có conformal evidence đều fail closed; không có cờ mặc định tắt Trust để giữ readiness xanh. Thay model qua admin activation/reload khởi tạo lại evaluator bằng pin hiện hành; evaluator không tái sử dụng calibration gắn với model cũ.

ASR lưu ngôn ngữ, confidence và metadata detector trên transcript. Trust ưu tiên metadata đó; transcript cũ được đánh giá bằng detector độc lập nếu adapter hỗ trợ, còn thiếu detector trả về `UNCERTAIN`. Guard chỉ đọc task/transcript, không tác động feature vector hoặc đầu ra scorer. Khi conformal set đơn lẻ hoặc hợp các cửa sổ có một band, bài có thể tiếp tục; nhiều band, ngôn ngữ chưa chắc, nghi ngờ sai đề/đọc prompt chuyển sang review mà không phạt điểm. Ngôn ngữ không phải tiếng Anh với confidence đủ cao đưa response sang `REJECTED`, report `NOT_EVALUATED`, không band/điểm và không tạo candidate chấm thông thường. Lỗi cấu hình hình học cửa sổ dài được ghi `LONG_RESPONSE_REVIEW`, report không ước lượng và chuyển review; đường tính cửa sổ hợp lệ vẫn chấm từng cửa sổ và giữ provenance kết quả.

Task topic keywords là metadata có version theo `(task_id, task_version)` trong bảng `runtime_settings` hiện có. Boot chỉ tạo metadata cho task row mới; config khởi động không ghi đè task đã tồn tại. Sửa prompt/keyword ở task đã có submission bị chặn, cần tạo version mới. Task cũ chưa có keyword metadata vẫn giữ ngữ cảnh không xác định thay vì suy diễn chủ đề.

Report lưu các Trust field dưới dạng trường tùy chọn, nên JSON cũ đọc được và không được bổ sung Trust giả. Năm criterion indicator luôn mang nhãn `chỉ báo`, không tạo điểm CEFR theo tiêu chí. Report builder chỉ gắn ID evidence đã qua validator và cùng criterion; tối đa tám ID mỗi criterion để giữ payload nhỏ. Evidence không hợp lệ vẫn nằm trong `evidence_issues` và không được gắn vào indicator.

## Hợp đồng API

`GET /api/v1/reports/{response_id}` yêu cầu bearer session của student, teacher hoặc admin.

| Kết quả | Hành vi |
| --- | --- |
| 200, student sở hữu response | Report; Trust chỉ gồm disposition, reason ổn định và hướng khắc phục. Không gửi prediction set, provenance nội bộ hoặc thông tin detector. Năm indicator chỉ có tên, nhãn và coverage. |
| 200, teacher/admin và response tồn tại | Report cùng Trust evidence/provenance đã lọc đường dẫn; quyền xem dựa trên response, không phụ thuộc response có review candidate. |
| 202, report chưa được ghi | Response ID, status và `report: null`. |
| 401 / 403 / 404 | Chưa xác thực / sai role / response ngoài quyền sở hữu hoặc không tồn tại. Student khác không dò được response. |

UI HTML dùng cùng nguyên tắc bỏ giá trị path khỏi `source_versions` và provenance. Student report giữ thông điệp recovery ngắn; teacher có thể xem detector, guard spans, conformal bounds và calibration identifiers cần thiết để rà soát. Blind token, rating hoặc định danh nghiên cứu không được đưa vào report payload.

## Giới hạn đã biết

- Guard dựa trên lexical overlap và trùng n-gram là tín hiệu sàng lọc, không kết luận gian lận và không thay điểm. Cần đánh giá precision/recall trên tập có nhãn trước khi thay threshold.
- Detector LID và calibration artifact phải được cung cấp theo cấu hình runtime đã xác thực. Thiếu artifact làm `/readyz` trả 503; các synthetic calibration trong test là fixture-only, không đại diện calibration sản phẩm.
- Task phiên bản cũ chưa có topic keywords có thể chỉ kiểm tra prompt-copy; guard off-topic báo thiếu evidence cho tới khi có task version mới chứa metadata.
- Tập conformal có nhiều band được giữ làm thông tin review; hệ thống không chọn tự động một band. Không có teacher verification mới được tạo.
- Báo cáo không tuyên bố chứng nhận CEFR. Đánh giá trên synthetic fixture không thay cho thử nghiệm người học hoặc kiểm định CEFR độc lập.

## Xác minh tích hợp

Lệnh kiểm tra scoped, dùng pinned model directory có sẵn ngoài Git:

```bash
AICEFR_MODEL_DIR=/home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr-runtime/models \
PYTHONPATH=src \
/home/thanglvc/Documents/HCMUTE/TLCN/ai-assessor-cefr/.venv/bin/coverage run -m pytest -q \
  tests/local/test_trust_integration.py tests/api/test_trust_api.py \
  tests/pipeline/test_coordinator.py tests/review/test_review_service.py \
  tests/local/test_foundation_runtime.py tests/portal/test_portal.py \
  tests/report/test_report_service.py
```

Kết quả: **111 passed**. `coverage report -m --include=src/aicefr/trust/service.py` ghi nhận **100% statement và 100% branch coverage** cho `RuntimeTrustEvaluator`. Ruff đã chạy trên các module integration/API/report/windows/routing và test tương ứng, kết quả sạch. Baseline toàn repo và real-audio smoke do root chạy riêng; con số này không được gộp vào scoped evidence.
