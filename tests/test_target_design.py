"""Kiem tra so do lop THIET KE DICH v3 (`docs/sdd/diagrams/target/`).

`tests/test_diagrams.py` bat so do HIEN TRANG mo ta dung ma dang chay. So do
dich thi nguoc lai: no di truoc ma, nen khong the doi chieu voi `src/`. Thu co
the -- va phai -- kiem la ban than thiet ke chat che:

  * moi thanh vien co kieu dung cu phap UML;
  * moi kieu ma mot thuoc tinh nhac ten deu duoc ve (khong co kieu mo coi);
  * moi hop thanh co thuoc tinh chua that va bo phan chi co mot the so huu;
  * tep `.drawio` dung la dau ra cua bo sinh, khong bi sua tay lech dac ta.
"""

from __future__ import annotations

import html
import pathlib
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

# The full design, and the overview drawn from the same rules for people to read.
DIAGRAMS = {
    "v3": pathlib.Path("docs/sdd/diagrams/target/02_class_v3.drawio"),
    "overview": pathlib.Path("docs/sdd/diagrams/target/02_class_v3_overview.drawio"),
}


@pytest.fixture(params=sorted(DIAGRAMS))
def spec(request) -> str:
    return request.param


# Kieu nguyen thuy va kieu cua thu vien chuan, khong phai lop cua mo hinh.
BUILTIN = {"str", "int", "float", "bool", "datetime", "Any"}

# Nhu `tests/test_diagrams.py::MEMBER`, them boi so `[0..1]` cua thuoc tinh
# (UML 2.5 cho phep boi so tren moi property). So do dich can no de ghi
# nguyen tac "thieu du lieu thi trong kem reason code" ngay tren hinh.
MEMBER = re.compile(r"^[+\-#] \w+(\([^)]*\))?: \w+(<[\w, ]+>)?( \[0\.\.1\])?$")


def _cells(spec: str) -> list[ET.Element]:
    return list(ET.parse(DIAGRAMS[spec]).getroot().iter("mxCell"))


def _boxes(spec: str) -> dict[str, tuple[str, bool]]:
    """id hop -> (ten lop, la enum hay khong)."""
    out = {}
    for c in _cells(spec):
        if "swimlane" in (c.get("style") or ""):
            value = c.get("value") or ""
            out[c.get("id")] = (value.split("<br>")[-1], "«enumeration»" in value)
    return out


def _members(spec: str) -> dict[str, list[str]]:
    boxes = _boxes(spec)
    rows: dict[str, list[str]] = {name: [] for name, _e in boxes.values()}
    for c in _cells(spec):
        if c.get("parent") in boxes and "swimlane" not in (c.get("style") or ""):
            rows[boxes[c.get("parent")][0]].append(html.unescape((c.get("value") or "").strip()))
    return rows


def _types_named(member: str) -> set[str]:
    """Moi ten kieu xuat hien sau dau `:` cua mot thuoc tinh hoac thao tac."""
    if ":" not in member:
        return set()  # dong cua hop enum: ten hang so, khong co kieu
    after = member.split(":", 1)[1] if "(" not in member else member.split("(", 1)[1]
    return set(re.findall(r"[A-Z]\w*|str|int|float|bool|datetime", after)) - {"List", "Map"}


def test_every_member_carries_a_uml_type(spec: str) -> None:
    enums = {name for name, is_enum in _boxes(spec).values() if is_enum}
    bad = [
        f"{cls}.{row}"
        for cls, rows in _members(spec).items()
        if cls not in enums
        for row in rows
        if not MEMBER.match(row)
    ]
    assert not bad, f"thành viên sai cú pháp UML: {bad}"


def test_no_type_is_left_undrawn(spec: str) -> None:
    """Thuoc tinh `ReasonCode` ma khong co hop `ReasonCode` la mot kieu mo coi."""
    drawn = {name for name, _e in _boxes(spec).values()}
    enums = {name for name, is_enum in _boxes(spec).values() if is_enum}
    orphan = sorted(
        {
            f"{cls} → {t}"
            for cls, rows in _members(spec).items()
            if cls not in enums
            for row in rows
            for t in _types_named(row)
            if t not in drawn and t not in BUILTIN
        }
    )
    assert not orphan, f"kiểu được nhắc tên nhưng không được vẽ: {orphan}"


def _compositions(spec: str) -> list[tuple[str, str]]:
    boxes = _boxes(spec)
    return [
        (boxes[c.get("source")][0], boxes[c.get("target")][0])
        for c in _cells(spec)
        if c.get("edge") == "1" and "diamondThin" in (c.get("style") or "")
    ]


def test_every_composition_has_a_containing_attribute(spec: str) -> None:
    members = _members(spec)
    bad = [
        f"{whole} ◆— {part}"
        for whole, part in _compositions(spec)
        if not any(part in _types_named(row) for row in members[whole] if "(" not in row)
    ]
    assert not bad, f"hợp thành nhưng thể không có thuộc tính chứa bộ phận: {bad}"


def test_every_composition_part_has_one_owner(spec: str) -> None:
    owners: dict[str, list[str]] = {}
    for whole, part in _compositions(spec):
        owners.setdefault(part, []).append(whole)
    shared = {part: ws for part, ws in owners.items() if len(ws) > 1}
    assert not shared, f"bộ phận của hợp thành bị nhiều thể sở hữu: {shared}"


def test_enum_values_are_unique_and_not_placeholders(spec: str) -> None:
    enums = {name for name, is_enum in _boxes(spec).values() if is_enum}
    for name in enums:
        rows = _members(spec)[name]
        assert rows, f"enum {name} rỗng"
        assert len(rows) == len(set(rows)), f"enum {name} có giá trị lặp"
        assert all(re.fullmatch(r"[A-Z][A-Z0-9_]*", r) for r in rows), f"enum {name}: {rows}"
    assert "..." not in DIAGRAMS[spec].read_text(encoding="utf-8")


def test_file_is_the_generator_output(spec: str, tmp_path: pathlib.Path) -> None:
    """Sua tay tren app.diagrams.net roi luu de len se lech dac ta ma khong ai biet."""
    out = tmp_path / f"{spec}.drawio"
    subprocess.run(
        [sys.executable, "tools/gen_class_diagram.py", "--spec", spec, "--out", str(out)],
        check=True,
        capture_output=True,
    )
    assert out.read_text(encoding="utf-8") == DIAGRAMS[spec].read_text(encoding="utf-8"), (
        f"{DIAGRAMS[spec].name} khác đầu ra của bộ sinh: "
        f"sửa tools/class_spec_{spec}.py rồi sinh lại"
    )


@pytest.mark.parametrize("name", ["Response", "QcResult", "Feature", "Account", "Consent"])
def test_superseded_names_are_gone(spec: str, name: str) -> None:
    """D1: tên lớp theo spec đã duyệt; tên cũ không được sót lại trên hình."""
    assert name not in {n for n, _e in _boxes(spec).values()}


def test_the_overview_only_draws_what_the_full_design_has() -> None:
    """The overview is a view of the design, never a second design."""
    full = _members("v3")
    for cls in _members("overview"):
        assert cls in full, f"lớp {cls} không có trong thiết kế đầy đủ"
