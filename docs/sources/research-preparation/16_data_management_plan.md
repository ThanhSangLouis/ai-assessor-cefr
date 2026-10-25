# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

## 16. Kế hoạch quản lý dữ liệu

| Thuộc tính | Giá trị |
| --- | --- |
| Tuần | W1 - Nền tảng đo lường, phạm vi và điều kiện nghiên cứu |
| Trạng thái | DRAFT - cần thực hiện và xác nhận |
| Người phụ trách | SV3 |
| Người duyệt | GVHD + phụ trách đạo đức |
| Phiên bản | 1.1 |
| Ngày cập nhật | 02/09/2026 |

## 1. Mục đích

Quản lý dữ liệu theo nguyên tắc tối thiểu, tách danh tính, truy cập theo vai trò, có version và có thể rút/xóa.

Cơ sở pháp lý cần reviewer của trường xác nhận: [Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15](https://vanban.chinhphu.vn/?classid=1&docid=214590&pageid=27160&typegroup=) và [Nghị định 356/2025/NĐ-CP](https://vanban.chinhphu.vn/?classid=0&docid=216387&pageid=27160), cùng có hiệu lực 01/01/2026 (kiểm tra 02/09/2026). Đây không phải tư vấn pháp lý.

## 2. Danh mục dữ liệu

| Loại | Ví dụ | Nhạy cảm | Nơi lưu | Ai truy cập |
| --- | --- | --- | --- | --- |
| Identity/contact | Họ tên, email, MSSV nếu cần liên hệ | Cao | Identity vault riêng | SV3 được ủy quyền + GVHD |
| Consent | Phiếu đồng ý, ngày, version | Cao | Ethics folder riêng | SV3 + GVHD |
| Audio | Response WAV | Cao; là dữ liệu cá nhân, và có thể trở thành dữ liệu sinh trắc học nếu được xử lý để xác định cá nhân | Encrypted local storage | Nhóm theo quyền + rater |
| Transcript | ASR/manual text | Có thể chứa PII ngẫu nhiên | Model workspace đã mã hóa | Nhóm nghiên cứu |
| Rating | Rater scores/comments | Nội bộ | Research DB | SV2 + adjudicator |
| Metadata | task/prompt/device/QC | Trung bình | Research DB | Nhóm nghiên cứu |
| Features/models | Numeric features, weights | Thấp hơn nhưng vẫn controlled | Model workspace | SV1/SV2 |
| Reports | Estimated band/evidence | Giáo dục cá nhân | Product DB | Sinh viên tương ứng + GV |

## 3. Định danh

- `participant_id`: mã ngẫu nhiên, không chứa MSSV/ngày sinh.
- `response_id`: UUID/ngẫu nhiên độc lập; quan hệ với participant/task chỉ nằm trong manifest được kiểm soát.
- Không đưa `participant_id`, `response_id` hoặc tên file theo mẫu có thể suy ra MSSV/ngày sinh/lớp.
- `speaker_id` trong workflow chia fold là alias giả danh ổn định của `participant_id`, không phải speaker-identification biometric và không chứa danh tính trực tiếp.

## 3.1. Data contract tối thiểu tại boundary

| Artifact | Trường truy vết bắt buộc |
| --- | --- |
| Response manifest | `participant_id`, `speaker_id`, `response_id`, `task_id`, `audio_id`, `prompt_version`, `consent_version`, `qc_status` |
| ASR artifact | `response_id`, `asr_model`, `transcript_version`, timestamps/confidence, quality flags |
| Feature artifact | `response_id`, `feature_version`, input artifact hashes, extractor config/version |
| Rating artifact | `response_id`, `rater_id` giả danh, `rubric_version`, criterion/overall, `evidence_ids`, rating status |
| Model output | `response_id`, `model_version`, `calibration_version`, probabilities, missing status, `review_reason`, `evidence_ids` |
| Feedback/profile | `participant_id`, source `response_id`, rubric/model/calibration/prompt versions, evidence refs, `teacher_verified`, review audit ref |

Không xóa/đổi nghĩa field âm thầm. Breaking change phải cập nhật schema, migration/sample, docs và test trong cùng thay đổi.
- Bảng nối danh tính lưu riêng, mã hóa và không commit.
- Rater chỉ thấy response ID cần thiết.

## 4. Cấu trúc lưu trữ

```text
secure_identity/        # ngoài model workspace
  identity_map.enc
  consent/
research_data/
  raw_audio/
  asr/
  manual_transcripts/
  ratings_raw/
  adjudication/
  metadata/
  folds/
artifacts/
  features/
  models/
  reports/
```

Các tên trên là logical roots, không phải đường dẫn máy cá nhân. Trước collection, cấu hình phải ánh xạ chúng tới hai vùng đã được phê duyệt:

- `identity_root`: ngoài repository và ngoài model workspace, chỉ identity custodian/GVHD có quyền.
- `research_root`: encrypted local volume cho dữ liệu giả danh; ứng dụng chỉ nhận đường dẫn qua config/env.
- Encryption at rest, backup target và nơi giữ recovery key phải được ghi bằng sản phẩm/cơ chế cụ thể trong biên bản kiểm tra; câu “ổ đĩa có mã hóa” chưa đủ bằng chứng.

## 5. Access control

| Vai trò | Identity | Audio | Transcript | Rating | Model |
| --- | --- | --- | --- | --- | --- |
| SV1 | Không | Có mã hóa | Có | Chỉ khi phân tích | Có |
| SV2 | Không | Khi cần error analysis | Có | Có | Có |
| SV3 | Có giới hạn | Có để vận hành | Có giới hạn | Không sửa | API/report |
| Rater | Không | Bài được giao | Theo protocol | Chỉ rating của mình trước khóa | Không |
| Adjudicator | Không | Ca bất đồng | Theo protocol | Hai rating sau vòng độc lập | Không |

## 6. Retention và deletion

- Thời hạn lưu phải được ethics/GVHD chốt và ghi đúng trong consent.
- Giá trị hiện tại: `[CẦN PHÊ DUYỆT]`; không dùng mốc 12 tháng trong đề cương như chính sách đã duyệt.
- Khuyến nghị đưa ra G1/ethics: 12 tháng sau ngày bảo vệ, sau đó xóa identity map và xử lý research artifacts theo protocol đã duyệt. Đây là `PROPOSED`, không có hiệu lực cho đến khi DMP và consent được duyệt.
- Khi rút: xác minh participant ID, xác định dữ liệu có thể xóa, ghi deletion log.
- Không hứa xóa khỏi mô hình đã phát hành nếu quy trình kỹ thuật không bảo đảm; phải mô tả rõ thời điểm cutoff.
- Sau dự án: xóa identity map trước hoặc theo lịch đã duyệt; archive dữ liệu mã hóa cần thiết cho reproducibility theo quyền.

## 7. Backup và integrity

- Hai bản sao mã hóa ở hai thiết bị/vị trí được duyệt.
- Hash cho dataset snapshot.
- Dataset version chỉ tăng, không ghi đè raw.
- Fold assignment khóa và lưu checksum.
- Mỗi dataset/fold/artifact snapshot có version, checksum, created_at, owner và provenance; không ghi đè raw data.
- Log chỉ chứa ID giả danh, version, trạng thái, timing và reason code; cấm audio/transcript/PII trong log.

## 8. Incident response

1. Ngừng truy cập/chia sẻ.
2. Ghi thời gian, dữ liệu, người ảnh hưởng.
3. Báo GVHD/phụ trách theo protocol.
4. Thu hồi quyền/khóa credential.
5. Đánh giá nghĩa vụ thông báo người tham gia.
6. Ghi corrective action.

## 8.1. Test plan bắt buộc trước collection

Chỉ dùng dữ liệu synthetic; không dùng tên, audio hoặc transcript thật.

| Test | Điều kiện đạt |
| --- | --- |
| Tách danh tính | Research workspace không thể suy trực tiếp danh tính từ filename/ID; identity map chỉ ở `identity_root` |
| Quyền truy cập | Tài khoản/role không được cấp quyền bị từ chối khi đọc identity/audio/rating tương ứng |
| Log privacy | Log không chứa audio bytes, transcript, email, MSSV hoặc tên; chỉ có pseudonymous ID/version/status/timing/reason code |
| Withdrawal | Từ một `participant_id` synthetic, tạo được danh sách artifact cần xử lý, thực hiện theo cutoff và tạo deletion log không chứa PII |
| Raw immutability | Pipeline không ghi đè raw audio/dataset snapshot; snapshot mới có version/checksum mới |
| Backup restore | Khôi phục được một snapshot synthetic và đối chiếu checksum; recovery key không nằm trong repository |
| Boundary schema | Thiếu version/evidence/status bắt buộc bị reject bằng reason code, không tạo điểm mặc định |

Kết quả test phải ghi ngày, người chạy, config version, expected/actual và bằng chứng không nhạy cảm. Checklist Mục 10 chỉ được đánh dấu sau khi chạy thật.

## 9. Không được làm

- Upload audio lên dịch vụ ngoài chưa được consent/duyệt.
- Upload transcript/rating/metadata có thể nhận dạng lên cloud/API nếu chưa có data map, consent phù hợp và phê duyệt; local-first là mặc định.
- Đưa PII/audio vào Git.
- Dùng dữ liệu để suy luận thuộc tính nhạy cảm.
- Chia sẻ dataset công khai khi chưa có quyền và de-identification review.

## 10. Sign-off checklist

- [ ] Nơi lưu cụ thể đã chốt.
- [ ] Access owner đã chốt.
- [ ] Retention period đã chốt.
- [x] Withdrawal/deletion workflow đã test trên dữ liệu giả; xem `26_synthetic_dmp_test_report.md`.
- [ ] Backup và encryption đã xác minh.
- [ ] Encryption/key management cụ thể đã được chỉ định và test; không chỉ ghi chung “encrypted”.
- [x] Dữ liệu synthetic đã đi qua withdrawal/deletion test và có deletion log không chứa PII; script tự cleanup sau lần chạy.
