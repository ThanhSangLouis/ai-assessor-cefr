# Xây dựng hệ thống AI hỗ trợ đánh giá năng lực nói tiếng Anh theo CEFR cho sinh viên đại học Việt Nam ở trình độ A2-B2

## 03. Đặc tả manifest cho corpus ngoài

| Thuộc tính | Giá trị |
| --- | --- |
| Trạng thái | PROPOSED |
| Phạm vi | Metadata/provenance; không chứa audio hoặc PII |
| Ngày | 02/09/2026 |

## 1. Trường cấp dataset

| Field | Kiểu | Bắt buộc | Quy tắc |
| --- | --- | --- | --- |
| `dataset_id` | string | Có | Stable ID nội bộ, không dùng tên người |
| `dataset_version` | string | Có | Version của distributor; `unknown` không đủ để khóa snapshot |
| `source_url` | string | Có | Trang distributor chính thức |
| `retrieved_at` | ISO date | Có sau tải | Không điền trước |
| `archive_sha256` | string | Có sau tải | Hash archive nguyên bản |
| `license_id` | string | Có | SPDX nếu phù hợp, hoặc tên agreement |
| `license_snapshot_ref` | string | Có | Ref ngoài repo nếu license có registration identity |
| `approval_ref` | string/null | Có | Null trước approval; không chứa tên/email |
| `allowed_uses` | array[string] | Có | Ví dụ `ASR_SMOKE`, `PHONOLOGY_AUX`, `HOLISTIC_BASELINE` |
| `prohibited_uses` | array[string] | Có | Ví dụ `PRIMARY_CONFIRMATION`, `REDISTRIBUTION` |
| `speaker_id_available` | boolean | Có | False thì không đủ điều kiện speaker-disjoint evaluation |
| `label_provenance` | object | Có | Rater/protocol/source scale nếu biết; không tự gọi là CEFR analytic |
| `data_root_config_key` | string | Có sau tải | Config key, không hard-code path máy |

## 2. Trường cấp item

| Field | Kiểu | Bắt buộc | Ghi chú |
| --- | --- | --- | --- |
| `dataset_id` | string | Có | Foreign key |
| `source_item_id` | string | Có | Giữ ID source, không chứa direct identity |
| `speaker_id` | string/null | Có | Null phải làm item không đủ điều kiện evaluation |
| `l1` | string/null | Có | Không suy đoán từ accent |
| `age_group` | string/null | Có | Chỉ dùng metadata source tự cung cấp |
| `task_type` | enum | Có | `READ`, `MONOLOGUE`, `INTERACTION`, `OTHER` |
| `audio_relpath` | string | Có sau tải | Relative trong external root |
| `transcript_relpath` | string/null | Có | Không chép transcript vào log/manifest công khai |
| `source_label` | object/null | Có | Giữ scale/semantics gốc |
| `mapped_label` | object/null | Có | Chỉ có khi mapping version được duyệt |
| `cefr_label_provenance` | enum | Có | `DIRECT_RATING`, `EXTERNAL_TEST_LINK`, `MODEL_INDICATIVE`, `NONE` |
| `quality_status` | string | Có | Không lỗi thì vẫn ghi status |
| `evaluation_eligible` | boolean | Có | Phải false khi thiếu speaker ID hoặc sai protocol |
| `use_reason` | string | Có | Vai trò cụ thể trong dự án |

## 3. Ví dụ synthetic

```json
{
  "dataset_id": "L2_ARCTIC_V5",
  "dataset_version": "5.0",
  "source_item_id": "SYNTHETIC_ITEM_ONLY",
  "speaker_id": "SYNTHETIC_SPEAKER",
  "l1": "vi",
  "age_group": null,
  "task_type": "MONOLOGUE",
  "audio_relpath": "[NOT_DOWNLOADED]",
  "transcript_relpath": null,
  "source_label": null,
  "mapped_label": null,
  "cefr_label_provenance": "NONE",
  "quality_status": "NOT_INSPECTED",
  "evaluation_eligible": false,
  "use_reason": "ASR_PHONOLOGY_SMOKE_ONLY"
}
```

Ví dụ trên không đại diện một file thật và không được dùng để tuyên bố dataset đã tải.

## 4. Invariant tests

- Không có cùng `(dataset_id, speaker_id)` ở nhiều split của cùng evaluation run.
- `speaker_id=null` kéo theo `evaluation_eligible=false`.
- `task_type != INTERACTION` không được tạo Interaction label cho rubric dự án.
- `cefr_label_provenance=NONE` kéo theo `mapped_label=null`.
- Mọi mapped label có `mapping_version`, rationale và source scale.
- Không field nào chứa contact/license-registration identity.
- File/hash/version thiếu phải chặn dataset snapshot lock.

