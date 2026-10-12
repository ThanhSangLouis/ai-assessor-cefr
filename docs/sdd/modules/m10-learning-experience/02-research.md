# M10 — Research và Adaptation Map

**Version:** v0.1 · **STATUS:** DRAFT.
**Reference:** Sang `40907cc`, D023/D025–D027/D032; source chỉ đọc.

| REF-ID | Nguồn | Áp dụng | Quyết định |
| --- | --- | --- | --- |
| M10-REF-01 | `practice/bank.py`, `missions.py`, `feedback.py`, `recommend.py` | giữ mission/rule/recommend pattern, đổi sang contract/repository target | ADAPT |
| M10-REF-02 | `lessons/model.py`, `checks.py`, `align.py`, `text.py` | giữ nine-step domain và evidence semantics | ADAPT |
| M10-REF-03 | `lessons/seed.py`, `seed_topics.py` | kiểm kê seed 18/31, hash và idempotency | ADAPT |
| M10-REF-04 | `lesson_repository.py` | tham khảo persistence; target dùng migration/service hiện hành | INSPIRE |
| M10-REF-05 | `achievements.py`, `streak.py` | giữ effort-only invariants | ADAPT |
| M10-REF-06 | practice/lesson/teach UI | dùng flow/state, không copy router hoặc branding | INSPIRE |

Target hiện chưa có package practice/lessons; pipeline target đã có QC/ASR/feature/scoring và phải có nhánh purpose rõ để tránh accidental scoring. Rủi ro chính: seed ghi đè teacher content, published version bị mutate, practice lọt vào nghiên cứu, và wording UI biến measurement thành score.

Kết luận: một learning application service điều phối domain/repository; assessment pipeline và learning pipeline dùng chung audio/QC/ASR adapter nhưng tách disposition/persistence sau transcript.
