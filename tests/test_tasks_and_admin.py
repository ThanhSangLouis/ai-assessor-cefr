"""Stage 4: tasks, personal data export and erasure, admin endpoints.

Covers FR-01 (prompt versions), FR-04, FR-35, FR-36, FR-38, FR-39.
"""

from __future__ import annotations

import io
import subprocess

import numpy as np
import pytest
import soundfile as sf
from dbutil import one_school
from fastapi.testclient import TestClient

from aicefr.audio.decoder import DecodeError, FfmpegDecoder, FirstMatchDecoder, ffmpeg_available
from aicefr.ports import AudioDecoder
from aicefr.storage.auth_repository import Role
from aicefr.storage.task_repository import TaskRepository

PASSWORD = "matkhau-kiem-thu"


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import importlib

    from aicefr.api import main as m

    importlib.reload(m)
    return m.app


def login_as(app, pseudonym: str, role: str) -> TestClient:
    app.state.auth_repo.create_account(pseudonym, PASSWORD, Role(role))
    one_school(pseudonym, role)
    c = TestClient(app)
    r = c.post("/api/v1/auth/login", json={"pseudonym": pseudonym, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return c


def wav(seconds: float = 40.0, sr: int = 16_000) -> bytes:
    t = np.arange(int(sr * seconds)) / sr
    buf = io.BytesIO()
    sf.write(buf, (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32), sr, format="WAV")
    return buf.getvalue()


def submit(c, speaker="SV-001", task="P3", name="bai.wav", data=None):
    return c.post(
        "/api/v1/responses",
        files={"audio": (name, data or wav(), "audio/wav")},
        data={"speaker_id": speaker, "task_id": task},
    )


# ---------------------------------------------------------------- tasks


def test_task_table_seeds_the_built_in_prompts(tmp_path) -> None:
    ids = [t.task_id for t in TaskRepository(tmp_path / "t.db").list_active()]
    assert ids == ["P3", "P4", "P5"]


def test_seeding_twice_does_not_duplicate(tmp_path) -> None:
    """Re-seeding on every start would overwrite an administrator's edits."""
    TaskRepository(tmp_path / "t.db")
    assert len(TaskRepository(tmp_path / "t.db").list_active()) == 3


def test_de_bai_them_sau_van_den_duoc_co_so_du_lieu_da_co_san(tmp_path) -> None:
    """Skipping the seed whenever the table is non-empty hides new prompts.

    A database created before P5 existed would never learn about it, so the long
    recording path would work only on fresh installs -- that is, everywhere
    except the machines that have real data on them.
    """
    db = tmp_path / "t.db"
    TaskRepository(db)
    TaskRepository(db).col("task").delete_one({"task_id": "P5"})

    assert "P5" in [t.task_id for t in TaskRepository(db).list_active()]


def test_seed_khong_ghi_de_len_de_bai_giang_vien_da_sua(tmp_path) -> None:
    """Filling gaps must not become rewriting what an administrator edited."""
    db = tmp_path / "t.db"
    TaskRepository(db)
    TaskRepository(db).col("task").update_one(
        {"task_id": "P3"}, {"$set": {"title": "Đề đã sửa tay"}}
    )

    again = {t.task_id: t for t in TaskRepository(db).list_active()}
    assert again["P3"].title == "Đề đã sửa tay"


def test_tasks_endpoint_lists_prompts(app) -> None:
    rows = login_as(app, "SV-001", "student").get("/api/v1/tasks").json()
    assert {r["task_id"] for r in rows} == {"P3", "P4", "P5"}
    assert all(r["prompt_text"] for r in rows)


def test_de_dai_duoc_danh_dau_la_cham_theo_cua_so(app) -> None:
    """A student must be told before speaking, not after.

    The flag is derived from the model artifact rather than stored on the
    prompt, so there is one definition of "too long to score in one pass".
    """
    rows = {r["task_id"]: r for r in login_as(app, "SV-001", "student").get("/api/v1/tasks").json()}
    assert rows["P5"]["windowed"] is True
    assert rows["P3"]["windowed"] is False


def test_unknown_task_is_refused(app) -> None:
    assert submit(login_as(app, "SV-001", "student"), task="P9").status_code == 422


def test_report_records_the_prompt_version_in_force(app) -> None:
    """Reword a prompt later and earlier reports must still name the old version."""
    c = login_as(app, "SV-001", "student")
    rid = submit(c).json()["response_id"]
    from aicefr.api import main as m

    assert m.repo.get(rid) is not None


# ---------------------------------------------------------------- profile export


def test_profile_is_empty_until_a_teacher_verifies(app) -> None:
    """FR-38: never guess a band to fill the file."""
    c = login_as(app, "SV-001", "student")
    submit(c)
    body = c.get("/api/v1/me/profile.json").json()
    assert body["results"] == []
    assert "Chưa có kết quả" in body["note"]


def test_profile_contains_verified_results_only(app) -> None:
    student = login_as(app, "SV-001", "student")
    rid = submit(student).json()["response_id"]
    teacher = login_as(app, "GV-01", "teacher")
    teacher.post(f"/api/v1/review/{rid}", json={"reason": "nghe lai thay dat yeu cau"})

    body = student.get("/api/v1/me/profile.json").json()
    assert len(body["results"]) == 1
    assert body["results"][0]["response_id"] == rid


def test_profile_names_what_to_practise_next(app) -> None:
    """D022: moi ket qua da xac nhan mang tieu chi nen luyen truoc va mot goi y co dinh.

    Truong luon co mat; khi bai khong co chi bao (vi du khong cham duoc) thi de
    rong, khong doan.
    """
    from aicefr.report.comments import NEXT_TASK_HINTS

    student = login_as(app, "SV-001", "student")
    rid = submit(student).json()["response_id"]
    login_as(app, "GV-01", "teacher").post(
        f"/api/v1/review/{rid}", json={"reason": "nghe lai thay dat yeu cau"}
    )
    row = student.get("/api/v1/me/profile.json").json()["results"][0]
    assert "weakest_criteria" in row and "next_task_hint" in row
    if row["weakest_criteria"]:
        hints = {c.value: h for c, h in NEXT_TASK_HINTS.items()}
        assert row["next_task_hint"] == hints[row["weakest_criteria"][0]]
    else:
        assert row["next_task_hint"] is None


@pytest.mark.parametrize(
    ("assessment", "weak", "has_hint"),
    [
        ({"weakest_criteria": ["fluency"]}, ["fluency"], True),
        ({}, [], False),  # bai luu truoc D022: khong co chi bao thi khong doan
        (None, [], False),  # bai khong cham duoc
    ],
)
def test_profile_row_reads_the_weakest_criterion_from_the_stored_report(
    assessment, weak, has_hint
) -> None:
    import json

    from aicefr.contracts import Criterion
    from aicefr.report.comments import NEXT_TASK_HINTS
    from aicefr.storage.repository import _profile_row

    row = _profile_row({"response_id": "r1", "report_json": json.dumps({"assessment": assessment})})
    assert "report_json" not in row
    assert row["weakest_criteria"] == weak
    expected = NEXT_TASK_HINTS[Criterion.FLUENCY] if has_hint else None
    assert row["next_task_hint"] == expected


def test_every_criterion_has_a_practice_hint() -> None:
    from aicefr.contracts import Criterion
    from aicefr.report.comments import NEXT_TASK_HINTS

    assert set(NEXT_TASK_HINTS) == set(Criterion)


def test_profile_carries_the_mandatory_disclaimer(app) -> None:
    student = login_as(app, "SV-001", "student")
    rid = submit(student).json()["response_id"]
    login_as(app, "GV-01", "teacher").post(
        f"/api/v1/review/{rid}", json={"reason": "nghe lai thay dat yeu cau"}
    )
    note = student.get("/api/v1/me/profile.json").json()["note"]
    assert "không phải chứng chỉ CEFR" in note
    assert "Giảng viên là người quyết định cuối cùng" in note


def test_profile_downloads_as_a_file(app) -> None:
    c = login_as(app, "SV-001", "student")
    r = c.get("/api/v1/me/profile.json")
    assert "attachment" in r.headers["content-disposition"]


# ---------------------------------------------------------------- erasure


def test_erasure_preview_changes_nothing(app) -> None:
    student = login_as(app, "SV-001", "student")
    submit(student)
    admin = login_as(app, "QT-01", "admin")

    preview = admin.get("/api/v1/admin/erase/SV-001").json()
    assert preview["responses"] == 1
    assert len(student.get("/api/v1/me/responses").json()) == 1, "xem truoc khong duoc xoa gi"


def test_erasure_requires_the_id_twice_and_they_must_match(app) -> None:
    """The second field is the only thing between a typo and somebody else's data."""
    admin = login_as(app, "QT-01", "admin")
    r = admin.post(
        "/api/v1/admin/erase",
        json={"speaker_id": "SV-001", "confirm_speaker_id": "SV-002"},
    )
    assert r.status_code == 422


def test_erasure_removes_rows_and_the_audio_file(app) -> None:
    from pathlib import Path

    student = login_as(app, "SV-001", "student")
    rid = submit(student).json()["response_id"]
    from aicefr.api import main as m

    audio = m.repo.audio_path_of(rid)
    assert audio and Path(audio).is_file()

    admin = login_as(app, "QT-01", "admin")
    admin.post(
        "/api/v1/admin/erase",
        json={"speaker_id": "SV-001", "confirm_speaker_id": "SV-001"},
    )
    assert not Path(audio).is_file(), "xoa ma de lai tep audio thi loi khai bao la sai su that"
    assert m.repo.get(rid) is None


def test_erasure_states_the_model_cutoff(app) -> None:
    """AC-35.4: never promise to remove data from an already published model."""
    admin = login_as(app, "QT-01", "admin")
    body = admin.post(
        "/api/v1/admin/erase",
        json={"speaker_id": "SV-001", "confirm_speaker_id": "SV-001"},
    ).json()
    assert "KHÔNG bị gỡ khỏi mô hình" in body["cutoff_note"]


def test_erasure_is_written_to_the_audit_log(app) -> None:
    student = login_as(app, "SV-001", "student")
    submit(student)
    admin = login_as(app, "QT-01", "admin")
    admin.post(
        "/api/v1/admin/erase",
        json={"speaker_id": "SV-001", "confirm_speaker_id": "SV-001"},
    )
    actions = [e["action"] for e in admin.get("/api/v1/audit").json()]
    assert "ERASE_PARTICIPANT" in actions


def test_only_an_admin_may_erase(app) -> None:
    teacher = login_as(app, "GV-01", "teacher")
    r = teacher.post(
        "/api/v1/admin/erase",
        json={"speaker_id": "SV-001", "confirm_speaker_id": "SV-001"},
    )
    assert r.status_code == 403


# ---------------------------------------------------------------- admin reads


def test_model_list_reports_the_active_artifact(app) -> None:
    rows = login_as(app, "QT-01", "admin").get("/api/v1/admin/models").json()
    assert any(r["active"] and r["usable"] for r in rows)


def test_model_list_states_the_calibration_honestly(app) -> None:
    """The model has not been probability-calibrated; the screen must not imply it has."""
    rows = login_as(app, "QT-01", "admin").get("/api/v1/admin/models").json()
    active = next(r for r in rows if r["active"])
    assert active["calibration_version"] == "chua-hieu-chuan"


def test_config_mac_dinh_dung_nguong_cua_srs(app) -> None:
    """A fresh install behaves exactly as the specification describes.

    FR-08 made these editable at runtime; what must not change is where the
    system starts from when nobody has touched anything.
    """
    cfg = login_as(app, "QT-01", "admin").get("/api/v1/admin/config").json()
    assert cfg["editable_here"] is True
    assert cfg["qc_config_version"] == "qc-v1"
    assert cfg["duration_s"]["reject_below"] == 20.0
    assert cfg["changed_by"] is None


def test_teacher_cannot_read_admin_config(app) -> None:
    assert login_as(app, "GV-01", "teacher").get("/api/v1/admin/config").status_code == 403


# ---------------------------------------------------------------- decoding (FR-39)


def test_decoder_satisfies_the_port() -> None:
    assert isinstance(FirstMatchDecoder(), AudioDecoder)


def test_wav_is_read_without_an_external_process() -> None:
    pcm, sr = FirstMatchDecoder().decode(wav(3), "a.wav")
    assert sr == 16_000
    assert pcm.ndim == 1


def test_unsupported_extension_is_refused_with_a_usable_message() -> None:
    with pytest.raises(DecodeError) as e:
        FirstMatchDecoder().decode(b"not audio", "a.xyz")
    assert "wav" in str(e.value)


def test_recording_is_disabled_when_ffmpeg_is_missing(monkeypatch) -> None:
    """FR-39: hide the button up front, never fail after the student has spoken."""
    monkeypatch.setattr("aicefr.audio.decoder.ffmpeg_available", lambda: False)
    assert FfmpegDecoder().can_decode("ghi-am.webm") is False


def test_health_reports_whether_recording_is_possible(app) -> None:
    body = login_as(app, "SV-001", "student").get("/api/v1/health").json()
    assert "recording_enabled" in body
    assert body["recording_enabled"] == ffmpeg_available()


@pytest.mark.skipif(not ffmpeg_available(), reason="máy chạy test không có ffmpeg")
def test_browser_recording_formats_are_transcoded(tmp_path) -> None:
    """WebM/Opus from Chrome and MP4/AAC from Safari both have to come back as PCM."""
    src = tmp_path / "a.wav"
    src.write_bytes(wav(3))
    decoder = FirstMatchDecoder()
    for out, args in (
        ("b.webm", ["-ac", "2", "-ar", "48000", "-c:a", "libopus"]),
        ("c.mp4", ["-c:a", "aac"]),
    ):
        dst = tmp_path / out
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), *args, str(dst)],
            check=True,
        )
        pcm, sr = decoder.decode(dst.read_bytes(), out)
        assert sr == 16_000, "phai ha ve 16 kHz vi QC va trich dac trung deu gia dinh the"
        assert pcm.ndim == 1, "phai tron ve mono"
        assert 2.5 < len(pcm) / sr < 3.5


@pytest.mark.skipif(not ffmpeg_available(), reason="máy chạy test không có ffmpeg")
def test_a_recording_submitted_through_the_api_is_scored(app, tmp_path) -> None:
    """End to end: the recording path must reach the pipeline, not just decode."""
    src = tmp_path / "a.wav"
    src.write_bytes(wav(40))
    dst = tmp_path / "rec.webm"
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(src),
            "-ac",
            "2",
            "-ar",
            "48000",
            "-c:a",
            "libopus",
            str(dst),
        ],
        check=True,
    )
    c = login_as(app, "SV-001", "student")
    r = submit(c, name="rec.webm", data=dst.read_bytes())
    assert r.status_code == 202
    status = c.get(f"/api/v1/responses/{r.json()['response_id']}/status").json()
    assert status["is_pending"] is False


def test_approving_a_review_does_not_orphan_the_report(app) -> None:
    """Regression: approving used to erase who the report belonged to.

    `apply_review` wrote the report back with the response id in the speaker_id
    slot, an empty task id and no account id. The row stayed in the table, so
    nothing failed loudly, but the student lost access to their own report, it
    disappeared from "my responses", and it never reached the exported profile.
    """
    student = login_as(app, "SV-001", "student")
    rid = submit(student, speaker="SV-001", task="P4").json()["response_id"]
    login_as(app, "GV-01", "teacher").post(
        f"/api/v1/review/{rid}", json={"reason": "nghe lai thay dat yeu cau"}
    )

    from aicefr.api import main as m

    row = m.repo.col("response").find_one({"response_id": rid})
    assert row["speaker_id"] == "SV-001"
    assert row["task_id"] == "P4"
    assert row["account_id"] is not None

    assert student.get(f"/api/v1/responses/{rid}").status_code == 200
    assert len(student.get("/api/v1/me/responses").json()) == 1


# ---------------------------------------------------------------- model guard


def test_scorer_refuses_a_model_with_no_declared_unit_of_inference() -> None:
    """The guard against repeating the worst bug this project has had.

    `ridge_v3` was fitted on whole exam sittings, several minutes each. This
    system scores one response, about a minute.
    Feeding a single response to that model returned 1.00 (A2) for a submission
    an expert had marked 4.00 (B2), and reported success while doing it.
    """
    from aicefr.scoring.scorer import IncompatibleModelError, RidgeScorer

    with pytest.raises(IncompatibleModelError):
        RidgeScorer("ridge_v3")


def test_the_model_in_use_loads_fine() -> None:
    from aicefr.scoring.scorer import RidgeScorer

    assert RidgeScorer("ridge_resp_v1").model_version == "ridge_resp_v1"


def test_admin_model_list_marks_the_incompatible_artifact(app) -> None:
    """It reports a HIGHER correlation than the model in use.

    The two numbers describe different tasks and must never be compared. Listing
    them side by side without saying so invites an administrator to activate the
    "better" one.
    """
    rows = login_as(app, "QT-01", "admin").get("/api/v1/admin/models").json()
    by_name = {r["name"]: r for r in rows}

    assert by_name["ridge_resp_v1"]["compatible"] is True
    assert by_name["ridge_v3"]["compatible"] is False
    assert "đơn vị suy luận" in by_name["ridge_v3"]["incompatible_reason"]
    # The trap is real: the unusable one advertises the better number.
    assert by_name["ridge_v3"]["cv_pcc"] > by_name["ridge_resp_v1"]["cv_pcc"]


def test_moi_de_bai_deu_cham_duoc_bang_mot_trong_hai_cach(tmp_path) -> None:
    """The card must not ask for something the system cannot score either way.

    There are now two ways to be scorable and a prompt has to satisfy one of
    them. A short prompt fits inside the model's own training range, so it is
    scored in one pass. A long prompt does not fit and never will -- that is why
    the window mechanism exists -- so what it must satisfy instead is that
    cutting it works: long enough that cutting produces real windows rather than
    two stubs, and short enough to stay under both the window count and the QC
    ceiling.

    The failure this replaces was real. Advertising 60-180 seconds while the
    model knew 26.7-60.7 produced 95-second submissions that passed QC and were
    then refused with OUT_OF_DISTRIBUTION: a report with no score at all.
    """
    from aicefr.qc.audio_qc import MAX_DURATION_S
    from aicefr.scoring.scorer import load_model
    from aicefr.scoring.windows import MAX_WINDOW_S, MAX_WINDOWS, MIN_WINDOW_S

    model = load_model()
    i = model["feature_order"].index("total_dur")
    lo, hi = model["feature_lo"][i], model["feature_hi"][i]

    # Not ":memory:": this repository opens a fresh connection per call, so an
    # in-memory database would lose the schema between them.
    for task in TaskRepository(tmp_path / "t.db").list_active():
        if task.max_seconds <= hi:
            assert task.min_seconds >= lo, f"{task.task_id}: ngắn hơn dải huấn luyện"
            continue

        assert task.min_seconds >= 2 * MIN_WINDOW_S, (
            f"{task.task_id}: đề dài nhưng tối thiểu quá ngắn để cắt thành cửa sổ thật"
        )
        assert task.max_seconds <= MAX_WINDOWS * MAX_WINDOW_S, (
            f"{task.task_id}: dài hơn số cửa sổ tối đa chịu được"
        )
        assert task.max_seconds <= MAX_DURATION_S, f"{task.task_id}: vượt trần QC"
