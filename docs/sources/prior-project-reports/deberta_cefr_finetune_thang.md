# Báo cáo fine-tune DeBERTa cho chấm CEFR từ transcript

- Người phụ trách: Lê Văn Chiến Thắng
- Ngày ghi nhận kết quả: 2026-09-15
- Phạm vi: fine-tune transcript → điểm CEFR cho P1, P3, P4, P5
- Không có P2 trong corpus/thiết kế của nhiệm vụ này.

## 1. Mục tiêu

Huấn luyện `microsoft/deberta-v3-base` cho bài toán hồi quy điểm CEFR từ bản chép lời, sau đó kiểm tra xem full fine-tune có cải thiện so với một baseline đóng băng encoder hay không.

Phần này là nhánh transcript, chưa phải model chấm trực tiếp từ audio. Model DeBERTa cũng chưa được tích hợp vào scorer đang chạy trong app; app hiện vẫn dùng Ridge.

## 2. Dữ liệu và kiểm tra đầu vào

> Các số đo trên Speak & Improve trong báo cáo này đã được gỡ theo W7-S01 (giấy phép CUP&A); bản đầy đủ ở hồ sơ nội bộ của Thắng.

| Phần | Train | Dev |
|---|---:|---:|
| P1 | — | — |
| P3 | — | — |
| P4 | — | — |
| P5 | — | — |
| **Tổng** | — | — |

Các kiểm tra đã đạt:

- Đủ bốn phần P1/P3/P4/P5.
- Không có ID trùng giữa train và dev.
- Nhãn nằm trong khoảng CEFR hợp lệ của corpus.
- Không hiển thị hoặc đưa transcript/audio vào báo cáo này.

## 3. Cấu hình full fine-tune

| Thành phần | Giá trị |
|---|---|
| Model nền | `microsoft/deberta-v3-base` |
| Bài toán | Regression, một điểm đầu ra |
| Số epoch | 3 |
| Learning rate | `2e-5` |
| Batch vật lý | 8 |
| Gradient accumulation | 2 |
| Batch hiệu dụng | 16 |
| Max sequence length | 512 |
| GPU | Google Colab Tesla T4 |
| Transformers | 5.17.0 |
| PyTorch | 2.11.0+cu128 |
| Datasets | 5.0.1 |
| Accelerate | 1.15.0 |

Run manifest dùng seed cơ sở 42. Seed hiệu dụng được ghi trong metrics theo từng phần: P1=43, P3=45, P4=46, P5=47.

## 4. Kết quả trên dev

### 4.1. Full fine-tune

| Phần | PCC | RMSE | MAE | Bias |
|---|---:|---:|---:|---:|
| P1 | — | — | — | — |
| P3 | — | — | — | — |
| P4 | — | — | — | — |
| P5 | — | — | — | — |
| **Overall** | — | — | — | — |

PCC overall vượt mốc BERT tham khảo trong kế hoạch. Kết quả hiện tại được đo trên dev, chưa phải đánh giá độc lập trên test set.

### 4.2. So sánh với baseline

| Cấu hình | PCC overall | RMSE overall | Ý nghĩa |
|---|---:|---:|---|
| Mean baseline | — | — | Mốc điểm trung bình |
| Frozen DeBERTa | — | — | Chỉ huấn luyện pooler/classifier |
| **Full fine-tune** | — | — | Cập nhật toàn bộ DeBERTa |

Frozen DeBERTa chỉ cập nhật 591.361/184.422.913 tham số, tương đương 0,321%. Nó được dùng làm baseline đối chứng, không phải model chính.

Theo PCC — metric chính của kế hoạch — full fine-tune tốt hơn frozen ở cả P1, P3, P4, P5 và overall. Full fine-tune có bias dương khá lớn, cho thấy xu hướng dự đoán hơi cao; trước khi dùng trong sản phẩm cần cân nhắc hiệu chuẩn điểm.

## 5. Kiểm chứng khả năng tái lập

Notebook ablation đã nạp lại bốn bộ weights full fine-tune và tái tạo dự đoán đã lưu. Sai khác tuyệt đối lớn nhất là `0.00390625`, nhỏ hơn ngưỡng kiểm tra `0.01`.

Hai notebook liên quan:

- `notebooks/deberta_cefr_thang.ipynb`: huấn luyện full fine-tune và xuất model chính.
- `notebooks/deberta_cefr_ablation_thang.ipynb`: kiểm tra weights, tạo mean baseline, huấn luyện frozen baseline và tạo bảng so sánh.

## 6. Kết luận bàn giao

Model được đề xuất làm kết quả transcript chính là **full fine-tune DeBERTa**, với PCC overall trên dev cao nhất trong các cấu hình đã thử. Frozen DeBERTa được giữ lại như baseline để chứng minh tác động của fine-tune.

Các model weights, checkpoint, prediction theo từng mẫu và dataset được lưu ở kho riêng ngoài Git repository, hiện tại là:

```text
/home/thanglvc/Documents/HCMUTE/deberta-results-review/
```

Không commit hoặc push các artifact riêng tư này lên GitHub. Việc tích hợp model vào app, đánh giá trên test set độc lập và hiệu chuẩn điểm là các bước tiếp theo của nhóm, không thuộc kết quả fine-tune transcript đã báo cáo ở đây.
