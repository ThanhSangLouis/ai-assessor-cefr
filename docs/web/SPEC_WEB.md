# Đặc tả và kế hoạch xây dựng giao diện web

Phạm vi: tầng trình bày. Tài liệu chốt **làm gì, không làm gì, theo thứ tự nào**
trước khi viết dòng mã đầu tiên.

Nguồn chuẩn: `docs/srs/SRS.md`. Khi SRS và SDD mâu thuẫn, **SRS thắng** — SDD tự
ghi ở dòng 15 rằng nó viết trước SRS nên mã UC và ngưỡng có thể lệch.

| Phiên bản | Ngày | Nội dung | Đi cùng |
| --- | --- | --- | --- |
| 1.0 | 13/09/2026 | Đợt 0–4: xác thực, nộp bài, báo cáo, duyệt, quản trị | SRS 1.0 |
| 1.1 | 14/09/2026 | Đợt 5–6: tiến độ, thống kê lớp, in PDF, rà tiếp cận | SRS 1.2 |
| 1.2 | 07/10/2026 | Đợt 7–11: luyện tập, lộ trình bài học (D023, D025), giao diện học thuật và thanh điều khiển (D026, D027), tài khoản và thang band (D028), hồ sơ và đăng nhập Google (D029), chấm mù kép (D030) | SRS 1.3 |
| 1.3 | 07/10/2026 | Đợt 12: phông Roboto tự phục vụ, logo mới, chiều sâu và chuyển động trên mọi trang, trang giới thiệu 3D (D031); thêm W-NFR-3 | SRS 1.3 |
| 1.4 | 07/10/2026 | Đợt 13: thành tựu, kỷ lục chuỗi, ngày nghỉ được tính, so với tuần trước (D032); M8 có mục Thành tựu | SRS 1.5 |
| 1.5 | 07/10/2026 | Đợt 14: gói dịch vụ của trường, bảng so sánh, mua qua cổng thanh toán, trang cổng thử, trang kết quả, biên nhận (D034) | SRS 1.6 |
| 1.6 | 07/10/2026 | Đợt 15: chọn cổng thanh toán (Stripe, MoMo, VNPay, cổng thử), trang kết quả cho người rời trang cổng và cho kết quả chưa xác nhận được (D035); khung "Đăng nhập bằng Google" ở tab Cấu hình (D036) | SRS 1.7 |
| **1.7** | **07/10/2026** | Đợt 16: ảnh nền vẽ bằng mã — "bậc thang tiếng nói" sau mọi trang, cảnh đồi có chuyển động ở trang giới thiệu và trang đăng nhập (D037); thêm W-NFR-4 | SRS 1.7 |

---

## 1. Sáu mâu thuẫn — ĐÃ CHỐT ngày 13/09/2026

Đây là phần quan trọng nhất của tài liệu. Mỗi mâu thuẫn dưới đây, nếu code trước
rồi mới phát hiện, sẽ phải làm lại.

| Mã | Chốt là | Ghi ở |
| --- | --- | --- |
| X-1 | Giữ FastAPI + Jinja2, sửa SRS | QD-05 |
| X-2 | **Có làm** ghi âm trên trình duyệt, thêm FR-39 vào SRS | QD-06 |
| X-3 | Theo SRS: 20–300 giây, thêm vùng REVIEW 20–29 | QD-08, commit `5488887` |
| X-4 | Theo SRS: giữ enum 5 tiêu chí, báo cáo luôn có dòng Interaction | QD-08 |
| X-5 | Cookie phiên có chữ ký, không JWT | QD-07 |
| X-6 | Sửa ma trận truy vết theo cấu trúc mã thật | QD-05 |

### X-1 — Nền tảng giao diện: Streamlit hay FastAPI?

| Nguồn | Nói gì |
| --- | --- |
| SRS C-03 (dòng 187) | "Giao diện web: **Streamlit** (1 app, 4 trang). Không viết mobile native, không SPA phức tạp." |
| SRS §8 (dòng 1024) | "Giao diện là ứng dụng **Streamlit** một trang chủ với điều hướng theo vai trò." |
| SDD §2 (dòng 74) | "Web UI dạng **SPA**" |
| Mã nguồn hiện tại | **FastAPI + HTML nội tuyến**, đã chạy được |

Ba tài liệu, ba câu trả lời khác nhau, và mã nguồn là câu thứ tư.

**Khuyến nghị: giữ FastAPI + Jinja2, sửa SRS C-03 và §8.** Lý do: đã có 11
endpoint FastAPI chạy được và 74 test bám vào đó. Streamlit không tách được
tầng API khỏi tầng hiển thị, nên sẽ phải dựng song song hai thứ hoặc vứt bỏ phần
đã làm. Đổi một dòng ràng buộc trong SRS rẻ hơn nhiều so với viết lại.

**Phải làm kèm:** ghi quyết định này vào `docs/plan/QUYET_DINH.md` thành QĐ-05 và
sửa SRS, cùng một commit. Để SRS nói Streamlit mà sản phẩm là FastAPI chính là
dạng mâu thuẫn tài liệu mà rubric phạt.

### X-2 — Ghi âm trực tiếp trên trình duyệt: có hay không?

| Nguồn | Nói gì |
| --- | --- |
| SRS §8.8 (dòng 1091) | "Hệ thống **không điều khiển thiết bị thu**; chỉ nhận file do trình duyệt tải lên" |
| SDD | Có UC03 "Ghi âm và nộp bài nói", nhưng **không đặc tả gì thêm** — không nêu MediaRecorder, không nêu quyền micro, không có tiêu chí chấp nhận |

**Đã chốt: CÓ làm** (QD-06), ngược với khuyến nghị ban đầu của tài liệu này.
Ba khó khăn dưới đây vì vậy trở thành việc phải xử lý, không còn là lý do để bỏ:

1. `MediaRecorder` cho ra WebM/Opus trên Chrome/Firefox, MP4/AAC trên Safari.
   `soundfile` **không đọc được** hai định dạng này, nên phải thêm `ffmpeg` vào
   chuỗi triển khai.
2. Chất lượng bản ghi từ micro laptop trong phòng ồn sẽ bị QC từ chối, đẩy tỷ lệ
   REJECTED lên cao và làm hỏng số liệu kiểm định.
3. Không có tiêu chí chấp nhận nào để kiểm thử.

Vì đã chốt làm, đây là **tính năng mới có FR riêng là FR-39 trong SRS**, kèm tiêu
chí chấp nhận đầy đủ. Ràng buộc bắt buộc: khi máy chủ không có `ffmpeg` thì giao
diện **ẩn nút ghi âm ngay từ đầu**, không để người dùng nói xong mới báo lỗi.
Máy phát triển hiện tại chưa cài `ffmpeg`, nên đường lùi này sẽ được kiểm thử thật
chứ không phải nhánh mã chết.

### X-3 — Ngưỡng thời lượng: ba con số khác nhau

| Nguồn | REJECT | REVIEW | PASS |
| --- | --- | --- | --- |
| SRS dòng 291 | < 20 s hoặc > 300 s | 20–29 s | 30–300 s |
| SDD §4.2 | > 300 s | < 15 s | — |
| Mã nguồn `audio_qc.py` | `MIN_DURATION_S = 15.0` | không có vùng REVIEW | — |

Mã nguồn hiện **nhận bài 16 giây và cho đi thẳng tới chấm điểm**, trong khi SRS
nói bài đó phải bị từ chối.

**Khuyến nghị: theo SRS.** Sửa `audio_qc.py` thành `MIN_DURATION_S = 20.0`, thêm
vùng REVIEW 20–29 giây. Đây là sửa ở tầng QC chứ không phải tầng web, nhưng phải
làm trước vì giao diện phải hiển thị đúng chuỗi "≤ 25 MB, 20–300 giây".

> **Cập nhật 14/09/2026 — hoá ra ba con số vẫn chưa đủ.** Bảng trên chỉ nói về
> QC, và QC chưa bao giờ là chỗ thật sự chặn. Chỗ chặn thật là **mô hình chấm**:
> `ridge_resp_v2` khớp trên bài 26,7–60,7 giây và từ chối mọi bài quá ~77,8 giây.
> Hệ quả đo được trên dữ liệu thật: một bản ghi 94 giây **qua được QC** rồi nhận
> một báo cáo đầy đủ mà nội dung duy nhất là "không chấm được vì bài dài 94
> giây". Nói lâu hơn lại nhận được ít hơn nói ngắn.
>
> Ngưỡng đã chốt sau khi rà (bản dựng đã duyệt ngày 13/09/2026):
>
> | Ngưỡng | Trước | Nay | Vì sao |
> | --- | --- | --- | --- |
> | Tối thiểu để chấm | 20 s | 20 s — giữ nguyên | Dưới mức này số đo ngừng nghỉ không ổn định |
> | Khuyến nghị mỗi đề | 40–60 s | 40–60 s (đề ngắn) **và 120–300 s (đề dài)** | Hai loại đề, không phải một |
> | Trần ghi âm và tải lên | 300 s ở QC nhưng bộ ghi âm dừng ở 60 s | 300 s cho cả hai | Chỗ chặn thật nằm ở bộ ghi âm và ở khả năng chấm |
> | Cửa sổ phân tích | — | 30–60 s, đích 45 s | Mỗi cửa sổ nằm trong dải mô hình biết |
> | Đuôi ngắn | — | < 20 s thì gộp vào cửa sổ trước | Tránh chấm một mẩu 6 giây rồi kéo trung vị đi |
> | Số cửa sổ tối đa | — | 10 | 300 ÷ 30; quá số này bài không còn là một bài nói cho một đề |
>
> Cơ chế và lý lẽ đầy đủ: `docs/sdd/SDD.md` mục 4.5a. Điều bắt buộc nói ra trên
> giao diện: điểm của bài dài là **điểm tạm chưa kiểm định** và luôn qua giảng viên.

### X-4 — Interaction: bỏ hẳn hay hiển thị "chưa đủ bằng chứng"?

| Nguồn | Nói gì |
| --- | --- |
| SRS FR-23 + US-21 | Mục Interaction **phải hiển thị** "Chưa đủ bằng chứng", giá trị `null` + `insufficient_evidence`. Mục đích: chứng minh hệ thống không tự ý chấm |
| QĐ-04 | "Chỉ làm 5 tiêu chí, đã bỏ hẳn Interaction" |
| Mã nguồn | `Criterion` enum có đúng 5 giá trị; có test khẳng định `"interaction" not in Criterion` |

Hai cách hiểu khác nhau về chữ "bỏ". SRS hiểu là **không chấm nhưng vẫn nói rõ
với người dùng vì sao không chấm**. QĐ-04 và mã hiểu là **không tồn tại**.

**Khuyến nghị: theo SRS.** Giữ enum 5 giá trị ở tầng nghiệp vụ, nhưng **tầng
hiển thị luôn có dòng Interaction** với nhãn "Chưa đủ bằng chứng — hệ thống không
chấm tiêu chí này". Đây là dòng tĩnh trong template, không phải dữ liệu từ mô hình.

Lý do nghiêng về SRS: im lặng bỏ một trong sáu tiêu chí CEFR khiến người đọc báo
cáo tưởng hệ thống đã đánh giá đủ. Nói rõ ra là trung thực hơn, và US-21 cho thấy
đây là điều giảng viên muốn thấy.

### X-5 — Phiên đăng nhập: JWT hay cookie?

SRS NFR-07 nói **JWT hết hạn ≤ 8 giờ**, khóa tài khoản 15 phút sau 5 lần sai,
lần thứ 6 trả HTTP 429.

**Đã chốt: cookie phiên có chữ ký, không JWT** (QD-07). Lý do: JWT không thu hồi được
trước hạn — đăng xuất chỉ là xoá phía client, token vẫn hợp lệ tới khi hết hạn.
Với hệ thống có vai trò giảng viên sửa được điểm, không thu hồi được phiên là
điểm yếu thật. Cookie tra bảng `session` thì xoá là mất hiệu lực ngay.

Các ràng buộc còn lại của NFR-07 **giữ nguyên**: hết hạn 8 giờ, khóa 15 phút sau
5 lần sai, 429 ở lần thứ 6. Chỉ đổi cơ chế mang phiên, không nới lỏng bảo mật.

Cần sửa NFR-07 trong SRS từ "JWT" thành "phiên có chữ ký phía máy chủ".

### X-6 — Ma trận truy vết SRS trỏ tới file không tồn tại

SRS dòng 1173 trỏ FR-01 tới `src/aicefr/api/routes_sessions.py`. File này **không
có**. Cấu trúc mã thực tế là `api/main.py` + `api/schemas.py`.

**Khuyến nghị:** cập nhật cột đường dẫn của ma trận truy vết theo cấu trúc thật.
Rubric chấm khả năng truy vết; ma trận trỏ vào hư không thì mất điểm ở đúng chỗ
nó được thiết kế để lấy điểm.

---

## 2. Hiện trạng

| Thành phần | Tình trạng |
| --- | --- |
| `api/main.py` | 11 endpoint, 3 nhóm vai trò |
| `api/web.py` | 3 màn hình, HTML nội tuyến trong chuỗi Python, 206 dòng |
| `pipeline.py` | QC → ASR → VAD → 19 đặc trưng → chấm → bằng chứng → định tuyến |
| `storage/repository.py` | SQLite 3 bảng, audit log bắt buộc lý do |
| Kiểm thử | 74 test, độ phủ 83% |

Chưa có: xác thực, phát lại audio, xử lý bất đồng bộ, khóa bài khi duyệt, quản lý
đề bài, xuất hồ sơ, chính sách lưu trữ.

---

## 3. Khoảng trống nghiêm trọng

### G-1 — Không có xác thực, ai cũng duyệt được bài

`/review` và `POST /api/v1/review/{id}` mở công khai. Bất kỳ ai biết đường dẫn đều
sửa được điểm và đặt `teacher_verified = true`.

Lỗi này phá vỡ chính luận điểm của đề tài: "máy chấm sơ bộ, giảng viên quyết định
cuối". Nếu ai cũng đóng vai giảng viên thì `teacher_verified` vô nghĩa và audit
log chỉ ghi lại một danh tính tự khai. SRS FR-32 đã yêu cầu phân quyền.

### G-2 — Xử lý đồng bộ ngay trong request

`POST /api/v1/responses` chạy cả pipeline rồi mới trả lời. SRS AC-05.1 yêu cầu trả
**HTTP 202 kèm `job_id` và `status = "QUEUED"` trong dưới 300 ms**. Hiện tại
không đạt: NFR-01 cho phép pipeline chạy tới 60 giây, tức request treo 60 giây.

US-01 còn đòi trong **5 giây** sinh viên phải thấy "Đã nhận bài, đang xử lý".

### G-3 — Giảng viên không nghe được bài

SDD §6 yêu cầu `GET /review/{id}` trả `audio_url`. Không có endpoint nào phục vụ
audio. Toàn bộ bằng chứng có mốc thời gian trở nên vô dụng vì không tua tới được,
trong khi SRS FR-24 đòi bấm vào bằng chứng thì trình phát nhảy đúng mốc, sai số
≤ 0,5 giây.

### G-4 — Không có khóa bài khi duyệt

SRS FR-29 đòi hiển thị "Đang được [tên] xem" và khóa 15 phút. Hai giảng viên mở
cùng một bài hiện sẽ ghi đè quyết định của nhau mà không ai biết.

### G-5 — HTML nội tuyến trong chuỗi Python

206 dòng HTML, CSS, JavaScript trong chuỗi Python, thoát ký tự bằng tay (`\\'`
trong `onclick`). Không lint được, không test được.

### G-6 — Thư mục `uploads/` không giới hạn

File audio ghi thẳng vào `uploads/`, không xoá, không giới hạn. FR-35 về xoá khi
rút đồng thuận chưa hiện thực. Đây là rủi ro pháp lý: dữ liệu giọng nói là dữ
liệu cá nhân theo Luật 91/2025/QH15 và Nghị định 356/2025/NĐ-CP.

---

## 4. Quyết định thiết kế

| Mã | Quyết định | Thay cho | Lý do ngắn |
| --- | --- | --- | --- |
| QĐ-W1 | FastAPI + Jinja2, render phía máy chủ | Streamlit, SPA | Xem X-1 |
| QĐ-W2 | Cookie phiên ký `HttpOnly`, `SameSite=Lax`, tra bảng `auth_sessions`; băm **bcrypt cost ≥ 12** theo NFR-07 | JWT | Xem X-5 |
| QĐ-W3 | `BackgroundTasks` của Starlette | Celery + Redis | 60–90 sinh viên một học kỳ là tải rất nhẹ; thêm Redis là thêm dịch vụ phải dựng và phải giải thích |
| QĐ-W4 | Thêm trạng thái `QUEUED`, `RUNNING` | — | SRS FR-05 đã liệt kê hai trạng thái này; `contracts.py` chưa có |
| QĐ-W5 | **Có** ghi âm trên trình duyệt, kèm đường lùi khi thiếu `ffmpeg` | — | Xem X-2, QD-06 |
| QĐ-W6 | `GET /{id}/audio` có kiểm quyền và hỗ trợ HTTP Range | — | Cần cho FR-24; không bao giờ lộ đường dẫn hệ thống tệp |
| QĐ-W7 | Truy cập bài của người khác trả **404**, không phải 403 | — | SRS FR-04 yêu cầu rõ. 403 xác nhận bài đó tồn tại, tức rò rỉ thông tin |

**Đánh đổi của QĐ-W3 phải ghi nhận:** tiến trình chết giữa chừng thì bài kẹt ở
`RUNNING`. Xử lý: khi khởi động, mọi bài `RUNNING` quá 10 phút bị đánh dấu
`FAILED` kèm mã lý do, chứ không im lặng bỏ qua. NFR-11 đòi tỷ lệ job kết thúc
xác định ≥ 98%.

---

## 5. Đặc tả màn hình

### M1 — Đăng nhập  ·  `/login`  · FR-32, NFR-07

Bút danh + mật khẩu. Thông báo lỗi **không phân biệt** sai tài khoản với sai mật
khẩu. Sau 5 lần sai: khóa 15 phút; lần thứ 6 trả HTTP 429 kèm thông báo bị khóa.
Điều hướng sau đăng nhập theo vai trò: sinh viên về `/practice`, giảng viên về
`/review`, quản trị về `/admin`; có `?next=` cùng trang thì về đó (D024). Phiên hết
hạn sau 8 giờ.

### M2 — Nộp bài  ·  `/`  · FR-01, FR-02

| Khối | Nội dung | Ràng buộc |
| --- | --- | --- |
| Chọn đề | Thẻ đề bài, thời lượng khuyến nghị 60–180 giây | SRS §8.2 |
| Vùng nộp | Kéo thả, ghi rõ "≤ 25 MB, 20–300 giây, định dạng wav/mp3/m4a/webm" | SRS dòng 1033 |
| Bút danh | Chặn chuỗi giống MSSV/email → 422 `IDENTIFIER_LOOKS_LIKE_PII` | FR-01 |
| Ghi âm | Bộ ghi dùng chung với M11: dừng thì **nghe lại rồi mới nộp** (Nộp / Ghi lại); file chọn sẵn đi qua cùng bước nghe lại | D024 |
| Sau khi gửi | Trong ≤ 5 giây hiện "Đã nhận bài, đang xử lý" + mã UUID, chuyển sang M3 | US-01 |

D024: bút danh lấy từ phiên đăng nhập, nên ô nhập bút danh trên trang này đã bỏ
(máy chủ vốn không đọc nó). Đề đang chọn hiện đầy đủ ngay trên nút ghi âm.

Không lưu tên file gốc vào CSDL và không ghi vào log (AC-02.4).

### M3 — Theo dõi xử lý  ·  `/progress/{id}`  · FR-05

Nhãn tiến trình: `Đang tải` → `Đang kiểm tra chất lượng` → `Đang nhận dạng` →
`Đang chấm` → `Xong`, kèm thanh tiến trình. Trang tự làm mới. Bám theo NFR-01:
bài 120 giây xử lý trong ≤ 60 giây ở P90, nên đặt hạn chờ 5 phút rồi báo rõ.

Bị từ chối thì hiện câu tiếng Việt nêu **chỉ số đo được + ngưỡng + cách khắc phục**,
kèm nút "Nộp lại". **Tuyệt đối không hiển thị band hay điểm khi trạng thái là
REJECT hoặc FAILED** (AC-09.2).

### M4 — Báo cáo kết quả  ·  `/report/{id}`  · FR-21..FR-28

| Khối | Ràng buộc bắt buộc |
| --- | --- |
| Band | Cỡ lớn + nhãn "ước lượng"; `band_status = "estimated"`; cấm mọi chuỗi mang nghĩa "chứng chỉ", "đạt/không đạt", "kết quả chính thức" (SRS §11.3) |
| Tuyên bố | Nguyên văn SRS §9.4, hardcode, không sinh động |
| Độ tin cậy | Thanh phần trăm + phân loại Cao ≥ 75%, Trung bình 60–74%, Thấp < 60% (FR-22) |
| Sáu tiêu chí | Năm tiêu chí có điểm; **Interaction luôn hiện "Chưa đủ bằng chứng", không có điểm** (FR-23, xem X-4) |
| Bằng chứng | Tối đa 6 mục; mỗi dòng có loại, mốc `mm:ss`, số đo, nút "Nghe đoạn này"; bấm → trình phát nhảy đúng mốc, sai số ≤ 0,5 giây (FR-24) |
| Nhận xét | Mỗi câu liên kết ≥ 1 bằng chứng; không có bằng chứng → "Chưa đủ bằng chứng để đưa nhận xét" (FR-25) |
| Ưu tiên cải thiện | Tối đa 2 mục; nếu độ tin cậy < 0,50 → thay bằng "Kết quả cần giảng viên xác nhận trước khi đưa gợi ý luyện tập" (FR-26) |
| Bản chép | Từ có độ tin cậy < 0,50 tô nền xám + chú thích "Máy có thể nghe nhầm từ này" (FR-10, FR-16) |
| Chân trang | Đủ 7 trường provenance: `model_version`, `feature_version`, `asr_model`, `band_map_version`, `calibration_version`, `qc_config_version`, `scored_at` (FR-27) |
| Khi chờ duyệt | Nhãn "Chờ giảng viên xác nhận" + lý do **diễn đạt tiếng Việt**, không hiện mã kỹ thuật (FR-28) |
| Khi đã sửa | Hiện đồng thời `ai_band` và `final_band` + câu "Kết quả đã được giảng viên điều chỉnh" (AC-30.3) |

Trình phát audio có dấu mốc trên thanh thời gian: ngừng dài **cam**, cụm ngập
ngừng **tím**, từ tin cậy thấp **xám** (SRS §8.3).

D024 xếp lại thứ tự thành nhiều thẻ: kết quả và **bước tiếp** (nút mở nhiệm vụ
luyện cho khía cạnh nên luyện trước, ở band của bài) → nhận xét và ưu tiên →
bằng chứng cùng bản chép, trình phát ghim đầu thẻ → các khía cạnh (bảng chỉ báo
thu gọn) → chất lượng bản ghi và nguồn gốc (thu gọn; mở sẵn khi bài bị từ chối).
Lý do từ chối trích ngưỡng QC đang áp dụng, không chép số cứng vào mã.

### M5 — Hàng đợi duyệt  ·  `/review`  · FR-29

Sắp theo **độ tin cậy tăng dần** — bài máy ít chắc chắn nhất lên đầu. Lọc theo mã
lý do và band. Ở màn hình này **được phép hiện mã lý do kỹ thuật** vì người đọc là
giảng viên. Bài đang có người xem: nhãn "Đang được [tên] xem", nút lưu bị vô hiệu,
khóa 15 phút.

D024: bảng còn bốn cột (bài nộp, máy chấm, lý do gắn cờ, xử lý) và thành từng khối
trên điện thoại; nút **"Duyệt bài tiếp theo"** mở bài cũ nhất chưa ai giữ. Lý do
gắn cờ hiện bằng tên tiếng Việt dùng chung với M6, mã kỹ thuật nằm trong chú
thích khi rê chuột. Thực tế hàng đợi hiện sắp theo thời gian nộp, cũ nhất trước.

### M6 — Duyệt một bài  ·  `/review/{id}`  · FR-30, FR-31

Bố cục hai cột trong **một màn hình**, không cuộn qua lại: trái là trình phát +
bản chép đồng bộ; phải là điểm máy, bằng chứng, ô sửa.

SDD R-10 đặt mục tiêu thời gian duyệt trung bình **dưới 3 phút một bài**, nên cần
**phím tắt**: phát/dừng, tới bằng chứng kế, đồng ý, lưu.

- Nút "Đồng ý với kết quả AI": trong ≤ 2 giây bài rời hàng đợi và tự mở bài kế (US-15).
- Form sửa: chặn lưu khi thiếu lý do, báo "Cần ghi lý do (ít nhất 5 ký tự) cho mọi
  quyết định, kể cả khi đồng ý với máy". D024 thêm ba lý do soạn sẵn, bấm để chèn
  rồi sửa tiếp.
- D024: trình phát ghim dưới thanh đầu trang **cho cả trang**, không chỉ trong thẻ
  bản chép, để nghe tiếp khi đọc ô quyết định; trên điện thoại có nút "Tới phần
  quyết định". Phím cách không cướp nút đang được chọn.
- Tab "Lịch sử": audit theo thời gian, có giá trị trước, giá trị sau, mã lý do, người thực hiện (FR-31).

### M7 — Quản trị  ·  `/admin`  · FR-08, FR-34, FR-35, FR-36

Bốn tab:

- **Mô hình** (FR-36): danh sách phiên bản + chỉ số + nút kích hoạt; chặn kích hoạt khi thiếu file trọng số.
- **Cấu hình** (FR-08): sửa các ngưỡng QC trong khoảng cho phép; mỗi lần lưu tạo
  một phiên bản ngưỡng mới, ghi nhật ký kiểm toán. D024 nối form vào
  `POST /api/v1/admin/config` vốn đã có; trước đó màn hình ghi "chỉ đọc" và
  hiện `[object Object]` cho danh sách trường sửa được.
- **Yêu cầu dữ liệu** (FR-34, FR-35): ô nhập `participant_id`, nút "Xem trước", bảng liệt kê artifact, "Xác nhận xóa" + **nhập lại ID lần hai**. Thông báo hoàn tất phải nêu **mốc cutoff** của mô hình, không hứa xoá dữ liệu khỏi mô hình đã phát hành.
- **Vận hành**: tỷ lệ job kết thúc xác định ≥ 98% (NFR-11), tình trạng engine ASR, nhật ký audit.

---

### M8 — Tiến độ của tôi  ·  `/my-progress`  · FR-27

Thêm 14/09/2026. Khác M4 ở câu hỏi nó trả lời: M4 nói về **một bài**, màn này nói
về **một người theo thời gian**.

- Biểu đồ đường trên thang 0–6 **cố định** — co trục theo dữ liệu là cách dễ nhất
  để biến dao động 0,2 điểm thành một ngọn núi.
- Điểm giảng viên đã xác nhận và điểm máy ước lượng vẽ khác nhau (chấm đặc / chấm
  rỗng), kèm chú giải. Gộp chung sẽ khiến một con số chưa ai kiểm tra trông như
  một kết luận.
- Nhận định xu hướng chỉ xuất hiện từ **5 bài** trở lên, và nếu chênh lệch nhỏ
  hơn RMSE của chính mô hình thì ghi "chưa kết luận được" kèm lý do bằng số.
- Có nút in / lưu PDF và tải hồ sơ năng lực JSON.
- *Bản 1.4 (D032):* bên dưới có mục **Thành tựu** — 17 ô trong năm nhóm, ô đã đạt có huy hiệu đặc và ngày đạt,
  ô chưa đạt có thanh tiến độ, ô mới đạt mang nhãn "Mới" một lần. Vào thẳng bằng `/my-progress#achievements`.

### M9 — Thống kê lớp  ·  `/review/stats`  · FR-29

Thêm 14/09/2026. Dành cho giảng viên.

- Bốn ô số: bài đã nộp, bài máy chấm được, người nộp, bài đang chờ duyệt. Hai con
  số đầu tách nhau vì bài máy **không** chấm được vẫn là bài đã nộp — và là loại
  cần người nhất.
- Khối **"giảng viên và máy có đồng ý với nhau không"**: số lượt duyệt, số lần
  giữ nguyên band, số lần đổi, tỷ lệ. Dưới 70% thì cảnh báo thẳng rằng band của
  máy chưa đủ ổn định để dùng như một kết quả.
- Phân bố band và bảng theo đề, mỗi bảng kèm một câu nói rõ đọc nó thế nào là sai.
- **Không** có bảng xếp hạng sinh viên và **không** có bảng xếp hạng giảng viên:
  màn hình xếp hạng người thì sẽ được dùng để xếp hạng người.
- D023 thêm khối **"Luyện tập của lớp"**: số lần luyện, số người có luyện, tỷ lệ
  lần luyện hoàn thành mọi mục tiêu, và bảng theo tiêu chí. Không có dòng nào theo
  từng sinh viên. Các con số về máy chấm ở trên chỉ tính bài đánh giá.

### M10 — Luyện tập  ·  `/practice`  · FR-40, FR-42, FR-43

Thêm 06/10/2026 (D023). Trang chính của chế độ luyện tập, cho sinh viên.

- **Thẻ "Nên luyện tiếp"**: một nhiệm vụ, kèm câu giải thích vì sao chọn nó và bài
  đánh giá làm căn cứ (ngày, band, giảng viên đã xác nhận hay chưa). Luật chọn
  được viết ra ngay trên trang, mục "Hệ thống chọn nhiệm vụ gợi ý thế nào?".
- **Thẻ "Hôm nay"**: vòng mục tiêu ngày (mặc định 2 lần luyện), chuỗi ngày, bảy
  chấm của tuần. Chuỗi ngày cho nghỉ một ngày mỗi tuần mà không mất chuỗi.
- **Ôn lại**: nhiệm vụ lần gần nhất chưa hoàn thành, cũ nhất trước.
- **Lộ trình**: 5 tiêu chí × 3 band, mỗi ô một trạng thái bằng **hình và màu**
  (✓ đã hoàn thành, … đã thử, vòng rỗng chưa làm).
- **Không** có điểm, band hay bảng xếp hạng ở bất kỳ đâu trên trang.

### M11 — Một nhiệm vụ luyện  ·  `/practice/{task_id}`  · FR-40, FR-41

- Mục tiêu hiện **trước** khi nói, kèm thẻ từ của các mục tiêu dùng từ. Một mục
  tiêu chỉ nói ra sau khi nộp là một bài kiểm tra trá hình.
- Đề phát âm có đoạn văn mẫu để đọc to; mọi đề có mục "Mẹo".
- Ghi âm trực tiếp hoặc chọn file, cùng ràng buộc như M2 (đồng thuận, ffmpeg,
  ngữ cảnh bảo mật). Nộp xong trang tự chờ rồi chuyển sang M12.
- "Các lần đã thử": mười lần gần nhất, mỗi lần một kết luận ngắn.

### M12 — Kết quả một lần luyện  ·  `/practice/results/{id}`  · FR-41, FR-42, FR-43

- Thứ tự theo câu hỏi người học đặt ra: xong chưa (dải kết luận) → nên sửa gì
  trước (**một** lời khuyên chính, từ mục tiêu chưa hoàn thành đầu tiên) → máy
  dựa vào đâu (từng mục tiêu, số đo, chỗ trong bản ghi) → làm gì tiếp.
- Mỗi chỗ làm căn cứ có mốc thời gian là một nút: bấm là nghe lại đúng giây đó.
- Mỗi mục tiêu ghi số đo **lần trước cùng đề** để tự so; không so với ai khác.
- "Chưa đo được" (kèm lý do) tách hẳn khỏi "chưa hoàn thành".
- Câu lưu ý cố định: máy đếm trên bản chép tự động; mục tiêu ngữ pháp chỉ xem có
  dùng cấu trúc hay không, không chấm đúng sai.
- Bài bị từ chối (QC, không phải tiếng Anh) nói lý do và mời thử lại; không tính
  vào mục tiêu ngày.

---

## 6. Thay đổi API

### Thêm mới

| Phương thức | Đường dẫn | FR |
| --- | --- | --- |
| POST | `/api/v1/auth/login` | FR-32 |
| POST | `/api/v1/auth/logout` | FR-32 |
| GET | `/api/v1/me` | FR-32 |
| GET | `/api/v1/responses/{id}/status` | FR-05 |
| GET | `/api/v1/responses/{id}/audio` | FR-24, SDD §6 |
| GET | `/api/v1/tasks` | FR-01 |
| GET | `/api/v1/me/responses` | FR-04 |
| POST | `/api/v1/review/{id}/lock` | FR-29 |
| GET | `/api/v1/responses/{id}/history` | FR-31 |
| GET | `/api/v1/me/profile.json` | FR-38 |
| POST | `/api/v1/admin/erase` | FR-35 |
| GET | `/api/v1/admin/models` | FR-36 |
| GET | `/api/v1/practice` | FR-42, FR-43 (D023) |
| GET | `/api/v1/practice/tasks/{task_id}` | FR-40 (D023) |
| GET | `/api/v1/practice/attempts/{id}` | FR-41, FR-43 (D023); chỉ chủ bài, bài khác hoặc bài đánh giá trả 404 |
| GET | `/api/v1/me/achievements` | FR-65 (D032); chỉ của chính người gọi, lưu luôn những thành tựu vừa đạt |
| POST | `/api/v1/me/achievements/seen` | FR-65 (D032); thân `{"codes": [...]}` hoặc rỗng là mọi thành tựu mới |
| GET | `/api/v1/plan` | FR-67 (D034); giảng viên và quản trị viên |
| GET, POST, PATCH | `/api/v1/admin/billing`, `/quote`, `/orders`, `/license`, `/organization` | FR-67..FR-70 (D034); quản trị viên |
| GET | `/api/v1/billing/notify/{gateway}` | FR-69 (D034); máy chủ của cổng gọi, chữ ký là thứ xác thực |
| GET | `/api/v1/me/pronunciation` | FR-75 (D039); sinh viên, 400 lượt gần nhất của chính mình |
| GET | `/api/v1/teach/pronunciation` | FR-76 (D039); giảng viên và quản trị viên, bản gộp không chỉ ra ai |
| GET, POST | `/api/v1/admin/studies`, `/{id}/status`, `/{id}/report`, `/{id}/export.csv` | FR-77, FR-78 (D040); quản trị viên |
| GET, POST | `/api/v1/me/study`, `/survey`, `/withdraw` | FR-77, FR-78 (D040); sinh viên |
| GET | `/api/v1/review/kpi` | FR-79 (D041); giảng viên và quản trị viên, theo gói như thống kê lớp |
| GET, POST | `/api/v1/admin/measurement-error` | FR-80 (D042); quản trị viên |

### Đổi hành vi

`POST /api/v1/responses` trả **202** với `status = "QUEUED"` trong dưới 300 ms
thay vì chạy xong mới trả. **Đây là thay đổi phá vỡ tương thích** — test hiện có
sẽ hỏng và phải sửa theo, không được nới lỏng test để nó xanh.

### Bảng dữ liệu thêm mới

- `account(id, pseudonym, password_hash, salt, role, failed_attempts, locked_until, created_at, disabled)`
- `auth_sessions(token_hash, account_id, expires_at, created_at)` — tên tránh trùng bảng `sessions` (phiên đánh giá) đã có trong SRS mục 7.1
- `task(id, title, prompt_text, prompt_version, part, active)`
- `review_lock(response_id, reviewer_id, locked_until)`

Bảng `response` thêm `account_id`.

D032: bảng `achievement(account_id, code, unlocked_at, seen_at)`, khoá chính
`(account_id, code)`; `GET /api/v1/learn` trả thêm `today.best_streak`, `today.rest_days`,
`today.week_seconds`, `today.last_week_seconds` và khối `achievements`; hai API lượt luyện
trả thêm `achievements` (những thành tựu lượt đó vừa đạt).

D039–D042: nhãn từ của bài học thêm `pattern`; bảng `review_session(id, response_id,
reviewer_id, opened_at, decided_at, action)`; ba bảng của thực nghiệm `study`,
`study_participant`, `study_survey`; khoá cấu hình `measurement_error`.
`GET /api/v1/responses/{id}` trả `feedback_withheld: true` và danh sách phản hồi rỗng cho
người học nhóm "Chỉ điểm" khi thực nghiệm đang chạy; `GET /api/v1/me/progress` trả thêm
khối `reliable_change`.

D023: bảng `task` thêm `topic_keywords` (D022), `purpose`, `criterion`, `band`,
`missions_json`, `tips_json`, `reference_text`; bảng `response` thêm `purpose`
(mặc định `assessment`). `GET /api/v1/tasks` vẫn chỉ trả đề đánh giá;
`/api/v1/responses/{id}/status` và `/api/v1/me/responses` trả thêm `purpose`.

---

## 7. Yêu cầu phi chức năng ràng buộc giao diện

| Mã | Yêu cầu | Nguồn | Cách đo |
| --- | --- | --- | --- |
| NFR-02 | Endpoint đồng bộ ≤ 300 ms ở P95 với CSDL 1.000 bản ghi | SRS | locust, 20 người ảo, 5 phút |
| AC-05.1 | Nhận bài trả 202 trong dưới 300 ms | SRS | test hợp đồng |
| US-01 | Sinh viên thấy "đã nhận" trong ≤ 5 giây | SRS | test luồng |
| NFR-15 | Chrome ≥ 120, Edge ≥ 120, Firefox ≥ 121; đọc được ở 1366×768 | SRS | danh mục 12 thao tác, `tests/manual/browser_matrix.md` |
| NFR-07 | Phiên ≤ 8 giờ; khóa 15 phút sau 5 lần sai; 429 ở lần thứ 6 | SRS | test |
| NFR-09 | Không dòng log nào chứa email, chuỗi 7–10 chữ số, hoặc ≥ 5 từ liên tiếp của bản chép | SRS | test quét log |
| NFR-11 | Tỷ lệ job kết thúc xác định ≥ 98%, hiện trên màn hình quản trị | SRS | thống kê |
| W-NFR-1 | Toàn bộ văn bản hướng tới người dùng bằng tiếng Việt có dấu | SRS TC-23 | test |
| W-NFR-2 | Không nhúng tài nguyên từ CDN bên ngoài | **mới** | kiểm mã nguồn |
| W-NFR-3 | Chuyển động và hình 3D là trang trí: tắt hết khi người dùng chọn giảm chuyển động, không thông tin nào chỉ nằm trong chúng, và chúng ẩn với trình đọc màn hình | **mới** (D031) | `tests/test_ui_depth.py`, `tests/e2e/test_ui_depth_e2e.py` |
| W-NFR-4 | Ảnh nền là trang trí và không cản việc đọc: không chữ nào đứng trên ảnh bị kéo xuống dưới mức tương phản AA (4,5:1; chữ lớn 3:1) — chỗ nào chưa đạt khi không có ảnh thì ảnh không làm tệ hơn; ảnh không nhận cú bấm hay chạm, không làm trang cuộn ngang, không in ra giấy và ẩn với trình đọc màn hình | **mới** (D037) | `tests/test_art.py`, `tests/e2e/test_art_e2e.py` (đo trên điểm ảnh) |

W-NFR-2 là bổ sung, không có trong SRS. Lý do: phòng máy trong trường có thể chặn
mạng ngoài; demo trước hội đồng mà font hoặc script không tải được thì hỏng buổi.

**Khoảng trống có ý thức:** SRS không có yêu cầu nào về khả năng truy cập
(WCAG, điều hướng bàn phím, trình đọc màn hình) ngoài "phím tắt duyệt nhanh" ở
SDD R-10. Không tự thêm vào phạm vi; ghi nhận ở đây để trả lời được nếu bị hỏi.

---

## 8. Kế hoạch thực hiện

Bốn đợt. Mỗi đợt tự nó chạy được và demo được.

### Đợt 0 — Chốt mâu thuẫn

1. ~~Quyết định X-1 tới X-6~~ — xong, bảng ở mục 1.
2. ~~Áp đúng bộ ngưỡng QC của SRS, `QcResult` ba mức~~ — xong, commit `5488887`.
3. ~~Ghi QD-05 tới QD-08 vào `QUYET_DINH.md`~~ — xong.
4. Sửa SRS: C-03, mục 8, mục 8.8, NFR-07, thêm FR-39, sửa ma trận truy vết.
5. Thêm `ffmpeg` vào hướng dẫn cài đặt trong README.

Bước 2 chạm tầng QC chứ không phải tầng web, nhưng phải làm trước vì giao diện
hiển thị ngưỡng và test hợp đồng bám vào đó.

### Đợt 1 — Nền tảng, không đổi hành vi

4. Chuyển HTML từ chuỗi Python sang template Jinja2 + CSS tĩnh. Giao diện giữ
   nguyên, chỉ đổi cách tổ chức. Test hiện có phải xanh y nguyên.
5. Khai báo `jinja2` trong `pyproject.toml`. Bài học từ lỗi L2 trong
   `docs/ai-usage-log.md`: gói nào mã cần thì phải khai báo, chạy được trên máy
   mình không phải bằng chứng.

### Đợt 2 — Xác thực và phân quyền — **xong**

6. ~~Bảng `account`, `auth_sessions`; băm bcrypt cost ≥ 12; lệnh CLI tạo tài khoản~~
7. ~~Dependency `require_role(...)` gắn vào mọi endpoint giảng viên và quản trị~~
8. ~~Màn hình M1, kèm khóa tài khoản và 429~~
9. ~~Ghi `account_id` thật vào audit log thay cho danh tính tự khai~~
10. ~~Test: 403 cho vai trò sai, 404 cho bài người khác~~

Ghi chú thực hiện: trường `reviewer_id` đã bị **bỏ khỏi** `ReviewDecision`.
Danh tính người duyệt lấy từ phiên đăng nhập. Trước đó client tự khai trường
này, nên audit log chỉ ghi lại một chuỗi bất kỳ và không chứng minh được ai đã
sửa điểm — tức `teacher_verified` không có giá trị chứng cứ.

Các trang HTML **không** bị chặn bằng phụ thuộc vai trò mà để JavaScript xử lý
401/403 rồi chuyển hướng. Lý do: trả 401 thô cho một trang HTML thì người dùng
chỉ thấy một dòng JSON, không biết phải làm gì.

### Đợt 3 — Bất đồng bộ, phát audio, duyệt bài — **xong**

11. ~~Thêm `QUEUED`, `RUNNING`~~
12. ~~Chạy pipeline trong `BackgroundTasks`; dọn bài kẹt khi khởi động~~
13. ~~`GET /{id}/status` + màn hình M3~~
14. ~~`GET /{id}/audio` có Range và kiểm quyền~~
15. ~~Màn hình M4: bằng chứng bấm được để tua, 7 trường nguồn gốc, dòng Interaction~~
16. ~~Màn hình M5, M6: khóa 15 phút, phím tắt, tab lịch sử~~

Ghi chú thực hiện:

- Hai trường `band_map_version` và `calibration_version` **chưa từng tồn tại**.
  Đã thêm vào hiện vật mô hình. Giá trị hiệu chuẩn ghi là `chua-hieu-chuan` vì
  mô hình thật sự chưa qua hiệu chuẩn xác suất — đặt một số phiên bản nghe cho
  đủ bộ sẽ là khai báo sai nguồn gốc, đúng thứ FR-27 sinh ra để chặn.
- Dòng **Tương tác** trong báo cáo là dòng tĩnh trong giao diện, không phải dữ
  liệu từ mô hình. Enum `Criterion` vẫn đúng 5 giá trị.
- Khóa duyệt tự hết hạn sau 15 phút và được nhả khi lưu xong hoặc khi rời trang,
  nên một lần mở nhầm không làm bài kẹt.

### Đợt 4 — Hoàn thiện — **xong**

17. ~~Bảng `task`, màn hình chọn đề~~ — ba đề P3, P4, P5 gieo sẵn, có phiên bản prompt
18. ~~Lịch sử bài của tôi (FR-04), xuất hồ sơ (FR-38)~~
19. ~~Màn hình quản trị M7 với bốn tab~~ — mô hình, cấu hình, dữ liệu cá nhân, vận hành
20. ~~Ghi âm trực tiếp trên trình duyệt (FR-39, QD-06)~~

Ghi chú thực hiện:

- Port `AudioDecoder` nay đã hiện thực, đóng luôn một khoảng trống SDD để ngỏ từ
  đầu. Ba adapter: `SoundFileDecoder`, `FfmpegDecoder`, và `FirstMatchDecoder` là
  composite chọn adapter đầu tiên nhận định dạng.
- Đã kiểm trên **WebM/Opus và MP4/AAC thật** do `ffmpeg` tạo ra, đúng hai định
  dạng `MediaRecorder` sinh trên Chrome/Firefox và Safari. Cả hai được hạ về
  16 kHz mono trước khi vào pipeline.
- Khi máy chủ thiếu `ffmpeg`: `/api/v1/health` trả `recording_enabled: false` và
  giao diện **ẩn nút ghi âm ngay lúc render**. Giao diện còn phân biệt ba lý do
  khác nhau — thiếu `ffmpeg`, trình duyệt không hỗ trợ `MediaRecorder`, và không
  phải kết nối bảo mật — vì mỗi lý do cần một cách xử lý khác nhau.
- Xoá dữ liệu cá nhân xoá **cả tệp audio trên đĩa**, không chỉ dòng dữ liệu. Để
  lại tệp thì lời khai báo đã xoá là sai sự thật.
- `aicefr.db` và `uploads/` đã gỡ khỏi git và đưa vào `.gitignore`. Chỉ cần chạy
  thật một lần là chúng chứa bút danh và bản ghi giọng nói.

### Đợt 5 — Làm lại giao diện cho thuận tiện (D024) — **xong**

Chủ dự án yêu cầu ngày 06/10/2026: "làm lại UI cho thuận lợi", phạm vi **toàn bộ
web**; sau khi dừng ghi âm thì **nghe lại rồi mới nộp**. Khảo sát trước khi làm
(chụp từng màn ở 1280 px và 375 px) cho thấy:

- Đầu trang hai tầng, mọi vai trò thấy mọi mục: giảng viên thấy "Nộp bài" và
  "Luyện tập" đứng trước hàng đợi; trên điện thoại 6–9 mục trượt ngang.
- Trang nộp bài: nút chính nằm ở thẻ thứ ba, dưới toàn bộ đề và vùng kéo thả; còn
  ô "Mã bút danh SV-001" mà máy chủ không đọc. Hai bộ ghi âm (nộp bài, luyện tập)
  là hai bản chép đã lệch nhau.
- Báo cáo dài khoảng bốn màn hình; "Khía cạnh nên luyện trước" là một dòng chữ
  không dẫn đi đâu, đứng sau hai bảng giải thích.
- Bài của tôi là bảng bảy cột; hàng đợi chín cột với nút "Duyệt" ở cột cuối, khuất
  khỏi màn hình; trang duyệt hiện mã thô (`REVIEW_REQUIRED`, `SCORE_NEAR_BOUNDARY`).
- Quản trị ghi nút kích hoạt "chưa hiện thực" và tab cấu hình "chỉ đọc", trong khi
  hai API đó đã chạy.

Tiêu chí chấp nhận:

| Mã | Tiêu chí |
| --- | --- |
| **UX-01** | Mỗi vai trò chỉ thấy mục điều hướng của mình, đúng một mục mang `aria-current`; đăng nhập không có `next` về trang chính của vai trò. Tài khoản, đồng thuận, giao diện sáng/tối và đăng xuất gom vào một menu |
| **UX-02** | Trên điện thoại, điều hướng sinh viên là thanh tab dưới đáy màn hình; không trang nào cuộn ngang ở 375 px |
| **UX-03** | Một bộ ghi âm cho M2 và M11; dừng thì hiện bước nghe lại với "Nộp" và "Ghi lại"; không gửi gì trước khi bấm Nộp; phím cách bật/tắt ghi âm nhưng không làm gì ở bước nghe lại |
| **UX-04** | File chọn sẵn đi qua cùng bước nghe lại, báo độ dài, cảnh báo quá ngắn hoặc quá dài so với ngưỡng đang áp dụng trước khi nộp |
| **UX-05** | Đề đang chọn hiện đầy đủ ngay trên nút ghi âm |
| **UX-06** | Báo cáo đặt kết quả và bước tiếp lên đầu, có liên kết tới từng phần, thu gọn phần kỹ thuật |
| **UX-07** | Bài của tôi đọc được trên điện thoại và lọc được Đánh giá / Luyện tập |
| **UX-08** | Hàng đợi bốn cột, "Duyệt bài tiếp theo" mở bài cũ nhất chưa ai giữ, lý do bằng tiếng Việt |
| **UX-09** | Trang duyệt: trình phát ghim cả trang, trạng thái và lý do bằng tiếng Việt, lý do soạn sẵn một chạm |
| **UX-10** | Quản trị kích hoạt mô hình tương thích và sửa ngưỡng QC, cả hai hỏi lại trước khi làm; tab đang mở nằm trong URL |
| **UX-11** | Đồng thuận: rút lại phải xác nhận; ký xong có lối đi tiếp; tải được toàn bộ dữ liệu cá nhân |

Kiểm thử: TC-UI-E01..E11 và TC-UI-I01 trong `docs/test/TEST_PLAN_UI.md`;
`tests/test_ui_traceability.py` giữ kế hoạch và mã khớp nhau.

Ghi chú thực hiện:

- Tên tiếng Việt của trạng thái, lý do gắn cờ và khía cạnh nằm một chỗ,
  `window.ui` trong `common.js`, thay cho bốn bản chép đã lệch nhau. Không dùng
  biến toàn cục rời: ở script cổ điển, một `function statusBadge()` của trang ghi
  đè biến toàn cục cùng tên — lỗi này đã xảy ra khi làm, hàm tự gọi lại chính nó.
- `[hidden]` luôn thắng `display` của thành phần: một `.button-row` gắn `hidden`
  từng vẫn hiện ra.
- API chỉ thêm trường `home` trong phản hồi đăng nhập. Luật chấm, dữ liệu và các
  API khác giữ nguyên.

### Đợt 6 — Lộ trình bài học do giáo viên soạn (D025) — **xong**

Yêu cầu của chủ dự án ngày 06/10/2026: lộ trình luyện tập phải có bài học rõ ràng, đi từ đọc theo văn bản có từ gợi ý tới nói tự do, từ cơ bản tới nâng cao, do giáo viên soạn. Đề xuất có research (sư phạm, 18 sản phẩm, chấm tự động trên máy) được duyệt toàn bộ khuyến nghị. Yêu cầu chức năng: SRS FR-45..FR-50.

**Thang bốn bậc của mọi bài học.** Mẫu (đọc to, nghe và nhắc lại) → Có kiểm soát (đọc rồi nói lại, đoạn có chỗ trống) → Có hướng dẫn (ghép câu từ từ khóa, khung câu, mô tả tranh, dàn ý) → Tự do (đề song song, 2–3 lượt với thời gian giảm dần). Bậc cuối luôn là nói tự do vì luyện trên văn bản soạn sẵn thường không tự chuyển thành nói tự do.

**Màn hình mới**

| Mã | Màn hình | Đường dẫn | Vai trò |
| --- | --- | --- | --- |
| M13 | Lộ trình của tôi | `/practice` | Sinh viên |
| M14 | Học một bài | `/practice/lessons/{lesson_id}` | Sinh viên; giảng viên mở cùng trang này thì luôn là xem thử bản nháp |
| M15 | Ôn tập hôm nay | `/practice/review` | Sinh viên |
| M16 | Soạn lộ trình | `/teach` | Giảng viên, quản trị |
| M17 | Soạn một bài học | `/teach/lessons/{lesson_id}` | Giảng viên, quản trị |
| M18 | Theo dõi luyện tập | `/teach/insights` | Giảng viên, quản trị |

- **M13**: thẻ "Nên học tiếp" (bài nên học kèm lý do và căn cứ), thẻ "Hôm nay" (số giây đã thực nói trên mục tiêu 180 giây, chuỗi ngày, bảy ngày gần nhất), thẻ "Ôn tập" (số mục đến hạn, nút Ôn ngay khi có), rồi mục lục lộ trình theo chặng (band, chức năng giao tiếp, tiêu chí) với từng bài: số thứ tự hoặc dấu ✓, thang bốn bậc thu nhỏ, số bước đã đạt, trạng thái bằng chữ. Chọn được lộ trình khác khi có nhiều lộ trình đã xuất bản. Không điểm, không band, không bảng xếp hạng.
- **M14**: thanh tiến độ bước; cột trái danh sách bước kèm bậc (trên điện thoại thành một hàng số); khung chính hiện một bước: hướng dẫn, nội dung theo dạng bước, giọng mẫu, đồng hồ hiện câu hoặc đồng hồ chuẩn bị, bộ ghi âm dùng chung (nghe lại rồi mới nộp). Sau khi nộp: kết luận (Đạt / Chưa đạt / Chưa đo được), một gợi ý tự sửa, văn bản tô từng từ (máy nghe ra / chưa chắc / máy chưa nghe ra; bấm một từ để nghe lại đúng chỗ), chỗ trống, từ nghe thấy và chưa nghe thấy, các số đo, so sánh với lượt 1 ở bước nói tự do, nút Làm lại, Lượt tiếp hoặc Bước tiếp. Bước đã làm có dòng "Lần gần nhất" và nút Xem lại kết quả, kèm dấu khi giảng viên đã xem lại. Hết bài: tổng kết (bước đạt, từ sẽ quay lại trong Ôn tập, bài tiếp theo).
- **M15**: các mục đến hạn thành một buổi ôn ngắn: ghép câu với từ cần ôn, nói lại đề tự do với một lượt.
- **M16**: danh sách lộ trình; mỗi lộ trình có chặng (tên, band, chức năng, tiêu chí) và bài học (chưa xuất bản / đã xuất bản phiên bản N / có sửa đổi chưa xuất bản); nút Tạo lộ trình, Nhập từ tệp JSON, Sửa thông tin, Xuất JSON, Xuất bản lộ trình hoặc Gỡ xuất bản, Thêm chặng, Thêm bài học (từ đoạn văn mẫu và từ khóa, hoặc chỉ từ khóa), đổi thứ tự chặng và bài, Soạn, Xem thử, Lưu trữ bài.
- **M17**: danh sách bước (thêm, xoá, đổi thứ tự bằng nút lên/xuống; bước mới chèn trước bước nói tự do); biểu mẫu theo dạng bước; bản nháp tự lưu khi gõ (Ctrl/Cmd+S lưu ngay); khung soát lỗi cập nhật sau mỗi lần lưu, bấm một cảnh báo để tới đúng ô; ghi giọng mẫu bằng bộ ghi âm dùng chung, máy chép lại và báo tỷ lệ khớp văn bản; tải ảnh cho bước mô tả tranh; Lưu nháp, Xem như sinh viên, Xuất bản.
- **M18**: theo bài học: số sinh viên đã học, đã hoàn thành, số lượt luyện, bước hay dừng, tỷ lệ đạt của từng bước; từ cả lớp hay bị bỏ, chọn để tạo một bài ôn (bản nháp gồm bước từ khóa và bước nói tự do); danh sách lượt luyện gần đây, mở ra để nghe, xem bản chép, đổi nhận định từng từ hoặc kết luận của bước, kèm ghi chú cho sinh viên.

**API mới**

| Phương thức | Đường dẫn | Vai trò |
| --- | --- | --- |
| GET | `/api/v1/learn` | Sinh viên: lộ trình, tiến độ, hôm nay, ôn tập, bài nên học |
| GET | `/api/v1/learn/lessons/{lesson_id}` | Sinh viên: phiên bản đã xuất bản (không gửi đáp án chỗ trống) và lượt gần nhất của từng bước |
| POST | `/api/v1/learn/lessons/{lesson_id}/steps/{step_id}/attempts` | Sinh viên đã đồng thuận: ghi âm một bước, trả kết quả đo ngay |
| GET | `/api/v1/learn/attempts/{attempt_id}/audio` | Chủ lượt luyện hoặc giảng viên |
| GET | `/api/v1/learn/review` · POST `/api/v1/learn/review/attempts` (trường `review_id`) | Sinh viên: buổi ôn |
| DELETE | `/api/v1/learn/attempts/{attempt_id}` | Sinh viên: xoá một lượt luyện của chính mình |
| GET | `/api/v1/learn/media/{key}` | Người đã đăng nhập: giọng mẫu, ảnh |
| GET, POST, PATCH, DELETE | `/api/v1/teach/paths…`, `/api/v1/teach/units…`, `/api/v1/teach/lessons…` | Giảng viên: soạn, dựng bài, xuất bản, giọng mẫu, ảnh, xuất/nhập JSON |
| POST | `/api/v1/teach/preview` | Giảng viên: thử một bước, không lưu |
| GET | `/api/v1/teach/insights` · GET `/api/v1/teach/attempts/{id}` · POST `/api/v1/teach/attempts/{id}/override` | Giảng viên: theo dõi, sửa nhận định |

**Bảng dữ liệu mới:** `lesson_path`, `lesson_unit`, `lesson`, `lesson_version`, `step_attempt`, `review_item`, `lesson_media`. Lượt luyện theo bài học **không** nằm trong bảng `response`, nên tự nhiên đứng ngoài hàng đợi duyệt, thống kê chấm và bản xuất nghiên cứu.

**Ghi chú thực hiện**

- Máy nhận dạng không được gợi văn bản đáp án: gợi văn bản làm bản chép bám theo văn bản thay vì điều người đọc nói.
- Với người Việt đọc văn bản, bản chép của Whisper lệch khoảng 12% so với văn bản (McGuire 2025). Vì vậy ngưỡng "đạt" mặc định của bước đọc là 75% số từ, và mọi chữ trên màn hình nói "máy chưa nghe ra" chứ không nói "sai". Độ tin cậy trên giọng Việt [CẦN ĐO] với bản ghi thử có đồng thuận trước khi mở cho sinh viên thật.
- Lượt luyện xử lý ngay trong request, giới hạn bằng cùng số luồng chấm với bài đánh giá.
- Chỗ trống chỉ được ghép không tốn chi phí với đáp án hoặc từ trong ngân hàng từ; từ khác phải trả chi phí thay thế. Nhờ vậy lời nói thêm sau câu không bị đếm vào chỗ trống cuối cùng.
- Tên tiêu chí trong phần luyện tập dùng bộ tên của D023 (Độ trôi chảy, Mạch lạc, Vốn từ, Ngữ pháp, Phát âm dễ nghe), giống câu gợi ý do máy chủ viết; biểu mẫu của giảng viên ghi kèm tên CEFR gốc.

### Đợt 7 — Giao diện học thuật, trang nhã (D026) — **xong**

Chủ dự án yêu cầu "cải tạo lớn như sản phẩm bán cho khách hàng thật" và chọn phong cách học thuật, trang nhã.

- Tiêu đề chữ có chân, thân chữ không chân dễ đọc, nhãn chữ hoa nhỏ giãn cách; dùng phông có sẵn trên máy (không tải phông ngoài) để giữ CSP `script-src 'self'` và nguyên tắc chạy trên máy. *Đợt 12 (D031) thay phần này bằng một phông Roboto do ứng dụng tự phục vụ; vẫn không tải gì từ ngoài.*
- Bảng màu xanh mực làm màu chính, đỏ rượu làm điểm nhấn tiết chế; nền giấy sáng; có đủ giao diện tối.
- Trang giới thiệu sản phẩm ở `/` cho khách chưa đăng nhập: sản phẩm làm gì, cho ai, cách hoạt động, nguyên tắc trung thực (không cấp chứng chỉ, giảng viên quyết định cuối cùng), yêu cầu kỹ thuật lấy từ ngưỡng đang áp dụng. Người đã đăng nhập ở `/` vẫn là trang nộp bài (sinh viên); giảng viên và quản trị được đưa về trang chính của vai trò.
- Trang đăng nhập hai cột: giới thiệu ngắn và biểu mẫu.

### Đợt 8 — Thanh điều khiển bên trái, icon, lộ trình dạng đường đi (D027) — **xong**

Chủ dự án yêu cầu ngày 07/10/2026: nhiều icon thay vì chữ chằng chịt, thanh điều khiển dọc thay thanh tab trên đầu (đặt bên phải trước, rồi chủ dự án chọn chuyển sang bên trái cùng ngày), lộ trình có đường nối như Duolingo, chia theo nhiều chủ đề với nhiều mức khó.

- **Thanh điều khiển bên trái** cho người đã đăng nhập: thương hiệu, các mục của vai trò (icon và nhãn ngắn), tài khoản ở chân (đồng thuận, giao diện sáng/tối, đăng xuất, mở lên trên). Màn hẹp hơn 900 px: thanh thành một dải trên cùng (thương hiệu, tài khoản) và thanh tab ở đáy cho mọi vai trò. Khách chưa đăng nhập vẫn có thanh trên đầu của trang giới thiệu.
- **Bộ icon** `static/icons.svg`: một tệp SVG cùng nguồn, tự vẽ, nét 1,75 trên lưới 24 px, lấy màu chữ xung quanh; mẫu `_icons.html` và `window.ui.icon()` vẽ cùng một kiểu thẻ. Dùng cho điều hướng, tiêu đề trang, chín dạng bước, mười chủ đề, trạng thái và các nút.
- **M13 dạng đường đi**: ba phần theo trình độ (A2 Cơ bản, B1 Trung cấp, B2 Nâng cao); mỗi phần gồm các chặng theo chủ đề, mỗi chủ đề một màu riêng (dịu, có bản cho giao diện tối) và một icon. Mỗi bài là một "đồng xu" trên đường uốn lượn: dấu tick khi hoàn thành, màu chủ đề và vòng tiến độ khi đang học, mờ khi chưa tới lượt; bài nên học có cờ "Bắt đầu"/"Học tiếp". Bấm đồng xu mở thẻ bài (tóm tắt, số bước, nút học), Esc hoặc bấm ra ngoài thì đóng. Cột bên: bài nên học tiếp, mục tiêu hôm nay, ôn tập. Không khoá bài nào.
- **Chặng có chủ đề** (`lesson_unit.topic`): mười chủ đề cố định; giảng viên chọn chủ đề khi tạo hay sửa chặng; xuất/nhập JSON giữ chủ đề.
- **Lộ trình mẫu**: 18 chặng, 31 bài (16 bài soạn đủ, 15 bài dựng từ nhiệm vụ D023). Bản cài đã có lộ trình mẫu cũ được xếp lại một lần (ghi ở bảng `lesson_meta`): thêm chặng và bài còn thiếu, đặt tên, chủ đề, thứ tự; lượt luyện và bản nháp không bị đụng tới; chặng giảng viên tự thêm đứng sau.

### Đợt 9 — Hoàn thiện sản phẩm: tài khoản, việc đang chờ, thang band, chuẩn bị (D028) — **xong**

Chủ dự án yêu cầu ngày 07/10/2026 làm đầy đủ các chức năng còn thiếu, không cần chờ duyệt. Năm việc, chọn theo những chỗ người dùng thật sẽ vấp, không thêm phụ thuộc nào.

- **M19 Tài khoản của tôi** (`/account`, mọi vai trò, mở từ menu tài khoản ở chân thanh điều khiển): đổi mật khẩu bằng mật khẩu hiện tại, các điều kiện tự đánh dấu khi gõ (từ 8 ký tự, khác bút danh, khác mật khẩu cũ); đổi xong mọi thiết bị khác bị đăng xuất. Thông tin đăng nhập: bút danh, vai trò, lúc tạo, lần đăng nhập gần nhất, lần đổi mật khẩu gần nhất, số thiết bị đang đăng nhập; nút "Đăng xuất khỏi các thiết bị khác".
- **Tab Tài khoản của trang quản trị** (tab đầu tiên): tạo một bút danh hoặc một dãy (SV-, GV-, QT- theo vai trò, đánh số tiếp nối, xem trước "Sẽ tạo SV-011 → SV-020"). Mật khẩu tạm hiện một lần trên **phiếu tài khoản** in được (hai phiếu một hàng trên giấy, chỉ in phiếu), tải được CSV; rời trang khi phiếu còn trên màn hình thì trình duyệt hỏi lại. Danh sách tìm theo bút danh, lọc theo vai trò; mỗi dòng có trạng thái (đang dùng, đã tắt, tạm khoá, chờ đổi mật khẩu tạm) và nút icon: cấp lại mật khẩu tạm, gỡ khoá, tắt/bật.
- **Mật khẩu tạm chỉ mở được việc đổi mật khẩu:** API khác trả 403, trang khác chuyển về `/account?first=1`; đăng nhập bằng mật khẩu tạm luôn về trang đó dù `?next=` là gì.
- **Con số trên thanh điều khiển:** "Bài của tôi" (quyết định mới của giảng viên), "Luyện tập" (mục ôn hôm nay), "Hàng đợi duyệt" (bài chờ duyệt). Màu đỏ rượu như dấu "chỗ của bạn", không phải màu báo động; trên điện thoại con số nằm ở góc icon của thanh tab dưới đáy. Danh sách "Bài của tôi" đánh dấu "Mới xác nhận" trên bài vừa được quyết định.
- **Trang `/bands`** cho mọi người: hai ngưỡng band của mô hình đang chấm, năm mặt của kỹ năng nói mỗi mặt một thẻ với nhãn máy đo gián tiếp / máy không đo / không đánh giá, "máy dùng" và "máy không thấy", mô tả A2/B1/B2, khối giới hạn. Chân trang và báo cáo có đường dẫn tới trang này.
- **Chuẩn bị 30 giây** trên trang nộp bài, ngay dưới đề: vòng tròn đếm ngược đầy dần, "Nói ngay" và "Huỷ"; hết giờ thì tự ghi âm. Trình đọc màn hình nghe báo lúc bắt đầu, còn 10 giây và hết giờ, không nghe từng giây.

### Đợt 10 — Hồ sơ cá nhân, đăng nhập Google, quản lý tài khoản đầy đủ (D029) — **xong**

Chủ dự án yêu cầu ngày 07/10/2026: làm đầy đủ trang quản lý tài khoản và hồ sơ cá nhân, có đăng nhập bằng Google.

- **M19 mở rộng thành bốn mục** (tab, giữ chỗ trên URL `#security`): **Hồ sơ** (ảnh đại diện = biểu tượng + màu, xem trước ngay ở đầu trang; mục tiêu nói mỗi ngày 1/2/3/5/10 phút cho sinh viên, lưu ngay khi chọn; giao diện và cỡ chữ lưu trên trình duyệt; thông tin đăng nhập), **Bảo mật** (đổi mật khẩu; đăng nhập bằng Google: trạng thái, liên kết, gỡ liên kết, lời giải thích chỉ lưu mã băm; danh sách phiên với tên thiết bị, cách đăng nhập, "Máy này", đăng xuất từng phiên), **Hoạt động** (đăng nhập, lần sai, thay đổi; việc của quản trị viên ghi là "Quản trị viên"), **Dữ liệu** của sinh viên (trạng thái đồng thuận, tải toàn bộ dữ liệu JSON theo FR-34, cách xoá). Tài khoản còn mật khẩu tạm chỉ thấy biểu mẫu đổi mật khẩu.
- **Trang đăng nhập**: nút hiện/ẩn mật khẩu, cảnh báo Caps Lock, nút "Đăng nhập bằng Google" khi máy chủ có cấu hình, mục "Quên mật khẩu?" nói thẳng cách lấy lại (quản trị viên cấp mật khẩu tạm, hoặc đăng nhập bằng Google đã liên kết), thông báo lỗi Google bằng câu cố định theo mã.
- **Luồng Google**: `/auth/google/start?mode=login|link&next=` và `/auth/google/callback`; cookie `aicefr_oauth` HttpOnly, SameSite=Lax, đường dẫn `/auth/google`, mười phút. Cấu hình: `AICEFR_GOOGLE_CLIENT_ID`, `AICEFR_GOOGLE_CLIENT_SECRET`, tuỳ chọn `AICEFR_GOOGLE_DOMAIN` và `AICEFR_PUBLIC_URL` (dựng redirect URI sau proxy). Trên Google Cloud Console tạo OAuth client loại "Web application" và thêm `<địa chỉ>/auth/google/callback` vào danh sách redirect URI.
- **Tab Tài khoản của quản trị**: ảnh đại diện trong danh sách, nhãn "Có Google", tải danh sách CSV; bấm bút danh mở **bảng chi tiết** (trạng thái, phiên, Google, lịch sử 20 dòng) với các nút cấp mật khẩu tạm, đăng xuất mọi thiết bị, gỡ Google, gỡ khoá, tắt/bật, xoá dữ liệu (chuyển sang mục Dữ liệu với bút danh điền sẵn) và đổi vai trò. Dòng của chính quản trị viên không có nút thao tác.

### Đợt 11 — Chấm mù kép (D030) — **xong**

Hạng mục 2.1 của "Hướng phát triển tiếp" và mục 6 kế hoạch khảo sát: điểm của người phải độc lập với máy, nên chấm có đường riêng, mù theo cấu tạo.

- **M20 Chấm mù** (`/rate`, vai trò giảng viên và quản trị, mục "Chấm mù" có con số phiếu chưa làm trên thanh điều khiển): mỗi đợt một thẻ với thanh tiến độ, nút "Bắt đầu chấm"/"Chấm tiếp" và các ô phiếu đánh số theo thứ tự riêng của giám khảo (xám chưa mở, viền đang chấm, xanh đã nộp; dấu * là bài phân xử).
- **M21 Phiếu chấm** (`/rate/{mã phiếu}`): đề bài, trình phát bản ghi (địa chỉ của phiếu, tên tệp `bai-N.wav`), biểu mẫu năm tiêu chí và điểm tổng ô số bước 0,5, band dạng nút chọn, một dòng lý do, ô "Không chấm được" kèm ba lý do. Nộp xong tự mở phiếu kế tiếp; phiếu đã nộp hiện chỉ đọc. Không có bút danh, mã bài, điểm máy hay điểm của người khác ở bất kỳ đâu trên trang; không có gợi ý band theo điểm (đó cũng là một mỏ neo).
- **Tab Chấm mù của trang Quản trị**: số bài đủ điều kiện, biểu mẫu tạo đợt (tên, giám khảo, số bài, hạt giống, chỉ bài chưa vào đợt), danh sách đợt với tiến độ từng giám khảo, số bài cần phân xử và nút giao phân xử, "Báo cáo", "CSV", "Đóng"/"Mở lại". **Báo cáo** mở trong hộp thoại, đọc từ trên xuống theo đúng thứ tự phải đọc: người–người, máy–người, cờ chuyển giảng viên, ghi chú về chỉ số không tính được; mốc kế hoạch ghi rõ là chưa ký.
- **Chặn đường vòng**: giảng viên còn phiếu chấm mù của một bài thì báo cáo, lịch sử, khoá và quyết định duyệt của bài đó trả 403, hàng đợi của họ không hiện bài đó, và con số chờ duyệt trên thanh điều khiển không đếm bài đó. Quản trị viên làm giám khảo được che như vậy trên màn quản trị: danh sách bài bỏ bài đó, bản xuất nghiên cứu, báo cáo và CSV của đợt báo "nộp xong rồi xem".
- **Đã xem là hết mù** (BR-27): ai đã mở kết quả của máy cho một bài thì không được giao chấm bài đó; phiếu đang nợ của họ (ví dụ mở báo cáo trong lúc đợt tạm đóng) hiện ô gạch ngang "không còn mù", trang phiếu báo lý do và không cho nộp; tiến độ đợt đếm những phiếu như vậy, và quản trị viên bấm "Giao lại N phiếu" để chuyển chúng cho giám khảo khác. Hộp xác nhận "Đóng đợt" nói trước điều này.

### Đợt 12 — Phông Roboto, logo mới, chiều sâu và chuyển động trên mọi trang (D031) — **xong**

Chủ dự án yêu cầu giao diện "đẹp, mượt mà và chuyên nghiệp", logo và phông Roboto mới, trang giới thiệu ít chữ có đồ hoạ 3D, rồi đồ hoạ đẹp và mượt cho toàn bộ các trang.

- **Phông và logo.** Roboto (thẳng và nghiêng, ba tập ký tự) đặt trong `static/fonts/`, tải trước tập latin và vietnamese; tiêu đề đậm hơn và khít hơn thay cho chữ có chân. Logo là bong bóng thoại chứa ba thanh cao dần A2 → B1 → B2, đổi màu theo giao diện sáng/tối; favicon cùng hình. Tên sản phẩm hai màu: "AI Assessor" màu mực, "CEFR" đỏ rượu.
- **Trang giới thiệu.** Câu chủ đạo "Luyện nói có lộ trình. Tiến bộ có bằng chứng." (dùng lại ở trang đăng nhập và tiêu đề tab), một câu dẫn, hai nút, ba dòng thông tin ngắn; tiêu đề các mục viết lại cho gọn và chuyên nghiệp ("Từ lượt nói đến kết quả được xác nhận", "Gợi ý ít dần, đến khi bạn tự nói được", "Bài học do giảng viên soạn", "Minh bạch về những gì máy làm được"), không hứa điều hệ thống chưa làm; bên phải là cảnh 3D: ba khối A2/B1/B2 trên sàn lưới, bốn thẻ kính lấy từ màn hình thật (đọc to có đánh dấu từ, đang ghi âm, ước lượng, giảng viên đã duyệt), cả cảnh nghiêng theo con trỏ. Bên dưới: ba bước dạng thẻ nghiêng có vệt sáng, bốn bậc phương pháp dạng khối 3D cao dần, màn hình mẫu nghiêng cho giảng viên, bốn nguyên tắc, ba câu hỏi nhanh (ngưỡng thời lượng vẫn đọc từ cấu hình), dải kêu gọi đăng nhập. Trên điện thoại, thanh đầu trang gọn một dòng.
- **Mọi trang.** Nền ánh màu cố định sau nội dung; thanh bên (màn rộng) và thanh đầu trang mờ kính; ô biểu tượng tiêu đề và dấu của trạng thái rỗng nền nhạt, viền mảnh; thẻ bo 14 px với bóng mềm, trung tính; nút một màu với bóng mảnh, chỉ lún một điểm ảnh khi bấm (các nút chỉ mượn thẻ `<button>` như tab, liên kết trong bảng, chip vẫn phẳng); nhãn trạng thái có chấm màu, chấm nhấp nháy khi đang xử lý; thanh tiến độ màu chuyển và mọc dần khi hiện; mục gập trượt mở; các khối của trang trồi lên lần lượt khi vào trang; chuyển trang mờ dần, thanh bên đứng yên; hộp thoại phóng và mờ dần, nền sau mờ đi.
- **Khối 3D dùng chung.** Khối mờ màu nhạt với viền mảnh, mỗi hàng chỉ một khối màu đậm. Bục band trên báo cáo (band ước lượng tô màu đỏ rượu, band khoảng tin cậy chạm tới đậm hơn một bậc), cột phân bố band ở thống kê lớp (cao theo tỷ lệ), ba khối ở trang band và trang đăng nhập. Con số luôn được viết ra bên cạnh; khối chỉ để nhìn.
- **Bề mặt mờ, không bóng nhựa.** Bản đầu bị chủ dự án nhận xét "nhìn bị nhựa"; bản này bỏ lớp sáng trên nút và ô biểu tượng, viền sáng bên trong, bóng đổ có màu, chữ chuyển màu, các khối chuyển sắc, và làm chuyển động ngắn lại (thẻ nghiêng tối đa 5°, vật trôi 4 px).
- **Giới hạn.** View transition giữa hai trang, `@starting-style` và mở mục gập bằng trượt là nâng cấp dần: trình duyệt chưa hỗ trợ thì trang vẫn chạy như cũ, chỉ không có hiệu ứng.

### Đợt 13 — Thành tựu và nhịp luyện của chính mình (D032) — **xong**

Chủ dự án yêu cầu "làm tiếp các thứ như streak, thành tựu ... để tăng engagement của người học". Lấy cơ chế của các ứng dụng học hiện nay nhưng bỏ phần gây hại (BR-28): không bảng xếp hạng, không điểm kinh nghiệm, không thưởng theo điểm hay band, không lời đe doạ mất chuỗi.

- **Thẻ Hôm nay** (M13 `/practice`): dưới chuỗi ngày là kỷ lục ("Kỷ lục của bạn: N ngày", hoặc "Đang là kỷ lục của bạn"); dải bảy ngày vẽ ngày nghỉ được tính bằng ô viền đứt, chú thích "nghỉ, chuỗi vẫn giữ"; dòng cuối "7 ngày qua: X · 7 ngày trước đó: Y". Trên điện thoại hai dòng mới ẩn như dải bảy ngày.
- **Thẻ Thành tựu** (M13, cột bên): "Thành tựu N/17", ba huy hiệu gần nhất, nhãn "k mới", dòng "Sắp đạt" với thanh tiến độ cho thành tựu gần đạt nhất đã bắt đầu, liên kết "Xem tất cả" tới `/my-progress#achievements`. Người mới chưa có gì thấy một câu mời ghi lượt nói đầu tiên, không thấy "0/30".
- **Cột bên chỉ dính khi vừa màn hình.** Bốn thẻ cao hơn một màn hình 1280×820; khi đó cột cuộn cùng trang thay vì dính lên đầu và giấu các thẻ dưới cùng cho tới cuối lộ trình (`fitSide`).
- **Chúc mừng sau lượt nói** (M14): lượt vừa đạt thành tựu hiện một thông báo "Thành tựu mới: …. Xem ở trang Tiến độ." — một lần, không pháo hoa, không âm thanh.
- **Danh sách** (M8 `/my-progress`): năm nhóm Đều đặn, Thời gian nói, Lộ trình, Kiên trì, Đánh giá. Ô đã đạt: huy hiệu màu mực, ngày đạt màu xanh; ô chưa đạt: huy hiệu viền đứt, chữ vẫn đậm đủ để đọc, thanh tiến độ và "x/y đơn vị · chưa đạt"; ô mới: viền đỏ rượu, nhãn "Mới", huy hiệu phóng nhẹ khi hiện (tắt khi giảm chuyển động). Mở danh sách là đánh dấu đã xem.
- **Riêng tư.** Không có màn hình nào cho người khác xem thành tựu của một người học; bản xuất dữ liệu cá nhân có thành tựu; xoá dữ liệu người học là xoá theo.

### Đợt 14 — Gói dịch vụ của trường và thanh toán (D034) — **xong**

Chủ dự án yêu cầu "phải có thanh toán để làm thêm luồng payment", rồi "tìm ra cách upgrade xứng đáng" và hỏi "chỗ" là gì. Trả lời bằng một thang gói mà mỗi bậc thêm thứ nhìn thấy được, viết bằng chữ của trường: "số sinh viên" thay cho "chỗ". Chỉ chạy khi bật thu phí (`AICEFR_BILLING`); sinh viên không thấy gì của đợt này (BR-29, FR-W7).

- **Tab "Gói dịch vụ"** (M23, trang Quản trị): biểu ngữ cổng thử ("không có tiền thật"), ân hạn hay vừa về Miễn phí; thẻ **Gói đang dùng** (tên gói, tổ chức, hiệu lực, còn lại, số sinh viên, ba công cụ có dấu tích hoặc ổ khoá) cạnh thẻ **Mức đang dùng** (thanh sinh viên đang có tài khoản trên số cho phép; thanh bài đánh giá của tháng trên số dự kiến, bỏ người đồng thuận nghiên cứu, cảnh báo ở 80% và 100% mà không chặn ai); **bảng so sánh** Miễn phí, Chuẩn (nhãn "Phổ biến"), Nâng cao — dòng có ở mọi gói, dòng mỗi bậc thêm, số sinh viên, số bài dự kiến, hỗ trợ — cột đang dùng tô nền, nút "Chọn gói …" hay "Gia hạn" chọn sẵn gói ở biểu mẫu dưới; **Nâng cấp hoặc gia hạn**: hai thẻ gói, số sinh viên, thời hạn 6 hoặc 12 tháng (giảm 15%), báo giá tự cập nhật (loại, thời hạn, giá, giảm, phần trừ của gói cũ, số phải trả), nút "Thanh toán … đ"; **Đơn hàng** với trạng thái và liên kết biên nhận; **Tổ chức và hợp đồng**: tên tổ chức, ô dán mã giấy phép.
- **Trang cổng thử** (`/billing/sandbox/{mã đơn}`): đứng thay trang của cổng thật, ghi to "Môi trường thử"; số tiền lớn, mã đơn, nội dung, thời hạn, bên mua; ba nút "Thanh toán thành công", "Thanh toán không thành công", "Huỷ giao dịch".
- **Trang kết quả** (`/billing/return/{cổng}`): thành công (gói, số sinh viên, thời hạn, có hiệu lực ngay hay khi gói đang dùng kết thúc, mã giao dịch, nút biên nhận); không thành công hoặc huỷ (gói không đổi); không xác nhận được (chữ ký sai, sai số tiền) kèm lời dặn liên hệ khi đã bị trừ tiền.
- **Biên nhận** (`/billing/orders/{mã đơn}/receipt`): bên bán, bên mua, dòng gói, giảm theo năm, phần trừ, đã thanh toán, cổng, mã giao dịch; nút "In hoặc lưu PDF"; ghi rõ không phải hoá đơn giá trị gia tăng.
- **Nơi giảng viên làm việc**: trang soạn lộ trình báo gói đang dùng chưa có soạn bài riêng và khoá nút "Tạo lộ trình", "Nhập từ tệp JSON"; trang thống kê luyện tập nói gói nào mở thống kê thay vì "không có quyền".

### Đợt 15 — Chọn cổng thanh toán; khung cấu hình đăng nhập Google (D035, D036) — **xong**

Chủ dự án muốn thử thanh toán với Stripe vì có môi trường thử, và để ngỏ MoMo, VNPay "cho đa dạng"; rồi hỏi đăng nhập Google có PKCE không và nhờ thiết kế sẵn để đưa khoá sau. Giao diện của đợt này là hai chỗ người vận hành thấy cấu hình đã đúng hay chưa, và một lựa chọn cho quản trị viên lúc trả tiền. Sinh viên vẫn không thấy gì (BR-29).

- **Ô "Thanh toán qua"** (M23, biểu mẫu Nâng cấp hoặc gia hạn): mỗi cổng đang bật là một thẻ chọn — tên cổng, nhãn "Thử" khi không có tiền thật, cách người trả trả tiền (Stripe: thẻ quốc tế Visa, Mastercard, JCB; MoMo: ví MoMo, quét mã QR; VNPay: thẻ ATM nội địa, thẻ quốc tế, QR ngân hàng; Cổng thử), và cách trả ở môi trường thử (Stripe: thẻ 4242 4242 4242 4242). Cổng đầu được chọn sẵn; nút thanh toán ghi "Thanh toán … đ qua <cổng>". Trên điện thoại các thẻ xếp dọc, trang không cuộn ngang.
- **Biểu ngữ** đầu tab: "Môi trường thử: <các cổng>" khi có cổng không thu tiền thật; "Cấu hình cổng thanh toán cần xem lại" liệt kê từng cổng chưa bật và lý do bằng tên biến (không bao giờ giá trị khoá); "Chưa có cổng thanh toán nào được bật" khi danh sách trống.
- **Bảng đơn hàng** có cột "Cổng" (tên cổng, "(thử)" khi không có tiền thật); **biên nhận** ghi cổng và "môi trường thử, không có tiền thật" khi đúng như vậy.
- **Trang kết quả** (`/billing/return/{cổng}`) thêm hai trạng thái: **"Bạn đã rời trang thanh toán"** (rời trang Stripe khi chưa trả: chưa trừ tiền, phiên tự hết hạn, đặt lại đơn) và **"Chưa xác nhận được với <cổng>"** (không hỏi được Stripe: đơn được ghi nhận khi cổng báo về); dòng "Môi trường thử của <cổng>" theo đơn chứ không theo cấu hình hiện tại.
- **Khung "Đăng nhập bằng Google"** (tab Cấu hình của M7): nhãn Đang bật / Chưa bật; một câu nói luồng là OAuth 2.0 có PKCE (S256), `state`, `nonce` và hệ thống chỉ giữ mã băm; mục "Cần xem lại" khi có; bảng hai cột — địa chỉ chuyển hướng cần đăng ký (kèm nút **Sao chép**, và ghi chú khi địa chỉ lấy theo trang đang mở vì chưa đặt `AICEFR_PUBLIC_URL`), Client ID, client secret ("Đã đặt (không bao giờ hiển thị)" hoặc "Chưa đặt"), phạm vi xin, tên miền giới hạn, tên cookie của luồng, số tài khoản đã liên kết; dòng cuối chỉ tới hướng dẫn lấy khoá.

### Đợt 16 — Ảnh nền vẽ bằng mã: bậc thang tiếng nói (D037) — **xong**

Chủ dự án muốn giao diện có hình và chuyển động, "thiết kế ảnh để làm giao diện chứ không đơn thuần là dùng nền mặc định nữa", cho toàn bộ trang web. Ban đầu chủ dự án nhắc tới Rive; khi được hỏi, chủ dự án chọn vẽ trong mã và không tải Rive. Vì vậy đợt này không thêm thư viện và không tải gì từ ngoài (W-NFR-2).

- **Ý tưởng hình.** Ruộng bậc thang là hình ảnh tiến bộ từng bậc mà sinh viên Việt Nam quen thuộc. Ở đây, sống mỗi ngọn đồi là đường bao âm lượng của một câu nói, mỗi gợn là một âm tiết. Ngọn đồi là chặng từ A2 lên B2, còn các gợn là những lần nói.
- **Mọi trang.**
  - Một nền cố định nằm sau nội dung: góc trên bên phải có các đường đồng mức mờ dần về bên trái; góc dưới bên phải có dãy đồi bốn tầng.
  - Nền đứng yên và không đổi chỗ khi chuyển trang.
  - Trang của giảng viên và quản trị viên có nền nhạt hơn, vì đó là nơi người dùng đọc số liệu.
  - Trạng thái rỗng (ví dụ "Chưa có bài nào được chấm") có một dải đồi thấp ở chân khung.
- **Trang giới thiệu.**
  - Cảnh đồi bốn tầng nằm dưới cảnh 3D. Sống đồi tự vẽ ra lần lượt từ xa đến gần.
  - Sống đồi gần nhất có màu đỏ rượu và chuyển động chậm như đang thở.
  - Mặt trời thấp mọc sau đồi xa; ở giao diện tối là mặt trăng.
  - Khi di chuột, cảnh đồi trôi nhẹ ngược với cảnh 3D.
  - Phía bên trái, nơi có chữ, cảnh mờ dần theo một đường cong êm, để không thành một mép thẳng.
- **Trang đăng nhập.** Cùng cảnh đồi, hiện ra từ phía sau khung đăng nhập. Không có mặt trời, vì khung đăng nhập che đúng chỗ đó. Chữ bên trái nằm trên nền trơn.
- **Màu và kích thước.**
  - Hình chỉ là mặt nạ và nét vẽ, được tô bằng biến màu của giao diện, nên một hình dùng được cho cả giao diện sáng và tối.
  - Trên màn hình rộng, cảnh đồi giãn theo khung chứ không bị cắt đỉnh. Mặt trời là một phần tử riêng nên vẫn tròn.
  - Trên điện thoại, cảnh hiện như một khung nhìn vào phần bên phải.
- **Giới hạn.**
  - Chuyển động chỉ chạy khi người dùng không chọn giảm chuyển động.
  - Khi in, không có hình nào.
  - Hình ẩn với trình đọc màn hình và không nhận cú bấm (W-NFR-3, W-NFR-4).
- **Cách làm.**
  - `tools/make_art.py` vẽ ra ba tệp từ cùng một hình học:
    - `static/art/hills.svg` khoảng 8,7 KB;
    - `static/art/contours.svg` khoảng 8,5 KB;
    - `templates/_art.html` khoảng 14 KB, là cảnh nhúng thẳng vào trang để stylesheet tô màu và vẽ từng đường.
  - Script cho ra kết quả giống hệt nhau đến từng byte mỗi lần chạy. Có test kiểm tra rằng tệp đã commit đúng bằng tệp script vẽ ra.

### Đợt 17 — Bằng chứng học tập: phát âm, thực nghiệm phản hồi, thời gian giảng viên, tiến bộ đáng tin (D039–D042) — **xong**

Bốn hướng chủ dự án chọn sau đề xuất làm đề tài mạnh hơn, GVHD đã duyệt (theo chủ dự án, 11/10/2026). Mỗi màn hình dưới đây nói một khẳng định về người học hay giảng viên, nên đều kèm số lần đo và im lặng khi chưa đủ.

- **"Phát âm cần chú ý"** (M8, dưới biểu đồ): mỗi lỗi một dòng — tên lỗi, nhãn "lỗi/lần gặp · %" (màu cảnh báo từ 30 %), thanh tỉ lệ, tối đa 5 ví dụ «từ» → máy nghe «…» dẫn về bài học, và một câu cách luyện. Chưa đủ 8 lần gặp thì nhãn ghi "Chưa đủ dữ liệu · n/8 lần gặp". Câu cuối nói máy chỉ đếm thiếu và giọng Việt không phải lỗi. Trong bài học, chú thích của từ máy nghe khác ghi thêm tên lỗi.
- **"Tiến bộ đáng tin"** (M8, dưới đường xu hướng): một khối nói kết luận — tiến bộ, giảm, chưa vượt sai số đo, chưa đo được sai số, chưa đủ dữ liệu — kèm trung bình đầu, cuối, chênh lệch, ngưỡng và nguồn của sai số đo.
- **"Thực nghiệm phản hồi"** (M8, chỉ hiện với người tham gia): tên thực nghiệm, nhóm, vì sao chia nhóm; ở giai đoạn khảo sát là năm câu 1–5; nút "Rời thực nghiệm". Báo cáo (M4) của nhóm "Chỉ điểm" chỉ có điểm và mức, kèm thông báo vì sao và đường tới nút rời.
- **Trang `/admin/study`** (từ tab Xoá dữ liệu của M7): biểu mẫu bắt đầu (tên, số ngày tối thiểu giữa bài đầu và cuối) khi không có thực nghiệm chưa đóng; bảng thực nghiệm với trạng thái, số tham gia, số khảo sát, nút Xem kết quả, CSV và chuyển giai đoạn; khung kết quả hai cột theo nhóm và một dòng chênh lệch kèm khoảng tin cậy 95 % và Hedges g, ghi rõ là nghiên cứu thăm dò.
- **Thống kê lớp** (M9) thêm hai thẻ: **"Hiệu quả cho giảng viên"** — phút duyệt một bài có máy, phút chấm mù một bài không có máy, thời gian tiết kiệm, tỉ lệ máy tự xử lý và tỉ lệ giữ nguyên band, mỗi tỉ lệ có khoảng tin cậy và số đếm; **"Phát âm của cả lớp"** — danh sách như M8, ví dụ không dẫn tới bài của ai.
- **Tab Cấu hình** (M7) thêm khung **"Sai số đo cho tiến bộ đáng tin"**: sai số đang dùng và nguồn, số cặp bài thử lại hiện có, nút dùng sai số từ bài thử lại (tắt khi chưa đủ 10 cặp), ô nhập tay bắt buộc kèm nguồn.

### Ngoài phạm vi tài liệu này nhưng phải lên lịch

Đóng gói Docker và triển khai staging. Mốc ký cam kết sản phẩm cuối là **hết tuần 7**,
và cam kết đó cần một bản chạy được cho giảng viên hướng dẫn xem.

---

## 9. Chiến lược kiểm thử

| Lớp | Nội dung |
| --- | --- |
| Đơn vị | Băm mật khẩu, kiểm phiên, kiểm vai trò, đếm lần đăng nhập sai |
| Hợp đồng API | Mã trạng thái, hình dạng dữ liệu, 403 vai trò sai, 404 bài người khác, 202 khi nhận bài |
| Template | Render được; có tuyên bố bắt buộc; **không chứa chuỗi cấm** theo SRS §11.3; không lộ thông tin định danh |
| Luồng | Nộp → QUEUED → RUNNING → xong → xem báo cáo → khóa → duyệt → lịch sử |
| Thủ công | Danh mục 12 thao tác trên Chrome, Edge, Firefox ở 1366×768 |

Ngưỡng: độ phủ không tụt dưới **80%**. Mỗi endpoint mới có ít nhất một test đường
thành công và một test đường từ chối quyền.

Hai test đáng viết sớm nhất vì bắt được lỗi nguy hiểm nhất:

- `test_reject_khong_lo_band` — trạng thái REJECT/FAILED thì HTML không được chứa
  chuỗi band hay điểm ở bất kỳ dạng nào.
- `test_khong_co_chuoi_cam` — mọi template không được chứa chuỗi mang nghĩa
  "chứng chỉ CEFR", "đạt/không đạt", "kết quả chính thức".

---

## 10. Rủi ro

| Rủi ro | Ảnh hưởng | Cách giảm |
| --- | --- | --- |
| Đổi máy trạng thái làm vỡ test và tài liệu rải rác | Mất thời gian sửa lắt nhắt | Đổi `contracts.py`, SRS, SDD, test trong cùng một commit |
| Thêm xác thực làm hỏng toàn bộ test hiện có | Đợt 2 kéo dài | Test dùng cố định một tài khoản dựng sẵn qua fixture |
| Tự viết xác thực dễ sai | Rủi ro bảo mật | Dùng `bcrypt` theo NFR-07, không tự nghĩ thuật toán băm |
| Sửa SRS nhiều chỗ dễ bỏ sót | Tài liệu mâu thuẫn, rubric phạt | Sau đợt 0, chạy một lượt rà toàn văn tìm "Streamlit", "JWT", "15 giây", "routes_" |
| `BackgroundTasks` chết giữa chừng | Bài kẹt ở RUNNING, hỏng NFR-11 | Dọn bài kẹt khi khởi động, đánh dấu FAILED kèm mã lý do |

---

## 10b. Quy ước ngôn ngữ trong mã nguồn

Chốt ngày 13/09/2026, áp cho toàn bộ repo.

| Thành phần | Ngôn ngữ | Lý do |
| --- | --- | --- |
| Định danh trong mã: tên hàm, biến, hằng, lớp, tệp | **Tiếng Anh** | Quy ước chung của ngành; công cụ, thư viện và thông báo lỗi đều bằng tiếng Anh |
| Chú thích và docstring | **Tiếng Anh** | Đi liền với mã |
| Tên lớp CSS, id phần tử, biến màu | **Tiếng Anh** | Cũng là định danh |
| Tên hàm kiểm thử | **Tiếng Anh** | Cũng là định danh |
| Thực thể trong sơ đồ lớp, ERD, deployment | **Tiếng Anh** | Ánh xạ một–một sang tên trong mã |
| **Chuỗi hiển thị cho người dùng** | **Tiếng Việt có dấu** | SRS bắt buộc; có test `test_reject_message_in_vietnamese` chặn |
| Đường dẫn URL (`/report/{id}`, `/login`, `/progress/{id}`) | **Tiếng Anh** | URL là bề mặt kỹ thuật; lập trình viên và công cụ đọc nó, không phải sinh viên |
| Nhãn nhóm trong tài liệu API (`student`, `teacher`, `admin`) | **Tiếng Anh** | Tài liệu cho lập trình viên |
| Sơ đồ use case và activity | **Tiếng Việt** | Mô tả yêu cầu cho hội đồng đọc, không phải thực thể kỹ thuật |
| Tài liệu trong `docs/` | **Tiếng Việt** | Sản phẩm nộp cho giảng viên hướng dẫn |

Ranh giới quyết định là **ai đọc**: máy và lập trình viên đọc thì tiếng Anh,
người dùng cuối và hội đồng đọc thì tiếng Việt.

**Đính chính ngày 13/09/2026.** Bản đầu của bảng này xếp đường dẫn URL vào nhóm
tiếng Việt, lập luận rằng URL là bề mặt sản phẩm. Lập luận đó sai: sinh viên
hầu như không bao giờ gõ URL, còn lập trình viên và công cụ thì đọc nó liên tục.
Đã đổi toàn bộ sang tiếng Anh: `/dang-nhap` → `/login`, `/ket-qua/{id}` →
`/report/{id}`, `/bai/{id}` → `/progress/{id}`, `/bai-cua-toi` →
`/my-responses`, `/quan-tri` → `/admin`, tham số `?tiep=` → `?next=`.

**Đính chính ngày 06/10/2026.** Hai màn thêm ngày 14/09 vẫn dùng đường dẫn tiếng
Việt, trái quy ước trên: `/tien-do` → `/my-progress`, `/review/thong-ke` →
`/review/stats`. Chế độ luyện tập (D023) dùng `/practice`, `/practice/{task_id}`,
`/practice/results/{id}`. Comment, docstring và tên test của D023 viết bằng tiếng
Anh theo đúng bảng trên; phần mã cũ còn comment và tên test tiếng Việt không dấu
sẽ được dọn trong một thay đổi riêng.

---

## 11. Không làm trong phạm vi này

- Không làm ứng dụng di động, không tối ưu cho màn hình điện thoại (NFR-15 chỉ đòi 1366×768).
- Không dùng WebSocket; trang tự làm mới là đủ.
- Không đăng nhập bằng tài khoản trường (SSO/LDAP). *Đăng nhập bằng Google đã đưa vào phạm vi ở D029, chỉ cho tài khoản đã liên kết, không tự tạo tài khoản, không lưu email.*
- Không đa ngôn ngữ; chỉ tiếng Việt.
- Không tự cấp chứng chỉ hay xuất chứng nhận CEFR.
- Không bảng xếp hạng, không điểm kinh nghiệm, không thành tựu theo điểm hay band (FR-W6, D032).
- Không cho sinh viên tự mua gói, không gói cá nhân, không quảng cáo hay lời mời mua trên trang của sinh viên (FR-W7, D034).
