# Mở rộng hệ thống: điểm nghẽn theo thứ tự và cách vượt qua

Tài liệu này trả lời một câu hỏi cụ thể: **khi số người dùng tăng, cái gì hỏng
trước, và phải đổi gì.**

Nguyên tắc xuyên suốt: mỗi thứ sẽ phải thay đều nằm sau một **cổng** (port) khai
báo trong `src/aicefr/ports.py`. Tầng nghiệp vụ chỉ biết cổng, không biết công
nghệ. Nhờ vậy mỗi bước mở rộng là **thêm một bộ chuyển đổi**, không phải sửa lại
luồng xử lý.

---

## 1. Hiện tại chịu được bao nhiêu

| Thành phần | Giới hạn | Vì sao |
| --- | --- | --- |
| Chấm điểm | **2 bài cùng lúc** | `AICEFR_MAX_JOBS`, mặc định 2. Mỗi bài giữ một bản Whisper trong bộ nhớ |
| Thông lượng chấm | ~4–6 bài/phút với `large-v3-turbo` trên Apple Silicon | Đo thật: một bài 45 giây mất 10–15 giây |
| Đọc ghi dữ liệu | Hàng nghìn thao tác/giây | SQLite đã bật WAL, đọc không chặn ghi |
| Người dùng đồng thời | Vài chục người duyệt web thoải mái | Trang tĩnh, truy vấn nhẹ |
| Bản ghi giọng nói | Giới hạn bởi dung lượng đĩa | 25 MiB mỗi bài |

**Một lớp 40 sinh viên nộp bài cùng lúc**: tất cả nhận `202` trong vài trăm mili
giây, rồi hàng đợi xử lý dần. Bài cuối cùng xong sau khoảng 7–10 phút. Chấp nhận
được, vì màn hình theo dõi cho biết đang ở đâu.

**Ba lớp cùng lúc, hoặc cả khoa nộp trong một buổi**: không chịu được. Dưới đây
là thứ tự hỏng.

---

## 2. Điểm nghẽn theo đúng thứ tự sẽ gặp

### Nghẽn 1 — Chấm điểm, ở khoảng 200 bài mỗi giờ

Đây là nghẽn thật đầu tiên và nó đến sớm hơn mọi thứ khác, vì nhận dạng tiếng
nói nặng gấp hàng nghìn lần mọi thao tác khác trong hệ thống.

**Không cần đổi kiến trúc.** Tăng `AICEFR_MAX_JOBS` theo số lõi và bộ nhớ, hoặc
đổi sang mô hình nhỏ hơn. Chỉ khi một máy không đủ mới sang nghẽn 2.

### Nghẽn 2 — Một tiến trình, khi cần máy thứ hai

Đây là ranh giới kiến trúc thật sự. Ba thứ hỏng **cùng lúc** khi có instance thứ hai:

| Hỏng gì | Triệu chứng thực tế |
| --- | --- |
| Bản ghi nằm trên đĩa cục bộ | Máy A lưu, máy B phục vụ → trình phát trả 404, **lúc được lúc không**, tuỳ bộ cân bằng tải đẩy request sang đâu |
| Hàng đợi nằm trong tiến trình | Việc xếp ở máy A, máy B không thấy; khởi động lại là mất |
| Bộ đếm tần suất nằm trong bộ nhớ | "10 lần/phút" thành "10 lần/phút **mỗi máy**" — lớp bảo vệ yếu đi đúng lúc hệ thống lớn lên |

Cái thứ ba đáng chú ý: nó không chỉ là giới hạn mở rộng mà là **lỗi đúng sai**.

**Cách vượt qua — mỗi thứ là một bộ chuyển đổi mới, không sửa luồng:**

| Cổng | Hôm nay | Khi cần nhiều máy | Chạm vào gì |
| --- | --- | --- | --- |
| `BlobStore` | `LocalBlobStore` | `S3BlobStore` (MinIO, S3, R2) | một tệp mới trong `infra/` |
| `JobQueue` | `InProcessJobQueue` | `RedisJobQueue` + tiến trình worker | một tệp mới + một điểm khởi chạy |
| `RateLimiter` | `InMemoryRateLimiter` | `RedisRateLimiter` | một tệp mới |
| `ResponseStore` | `Repository` (SQLite) | `PostgresRepository` | một tệp mới |

Không endpoint nào đổi. Không `ResponseProcessor` nào đổi. Không test nghiệp vụ
nào đổi — `tests/test_ports.py` đã khẳng định từng bộ chuyển đổi thoả đúng cổng
của nó, nên bộ chuyển đổi mới chỉ cần qua chính những test đó.

**Bằng chứng cách làm này có tác dụng:** hàng đợi đã có **hai** bộ chuyển đổi
ngay từ bây giờ. `InlineJobQueue` chạy ngay tại chỗ cho kiểm thử,
`InProcessJobQueue` chạy trên nhóm luồng cho vận hành. Chọn bằng một biến môi
trường, `AICEFR_JOB_MODE`. Bộ chuyển đổi thứ ba dùng Redis lắp vào đúng chỗ đó.

### Nghẽn 3 — SQLite, ở khoảng vài chục nghìn bài

SQLite với WAL đi xa hơn nhiều người tưởng. Nó hỏng khi:

- cần **nhiều máy ghi** — một tệp không chia sẻ được qua mạng một cách an toàn;
- cần sao lưu liên tục hoặc bản sao chỉ đọc;
- một truy vấn nặng chặn việc ghi lâu hơn `busy_timeout`.

Lược đồ hiện tại dùng SQL thuần và kiểu dữ liệu phổ thông, nên chuyển sang
PostgreSQL là đổi chuỗi kết nối và vài câu lệnh `INSERT OR REPLACE`. **Không**
dùng ORM chính là thứ khiến việc này rẻ chứ không phải đắt.

### Nghẽn 4 — Mô hình chấm điểm

Ở quy mô lớn hơn nữa, mỗi worker giữ một bản mô hình là lãng phí. Lúc đó tách
việc chấm thành một dịch vụ riêng, và `Scorer` đã là một cổng nên tầng nghiệp vụ
không biết nó gọi qua mạng hay gọi trong tiến trình.

---

## 3. Những thứ CỐ Ý không làm sẵn

Nói rõ để khỏi bị hiểu là bỏ sót.

**Không dùng Redis hay Celery ngay từ đầu.** Một tiến trình phục vụ 60–90 sinh
viên trong một học kỳ là tải rất nhẹ. Thêm một dịch vụ nữa nghĩa là thêm một thứ
phải dựng, phải giám sát, phải giải thích, và thêm một cách hỏng mới. Cái giá
đúng phải trả bây giờ là **khai báo cổng**, không phải hiện thực bộ chuyển đổi
chưa cần tới.

**Không dùng PostgreSQL ngay.** Cùng lý do, và SQLite còn có một ưu điểm thật ở
giai đoạn này: toàn bộ dữ liệu nằm trong một tệp, sao lưu và khôi phục bằng một
lệnh.

**Không dùng ORM.** ORM làm cho việc đổi cơ sở dữ liệu *trông* dễ hơn nhưng
thường làm nó khó hơn: lược đồ bị sinh ra thay vì được thiết kế, và những truy
vấn khó nhất vẫn phải viết tay. SQL thuần trên kiểu dữ liệu phổ thông chuyển
được thẳng.

**Không dùng Kubernetes.** Ở quy mô này, `docker compose` trên một máy đã đủ, và
cấu hình đã sẵn sàng cho nhiều bản sao khi ba bộ chuyển đổi ở nghẽn 2 xong.

---

## 4. Những thứ KHÔNG rẻ để đổi, nói thẳng

Không phải mọi thứ đều nằm sau một cổng.

| Thứ | Vì sao khó đổi | Giảm nhẹ thế nào |
| --- | --- | --- |
| **19 đặc trưng** | Mô hình được khớp trên đúng bộ này. Thêm hay bớt một đặc trưng là phải huấn luyện lại | `feature_version` ghi trong mọi báo cáo, nên biết bản nào sinh ra số nào |
| **Cặp mô hình ↔ hệ nhận dạng** | Đổi hệ nhận dạng làm lệch đặc trưng có hệ số lớn nhất | Đã có lớp chặn: hiện vật khai `trained_with`, runtime khác thì gắn cờ và chuyển giảng viên |
| **Ngưỡng band** | Nằm trong hiện vật, nhưng đổi là đổi ý nghĩa mọi kết quả cũ | `band_map_version` ghi trong mọi báo cáo |
| **Lược đồ `report_json`** | Báo cáo cũ đã lưu dạng JSON theo lược đồ lúc đó | `config_version` ghi trong mọi hàng |

Điểm chung: chúng khó đổi vì **ý nghĩa của kết quả phụ thuộc vào chúng**, không
phải vì mã viết tệ. Cách xử lý đúng không phải là trừu tượng hoá thêm, mà là
**ghi phiên bản vào mọi kết quả** — và điều đó đã làm.

---

## 5. Bảng tra nhanh

| Triệu chứng | Nghẽn | Việc cần làm |
| --- | --- | --- |
| Bài xếp hàng lâu, máy còn rảnh | 1 | Tăng `AICEFR_MAX_JOBS` |
| Bài xếp hàng lâu, máy đã đầy tải | 1 | Thêm lõi, hoặc đổi mô hình nhận dạng nhỏ hơn |
| Cần máy thứ hai | 2 | Làm `S3BlobStore`, `RedisJobQueue`, `RedisRateLimiter` |
| `database is locked` xuất hiện | 3 | Chuyển sang PostgreSQL |
| Mỗi worker ngốn vài GB RAM | 4 | Tách dịch vụ chấm điểm riêng |
