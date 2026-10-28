# Đề xuất mô hình gói dịch vụ và cơ chế nâng cấp

| Thuộc tính | Giá trị |
| --- | --- |
| Trạng thái | Mô hình bán cho trường: **ĐỀ XUẤT** — chờ chủ dự án và GVHD (D033, PROPOSED). Luồng mua gói và thanh toán: **đã làm** theo yêu cầu của chủ dự án ngày 07/10/2026 (D034, mục 8), tắt mặc định, không thu tiền thật |
| Ngày | 07/10/2026 |
| Người lập | Võ Thanh Sang |
| Đề tài | Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2 |
| Căn cứ | SRS 1.6 (BR-01..BR-04, BR-29..BR-33, C-09, mục 1.1, mục 3.9g), `docs/plan/KE_HOACH_KHAO_SAT.md` §9 và Phụ lục A, `docs/license_inventory.md`, `AGENTS.md` |

## Tóm tắt

**Khuyến nghị: bán gói cho trường, sinh viên không trả tiền.** "Premium" là gói của trường, tính theo **số sinh viên** — số tài khoản sinh viên trường được mở cùng lúc; tài khoản giảng viên và quản trị không tính. Thang ba bậc, mỗi bậc thêm một thứ trường nhìn thấy được:

| | **Miễn phí** | **Chuẩn** | **Nâng cao** |
| --- | --- | --- | --- |
| Dành cho | Một lớp bắt đầu dùng | Một khoa | Trường, trung tâm ngoại ngữ cần đảm bảo chất lượng |
| Số sinh viên | Tối đa 30 | Theo số mua | Theo số mua |
| Sinh viên: bài đánh giá có bằng chứng, lộ trình, ôn tập, thành tựu, tiến độ, tải dữ liệu | ✓ | ✓ | ✓ |
| Giảng viên: hàng đợi duyệt, sửa kết quả của máy có lý do, lộ trình mẫu | ✓ | ✓ | ✓ |
| **Soạn lộ trình riêng của trường** (bài học, giọng mẫu, hình, nhập/xuất) | — | ✓ | ✓ |
| **Thống kê lớp và theo dõi từng bài học** | — | ✓ | ✓ |
| **Chấm mù kép và báo cáo đồng thuận giữa giảng viên** | — | — | ✓ |
| Bài đánh giá dự kiến mỗi sinh viên mỗi tháng (chỉ để cảnh báo) | 2 | 4 | 8 |

Trường mới bắt đầu bằng **Dùng thử 30 ngày đủ tính năng**, rồi về Miễn phí. Trả theo năm học giảm 15%. Việc học của sinh viên như nhau ở mọi gói — không bao giờ có bài học, báo cáo hay dữ liệu nào nằm sau tường thu phí.

**Ba việc phải xong trước khi thu đồng nào**, đều nằm ngoài đồ án:

1. **Giấy phép của mô hình chấm.** Mô hình chấm học từ Speak & Improve theo giấy phép nghiên cứu, phi thương mại, không phát tán (`docs/license_inventory.md`; `KE_HOACH_KHAO_SAT.md` §9). Bán dịch vụ dùng mô hình đó cần bên cấp phép đồng ý, hoặc một mô hình học lại trên dữ liệu được phép dùng thương mại.
2. **Pháp nhân.** Ký hợp đồng với trường, xuất hoá đơn, mở cổng thanh toán đều cần một doanh nghiệp hoặc hộ kinh doanh; bán trực tuyến còn phải thông báo website thương mại điện tử với Bộ Công Thương.
3. **Đồng thuận riêng cho người dùng dịch vụ.** Phiếu đồng thuận hiện nay chỉ cho phép dùng bản ghi để **kiểm định hệ thống** (Phụ lục A). Người dùng trả phí cần văn bản khác, và dữ liệu nghiên cứu không bao giờ thành dữ liệu dịch vụ.

**Vì sao khớp đề tài.** Tên đề tài nói hệ thống phục vụ **sinh viên đại học**; người cấp tài khoản cho sinh viên — và chịu trách nhiệm chuẩn đầu ra ngoại ngữ của họ — là **trường**. Mô hình bán cho trường giữ nguyên tên đề tài, đối tượng, phạm vi đo; không biến sản phẩm thành ứng dụng bán lẻ, không biến nó thành LMS.

---

## 1. Hệ thống hiện nay đã chọn sẵn ai là khách hàng

Sáu quy tắc đang chạy trong mã và tài liệu quyết định phần lớn câu trả lời:

| Quy tắc | Nói gì | Hệ quả cho việc thu tiền |
| --- | --- | --- |
| BR-03 | Không tự đăng ký; quản trị viên cấp mỗi tài khoản kèm vai trò | Người mua tự nhiên là đơn vị có quản trị viên: trường, khoa, trung tâm ngoại ngữ. Bán lẻ cho cá nhân phải mở tự đăng ký |
| BR-02 | Hệ thống chỉ biết bút danh; không email, số điện thoại, họ tên | Thanh toán cá nhân cần người mua thật (hoá đơn, đối soát, hoàn tiền) — đưa dữ liệu cá nhân vào hệ thống đang cố ý không có |
| BR-01, C-09 | Không cấp chứng chỉ, không quyết định đậu/rớt; giảng viên quyết định | Không có gì kiểu "chứng chỉ", "điểm chính thức", "chấm có cam kết" để bán |
| BR-04 + đạo đức khảo sát | Tham gia tự nguyện, không gắn điểm học phần, người tham gia không bị thiệt | Không khoá tính năng với người tham gia; không thể có hai nhóm người tham gia hưởng hai mức khác nhau |
| Giấy phép dữ liệu | Speak & Improve: nghiên cứu, phi thương mại, không phát tán | Mọi phương án có doanh thu thật đều vướng — xem Tóm tắt |
| `AGENTS.md` | Không thêm dịch vụ trả phí hay API ngoài khi chưa giải thích và được đồng ý | Cổng thanh toán là API ngoài; trong đồ án dùng cổng thử, VNPay chỉ bật khi có pháp nhân |

Nhu cầu thật thì ở phía trường: sinh viên phải đạt chuẩn đầu ra ngoại ngữ, còn trường thiếu công cụ để sinh viên **luyện nói thường xuyên** và để giảng viên **theo dõi cả lớp** mà không phải nghe từng bài. Hệ thống không thay kỳ đánh giá chính thức và không quy đổi sang bậc của Khung năng lực ngoại ngữ 6 bậc — điều đã cân nhắc và loại ở `HUONG_PHAT_TRIEN_TIEP.md` §3.3.

## 2. Ba phương án

**A — Gói cho trường (B2B).** Trường hoặc khoa trả theo số sinh viên mỗi học kỳ hay năm học. Sinh viên không trả gì, không thấy lời mời mua nào.

**B — Freemium cho cá nhân (B2C).** Ai cũng dùng miễn phí ở mức giới hạn; trả tiền tháng hoặc năm để mở thêm, như Duolingo, ELSA Speak, Speak đang làm với người học cá nhân.

**C — Lai.** A là kênh chính; ngoài ra trung tâm ngoại ngữ của trường bán gói cá nhân như một phần học phí khoá luyện nói mà họ vẫn thu, rồi phát **mã kích hoạt**. Hệ thống chỉ ghi quyền dùng, không đụng tới tiền.

| Tiêu chí | A — Trường | B — Cá nhân | C — Lai |
| --- | --- | --- | --- |
| Khớp tên đề tài và đối tượng | **Khớp**: sinh viên của một trường | Lệch: người học bất kỳ | Khớp |
| BR-02, BR-03 (bút danh, không tự đăng ký) | **Giữ nguyên** | Phải bỏ cả hai | Giữ nguyên (mã kích hoạt gắn bút danh) |
| Đạo đức nghiên cứu | **Không đụng**: mọi người học cùng một mức | Người tham gia trả và không trả được đối xử khác nhau | Phải miễn trừ người tham gia khỏi gói cá nhân |
| Công bằng giữa sinh viên một lớp | **Như nhau** | Người có tiền luyện được nhiều hơn | Như B, trong phạm vi khoá học |
| Pháp lý khi bán thật | Hợp đồng + hoá đơn; cổng thanh toán để gia hạn nhanh | Cổng thanh toán, thông báo website, bảo vệ người tiêu dùng, hoàn tiền | Trung tâm vẫn thu như hiện nay |
| Dữ liệu cá nhân mới | Tên tổ chức, người đại diện ký hợp đồng (ngoài hệ thống) | Người mua, giao dịch | Không |
| Việc phải làm trong mã | Vừa: gói, giấy phép, giới hạn, trang quản trị, thanh toán | Lớn: tự đăng ký, thanh toán, khôi phục mật khẩu qua email, gói cá nhân | A + mã kích hoạt |
| Sức mua | Ngân sách của khoa, thường theo năm học | Từng người, cạnh tranh trực tiếp với ứng dụng miễn phí hoặc rẻ | A cộng một phần nhỏ |
| Rủi ro lớn nhất | Chu kỳ bán dài | Lệch đề tài; vi phạm ba quy tắc đang có | Phức tạp hoá để thu thêm ít |

**Chọn A.** C để ngỏ cho sau đồ án, khi đã có trường dùng thật và trung tâm ngoại ngữ đề nghị. B loại: muốn làm phải viết lại BR-02, BR-03, đạo đức khảo sát và cả đối tượng của đề tài.

## 3. Vì sao thang này đáng nâng cấp

Mỗi bậc trả lời một việc trường thật sự cần làm, và không bậc nào lấy đi thứ bậc dưới có:

- **Miễn phí → Chuẩn: dạy theo chương trình của chính khoa.** Lộ trình mẫu đủ để bắt đầu, nhưng mỗi khoa có chủ đề, giáo trình và đề riêng. Gói Chuẩn cho giảng viên soạn lộ trình của khoa (bài học từ đoạn văn mẫu, từ khoá, giọng mẫu tự ghi, hình) và **thấy lớp đang vướng ở bài nào, bước nào, từ nào** mà không phải nghe từng bản ghi. Đây là phần tiết kiệm thời gian của giảng viên — thứ khoa sẵn sàng trả.
- **Chuẩn → Nâng cao: chứng minh được điểm của giảng viên nhất quán.** Chấm mù kép và báo cáo đồng thuận (kappa, ICC, khoảng tin cậy theo người nói) là bằng chứng đảm bảo chất lượng mà một trung tâm ngoại ngữ cần cho kiểm định chương trình — và cũng là công cụ nghiên cứu của chính đồ án.
- **Số sinh viên** tăng theo quy mô; **số bài đánh giá dự kiến** chỉ để khoa biết mình đang dùng bao nhiêu, vượt thì cảnh báo, không bao giờ chặn sinh viên.

Những thứ **không** bán, dù bán được: việc học của sinh viên (BR-29), cách đăng nhập (đăng nhập Google có ở mọi gói), dữ liệu của trường (bản xuất nghiên cứu, báo cáo, CSV không bị khoá), và mọi thứ đã bắt đầu (BR-31).

**Giá.** Giá trên giao diện là **giá minh hoạ** đặt bằng biến môi trường (Chuẩn 10.000 đ, Nâng cao 15.000 đ mỗi sinh viên mỗi tháng), không phải bảng giá. Một con số thật cần:

- **Chi phí** = máy chủ + vận hành + hỗ trợ + cập nhật mô hình, chia cho số sinh viên. Chi phí máy chủ phụ thuộc thời gian máy xử lý một bài đánh giá và một lượt luyện trên cấu hình dự kiến — đo bằng pipeline thật trên bộ bản ghi thử, như `tools/repeatability_bench.py` đã chạy; hiện **chưa đo**.
- **Mức trả được** hỏi trực tiếp khoa hoặc trung tâm ngoại ngữ sau đợt dùng thử, không đưa vào phiếu khảo sát sinh viên của đồ án.

## 4. Giải pháp kỹ thuật (đã làm — chi tiết ở SDD 1.5, mục 4.15 và ADR-11)

- **Tắt mặc định.** Mọi thứ chỉ chạy khi bật `AICEFR_BILLING`. Bản triển khai chạy khảo sát của đồ án để tắt: không giới hạn gì, như trước (BR-30).
- **Gói đang dùng** tính từ các giấy phép theo ngày: giấy phép bắt đầu sau cùng có hiệu lực; gói trả tiền hết hạn còn 14 ngày ân hạn rồi về Miễn phí; dùng thử bắt đầu một lần ở lần đầu có người hỏi tới gói.
- **Chỗ áp gói** — chỉ việc mới (BR-31): tạo, bật lại, đổi vai trò tài khoản sinh viên vượt số cho phép (409 kèm số liệu); soạn lộ trình, xem thống kê lớp, tạo đợt chấm mù khi gói chưa có (403 kèm gói mở nó). Trang soạn lộ trình nói trước khi giảng viên gõ.
- **Báo giá**: mua mới từ hôm nay; gia hạn nối tiếp; nâng cấp từ hôm nay trừ phần chưa dùng theo ngày; hạ gói từ khi gói hiện tại kết thúc; 12 tháng giảm 15%; phần phải trả dưới 10.000 đ được miễn, đơn 0 đ kích hoạt ngay.
- **Thanh toán qua một cổng** (`PaymentGateway`): **cổng thử** trong ứng dụng — trang thanh toán ghi rõ không có tiền thật, ký kết quả như cổng thật — và **VNPay 2.1.0** bật bằng biến môi trường. Kết quả chỉ được tin khi đúng chữ ký và số tiền, ghi nhận một lần dù trình duyệt và máy chủ của cổng cùng báo, mọi thông điệp lưu để đối soát, thanh toán tới muộn vẫn được ghi nhận (BR-33). Không có số thẻ, tài khoản ngân hàng hay tên người trả nào trong hệ thống (BR-32).
- **Mã giấy phép** cho trường trả theo hợp đồng: `AICEFR1.<nội dung>.<chữ ký>`, HMAC-SHA256. Giới hạn: người giữ chuỗi bí mật ký được, nên với bản cài tại trường cần chữ ký bất đối xứng (Ed25519, thêm thư viện `cryptography`) — chưa làm vì cần duyệt phụ thuộc mới.
- **Biên nhận** in được, ghi rõ không phải hoá đơn giá trị gia tăng.

## 5. Lộ trình

| Bước | Việc | Trạng thái |
| --- | --- | --- |
| 0 | Chủ dự án chọn mô hình; trình GVHD tài liệu này | Đang chờ |
| 1 | Gói, giấy phép, chỗ áp gói, tab Gói dịch vụ, test ba tầng, tài liệu | **Xong** (D034) |
| 2 | Cổng `PaymentGateway`, cổng thử, VNPay, đơn hàng, biên nhận | **Xong** (D034) |
| 3 | Sau đồ án, trước khi thu tiền: mô hình không vướng giấy phép phi thương mại; pháp nhân, hợp đồng mẫu, hoá đơn; đồng thuận cho người dùng dịch vụ; đăng ký VNPay thật; chữ ký Ed25519 cho mã giấy phép | Ngoài đồ án |

## 6. Câu hỏi GVHD có thể đặt, và câu trả lời

**Thêm thu phí có làm lệch đề tài không?** Không. Đóng góp của đồ án vẫn là hệ thống AI hỗ trợ đánh giá có bằng chứng, có giảng viên quyết định. Gói dịch vụ là phần vận hành sản phẩm, không thêm gì vào phép đo và không đổi đối tượng.

**Sinh viên tham gia khảo sát có bị thiệt không?** Không. Bản chạy khảo sát để tắt thu phí; người đồng thuận nghiên cứu không bị tính vào số bài dự kiến (BR-30); và ở mọi gói sinh viên học như nhau, không thấy lời mời mua.

**Dữ liệu của sinh viên có bị bán không?** Không. Dữ liệu chỉ dùng như phiếu đồng thuận đã ghi; gói dịch vụ bán quyền dùng phần mềm cho trường, không bán dữ liệu.

**Mô hình học từ dữ liệu phi thương mại thì bán thế nào?** Trong đồ án không bán: cổng mặc định là cổng thử, không có tiền thật. Thu tiền thật chỉ sau khi có giấy phép thương mại từ bên cấp dữ liệu, hoặc một mô hình học lại trên dữ liệu được phép.

**Sao lại có VNPay?** Để luồng thanh toán là luồng thật của một cổng Việt Nam chứ không phải một nút giả. Bộ chuyển đổi VNPay chỉ bật khi có mã website và chuỗi bí mật VNPay cấp cho một pháp nhân; test dựng và ký thông điệp đúng như VNPay mô tả, không gọi VNPay.

## 7. Việc còn chờ chủ dự án

1. Xác nhận mô hình bán cho trường (A) để D033 thành APPROVED, hoặc chọn B hay C.
2. Giá thật, sau khi đo chi phí máy chủ và hỏi khoa.
3. Có thêm thư viện `cryptography` để ký mã giấy phép bằng Ed25519 không.

## 8. Đã làm ở D034, và chỗ đổi so với bản đề xuất đầu

Chủ dự án yêu cầu ngày 07/10/2026: "phải có thanh toán để làm thêm luồng payment luôn", rồi "tìm ra cách upgrade xứng đáng ... slot gì tôi chưa hiểu". Bản đầu của đề xuất tính theo "chỗ" và để gói dùng thử có chấm mù kép mà gói Chuẩn không có, nên mua gói lại thấy mất bớt. Đã đổi:

| Bản đề xuất đầu | Đã làm |
| --- | --- |
| "Số chỗ" | **Số sinh viên** — số tài khoản sinh viên mở cùng lúc |
| Thử nghiệm, Chuẩn, Nâng cao; hết hạn thì khoá tạo mới | **Miễn phí** (vĩnh viễn, 30 sinh viên) → **Chuẩn** → **Nâng cao**, mỗi bậc chỉ thêm; **Dùng thử** 30 ngày rồi về Miễn phí; gói trả tiền có ân hạn rồi về Miễn phí |
| Chuẩn và Nâng cao chỉ khác ở chấm mù | Chuẩn mở **soạn lộ trình riêng** và **thống kê lớp**; Nâng cao thêm **chấm mù kép** |
| Giới hạn tên miền Google ở gói Chuẩn | Đăng nhập Google có ở **mọi** gói: không khoá cách người ta đăng nhập |
| Giá theo học kỳ | 6 hoặc 12 tháng, **12 tháng giảm 15%**; nâng cấp được trừ phần chưa dùng |
| Lưu giấy phép ở `app_config` | Bốn bảng `billing_*` riêng, có lịch sử đơn và thông điệp của cổng |
| Thanh toán mô phỏng `MockGateway` | **Cổng thử** ký kết quả như cổng thật + **VNPay 2.1.0** thật sự, bật bằng biến môi trường |
| Một cổng mỗi bản triển khai | **Nhiều cổng một lúc** (D035): cổng thử, VNPay, **Stripe** (chế độ thử) và **MoMo** (môi trường thử); quản trị viên chọn cổng cho từng đơn; cổng thu tiền thật chỉ chạy khi bật `AICEFR_PAYMENTS_LIVE`. Stripe chưa mở tài khoản bán hàng cho doanh nghiệp tại Việt Nam, nên bán thật vẫn đi qua VNPay hoặc MoMo |
