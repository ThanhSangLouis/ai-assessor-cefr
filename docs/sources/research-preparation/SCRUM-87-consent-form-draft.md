# SCRUM-87 — Dự thảo phiếu thông tin và đồng thuận

**Trạng thái:** `DRAFT / REFERENCE_ONLY` · **Task:** SCRUM-87 · **Base implementation:** `82fe708`  
**Mục đích:** đưa một bản nháp có thể review và bảng ánh xạ với consent flow hiện tại. Đây chưa phải mẫu của trường, tư vấn pháp lý, ethics approval, hay căn cứ để mời người tham gia/thu audio.

> **Không phát hành/ký bản này khi các mục `[CẦN CHỐT]` còn trống.** Nguồn quy trình và chính sách hiện có vẫn `DRAFT`; phiếu cần được đối chiếu với mẫu trường, protocol và người duyệt có thẩm quyền.

## A. Bản thông tin cho người tham gia — bản nháp

### Thông tin nghiên cứu

| Mục | Nội dung cần hoàn thiện |
| --- | --- |
| Tên đề tài | `[CẦN CHỐT: tên đề tài theo hồ sơ đã duyệt]` |
| Đơn vị/nhóm thực hiện | `[CẦN CHỐT: tên chính thức và thành viên phụ trách]` |
| Người hướng dẫn | `[CẦN CHỐT: họ tên, chức danh, kênh liên hệ]` |
| Liên hệ câu hỏi/khiếu nại | `[CẦN CHỐT: nhóm nghiên cứu, GVHD và đầu mối ethics của trường]` |
| Phiên bản phiếu và ngày hiệu lực | `[CẦN CHỐT: phải khớp consent version được cấu hình trong hệ thống]` |

### Mục đích và việc người tham gia sẽ làm

Nhóm đang đánh giá một hệ thống hỗ trợ phản hồi bài nói tiếng Anh. Hệ thống có thể tạo kết quả tự động và giảng viên/người được giao có thể xem bài để kiểm tra theo protocol. Kết quả có thể sai; hệ thống không cấp chứng chỉ CEFR.

Người tham gia được mời thực hiện: `[CẦN CHỐT theo protocol SCRUM-88: số đề, nội dung, thời lượng, thời gian chuẩn bị, thiết bị và địa điểm]`. Không dùng thông số đề xuất ở tài liệu nguồn như lịch thu hay thời lượng cuối cùng cho tới khi protocol được duyệt.

### Dữ liệu và cách xử lý

Theo phạm vi được duyệt, hệ thống có thể nhận audio và thông tin vận hành cần thiết như task/version, mã response giả danh, thời điểm và trạng thái xử lý. Audio được gửi để hệ thống tạo phản hồi; phần mềm AI/ASR và người được phân quyền có thể xử lý/nghe audio theo protocol. Transcript, đặc trưng, điểm/ước lượng, rating và feedback chỉ được nêu tại đây sau khi owner xác nhận chính xác danh mục nào được thu và lưu.

| Thông tin bắt buộc trong bản phát hành | Giá trị đã được người có thẩm quyền chốt |
| --- | --- |
| Nơi lưu audio, bản chép lời và rating | `[CẦN CHỐT: vị trí/loại storage; không ghi đường dẫn máy cá nhân]` |
| Vai trò nào có quyền truy cập từng loại dữ liệu | `[CẦN CHỐT theo access matrix]` |
| Thời hạn lưu và thời điểm bắt đầu tính | `[CẦN CHỐT bởi GVHD/ethics; hiện chưa có retention được duyệt]` |
| Backup, bảo vệ dữ liệu và xử lý sự cố | `[CẦN CHỐT bằng cơ chế cụ thể]` |
| Bên nhận/xử lý ngoài nhóm hoặc dịch vụ cloud | `[CẦN CHỐT; không ghi “không chia sẻ” nếu chưa đối chiếu luồng thực tế]` |

Rủi ro có thể gồm cảm giác không thoải mái khi ghi âm, kết quả nhận dạng/chấm sai và rủi ro truy cập dữ liệu không phù hợp. Không cam kết hệ thống chính xác tuyệt đối hoặc an toàn tuyệt đối. Lợi ích trực tiếp: `[CẦN CHỐT; không hứa cải thiện điểm]`.

Việc tham gia có tự nguyện hay không và có ảnh hưởng tới điểm/quyền lợi môn học hay không: `[CẦN GVHD xác nhận theo bối cảnh tuyển người thực tế trước khi phát hành]`.

### Đồng thuận cốt lõi để tham gia luồng hiện tại

Các câu dưới đây là nội dung thông tin gắn với **một** consent version cốt lõi trên hệ thống, không phải các toggle độc lập trong implementation hiện tại:

- [ ] Tôi đã được cung cấp thông tin ở trên, có cơ hội đặt câu hỏi và hiểu mục đích, dữ liệu, cách xử lý cùng các giới hạn còn được nêu.
- [ ] Tôi hiểu việc nộp bài qua hệ thống hiện yêu cầu audio được thu/tải lên và xử lý để tạo phản hồi; nếu không đồng ý phần xử lý cốt lõi này, tôi không tiếp tục nộp bài qua luồng hiện tại.
- [ ] Tôi hiểu kết quả AI/ASR có thể sai và không phải chứng chỉ CEFR; người có phân quyền có thể xem bài theo protocol đã duyệt.
- [ ] Tôi đồng ý tham gia theo protocol và consent version ghi ở đầu phiếu.

**CẦN CHỐT trước khi dùng:** nếu nhóm muốn người tham gia có quyền chọn riêng “cho phép lưu audio” trong khi vẫn dùng một luồng không cần lưu audio, implementation hiện tại chưa hỗ trợ lựa chọn đó. Khi audio lưu là điều kiện của luồng hiện tại, phiếu phải mô tả đây là phần xử lý cốt lõi để tham gia; người không chấp thuận có thể không tham gia. Chủ dự án phải quyết định yêu cầu sản phẩm/consent trước khi tuyên bố giấy khớp hệ thống.

### Lựa chọn riêng về nghiên cứu thứ cấp

Checkbox hiện có trên hệ thống được mô tả là cho phép dùng **số liệu tổng hợp đã bỏ ID tài khoản cho nghiên cứu**. Nếu muốn giữ nguyên implementation hiện tại, nội dung giấy phải giới hạn cùng phạm vi đó:

- [ ] **Tùy chọn:** Tôi đồng ý cho phép dùng số liệu tổng hợp đã bỏ ID tài khoản cho mục đích nghiên cứu như đã mô tả ở trên.

Không chọn ô này không được diễn giải thành từ chối phần xử lý audio cần thiết cho bài đánh giá hiện tại. Ô này cũng **không** thể hiện sự đồng ý dùng lại raw audio cho một nghiên cứu khác hay chuyển audio/transcript/rating tới cloud/bên thứ ba. Các mục đích đó chưa có lựa chọn tương ứng trong UI; phải có quyết định, consent version và implementation phù hợp trước khi thực hiện.

### Dừng tham gia, rút đồng ý và dữ liệu đã thu

Người tham gia có thể dừng các lần nộp tiếp theo bằng thao tác rút consent hoặc liên hệ `[CẦN CHỐT: kênh liên hệ]`. Trong implementation hiện tại, rút consent đặt trạng thái thành `WITHDRAWN`, tắt `research_allowed` và chặn nộp mới. M08 Specification ghi rõ dữ liệu đã nộp **không tự bị xóa** khi rút consent trong scope W2.

Trước khi phát hành, phải bổ sung chính sách đã duyệt về việc xử lý audio/rating đã thu, phạm vi và cutoff yêu cầu xóa, dữ liệu đã dùng trong báo cáo tổng hợp, thời gian phản hồi và ngoại lệ nếu có: `[CẦN CHỐT bởi GVHD/ethics]`. Không hứa xóa toàn bộ dữ liệu hoặc khỏi model khi implementation/policy chưa bảo đảm.

### Xác nhận và chữ ký — bản giấy

| Người ký | Họ tên/chữ ký | Ngày |
| --- | --- | --- |
| Người tham gia | `[điền trên bản giấy được duyệt]` | `[ngày]` |
| Người giải thích phiếu (nếu mẫu trường yêu cầu) | `[điền trên bản giấy được duyệt]` | `[ngày]` |

Bản gốc có chữ ký được lưu tại `[CẦN CHỐT: kho hồ sơ ethics hạn chế truy cập]`; không commit bản có tên/chữ ký vào Git. Hệ thống hiện không nhận chữ ký giấy hay lưu tham chiếu tới bản scan.

## B. Ánh xạ phiếu giấy ↔ implementation hiện tại

| Nội dung phiếu | Hành vi/field hiện tại tại base `82fe708` | Kết quả đối chiếu / việc còn thiếu |
| --- | --- | --- |
| Consent cốt lõi và phiên bản | `/student/consent` hiển thị consent version; POST accept ghi state `ACTIVE`. M01/M08 yêu cầu active consent version trước submission. | Có thể map nội dung cốt lõi vào active consent version. Cần cấu hình và ghi version của bản giấy sao cho trùng version hiển thị ở UI. UI không ghi từng checkbox/câu xác nhận con. |
| Cho phép nghiên cứu tổng hợp | Checkbox `research_allowed`, bỏ chọn mặc định; server coi thiếu checkbox là `false`. Label UI giới hạn ở số liệu tổng hợp đã bỏ ID tài khoản. | Giữ đúng cùng phạm vi và mặc định không chọn. Không gán checkbox này cho raw audio reuse, cloud sharing hoặc consent tham gia cốt lõi. |
| Audio ghi/tải lên và lưu để xử lý | Upload/recording yêu cầu consent active; `StorageService` kiểm tra consent trước khi tạo response; system lưu audio/blob cho xử lý và review theo flow hiện tại. | Không có field `audio_storage_allowed`. Quyết định: mô tả storage là điều kiện cốt lõi hay mở task thay đổi contract/UI/backend rồi mới cập nhật phiếu. |
| Rút consent | POST `/student/consent/withdraw` ghi `WITHDRAWN`, `research_allowed=false`; submit mới bị từ chối với `CONSENT_VERSION_STALE`. | Map được hành vi chặn submission mới. Không tuyên bố dữ liệu cũ tự xóa; M08 ghi rõ không xóa dữ liệu đã có trong scope W2. Cần chính sách rút/xóa đã duyệt. |
| Retention, contact, access, signature giấy | Không được lựa chọn bởi `research_allowed` và không có các trường này trong consent UI hiện tại. | Phải lấy từ DMP/ethics đã duyệt và công bố trong phiếu. Bản giấy lưu ngoài hệ thống trong vùng được duyệt. |
| Nghiên cứu khác/cloud | UI hiện không có lựa chọn này; project data policy yêu cầu duyệt riêng. | Không coi là đã được đồng ý. Cần consent version/field/UI riêng trước khi sử dụng hoặc chuyển dữ liệu. |

## C. Điều kiện để chuyển khỏi `DRAFT`

1. Chốt protocol và phiên bản phiếu cùng task SCRUM-88; điền số bài, nội dung, thời lượng, địa điểm và thiết bị.
2. GVHD/trường xác nhận mẫu bắt buộc, contact, tuyển người, việc tham gia có ảnh hưởng điểm hay không và nơi lưu bản giấy.
3. Chốt data inventory, access roles, retention, withdrawal/deletion cutoff, backup và cloud policy; đối chiếu implementation thực tế.
4. Chủ dự án quyết định audio storage là xử lý bắt buộc trong bài hiện tại hay cần lựa chọn độc lập và thay đổi hệ thống.
5. Chốt một consent version duy nhất cho UI và giấy; review lại các route accept/withdraw, upload gate và thông tin người tham gia trên web trước khi phát hành.

**Chưa thực hiện:** ethics/legal review, ký phiếu, tuyển người, thu audio, test trên participant thật, hay thay đổi product code. Các trạng thái đó cần evidence riêng và không được suy ra từ bản nháp này.

## Nguồn implementation và SDD đã đối chiếu

- [Consent UI](../../../src/aicefr/api/templates.py) (`render_consent`), [consent routes/upload gate](../../../src/aicefr/api/wsgi.py), [ConsentService](../../../src/aicefr/auth/service.py).
- [M08 Requirement](../../sdd/modules/m08-identity-storage-admin/01-requirement.md), [M08 Specification](../../sdd/modules/m08-identity-storage-admin/03-specification.md), [M11 Requirement](../../sdd/modules/m11-identity-account/01-requirement.md), [M11 Status](../../sdd/modules/m11-identity-account/07-status.md).
- [Source consent checklist](17_consent_requirements.md), [source DMP](16_data_management_plan.md), [survey plan](KE_HOACH_KHAO_SAT.md).
