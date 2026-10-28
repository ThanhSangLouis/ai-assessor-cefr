# Giải thích sơ đồ lớp từ A đến Z

**Dùng để làm gì.** Tài liệu này để bạn trình bày sơ đồ lớp trước giảng viên
hướng dẫn mà không phải thuộc lòng. Nó đi từ *"một cái hộp trên hình nghĩa là
gì"* tới *"vì sao mô hình cần đúng những lớp này"*, và kết thúc bằng những câu
hỏi giảng viên hay hỏi kèm câu trả lời — **bao gồm cả những chỗ sơ đồ còn chưa
chuẩn**, vì bị hỏi trúng chỗ yếu mà chưa chuẩn bị thì mọi phần trước cũng mất
giá.

Hình: `docs/sdd/images/02_class.png` — nguồn: `docs/sdd/diagrams/02_class.drawio`

Số liệu hiện tại: **24 hộp** (6 «entity», 10 «value object», 8 «enumeration»),
**34 quan hệ** (11 hợp thành, 6 liên kết, 17 phụ thuộc).

---

## Mục lục

1. [Sơ đồ lớp là gì — và sơ đồ này *không* phải cái gì](#1-sơ-đồ-lớp-là-gì--và-sơ-đồ-này-không-phải-cái-gì)
2. [Đọc một cái hộp](#2-đọc-một-cái-hộp)
3. [Ba khuôn dập: entity, value object, enumeration](#3-ba-khuôn-dập-entity-value-object-enumeration)
4. [Bốn loại đường nối](#4-bốn-loại-đường-nối)
5. [Bội số — và vì sao nó nằm trên cạnh](#5-bội-số--và-vì-sao-nó-nằm-trên-cạnh)
6. [Đi hết một bài nộp, bằng số thật](#6-đi-hết-một-bài-nộp-bằng-số-thật)
7. [Ví dụ thứ hai: khi hệ thống *từ chối* chấm](#7-ví-dụ-thứ-hai-khi-hệ-thống-từ-chối-chấm)
8. [Bảng tra nhanh 22 lớp](#8-bảng-tra-nhanh-22-lớp)
9. [Mười hai câu hỏi giảng viên hay hỏi](#9-mười-hai-câu-hỏi-giảng-viên-hay-hỏi)
10. [Những chỗ sơ đồ còn chưa chuẩn](#10-những-chỗ-sơ-đồ-còn-chưa-chuẩn)
11. [Cách tái tạo hình và những test giữ nó đúng](#11-cách-tái-tạo-hình-và-những-test-giữ-nó-đúng)
12. [Phụ lục — tái tạo hai ví dụ](#phụ-lục--tái-tạo-hai-ví-dụ-ở-mục-6-và-7)

---

## 1. Sơ đồ lớp là gì — và sơ đồ này *không* phải cái gì

Sơ đồ lớp trả lời một câu: **hệ thống này nói về những khái niệm nào, và chúng
quan hệ với nhau ra sao.** Nó là bản đồ *danh từ* của bài toán.

Điều quan trọng khi trình bày là nói rõ **ba thứ nó không phải**, vì giảng viên
thường hỏi ngay:

| Không phải là | Vì sao | Cái đó ở đâu |
| --- | --- | --- |
| **Lược đồ cơ sở dữ liệu** | Trên hình có 24 hộp nhưng CSDL chỉ có **9 bảng**. `Assessment`, `Evidence`, `Comment`… không có bảng riêng — chúng nằm trong cột `report_json` của bảng `response` | `src/aicefr/storage/repository.py` |
| **Sơ đồ kiến trúc** | Không có `RidgeScorer`, `WhisperEngine`, `ResponseProcessor` trên hình. Đó là *cơ chế*, không phải *khái niệm nghiệp vụ* | `docs/sdd/diagrams/02b_kien_truc.puml` |
| **Sơ đồ luồng xử lý** | Hình không nói thứ tự. Thứ tự nằm ở sơ đồ tuần tự | SDD mục 3.3 |

**Một câu để mở đầu buổi trình bày:**

> "Sơ đồ này là tầng nghiệp vụ. Mỗi hộp là một khái niệm mà người dùng hoặc
> giảng viên có thể gọi tên được, và mọi hộp trên hình đều tồn tại trong mã dưới
> đúng cái tên đó — có test kiểm điều này."

Câu cuối không phải nói cho hay: `tests/test_diagrams.py` có test
`test_nothing_drawn_is_missing_from_the_code` làm đúng việc đó.

---

## 2. Đọc một cái hộp

Mỗi hộp có **ba ngăn**, đọc từ trên xuống:

```
┌─────────────────────────────┐
│       «value object»        │  ← ngăn 1: khuôn dập + tên lớp
│            Word             │
├─────────────────────────────┤
│  - text: str                │  ← ngăn 2: thuộc tính
│  - startS: float            │
│  - endS: float              │
│  - prob: float              │
├─────────────────────────────┤
│  + isUncertain(): bool      │  ← ngăn 3: thao tác
└─────────────────────────────┘
```

**Ký hiệu tầm nhìn** (visibility) đứng đầu mỗi dòng:

| Ký hiệu | Nghĩa | Trên hình này |
| --- | --- | --- |
| `-` | private — chỉ chính lớp đó dùng | mọi thuộc tính |
| `+` | public — nơi khác gọi được | mọi thao tác |
| `#` | protected | không dùng |

**Quy ước tên.** Trên hình dùng `camelCase` (`startS`, `isUncertain`) theo chuẩn
UML; trong mã Python là `snake_case` (`start_s`, `is_uncertain`). Đây là chuyển
đổi có quy tắc, không phải hai thứ khác nhau — và test tra theo quy tắc đó.

**Mọi thành viên đều phải có kiểu.** Bản nháp đầu tiên bỏ kiểu đi "cho gọn". Lý
do đó sai ở một điểm quyết định: **sơ đồ lớp không có kiểu thì không rã xuống mã
được**. Người đọc không biết `reasons` là một mã hay một danh sách
(`List<ReasonCode>`), không biết `assessment` là một đối tượng hay một khoá
ngoại. Kiểu chính là phần nói ra điều đó. Test
`test_every_member_on_the_class_diagram_carries_a_type` chặn việc này.

**Kiểu có tham số** đọc như sau:

| Viết | Nghĩa | Ví dụ thật |
| --- | --- | --- |
| `List<Word>` | một **dãy** các `Word`, có thứ tự | `Transcript.words` — thứ tự từ trong câu |
| `float` | một số thực | `Word.prob` = `0.85` |
| `Band` | một giá trị của kiểu liệt kê `Band` | `A2`, `B1` hoặc `B2` |

---

## 3. Ba khuôn dập: entity, value object, enumeration

Chữ trong «…» gọi là **stereotype** (khuôn dập) — một nhãn phân loại của UML.
Sơ đồ này dùng ba loại, và ranh giới giữa chúng **không** phải vấn đề thẩm mỹ:
nó quyết định lớp đó cần khoá hay không, có được sửa hay không.

### «entity» — có danh tính riêng

Định nghĩa dùng ở đây: **tra cứu được bằng danh tính, và sống qua nhiều lần
sửa.**

Ví dụ dễ nhớ: hai lần duyệt bài của giảng viên có cùng điểm cũ và điểm mới
**vẫn là hai lần duyệt khác nhau** — vì mỗi lần xảy ra ở một thời điểm và do một
người. Nên `Review` là entity.

Sáu entity: `Account`, `Consent`, `Task`, `Response`, `Assessment`, `Review`.

### «value object» — so sánh bằng nội dung, bất biến

Ví dụ đối chiếu: hai `Word` cùng `text`, `startS`, `endS`, `prob` là **cùng một**
từ. Hỏi *"từ nào"* là câu hỏi vô nghĩa — không có "từ số 1" và "từ số 2" khác
nhau khi mọi thuộc tính giống nhau.

Mười value object: `QcResult`, `Transcript`, `Word`, `FeatureSet`, `Feature`,
`Evidence`, `CriterionCoverage`, `AnalysisWindow`, `Comment`, `Priority`.

### «enumeration» — tập giá trị đóng

Một danh sách hữu hạn, cố định. `Band` chỉ có `A2`, `B1`, `B2` — đề tài giới hạn
ở ba bậc này. `Criterion` có đúng năm tiêu chí CEFR, **không có Interaction**
theo quyết định QĐ-04 (không thể đánh giá tương tác từ một bài nói độc thoại).

Tám enum: `Role`, `Status`, `QcStatus`, `Band`, `Criterion`, `EvidenceKind`,
`TaskPart`, `ReasonCode`.

### Phép thử để phân biệt khi bí

Hỏi: *"Nếu tôi có hai cái giống nhau ở mọi thuộc tính, chúng là một hay là
hai?"*

- Là **một** → value object
- Là **hai** → entity

---

## 4. Bốn loại đường nối

Đây là phần giảng viên hỏi nhiều nhất, vì đây là chỗ dễ vẽ sai nhất.

### 4.1. Hợp thành — composition (hình thoi **đặc** ◆)

```
Transcript ◆────1 : 0..*────> Word
```

Đọc: *"một `Transcript` **chứa** các `Word`; từ không tồn tại ngoài bản chép của
nó."*

**Ba điều kiện, phải đủ cả ba:**

| Điều kiện | Kiểm bằng cách nào |
| --- | --- |
| 1. Thể **chứa** bộ phận | Lớp thể phải có một trường thật trỏ tới bộ phận |
| 2. Sở hữu **độc quyền** | Không lớp nào khác chứa bộ phận đó |
| 3. Vòng đời **trùng nhau** | Xoá thể thì bộ phận mất theo |

Hai điều kiện đầu **kiểm được tự động** và đang được kiểm:
`test_every_composition_has_a_real_containing_field` và
`test_every_composition_part_has_exactly_one_owner`. Điều kiện thứ ba là phần
xét đoán, ghi bằng lời trong SDD mục 3.2.

### 4.2. Liên kết — association (đường liền, không hình thoi)

```
Response ────1 : 0..*────> Review
```

Đọc: *"một `Response` có thể có nhiều lần duyệt, nhưng lần duyệt **không nằm
trong** bài nộp."*

**Đây là chỗ tôi đã vẽ sai và phải sửa.** Bản đầu vẽ `Response ◆ Review` là hợp
thành. Sai, vì `Review` nằm ở **bảng riêng** `review_action` trong CSDL — xoá một
bài nộp thì bản ghi duyệt vẫn còn đó. Vi phạm điều kiện 1 và 3. Nay là liên kết,
và có test ghim để không tái diễn.

**Nói câu này khi trình bày** — nó cho thấy bạn hiểu ký hiệu, không chỉ dùng
ký hiệu:

> "Hợp thành không phải một mũi tên đẹp hơn liên kết. Nó **hứa** ba điều, và nếu
> mã không giữ được cả ba thì vẽ hợp thành là nói sai."

### 4.3. Phụ thuộc — dependency (đường **nét đứt**, mũi hở)

```
QcResult ┄┄┄> QcStatus
```

Đọc: *"`QcResult` **dùng** kiểu `QcStatus`."* Trên hình này, mọi đường nét đứt
đều đi tới một kiểu liệt kê. Đó là lý do có 15 đường nét đứt: sáu lớp mang
`List<ReasonCode>`, cộng các lớp dùng `Band`, `Criterion`, `Status`, `QcStatus`,
`Role`.

### 4.4. Kết hợp — aggregation (hình thoi **rỗng** ◇): **không có trên hình này**

Kết hợp là *"chứa nhưng không sở hữu độc quyền"*. Ví dụ kinh điển từ bài tham
khảo OneShop của bạn: `Order ◇ Customer` — xoá đơn hàng thì khách hàng vẫn còn.

**Sơ đồ này không có quan hệ kết hợp nào**, và đó là câu trả lời có chuẩn bị cho
câu hỏi *"sao bản shop có 16 kết hợp mà bản này không có cái nào?"*:

> "Vì ở đây không có đối tượng nào được **dùng chung** giữa hai thể. Mọi bộ phận
> — bản chép, đặc trưng, bằng chứng, nhận xét — đều sinh ra từ đúng một bài nộp
> và mất theo bài nộp đó. Khác biệt này đến từ bản chất bài toán: bản shop có
> khách hàng tồn tại độc lập với đơn hàng, còn ở đây không có gì tương tự."

---

## 5. Bội số — và vì sao nó nằm trên cạnh

**Bội số** (multiplicity) là con số ở hai đầu một cạnh, nói *"bao nhiêu cái"*.

| Viết | Đọc |
| --- | --- |
| `1` | đúng một |
| `0..1` | không có, hoặc một |
| `0..*` | không giới hạn |
| `1..*` | ít nhất một |
| `0..10` | tối đa mười |
| `5` | đúng năm |

Ví dụ trên hình: `Assessment ◆──1 : 5──> CriterionCoverage` đọc là *"mỗi kết quả
chấm có đúng năm độ bao phủ tiêu chí"* — đúng năm, vì CEFR ở đây có đúng năm
tiêu chí.

### Bội số phải nằm trên **cạnh**, không nằm trong thuộc tính

Bản nháp từng viết `- evidence: List<Evidence> [0..10]` — sai. Bội số là khái
niệm của **một đầu liên kết**, không phải của một thuộc tính. Thuộc tính viết
kiểu thuần (`- evidence: List<Evidence>`), còn `0..10` viết trên cạnh.

### Bội số phải là **giới hạn mã thật giữ**, không phải giới hạn mong muốn

Đây là bài học đắt nhất của phần này. Bản nháp vẽ `evidence 0..6` vì tài liệu
yêu cầu FR-24 ghi tối đa 6 bằng chứng. Nhưng mã thật cho tới **10** (3 chỗ ngừng
+ 3 tiếng đệm + 3 từ tin cậy thấp + 1 từ vựng, không có giới hạn tổng). Vẽ 6 là
**hứa một ràng buộc hệ thống không giữ**.

Nay bội số được ghim bằng test `test_multiplicities_match_what_the_code_enforces`,
đối chiếu nhãn trên cạnh với giới hạn thật trong mã:

| Quan hệ | Bội số | Giới hạn nằm ở đâu trong mã |
| --- | --- | --- |
| `Assessment` → `CriterionCoverage` | `5` | `CRITERION_FEATURES` có 5 khoá |
| `Assessment` → `Evidence` | `0..10` | `3 × MAX_PER_KIND + 1` = 3 chỗ ngừng + 3 tiếng đệm + 3 từ tin cậy thấp + 1 từ vựng (`report/evidence.py:9`) |
| `Assessment` → `Comment` | `0..4` | 4 nhánh sinh nhận xét; hai nhánh cuối là `if/elif` **loại trừ nhau** nên không bao giờ ra 5 (`report/comments.py:186,198`) |
| `Assessment` → `Priority` | `0..2` | `MAX_PRIORITIES = 2` (`report/comments.py:35`) |
| `Assessment` → `AnalysisWindow` | `0..10` | `MAX_WINDOWS = 10` (`scoring/windows.py:46`) |
| `FeatureSet` → `Feature` | `1..*` | `items: list[Feature] = Field(min_length=1)` |
| `Comment` → `Evidence` | `1..*` | `CommentBuilder.comments()` lọc bỏ mọi nhận xét rỗng bằng chứng trước khi trả về |

**Chênh lệch còn tồn tại, phải nói ra:** FR-24 ghi 6, mã cho 10. Hình vẽ theo
**mã**. Việc sửa tài liệu yêu cầu hay sửa mã là quyết định chưa làm, và nó được
ghi trong báo cáo tuần 1 mục 11.3 là *"chưa sửa"* chứ không bị che đi.

---

## 6. Đi hết một bài nộp, bằng số thật

Đây là phần làm sơ đồ "sống".

**Đọc kỹ chỗ này trước khi trình bày.** Các số ở **bước 5 và bước 6** (đặc trưng,
điểm, band, độ bao phủ, mã lý do) là **kết quả chạy thật** bằng
`FeatureExtractor` và `RidgeScorer` của dự án, trên một bài nói **tổng hợp** dài
54,5 giây gồm 96 từ — tái tạo được bằng đoạn mã ở phụ lục. Các giá trị ở bước 1,
2, 3, 4, 7, 8 (mã sinh viên, ngày ký, `snrDb`, câu nhận xét, lần duyệt) là **ví
dụ minh hoạ cho cấu trúc**, không phải số đo. Đừng trình bày chúng như dữ liệu
thật; nếu bị hỏi, nói đúng như vậy.

### Bước 1 — `Account` và `Consent`: được phép nộp chưa?

```
Account(accountId="sv-014", pseudonym="sv-014", role=STUDENT)
Consent(consentVersion="v2", audioStorageAllowed=True,
        researchUseAllowed=False, signedAt="2026-09-14T09:12:00Z",
        withdrawnAt=None)
   → maySubmit() = True
```

`maySubmit()` gộp ba điều kiện: **đã ký** và **chưa rút** và **cho phép lưu
audio**. Thiếu một là không nộp được. Ba điều kiện này nằm ở *một* chỗ, nên
không có chuyện điểm vào này kiểm đủ mà điểm vào kia kiểm thiếu.

### Bước 2 — `Task`: đề bài nào?

```
Task(taskId="P3", part=TaskPart.P3, minSeconds=40, maxSeconds=60)
```

Điểm chỉ có nghĩa **so với một đề cụ thể**, và `part="P3"` ghi lại rằng bài này
thuộc phần thi mà mô hình được huấn luyện trên đó.

### Bước 3 — `QcResult`: âm thanh có dùng được không?

```
QcResult(durationMs=54500, sampleRateHz=16000, silenceRatio=0.055,
         clippingRatio=0.0, snrDb=24.1, qcStatus=PASS, reasons=[])
   → passed() = True
```

`passed()` mã hoá một luật không đoán ra được từ thuộc tính: **`REVIEW` vẫn chạy
tiếp, chỉ `REJECT` mới dừng**. Nếu không có nó, mỗi nơi gọi sẽ tự viết lại, và
chỉ cần một nơi viết `qcStatus == PASS` là bài `REVIEW` bị chặn oan.

### Bước 4 — `Transcript` và `Word`: chép lời

```
Transcript(text="my hometown located southern part vietnam…",
           engine="whisper-large-v3-turbo", isVerbatim=True,
           words=[Word(text="my", startS=0.5, endS=0.79, prob=0.86), …])   ← 96 Word
```

Đây là quan hệ **hợp thành**: `Transcript ◆ 1 : 0..* Word`. Từ không tồn tại
ngoài bản chép chứa nó.

`Word.prob` là độ tin cậy của bộ nhận dạng, và `isUncertain()` trả `prob < 0,50`.
Luật này từng được viết lại ở **ba nơi** trước khi đưa vào lớp.

### Bước 5 — `FeatureSet` và `Feature`: đo

18 phép đo, đây là mười cái chính (số thật):

| Feature | value | Nghĩa |
| --- | --- | --- |
| `n_words` | 96.0 | số từ |
| `words_per_sec` | 1.7615 | tốc độ nói |
| `ttr` | 0.4688 | tỷ lệ từ khác nhau / tổng từ |
| `log_uniq` | 3.8286 | log số từ vựng khác nhau |
| `mean_word_len` | 5.7917 | độ dài từ trung bình |
| `asr_conf_mean` | 0.8501 | độ tin cậy nhận dạng trung bình |
| `filler_ratio` | 0.0521 | tỷ lệ tiếng đệm ("erm", "uh") |
| `vad_pause_per_min` | 3.3028 | số lần ngừng mỗi phút |
| `vad_mean_pause` | 0.8333 | độ dài lần ngừng trung bình (giây) |
| `vad_silence_ratio` | 0.055 | tỷ lệ im lặng |

Mỗi dòng trong bảng là **một đối tượng `Feature`**:

```
Feature(name="ttr", value=0.4688, reason=None)
Feature(name="asr_conf_mean", value=None, reason=TOO_FEW_WORDS)   ← khi đo không được
```

**Đây là chỗ đáng kể nhất khi trình bày,** vì nó cho thấy sơ đồ đã được sửa vì
một lý do đúng. Trước đây `FeatureSet` mang hai thuộc tính:

```
- values: Map<str, float>          ← 18 số, khoá bằng tên
- invalid: Map<str, ReasonCode>    ← lý do, cũng khoá bằng tên
```

Hai vấn đề:

1. **`Map` là cấu trúc dữ liệu, không phải khái niệm nghiệp vụ.** Một `Map` khoá
   bằng chuỗi luôn có nghĩa là *có một khái niệm đang bị giấu*. Khái niệm đó là
   *một phép đo*.
2. **Hai bảng cùng khoá mà không gì buộc chúng khớp.** Và sai lệch đã xảy ra
   thật: `asr_conf_mean` trả `None` khi không từ nào mang xác suất, **không kèm
   mã lý do nào** — trong khi chú thích ngay trên dòng đó viết *"missing data
   returns None with a reason code"*.

Nay `Feature` có một `model_validator` từ chối phép đo vắng số mà không mang lý
do, nên khe hở đó **không mở lại được trong im lặng**. Cách chứng minh: bỏ vòng
bù mã lý do trong `extract.py` rồi chạy test — hai test chuyển đỏ; phục hồi thì
xanh lại.

### Bước 6 — `Assessment`, `CriterionCoverage`: chấm

```
Assessment(overall06=4.13, overallBand=B2,
           modelVersion="ridge_resp_v2",
           calibrationVersion="chua-hieu-chuan",
           windowSpread=None,
           reasons=[SCORE_NEAR_BOUNDARY],
           teacherVerified=False)
   → isCalibrated() = False
```

Năm `CriterionCoverage`, mỗi tiêu chí một cái, `coverage = 1.0` cả năm — nghĩa
là **mọi đặc trưng của tiêu chí đó đều đo được**, không phải "chắc chắn 100%".
Xem câu hỏi 8 ở mục 9.

Ngưỡng bậc: `A2_B1 = 2.75`, `B1_B2 = 3.75`. Điểm 4.13 > 3.75 nên là **B2**.

**Nhưng `reasons` có `SCORE_NEAR_BOUNDARY`,** và đây là lúc ví dụ này phơi ra
đúng khuyết điểm đã ghi trong báo cáo: `boundary_margin = 0.5`, nên vùng "sát
ranh giới" quanh 3.75 là **[3.25 ; 4.25]**. Điểm 4.13 rơi vào đó → bài bị chuyển
giảng viên dù cách ngưỡng tới 0,38 điểm. Cộng hai vùng quanh hai ngưỡng thì
**toàn bộ bậc B1 bị nuốt trọn**.

Nói thẳng điều này khi trình bày. Nó là một lỗi **cấu hình**, không phải lỗi
thiết kế, và sơ đồ lớp đang làm đúng việc của nó: `Assessment.reasons` ghi lại
*vì sao* bài bị chuyển, nên lỗi này tìm ra được thay vì ẩn đi.

### Bước 7 — `Evidence`, `Comment`, `Priority`: nói cho người học hiểu

```
Evidence(evidenceId="ev-01", criterion=FLUENCY, kind=EvidenceKind.PAUSE,
         startS=17.8, endS=18.8, snippet=None,
         note="Chỗ ngừng dài 1,0 giây")

Comment(criterion=FLUENCY,
        text="Bài có khoảng 3 lần ngừng mỗi phút; những chỗ ngừng dài nhất
              được đánh dấu trong bằng chứng bên dưới.",
        evidenceRefs=["ev-01"])                      ← không vẽ trên hình

Priority(feature_name="vad_mean_pause", text="Luyện nói liền mạch hơn", impact=0.21)
```

**Đây là cơ chế chống bịa của cả đề tài.** Một câu nhận xét chỉ được viết ra khi
trỏ được tới `evidenceId` của một bằng chứng có thật, và có test kiểm **mọi id
được trích dẫn đều tồn tại**. Bỏ cơ chế này đi thì phần nhận xét tụt xuống thành
văn bản trôi chảy mà không ai kiểm được — thứ dễ sinh ra nhất và vô dụng nhất.

`Priority.impact = 0.21` là **mức kéo điểm xuống tính bằng điểm trên thang 0–6**.
Nên câu hỏi *"vì sao khuyên luyện cái này trước cái kia"* có câu trả lời bằng số.

### Bước 8 — `Review`: giảng viên vào cuộc

```
Review(reviewerId="gv-03", oldScore=4.13, newScore=3.5,
       oldBand=B2, newBand=B1,
       reason="Phát âm còn ảnh hưởng nghe hiểu", createdAt="2026-09-16T14:02:00Z")
```

Ghi **cả điểm cũ lẫn điểm mới**, nên câu hỏi *"máy lệch bao nhiêu so với
người"* trả lời được bằng dữ liệu đã có, không cần chạy lại gì.

---

## 7. Ví dụ thứ hai: khi hệ thống *từ chối* chấm

Ví dụ này quan trọng không kém, vì nó cho thấy mô hình **biết khi nào nó không
biết**. Cùng bộ mã, nhưng bài nói dùng kho từ hẹp hơn:

```
ttr = 0.1739                      ← chỉ 17% từ là khác nhau
out_of_distribution() = có
```

Kết quả:

```
Assessment(overall06=None, overallBand=None,
           reasons=[OUT_OF_DISTRIBUTION])

CriterionCoverage × 5: coverage=None, reasons=[OUT_OF_DISTRIBUTION]
```

**Không có điểm nào được sinh ra.** Đặc trưng nằm ngoài khoảng mà mô hình từng
thấy khi huấn luyện, nên nó trả về *"không chấm"* kèm lý do, thay vì một con số
trông hợp lệ.

Liên hệ với sơ đồ: `overall06` và `overallBand` là những thứ **có thể vắng**, và
`Assessment.reasons: List<ReasonCode>` là chỗ ghi vì sao chúng vắng. Nếu sơ đồ
không có trường `reasons`, hệ thống chỉ có thể trả về `None` mà không nói được
tại sao — và người dùng sẽ đoán.

Đây cũng là lý do lớp `CriterionCoverage` **không** mang `score06` và `band`.
Bản cũ tên `CriterionScore` và có hai trường đó, nhưng mô hình chỉ có **một**
đầu ra, nên bản cũ chép cùng một con số vào cả năm tiêu chí — trông như năm mô
hình trong khi chỉ có một.

---

## 8. Bảng tra nhanh 22 lớp

| Lớp | Khuôn dập | Một câu | Khai báo ở |
| --- | --- | --- | --- |
| `Account` | entity | Người dùng, định danh bằng bút danh + vai trò | `storage/auth_repository.py` |
| `Consent` | entity | Chữ ký đồng thuận, đúng như lúc được ký | `storage/consent_repository.py` |
| `Task` | entity | Đề bài nói, có phiên bản, giới hạn thời lượng và **phần thi** | `storage/task_repository.py` |
| `Response` | entity | Bài đã nộp và mọi kết quả sinh ra từ nó | `contracts.py` |
| `Assessment` | entity | Kết quả chấm cùng toàn bộ nguồn gốc phiên bản | `contracts.py` |
| `Evidence` | value object | Đoạn cụ thể trên bản ghi làm căn cứ cho nhận xét | `contracts.py` |
| `Review` | entity | Một lần giảng viên giữ hoặc sửa kết quả, kèm lý do | `contracts.py` |
| `QcResult` | value object | Kết quả kiểm tra chất lượng âm thanh | `contracts.py` |
| `Transcript` | value object | Bản chép lời, kèm máy nào tạo ra | `contracts.py` |
| `Word` | value object | Một từ, mốc thời gian, độ tin cậy | `contracts.py` |
| `FeatureSet` | value object | Tập phép đo của một bài | `contracts.py` |
| `Feature` | value object | **Một** phép đo: tên, giá trị, lý do khi vắng | `contracts.py` |
| `CriterionCoverage` | value object | Tỷ lệ phép đo tính được của một tiêu chí | `contracts.py` |
| `AnalysisWindow` | value object | Một cửa sổ thời gian của bài dài + điểm riêng | `contracts.py` |
| `Comment` | value object | Một câu nhận xét | `contracts.py` |
| `Priority` | value object | Việc nên luyện tiếp + mức ảnh hưởng tới điểm | `contracts.py` |
| `Role` | enum | `STUDENT`, `TEACHER`, `ADMIN` | `storage/auth_repository.py` |
| `Status` | enum | Vòng đời bài nộp (6 trạng thái) | `contracts.py` |
| `QcStatus` | enum | `PASS`, `REVIEW`, `REJECT` | `contracts.py` |
| `Band` | enum | `A2`, `B1`, `B2` | `contracts.py` |
| `Criterion` | enum | 5 tiêu chí CEFR (không có Interaction) | `contracts.py` |
| `EvidenceKind` | enum | `PAUSE`, `FILLER`, `LOW_CONFIDENCE_WORD`, `LEXICAL` | `contracts.py` |
| `TaskPart` | enum | `P3`, `P4` (trong dải huấn luyện), `P5` (đề dài, cố ý ngoài dải) | `contracts.py` |
| `ReasonCode` | enum | 22 mã lý do chẩn đoán | `contracts.py` |

Chi tiết *"vì sao mô hình cần lớp này"* cho từng lớp: báo cáo tuần 1 mục 10.4.

---

## 9. Mười hai câu hỏi giảng viên hay hỏi

**1. Vì sao `ReasonCode` có tới 22 giá trị? Enum lớn thường là thiết kế xấu.**

Enum lớn là dấu hiệu xấu **khi nơi tiêu thụ nó phải rẽ nhánh theo từng giá trị**
— một `switch` 22 nhánh thì đúng là tệ. Ở đây thì không: `ReviewRouter` chỉ lấy
**giao tập hợp** giữa tập lý do và một tập kích hoạt, còn giao diện tra một **từ
điển** nhãn. Thêm một mã là thêm một dòng vào hai cấu trúc *dữ liệu*, không dòng
nào vào luồng điều khiển.

Ngược lại, gộp chúng lại mới là hỏng: sinh viên sẽ đọc *"có lỗi"* thay vì *"âm
thanh quá ngắn"*. Cả hệ thống tồn tại để mọi phán xét đều có lý do kiểm tra
được, nên **độ phân giải của lý do chính là sản phẩm**.

Kèm bằng chứng: **cả 22 mã đều có nhãn hiển thị cho người dùng**, và 3 mã từng
tồn tại mà không nơi nào sinh ra đã bị xoá.

**2. Sao không dùng kế thừa cho `Student` / `Teacher` / `Admin`?**

Vì ba loại người này **khác nhau ở quyền, không khác nhau ở dữ liệu**. Chúng có
đúng cùng bộ thuộc tính. Tách ba lớp con rỗng chỉ để phân biệt một giá trị là
thêm ba hộp mà không thêm thông tin, và nó làm việc đổi vai trò của một người
trở thành đổi lớp của một đối tượng — điều không làm được trong hầu hết ngôn
ngữ. `role: Role` cộng `isTeacher()` nói đúng điều cần nói.

**3. Sao `Response` và `Assessment` là hợp thành mà không phải liên kết?**

Vì cả ba điều kiện đều đúng: `Response` có trường `assessment: Assessment`; không
lớp nào khác chứa `Assessment`; và kết quả chấm được lưu trong cột `report_json`
của **chính hàng** `response` đó, nên xoá bài nộp là mất kết quả chấm.

Đối chiếu ngay với `Review` để cho thấy bạn phân biệt được: `Review` nằm ở bảng
riêng `review_action`, nên nó là **liên kết**, không phải hợp thành.

**4. Vì sao chỉ có 22 hộp mà CSDL có 9 bảng — không khớp?**

Đúng là không khớp, và **cố ý**. Sơ đồ lớp là mô hình khái niệm; lược đồ CSDL là
quyết định lưu trữ. `Assessment`, `Evidence`, `Comment`, `Priority`,
`CriterionCoverage`, `AnalysisWindow`, `FeatureSet`, `Feature`, `Transcript`,
`Word`, `QcResult` đều nằm gọn trong cột `report_json` của bảng `response`, vì
chúng luôn được đọc **cùng nhau** như một báo cáo.

**5. `Feature` với 18 đối tượng — sao không khai 18 thuộc tính có tên?**

Vì nguồn sự thật về việc *có những đặc trưng nào* là `feature_order` bên trong
tệp mô hình (`ridge_resp_v2.json`), không phải lớp này. Thêm một đặc trưng là
phát hành tệp mô hình mới; nếu lớp khai 18 tên thì đó là **chỗ thứ hai** phải
sửa tay, và hai chỗ thì sẽ có lúc lệch.

**6. Vậy `Map<str, float>` cũng có lý do tương tự, sao lại bỏ?**

Vì lý do đó chỉ chứng minh *"không nên khai 18 thuộc tính"* — nó **không** chứng
minh *"phải là `Map` thay vì danh sách các đối tượng"*. Một `List<Feature>` cũng
do tệp mô hình quyết định y như vậy. Đây là chỗ tôi từng dùng một lý do đúng để
che một lựa chọn khác.

**7. `windowSpread` là gì?**

Bài dài được cắt thành nhiều `AnalysisWindow`, chấm từng cửa sổ, rồi lấy **trung
vị** chứ không phải trung bình — một cửa sổ hỏng không kéo được cả bài.
`windowSpread` là độ tản của các cửa sổ, tức một thước đo *"kết quả này ổn định
tới đâu"*. Bài ngắn chỉ có một cửa sổ nên `windowSpread = None`.

**8. `CriterionCoverage.coverage = 1.0` nghĩa là chắc chắn 100%?**

**Không**, và đây là chỗ tên thuộc tính đang hứa nhiều hơn nó có. Nó là **tỷ lệ
đặc trưng của tiêu chí đó tính được**, không phải xác suất điểm đúng. Ví dụ tiêu
chí ACCURACY có 2 đặc trưng; nếu cả 2 đo được thì `coverage = 1.0`, nếu 1 cái
không đo được thì `0.5`. Trường này **từng tên là `confidence`** và đã được đổi
vì đúng lý do đó — xem mục 10.

**9. Mô hình có tốt không?**

Ba số phải nói cùng lúc, không được tách:
`cv_pcc`, `cv_rmse`, `train_n` (đọc trong artifact ngoài repo, W7-S01), GroupKFold 5 chia **theo
người nói**. Và ba điều kèm theo: mô hình huấn luyện trên **nhãn tổng thể** chứ
không phải nhãn từng tiêu chí; `calibration_version = "chua-hieu-chuan"`; đặc
trưng huấn luyện lấy từ bản chép của `whisper-small` trong khi hệ thống chạy
`whisper-large-v3-turbo`.

**10. Sao điểm từng tiêu chí không có trên `CriterionCoverage`?**

Vì mô hình chỉ có **một** đầu ra. Bản cũ (`CriterionScore`) có `score06` và
`band`, và nó chép cùng một con số vào cả năm tiêu chí — trông như năm mô hình
trong khi chỉ có một. Bỏ hai trường đó đi là **trung thực hơn**, dù hình trông
nghèo hơn.

**11. Làm sao biết sơ đồ khớp với mã?**

Có **13 test** kiểm điều đó trên CI, không phải kiểm bằng mắt. Mỗi test đều được
chứng minh **đỏ** bằng cách làm hỏng đúng thứ nó bảo vệ, rồi phục hồi.

| Test | Ghim điều gì |
| --- | --- |
| `test_nothing_drawn_is_missing_from_the_code` | Mọi hộp trên hình tồn tại trong mã |
| `test_every_member_on_the_class_diagram_carries_a_type` | Mọi thuộc tính và thao tác đều có kiểu; **không** bội số trong thuộc tính |
| `test_every_enum_on_the_diagram_lists_all_its_values` | Hộp enum liệt kê đủ, không thiếu giá trị nào |
| `test_no_placeholder_on_the_diagram` | Không có dấu `...` thay cho nội dung thật |
| `test_every_composition_has_a_real_containing_field` | Hợp thành phải có trường chứa thật (điều kiện 1) |
| `test_every_composition_part_has_exactly_one_owner` | Bộ phận chỉ có **một** chủ (điều kiện 2) |
| `test_multiplicities_match_what_the_code_enforces` | Bội số trên cạnh = giới hạn mã thật giữ |
| `test_no_orphan_type_on_the_diagram` | Không nhắc tên một kiểu mà không vẽ hộp cho nó |
| `test_every_operation_on_the_diagram_has_a_caller` | Không vẽ thao tác mà không nơi nào gọi |
| `test_no_edge_crosses_a_box` | Không đường nối nào đi xuyên hộp |
| `test_no_two_edges_are_drawn_on_top_of_each_other` | Không hai đường nối nào đè lên nhau |
| `test_each_diagram_has_a_rendered_image` | Tệp nguồn nào cũng có ảnh đã kết xuất |
| `test_each_image_fits_on_a_page` | Ảnh có tỷ lệ in được trên một trang |

**12. Có chỗ nào em thấy chưa ổn không?**

Có — mục 10 dưới đây. Trả lời câu này bằng *"không có"* là câu trả lời tệ nhất.

---

## 10. Những chỗ sơ đồ còn chưa chuẩn

Chín điểm đã được nêu ra và soi lại. **Sáu đã sửa, ba giữ nguyên có lý do.** Nói
ra trước, đầy đủ — trả lời câu hỏi 12 bằng *"không có"* là câu trả lời tệ nhất.

### Sáu điểm đã sửa

| # | Điểm | Đã làm gì |
| --- | --- | --- |
| 1 | `Evidence` dán nhãn «entity» nhưng không có bảng riêng, mã `ev-01` chỉ có nghĩa trong một báo cáo | Đổi thành **«value object»**. Nay 6 entity, 10 value object |
| 3 | `Evidence.kind: str` chỉ nhận 4 giá trị, viết trần trong mã | Thành **`EvidenceKind`**, kế thừa `str` nên JSON không đổi. Hộp enum nay có trên hình |
| 4 | `Priority.feature: str` là con trỏ treo tới `Feature` | Đổi tên thành **`feature_name`** (tên nói rõ đây là tham chiếu **theo tên**) + test đối chiếu khoá `ADVICE` với `feature_order` của tệp mô hình |
| 6 | `Task.part: str` là tập đóng viết bằng kiểu mở | Thành **`TaskPart`** với **ba** giá trị — xem ghi chú bên dưới |
| 7 | `CriterionCoverage.confidence` hứa nhiều hơn nó có | Đổi thành **`coverage`**, giữ alias cũ nên báo cáo đã lưu vẫn đọc được |
| 8 | Docstring của `Task` tự gọi nó là *value object* trong khi hình dán «entity» | Sửa docstring: `Task` **là** entity (có `task_id`, có bảng riêng, tra cứu theo id) |

**Điểm 6 đáng kể lại khi trình bày,** vì nó cho thấy giá trị của việc chạy test
thay vì tin vào chú thích. Chú thích trong mã viết *"hai phần thi mô hình được
huấn luyện trên đó"*, nên enum đầu tiên làm ra chỉ có `P3` và `P4`. Test đỏ ngay:
có **ba** — `P5` là đề dài 120–300 giây, **cố ý** nằm ngoài dải huấn luyện, được
chấm bằng cắt cửa sổ và luôn chuyển giảng viên. Tức là `part` chính là thứ quyết
định bài đi theo nhánh chấm nào, và một chuỗi tự do đã giấu mất điều đó.

### Ba điểm giữ nguyên, có lý do

| # | Điểm | Trả lời thế nào |
| --- | --- | --- |
| 2 | `Assessment` là «entity» mà không có thuộc tính định danh | "Khoá của nó là `responseId`; quan hệ 1–1 làm khoá riêng thành thừa. Giữ «entity» vì nó **biến đổi** — giảng viên sửa điểm — nên không thể là value object." |
| 5 | Bội số `1..*` giữa `Comment` và `Evidence` | **Nhận định trước của em chưa đủ và em đã sửa lại.** Ràng buộc này **có** được giữ trong mã sản xuất: `CommentBuilder.comments()` kết thúc bằng `return [c for c in out if c.evidence_refs]`. Mô hình vẫn cho phép một `Comment` rỗng tồn tại riêng lẻ, và đó là chủ ý: thiếu trích dẫn thì mất **câu đó**, không hỏng cả báo cáo |
| 9 | Sơ đồ không có quan hệ kết hợp nào | "Đúng với mô hình này — không có đối tượng nào dùng chung giữa hai thể. Khác bản OneShop (16 kết hợp) vì bản chất bài toán khác." |

### Một chênh lệch vẫn mở

**FR-24 ghi tối đa 6 bằng chứng, mã cho tới 10.** Hình vẽ theo **mã**. Sửa tài
liệu yêu cầu hay sửa mã là quyết định chưa làm, và nó được ghi trong báo cáo tuần
1 mục 11.3 là *"chưa sửa"* chứ không bị che đi. Bốn lớp của mô hình miền vẫn nằm
ở tầng lưu trữ thay vì `contracts.py` — dời chúng là một lần tái cấu trúc riêng.

**Một câu để kết:**

> "Chín điểm này em ghi ra trước vì nếu thầy/cô tìm được chúng mà em không biết,
> thì những phần em vừa trình bày cũng mất giá trị. Sáu cái đã sửa, ba cái giữ
> nguyên và em nói được lý do."

## 11. Cách tái tạo hình và những test giữ nó đúng

Hình **không** được kéo thả bằng tay. Nó do một bộ sinh tạo ra từ một đặc tả
ngắn, nên nội dung và bố cục không lệch nhau được:

```bash
.venv/bin/python tools/gen_class_diagram.py && ./render.sh
```

Bộ sinh giải quyết một việc mà draw.io không tự làm được: **định tuyến đường nối
sao cho không đường nào đè lên nhau.** Bản đầu tiên có bố cục đúng nhưng đọc
không ra — kết quả đo được:

| Phép đo | Trước | Sau |
| --- | --- | --- |
| Đoạn đi xuyên một hộp thứ ba | 0 | 0 |
| Đoạn kẻ ngang qua lòng **hộp đầu mút của chính nó** | 10 | 0 |
| Cặp đường **trùng nhau** | 19 | 0 |
| Cặp cách nhau dưới 8 điểm | 4 | 0 |

Nặng nhất là `Assessment→CriterionCoverage` chồng `Assessment→ReasonCode`
**755 điểm**. Cách sửa: mỗi cạnh được cấp **một làn dọc riêng** trong từng khe
giữa hai cột nó đi qua, cộng một cổng ra và một cổng vào riêng cách nhau tối
thiểu 22 điểm.

Nếu giảng viên hỏi *"em kiểm bằng mắt hay bằng gì?"* — bằng test đọc trực tiếp
toạ độ trong tệp `.drawio`, chạy trên CI:

```bash
.venv/bin/python -m pytest tests/test_diagrams.py -q
```

Mười ba test, mỗi cái ghim một điều khác nhau. Bảng đầy đủ ở câu hỏi 11.

---

## Phụ lục — tái tạo hai ví dụ ở mục 6 và 7

Chạy được ngay, không nạp mô hình nhận dạng tiếng nói nên rất nhanh:

```python
import random
from aicefr.contracts import Word
from aicefr.features.extract import FeatureExtractor
from aicefr.scoring.scorer import RidgeScorer, load_model, out_of_distribution

random.seed(11)
kho = ("my hometown located southern part vietnam quite small town however people there "
       "very friendly helpful weather warm almost year round many traditional markets "
       "where families buy fresh vegetables early morning i usually visit grandparents "
       "during summer holiday they live near river with beautiful bridge").split()
words, t = [], 0.5
for i in range(96):
    w = kho[i % len(kho)] if i % 23 else "erm"
    dur = 0.26 + random.random() * 0.2
    words.append(Word(text=w, start_s=round(t, 2), end_s=round(t + dur, 2),
                      prob=round(0.70 + random.random() * 0.28, 2)))
    t += dur + (0.8 if i % 15 == 14 else 0.1)

segs = [(0.5, 17.8), (18.8, 36.2), (37.1, 53.9)]
fs = FeatureExtractor().extract(words, segs, 54.5)
a = RidgeScorer().score(fs)

print("ttr =", round(fs.value_of("ttr"), 4))
print("overall_0_6 =", a.overall_0_6, "| band =", a.overall_band)
print("reasons =", [r.value for r in a.reasons])
for c in a.criteria:
    print(c.criterion.value, c.coverage)
```

Cho ra đúng: `ttr = 0.4688`, `overall_0_6 = 4.13`, `band = B2`,
`reasons = ['SCORE_NEAR_BOUNDARY']`, cả năm tiêu chí `coverage = 1.0`.

Để có **ví dụ bị từ chối chấm** ở mục 7, đổi `kho` thành một kho từ hẹp hơn
(khoảng 18 từ khác nhau, lặp lại) — `ttr` tụt xuống 0,17 và kết quả thành
`overall_0_6 = None`, `reasons = ['OUT_OF_DISTRIBUTION']`.

---

## Tài liệu liên quan

- `docs/sdd/SDD.md` mục 3.2 — quyết định thiết kế và lý do
- `docs/sdd/SDD.md` mục 3.2.1 — bất biến hình học của đường nối
- `docs/sdd/SDD.md` mục 3.2.2 — bảng các điểm còn phải bàn
- `docs/reports/bao_cao_tuan_01.md` mục 10 — bản trình bày đầy đủ cho tuần 1
- `docs/reports/bao_cao_tuan_01.md` mục 10.4 — từng lớp làm gì và vì sao cần
- `src/aicefr/contracts.py` — nơi 18 trong 22 lớp được khai báo
- `tools/gen_class_diagram.py` — bộ sinh hình
- `tests/test_diagrams.py` — 12 test giữ hình khớp mã
