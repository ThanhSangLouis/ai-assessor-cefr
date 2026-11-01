"""The assessment prompts by band (D076).

* the bank gives every band A1..C2 prompts of the two kinds the scoring model
  knows (P3, P4), at 40-60 seconds, each with English topic words;
* the first two prompts are the bank's B1 ones and the long talk P5 is retired;
* the task list says each prompt's band;
* teachers add, reword (a new version) and retire prompts; learners cannot.
"""

from __future__ import annotations

from collections import Counter

import pytest
from test_billing import boot
from test_lessons_integration import login_as

from aicefr.contracts import Band, TaskPart
from aicefr.practice.assessment_bank import ASSESSMENT_PROMPTS, MAX_SECONDS, MIN_SECONDS

TEACH = "/api/v1/teach/tasks"


@pytest.mark.unit
def test_every_band_has_prompts_of_both_kinds_with_topic_words():
    per = Counter((p.band, p.part) for p in ASSESSMENT_PROMPTS)
    for band in Band:
        for part in (TaskPart.P3, TaskPart.P4):
            # B1 also has the two prompts the system started with.
            assert per[(band, part)] >= (2 if band is Band.B1 else 3), (band, part)
    assert len({p.task_id for p in ASSESSMENT_PROMPTS}) == len(ASSESSMENT_PROMPTS)
    for p in ASSESSMENT_PROMPTS:
        words = [w.strip() for w in p.topic_keywords.split(",")]
        assert len(words) >= 10 and all(w and " " not in w for w in words), p.task_id
    assert (MIN_SECONDS, MAX_SECONDS) == (40, 60)  # the model's training range


def test_learners_see_the_bank_by_band_and_no_long_talk(tmp_path, monkeypatch):
    m = boot(tmp_path, monkeypatch)
    tasks = login_as(m, "SV-001").get("/api/v1/tasks").json()
    bands = Counter(t["band"] for t in tasks)
    assert set(bands) == {b.value for b in Band} and all(n >= 6 for n in bands.values())
    assert {t["part"] for t in tasks} == {"P3", "P4"}
    assert all((t["min_seconds"], t["max_seconds"]) == (40, 60) for t in tasks)
    by_id = {t["task_id"]: t for t in tasks}
    assert by_id["P3"]["band"] == by_id["P4"]["band"] == "B1"
    assert "P5" not in by_id


def test_a_teacher_adds_rewords_and_retires_a_prompt(tmp_path, monkeypatch):
    m = boot(tmp_path, monkeypatch)
    teacher = login_as(m, "GV-01", "teacher")
    student = login_as(m, "SV-001")
    body = {
        "band": "A2",
        "part": "P3",
        "prompt_text": "Bạn thích sống ở thành phố hay nông thôn? Vì sao?",
        "topic_keywords": "City, countryside, village, quiet, city",
    }
    made = teacher.post(TEACH, json=body)
    assert made.status_code == 200, made.text
    task_id = made.json()["task_id"]
    row = next(t for t in teacher.get(TEACH).json() if t["task_id"] == task_id)
    assert (row["band"], row["prompt_version"], row["active"]) == ("A2", "v1", True)
    assert row["topic_keywords"] == ["city", "countryside", "village", "quiet"]
    assert task_id in {t["task_id"] for t in student.get("/api/v1/tasks").json()}

    edit = {"prompt_text": "Bạn muốn sống ở thành phố hay nông thôn khi về già? Vì sao?"}
    assert teacher.patch(f"{TEACH}/{task_id}", json=edit).status_code == 200
    row = next(t for t in teacher.get(TEACH).json() if t["task_id"] == task_id)
    assert row["prompt_version"] == "v2"  # earlier reports keep the old wording

    assert teacher.patch(f"{TEACH}/{task_id}", json={"active": False}).status_code == 200
    assert task_id not in {t["task_id"] for t in student.get("/api/v1/tasks").json()}
    assert teacher.patch(f"{TEACH}/khong-co", json={"active": False}).status_code == 404


def test_only_the_kinds_the_model_knows_and_only_staff(tmp_path, monkeypatch):
    m = boot(tmp_path, monkeypatch)
    teacher = login_as(m, "GV-01", "teacher")
    student = login_as(m, "SV-001")
    long_talk = {"band": "B2", "part": "P5", "prompt_text": "Thuyết trình năm phút về bất cứ gì."}
    assert teacher.post(TEACH, json=long_talk).status_code == 422
    assert student.get(TEACH).status_code == 403
    assert student.post(TEACH, json={**long_talk, "part": "P3"}).status_code == 403
    page = teacher.get("/teach/tasks")
    assert page.status_code == 200 and "Đề đánh giá theo band" in page.text
    gone = student.get("/teach/tasks", follow_redirects=False)
    assert gone.status_code == 303
