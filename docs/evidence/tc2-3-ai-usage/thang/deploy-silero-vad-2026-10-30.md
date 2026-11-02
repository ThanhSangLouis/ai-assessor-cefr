# Bật Silero trên bản deploy — 30/10/2026

- Base: `46ee31c9`; nhánh `codex/fix-deploy-silero-vad`.
- Yêu cầu: build image mới, tạo PR, merge bằng merge commit vào main rồi chờ người review. Chỉ dẫn sau cùng: giữ nguyên faster-whisper large-v3, chỉ bật VAD=1.
- Phạm vi: Compose build speech với VAD=1; Dockerfile cài torch CPU cho Silero; CI build và kiểm Silero offline; regression test cấu hình và hướng dẫn kiểm tra trên máy chủ.
- Whisper giữ mặc định large-v3. Không thay mã ASR, model chấm, ngưỡng OOD hay logic quy đổi band.
- Ảnh người dùng cho thấy số đoạn/phút rất cao; thiếu Silero hoặc lỗi nạp Silero có thể làm code fallback EnergyVad. Chưa kiểm tra runtime EC2 hoặc audio gốc, không kết luận chắc chắn nguyên nhân của bài cụ thể.
- Cảnh báo ASR khác model huấn luyện vẫn có thể còn khi dùng large-v3. Bật Silero không bảo đảm mọi bài đều có điểm hoặc hết REVIEW_REQUIRED.
- Review: đã rà thủ công diff theo chỉ dẫn tiếp tục của người dùng; skill ai-code-review không có trong repo và các vị trí tìm kiếm. Không tự ghi verdict nghiệm thu hay human review.

## Kiểm chứng

- Regression trước sửa: test cấu hình thiếu `speech.build.args.VAD`, thất bại. Test cuối kiểm VAD=1 và không thêm AICEFR_WHISPER_MODEL vào Compose.
- `docker build --target speech --build-arg VAD=1 -t aicefr-speech:silero-vad-fix .`: exit 0; image `sha256:3cc2b80ba2b7a5e103092130157e9f41d949d8a536a590b13dc8817e368301b3`.
- `docker run --rm --network none --entrypoint python aicefr-speech:silero-vad-fix ...`: exit 0; VAD=silero, Whisper=large-v3, torch=2.15.0+cpu, UID=10001; HF_HOME thuộc UID=10001 và ghi được. Kiểm tra khởi tạo Whisper chỉ đọc tên cấu hình, không tải model hoặc chép lời.
- Container tạm với mã nguồn mount read-only: `pytest --no-cov -p no:cacheprovider tests/test_deploy_config.py`: **12 passed**. Không truy cập DB local/production, không dùng audio thật.
- `ruff check --no-cache tests/test_deploy_config.py`, `ruff format --check --no-cache tests/test_deploy_config.py`, `git diff --check`: đạt.
- Compose base + production `config --quiet`: đạt với domain ví dụ chỉ trong tiến trình kiểm tra.
- Cú pháp CI YAML và `sh -n` cho các lệnh job image: đạt; giữ nguyên tên job bắt buộc.
- CI PR lần đầu: job build image, Silero offline, tài liệu và secret scan đạt. Job unit/coverage có 1461 passed, 45 skipped, 1 failed vì test cấu hình mới chưa được ghi trong kế hoạch kiểm thử. Đã bổ sung TC-DP-U11 vào TEST_PLAN_D045_D047.md; không thay test truy vết hoặc nới điều kiện CI.
- Sau khi bổ sung kế hoạch: `pytest --no-cov -p no:cacheprovider tests/test_deploy_config.py tests/test_product_traceability.py`: **63 passed**. Sửa lần này chỉ chạm tài liệu; Dockerfile và mã trong image đã build giữ nguyên.
- `python -X utf8 scripts/ci/check_forbidden_files.py` và `check_md_links.py`: đạt. Lượt đầu dùng encoding Windows mặc định không in được tiếng Việt, chạy lại UTF-8 thành công.
- NOT_EVALUATED: chấm audio thật trên EC2; human review. Không có audio thật, secret, model weights hoặc dữ liệu người học trong PR.

## Nhật ký và bảo toàn thay đổi

- Ghi ba prompt mới vào W07, sheet Thắng, giữ các ô đã có trong workbook local.
- Bản workbook đưa vào PR được tạo từ base và chỉ thêm ba prompt thuộc scope này; các thay đổi workbook có sẵn và nhật ký local khác không đưa vào commit.
- Artifact Tool thiếu dotnet.js đã xác nhận trong phiên; dùng openpyxl dự phòng, kiểm tra bảo toàn ô/công thức/style/hyperlink. NOT_EVALUATED: render và tính lại workbook bằng Excel.
