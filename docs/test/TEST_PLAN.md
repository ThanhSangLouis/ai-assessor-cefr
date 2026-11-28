# Kế hoạch kiểm thử tổng

**Hệ thống:** SpeakUp, hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR.
**Phiên bản tài liệu:** 1.0, ngày 28/11/2026, đo trên `main` `2dfa4fc`.

Tài liệu này là khung chung. Test case chi tiết của từng tính năng nằm ở 27 kế hoạch con `TEST_PLAN_D*.md` trong cùng thư mục (mục 7). Danh sách lỗi và trạng thái sửa nằm ở [DEFECTS.md](DEFECTS.md).

## 1. Mục tiêu

1. Mỗi yêu cầu chức năng trong SRS có ít nhất một test tự động chạy được, kể cả **ca lỗi** (đầu vào sai, không đủ quyền, hết lượt, tranh chấp đồng thời).
2. Không đổi hành vi đã có mà không biết: mọi PR chạy lại toàn bộ bộ test trên CI trước khi merge.
3. Bảo vệ ba thứ khó sửa sau khi lộ ra: **quyền truy cập**, **tiền/lượt**, **dữ liệu cá nhân**.

**Không thuộc kế hoạch này:** độ chính xác của mô hình chấm (RMSE, QWK…). Phần đó là thực nghiệm, ở chương thực nghiệm của luận văn. Test ở đây chỉ kiểm mô hình được nạp đúng, chấm đúng công thức và dự phòng đúng.

## 2. Phạm vi

| Trong phạm vi | Ngoài phạm vi |
| --- | --- |
| Toàn bộ mã `src/aicefr/` (ba dịch vụ core, speech, web), giao diện `api/static/`, cấu hình triển khai | Độ chính xác CEFR trên người học thật (thực nghiệm riêng) |
| API `/api/v1` (156 thao tác, [ENDPOINTS.md](../sdd/api/ENDPOINTS.md)), 35 trang HTML | Kiểm thử tải quy mô lớn |
| Luồng chính: đăng ký → vào lớp → nộp bài → chấm → báo cáo → giảng viên duyệt → luyện tập | Thử thâm nhập bởi bên thứ ba |
| Thanh toán payOS ở mức hợp đồng (chữ ký webhook, đối soát, cộng lượt một lần) | Giao dịch tiền thật trong CI |

## 3. Các tầng kiểm thử

Marker khai ở `pyproject.toml`. Số test đếm bằng `pytest --co` ngày 28/11/2026, tổng **1.901**.

| Tầng | Marker | Số test | Chạy gì | Ở đâu |
| --- | --- | --- | --- | --- |
| 1. Unit | `unit` | 428 | Logic thuần, không DB, không HTTP, không audio | Job `Dinh dang, lint, kiem thu` |
| 2. Tích hợp | `integration` và test không gắn marker | 407 có marker + ~1.000 test API qua `TestClient` | Pipeline thật, MongoDB trong bộ nhớ, API qua `TestClient` | Job `Dinh dang, lint, kiem thu` |
| 3. Hạ tầng thật | (chạy lại tầng 2) | – | Bộ test trên MongoDB 7 và Redis 7 thật, SeaweedFS (S3) | Job `Kiem thu tren MongoDB va Redis` |
| 4. E2E trình duyệt | `e2e` | 61 | Playwright Chromium trên máy chủ uvicorn thật | Chạy trên máy (cần `.[e2e]`); CI bỏ qua khi thiếu trình duyệt |
| 5. Đóng gói | – | – | Dựng ảnh Docker, compose hợp lệ, Silero nạp được khi không có mạng, Trivy quét lỗ hổng | Job `Dung anh va kiem docker compose` |
| 6. Tĩnh và bảo mật | – | – | ruff, ESLint, gitleaks, CodeQL, chặn tệp cấm, link Markdown | Các job còn lại của CI |
| 7. Khói (smoke) có mô hình thật | `slow` | – | Whisper, Silero, mô hình ghép trên audio thật | Chỉ chạy trên máy, không trong CI |

## 4. Môi trường

| Môi trường | Dùng cho |
| --- | --- |
| Máy cá nhân, `./demo.sh` (Docker cho MongoDB) | Phát triển, E2E, smoke có mô hình |
| GitHub Actions, Ubuntu, Python 3.12, Node 22 | CI mỗi PR và mỗi lần đẩy lên `main` |
| Production https://speakup.fit (EC2 2 vCPU, 8 GB) | Chỉ kiểm khói sau deploy (`/healthz`) và đo uptime (`.github/workflows/uptime.yml`) |

Dữ liệu kiểm thử là fixture do nhóm tạo, giọng tổng hợp (TTS), không dùng giọng người học thật.

## 5. Tiêu chí vào và ra

**Vào (bắt đầu kiểm một PR):** PR có mô tả, nhánh tạo từ `main` mới, có test cho thay đổi. Với sửa lỗi: có test tái hiện lỗi chạy đỏ trước khi sửa.

**Ra (được merge):**
- Mọi job CI xanh: lint, định dạng, ESLint, toàn bộ test, MongoDB/Redis, Docker, gitleaks, CodeQL.
- Độ phủ ≥ 70 % (CI chặn). Hiện tại **91,07 %**.
- Không còn defect mức Cao đang mở trong phạm vi PR.

## 6. Kết quả gần nhất

| Lần chạy | Kết quả |
| --- | --- |
| CI `main` `2dfa4fc`, 26/11/2026 ([run 45749465088](https://github.com/ThanhSangLouis/ai-assessor-cefr/actions/runs/45749465088)) | 1.802 passed, 49 skipped (E2E thiếu trình duyệt); trên MongoDB/Redis: 1.814 passed, 37 skipped; độ phủ 91,07 %; ruff sạch; gitleaks không phát hiện |
| Báo cáo độ phủ | Artifact `bao-cao-do-phu` (`coverage.xml`) của run trên |
| ESLint, 28/11/2026 | 0 lỗi, 0 cảnh báo trên 41 tệp ([trước khi sửa: 5 lỗi, 3 cảnh báo](../evidence/tc2-4-code-quality/reports/eslint-before-2026-11-28.txt)) |

## 7. Kế hoạch con theo tính năng

Mỗi tệp liệt kê rủi ro, test case có mã (ví dụ `TC-SR-I03`), tầng và tên hàm test. Ca lỗi được đặt cùng ca đúng.

| Tệp | Tính năng |
| --- | --- |
| [TEST_PLAN_D023](TEST_PLAN_D023.md) | Chế độ luyện tập |
| [TEST_PLAN_D025](TEST_PLAN_D025.md) | Lộ trình bài học do giáo viên soạn |
| [TEST_PLAN_D028](TEST_PLAN_D028.md) | Hoàn thiện sản phẩm |
| [TEST_PLAN_D029](TEST_PLAN_D029.md) | Hồ sơ cá nhân, đăng nhập Google, quản lý tài khoản |
| [TEST_PLAN_D031](TEST_PLAN_D031.md) | Phông Roboto, logo, chiều sâu và chuyển động |
| [TEST_PLAN_D032](TEST_PLAN_D032.md) | Thành tựu và nhịp luyện |
| [TEST_PLAN_D034](TEST_PLAN_D034.md) | Gói dịch vụ và thanh toán |
| [TEST_PLAN_D035](TEST_PLAN_D035.md) | Nhiều cổng thanh toán (Stripe, MoMo; đã gỡ ở D097) |
| [TEST_PLAN_D036](TEST_PLAN_D036.md) | Luồng đăng nhập Google không giả được |
| [TEST_PLAN_D037](TEST_PLAN_D037.md) | Ảnh nền vẽ bằng mã |
| [TEST_PLAN_D039_D042](TEST_PLAN_D039_D042.md) | Bằng chứng học tập |
| [TEST_PLAN_D043](TEST_PLAN_D043.md) | Ba dịch vụ (D043, D044) |
| [TEST_PLAN_D045_D047](TEST_PLAN_D045_D047.md) | Lược đồ có phiên bản, lộ trình ghép, triển khai |
| [TEST_PLAN_D049](TEST_PLAN_D049.md) | Tính lượt trên kênh NetID |
| [TEST_PLAN_D065](TEST_PLAN_D065.md) | Tự đăng ký, quên mật khẩu |
| [TEST_PLAN_D075](TEST_PLAN_D075.md) | Trả theo lượt; giảng viên soạn bài bằng AI |
| [TEST_PLAN_D086](TEST_PLAN_D086.md) | Thông báo trực tiếp (SSE) |
| [TEST_PLAN_D088](TEST_PLAN_D088.md) | Cài như ứng dụng (PWA), thông báo đẩy |
| [TEST_PLAN_D089](TEST_PLAN_D089.md) | Luyện lại từ máy nghe chưa rõ |
| [TEST_PLAN_D090](TEST_PLAN_D090.md) | Đoạn đọc quanh từ đang luyện |
| [TEST_PLAN_D094](TEST_PLAN_D094.md) | Tính lượt cho bản ghi trong lộ trình |
| [TEST_PLAN_D095](TEST_PLAN_D095.md) | Bán gói lượt qua payOS |
| [TEST_PLAN_D096](TEST_PLAN_D096.md) | Email cho luồng thanh toán |
| [TEST_PLAN_D098](TEST_PLAN_D098.md) | Vòng đời đơn gói lượt (mẫu State) |
| [TEST_PLAN_D099](TEST_PLAN_D099.md) | Lưới an toàn khi bán lượt bằng tiền thật |
| [TEST_PLAN_D101](TEST_PLAN_D101.md) | Lượt miễn phí cần email đã xác minh; sinh viên tự xoá tài khoản |
| [TEST_PLAN_UI](TEST_PLAN_UI.md) | Làm lại giao diện (D024) |

## 8. Rủi ro của chính việc kiểm thử

| Rủi ro | Cách giảm |
| --- | --- |
| E2E bị bỏ qua trên CI vì runner không cài trình duyệt | Chạy E2E trên máy trước khi merge thay đổi giao diện; số skip luôn ghi trong kết quả |
| Test dùng MongoDB trong bộ nhớ khác MongoDB thật | Job riêng chạy lại trên MongoDB 7 và Redis 7 thật |
| Test xanh nhưng mô hình chấm sai | Mô hình kiểm ở tầng smoke và thực nghiệm; test chỉ khẳng định nạp đúng artifact (kiểm SHA-256) và dự phòng đúng |
| Fixture không giống người học thật | Ghi rõ fixture là dữ liệu tạo; độ chính xác chỉ báo từ thực nghiệm |
