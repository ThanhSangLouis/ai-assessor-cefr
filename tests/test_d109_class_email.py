"""Email about classes (D109): the invited student and the class's teachers hear of it.

The assessment service publishes `classroom.invited` and `classroom.joined` on
the bus; the identity service, where the addresses are, emails. Emails land in
the in-memory outbox (`AICEFR_EMAIL_PROVIDER=outbox`).
"""

from __future__ import annotations

import pytest
from dbutil import email_of
from test_billing import boot
from test_classes import login_as, make_class

from aicefr.contracts import CLASS_INVITED, CLASS_JOINED
from aicefr.notify import classes
from aicefr.notify.email import has_mailbox, outbox
from aicefr.notify.messages import class_invite_email, class_joined_email

pytestmark = pytest.mark.integration

SITE = "https://speakup.example.vn"


@pytest.fixture
def m(tmp_path, monkeypatch):
    outbox().sent.clear()
    return boot(tmp_path, monkeypatch, AICEFR_EMAIL_PROVIDER="outbox", AICEFR_PUBLIC_URL=SITE)


def mail_to(address: str) -> list:
    return [e for e in outbox().sent if e.to == address]


def test_an_invited_student_gets_one_email_with_the_way_to_answer(m):
    teacher = login_as(m, "GV-01", "teacher")
    login_as(m, "SV-001")
    outbox().sent.clear()
    cid = make_class(teacher, "Lớp nói B1")["class_id"]
    people = {"people": [email_of("SV-001")]}
    teacher.post(f"/api/v1/classes/{cid}/members", json=people)
    teacher.post(f"/api/v1/classes/{cid}/members", json=people)  # pending: no second email

    [email] = mail_to(email_of("SV-001"))
    assert "Lớp nói B1" in email.subject and "mời bạn vào lớp" in email.subject
    assert f"{SITE}/my-classes" in email.text and f"{SITE}/my-classes" in email.html
    assert "rời lớp" in email.text.lower()
    assert mail_to(email_of("GV-01")) == []


def test_the_teachers_hear_when_a_student_accepts_or_joins_by_code(m):
    teacher = login_as(m, "GV-01", "teacher")
    first = login_as(m, "SV-001")
    second = login_as(m, "SV-002")
    cid = make_class(teacher, "Lớp nói B1")["class_id"]
    teacher.post(f"/api/v1/classes/{cid}/members", json={"people": [email_of("SV-001")]})
    outbox().sent.clear()

    first.post(f"/api/v1/me/classes/{cid}/accept")
    [accepted] = mail_to(email_of("GV-01"))
    assert "vừa vào lớp Lớp nói B1" in accepted.subject
    assert "nhận lời mời" in accepted.text and f"{SITE}/teach/classes/{cid}" in accepted.text

    code = teacher.post(f"/api/v1/classes/{cid}/code").json()["join_code"]
    second.post("/api/v1/me/classes/join", json={"code": code})
    second.post("/api/v1/me/classes/join", json={"code": code})  # a member already: no email
    by_code = mail_to(email_of("GV-01"))[1:]
    assert len(by_code) == 1 and "nhập mã lớp" in by_code[0].text
    assert "2 sinh viên" in by_code[0].text


def test_an_administrator_adding_or_a_decline_sends_no_email(m):
    teacher = login_as(m, "GV-01", "teacher")
    admin = login_as(m, "QT-01", "admin")
    student = login_as(m, "SV-001")
    login_as(m, "SV-002")
    cid = make_class(teacher)["class_id"]
    outbox().sent.clear()
    admin.post(f"/api/v1/classes/{cid}/members", json={"people": [email_of("SV-002")]})
    teacher.post(f"/api/v1/classes/{cid}/members", json={"people": [email_of("SV-001")]})
    student.post(f"/api/v1/me/classes/{cid}/decline")
    assert [e.to for e in outbox().sent] == [email_of("SV-001")]  # the invitation only


def test_a_second_delivery_of_an_event_sends_no_second_email(m):
    teacher = login_as(m, "GV-01", "teacher")
    student = login_as(m, "SV-001")
    cid = make_class(teacher)["class_id"]
    student_id = student.get("/api/v1/me").json()["account_id"]
    teacher_id = teacher.get("/api/v1/me").json()["account_id"]
    auth = m.app.state.auth_repo
    outbox().sent.clear()
    invited = dict(
        class_id=cid, class_name="Lớp", account_id=student_id, by=teacher_id,
        at="2026-11-16T10:00:00+00:00",
    )  # fmt: skip
    joined = dict(
        class_id=cid, class_name="Lớp", account_id=student_id, via="code",
        teacher_ids=[teacher_id], members=1, at="2026-11-16T10:01:00+00:00",
    )  # fmt: skip

    # Redis Streams may hand the same event over again (at least once).
    assert classes.on_invited(invited, auth, outbox(), SITE) is True
    assert classes.on_invited(invited, auth, outbox(), SITE) is False
    assert classes.on_joined(joined, auth, outbox(), SITE) == 1
    assert classes.on_joined(joined, auth, outbox(), SITE) == 0
    assert len(outbox().sent) == 2
    assert (CLASS_INVITED, CLASS_JOINED) == ("classroom.invited", "classroom.joined")


@pytest.mark.unit
def test_a_demo_address_has_no_mailbox():
    assert has_mailbox("an@truong.edu.vn")
    assert not has_mailbox("sv-001@demo.speakup.fit")
    assert not has_mailbox("SV-001@DEMO.SPEAKUP.FIT")
    assert not has_mailbox(None) and not has_mailbox("khong-phai-email")


@pytest.mark.unit
def test_the_class_emails_say_who_which_class_and_nothing_secret():
    invite = class_invite_email("an@vidu.vn", "An", "Lớp <b>B1</b>", "Cô Bình", SITE)
    assert "&lt;b&gt;" in invite.html and "<b>B1</b>" not in invite.html  # escaped
    assert "Cô Bình" in invite.text and "Lớp <b>B1</b>" in invite.text
    joined = class_joined_email(
        "binh@vidu.vn", "Bình", "An", "an@vidu.vn", "Lớp B1", "lop-1", "invite", 3, SITE
    )
    assert "Nhận lời mời" in joined.html and "3 sinh viên" in joined.text
    for email in (invite, joined):
        assert "mật khẩu" not in email.text and "password" not in email.html.lower()
