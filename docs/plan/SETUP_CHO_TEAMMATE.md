# Hướng dẫn setup — đọc cái này trước

> Dành cho cả nhóm. Làm theo đúng thứ tự, mỗi bước có cách kiểm tra đã đúng chưa.
>
> **File này nói về phần học máy và fine-tune.** Nếu việc bạn cần làm chỉ là
> chạy được hệ thống trên máy mình để sửa web hoặc chạy test, đọc
> [CHAY_TREN_LOCALHOST.md](CHAY_TREN_LOCALHOST.md) thay cho file này.

---

## Câu hỏi thường gặp trả lời ngay

**Máy ở nhà có fine-tune được không?**
Chạy lệnh này, script sẽ trả lời cụ thể cho từng loại fine-tune:

```bash
python3 tools/kiem_tra_may.py
```

Quy tắc ngắn gọn:

| Máy | Fine-tune văn bản (BERT) | Fine-tune âm thanh (wav2vec2) |
|---|---|---|
| NVIDIA từ 10 GB VRAM trở lên | Được, local | Được, local |
| NVIDIA 6–8 GB VRAM | Được | Dùng Kaggle |
| NVIDIA 4 GB (như RTX 3050 Ti) | Chật, nên dùng Colab | Không được |
| Mac Apple Silicon 16 GB trở lên | Được nhưng chậm hơn 2–3 lần | Không nên |
| Không có GPU | Dùng Colab | Dùng Kaggle |

**Remote về máy ở nhà có sao không?** Không sao. Nhưng nhớ chạy bằng `tmux` hoặc `nohup` để mất kết nối thì tiến trình vẫn sống:

```bash
nohup python3 train.py > train.log 2>&1 &
tail -f train.log
```

**Chưa có web để test, chỉ chạy script Python đúng không?** Không còn đúng nữa — web đã chạy được rồi, xem [CHAY_TREN_LOCALHOST.md](CHAY_TREN_LOCALHOST.md). Câu trả lời này giữ lại để biết tài liệu từng viết lúc nào.

---

## Bước 1. Cài môi trường

```bash
# macOS
brew install ffmpeg
python3 -m pip install --user torch transformers datasets accelerate sentencepiece \
    scikit-learn scipy soundfile silero-vad mlx-whisper jiwer

# Windows / Linux có NVIDIA
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install transformers datasets accelerate sentencepiece scikit-learn scipy \
    soundfile silero-vad faster-whisper jiwer
# ffmpeg: tải tại ffmpeg.org rồi thêm vào PATH
```

Kiểm tra:
```bash
python3 tools/kiem_tra_may.py     # phải thấy GPU hoặc MPS
ffmpeg -version                    # phải ra thông tin phiên bản
```

## Bước 2. Lấy dữ liệu

Đọc [CHOT_DATASET_VA_MODEL.md](CHOT_DATASET_VA_MODEL.md). Tóm tắt:

- **Mỗi người tự đăng ký** Speak & Improve bằng tài khoản riêng. Giấy phép **cấm chép cho nhau**.
- Gói khung 241 MB là đủ cho fine-tune văn bản, **không cần tải audio**.
- Chỉ tải audio khi làm nhánh âm thanh: dev 1,9 GB, train 13,1 GB.

Đặt gói corpus **ngoài thư mục git**, ví dụ `~/Documents/Project/sandi-corpus-2025`.

## Bước 3. Chạy thử để biết mọi thứ đã đúng

```bash
cd sandi-work
python3 quick_baseline_dev.py "../sandi-corpus-2025"
```
Kết quả phải khớp số ghi trong artifact ngoài repo (số đo trên Speak & Improve, giữ ở hồ sơ nội bộ, W7-S01). Nếu lệch nhiều thì báo nhóm.

---

## Ai làm gì

| Người | Mảng | Việc tuần này |
|---|---|---|
| **Thắng** | Học máy, fine-tune | Chạy `kiem_tra_may.py` trên máy ở nhà rồi báo kết quả. Dựng notebook Colab fine-tune DeBERTa trên transcript tập train |
| **Lê** | Pipeline tiếng nói | Chạy Whisper large-v3-turbo trên tập con, đo WER so với bản chép tay. Module trích đặc trưng ngừng nghỉ bằng VAD |
| **Nguyên** | Hệ thống, tài liệu | Rà và xác minh 6 sơ đồ trong `docs/sdd/`, dựng khung FastAPI và giao diện web tối thiểu |

---

## Về sơ đồ

**Đã có đủ 6 sơ đồ, đã xuất ảnh, đã chèn vào SRS và SDD.**

| Thư mục | Nội dung |
|---|---|
| `docs/sdd/diagrams/*.mmd` | Mã nguồn Mermaid, sửa ở đây |
| `docs/sdd/images/*.png` | Ảnh đã render, dùng chèn vào tài liệu |
| `docs/srs/SRS.md` mục 8.9 | Sáu hình đã được tham chiếu |

Sáu sơ đồ: use case, lớp, tuần tự, hoạt động, thực thể liên kết, thành phần và triển khai. Rubric yêu cầu tối thiểu 4 loại để đạt mức cao nhất.

**Sửa sơ đồ rồi render lại.** Sơ đồ PlantUML (`.puml`) render bằng script ở gốc repo:

```bash
./render.sh
```

Sơ đồ Mermaid (`.mmd`) render từng file:

```bash
npx -y @mermaid-js/mermaid-cli@11 \
    -i docs/sdd/diagrams/01a_usecase_sinhvien.mmd \
    -o docs/sdd/images/01a_usecase_sinhvien.png -w 2000 -b white
```

`tests/test_diagrams.py` sẽ đỏ nếu một sơ đồ chưa được render, ảnh có tỷ lệ
không in được A4, hoặc sơ đồ vẽ một lớp không tồn tại trong mã.

**Việc Nguyên cần xác minh:** rubric cho hội đồng đối chiếu ngẫu nhiên 5 điểm giữa sơ đồ và mã nguồn. Nghĩa là mỗi lớp, mỗi bảng, mỗi endpoint vẽ trong sơ đồ **phải tồn tại thật trong code**. Bảng ánh xạ nằm ở mục 7 của SDD, dùng nó làm danh sách kiểm.

---

## CEFR chỉ làm 5 tiêu chí

Đã chốt, ghi ở [QUYET_DINH.md](QUYET_DINH.md) mục QD-04.

**Làm:** Range, Accuracy, Fluency, Coherence, Phonology.
**Bỏ hẳn:** Interaction, và bỏ luôn dạng bài hội thoại khỏi quy trình thu dữ liệu.

Lý do: Interaction cần hội thoại có cấu trúc, cỡ mẫu dự kiến quá nhỏ để kết luận, và chưa hệ thống nào trên thế giới chấm tự động được tiêu chí này. Nêu rõ giới hạn mạnh hơn là tuyên bố 6 rồi để trống một cái.

---

## Ba điều cấm

1. Không đẩy audio, transcript, model của Speak & Improve lên GitHub hay Hugging Face. Giấy phép cấm tái phân phối.
2. Không chép corpus cho nhau, mỗi người tự đăng ký.
3. Mỗi người commit bằng **tài khoản GitHub riêng** của mình. Rubric chấm theo lịch sử commit để biết ai làm gì; commit chung một tài khoản là mất điểm.

## Ghi nhật ký sử dụng AI

Rubric bắt buộc. Không nộp thì tiêu chí làm chủ AI bị chặn ở mức 2. Kê khai mâu thuẫn với lịch sử Git thì bị 0 điểm và kích hoạt quy trình đạo văn.

Ghi vào `docs/ai-usage-log.md`, mỗi lần dùng một dòng: ngày, người, công cụ, nhờ AI làm gì, kết quả dùng ở file nào commit nào, đã kiểm chứng thế nào, phát hiện lỗi gì của AI.
