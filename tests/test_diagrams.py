"""The class diagrams must describe the code that exists.

Written after an audit found the class diagram had fallen a long way behind:
four of the eight ports were missing, along with every decoder, every blob and
queue adapter, both extra repositories and all five domain exceptions. A diagram
that describes a system nobody built is worse than no diagram -- it is a
confident, detailed, wrong answer, and the rubric treats a document that
contradicts the code as a plagiarism-level finding.

These tests do not check that every class is drawn. They check the opposite
direction and one specific subset:

  * nothing drawn may be absent from the code -- a drawn class that does not
    exist is a lie;
  * every PORT must be drawn somewhere, because the ports are the architecture.
"""

from __future__ import annotations

import ast
import pathlib
import re

import pytest

SRC = pathlib.Path("src/aicefr")
# Hai dinh dang, mot ly do. So do lop nam o `.drawio` vi day la hinh ma nguoi
# ta phai keo tha sap xep lai bang tay -- PlantUML tu dat vi tri, khong sua duoc.
# So do kien truc van la `.puml` vi no nho va bo cuc tu dong dung roi.
DIAGRAMS = sorted(
    [
        *pathlib.Path("docs/sdd/diagrams").glob("02*.puml"),
        *pathlib.Path("docs/sdd/diagrams").glob("02*.drawio"),
    ]
)

# Drawn on purpose but not classes in this codebase: types from the standard
# library or a dependency, shown so the reader can see what a field holds.
NOT_OURS = {"Path", "ThreadPoolExecutor"}

# Co y KHONG ve, va ly do phai nam o day chu khong chi trong dau nguoi ve.
#
# `ResponseStore`: co khai trong ports.py va co test ghim rang Repository thoa
# no, nhung api/main.py khoi tao bang kieu cu the va goi hon hai muoi phuong
# thuc ngoai cong do. Ve no nhu mot seam se hua rang doi SQLite sang thu khac
# chi la viet mot bo chuyen doi ba phuong thuc -- dieu khong dung. Docstring
# cua chinh `ResponseStore` ghi ro gioi han nay.
PORTS_NOT_DRAWN = {"ResponseStore"}

# Bo the kiem thu. Chung chung minh cong la that, nhung mot dong ghi chu tren
# hinh lam duoc viec do gon hon hai hop ngang hang voi bo chuyen doi that.
ADAPTERS_NOT_DRAWN = {"FakeAsrEngine", "InlineJobQueue"}


def classes_in_code() -> set[str]:
    found: set[str] = set()
    for path in SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found |= {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    return found


def classes_in_diagram(path: pathlib.Path) -> set[str]:
    """Ten cac lop duoc VE, doc duoc tu ca hai dinh dang.

    Voi `.drawio`, ten lop nam o thuoc tinh `value` cua nhung o co style
    `swimlane` -- do la hop UML; cac o con la tung dong thuoc tinh. Phai loc
    theo style chu khong the lay moi `value`, neu khong thi "- prob: float"
    cung bi tinh la mot lop.
    """
    if path.suffix == ".drawio":
        import xml.etree.ElementTree as ET

        drawn = set()
        for cell in ET.parse(path).getroot().iter("mxCell"):
            if "swimlane" not in (cell.get("style") or ""):
                continue
            # Tieu de co hai dong: stereotype tren, ten lop duoi.
            # Vi du "«entity»<br>Account" -> "Account".
            raw = (cell.get("value") or "").split("<br>")[-1]
            name = re.sub(r"«[^»]*»|<<[^>]*>>", "", raw).strip()
            if re.fullmatch(r"[A-Za-z_]\w*", name):
                drawn.add(name)
        return drawn

    text = path.read_text(encoding="utf-8")
    # `class Foo`, `interface Foo`, `enum Foo`, `abstract class Foo`
    return set(
        re.findall(r"^\s*(?:abstract\s+)?(?:class|interface|enum)\s+([A-Za-z_][\w]*)", text, re.M)
    )


@pytest.mark.parametrize("diagram", DIAGRAMS, ids=lambda p: p.name)
def test_nothing_drawn_is_missing_from_the_code(diagram: pathlib.Path) -> None:
    """A class on the diagram that does not exist is a confident wrong answer."""
    drawn = classes_in_diagram(diagram) - NOT_OURS
    real = classes_in_code()
    invented = sorted(drawn - real)
    assert not invented, f"{diagram.name} vẽ những lớp không có trong mã: {invented}"


def test_every_port_appears_on_a_diagram() -> None:
    """The ports are the architecture; leaving one out misrepresents the design.

    Four of eight were missing when this was written, including the three that
    decide whether the system can run on more than one machine.
    """
    ports_module = ast.parse((SRC / "ports.py").read_text(encoding="utf-8"))
    ports = {n.name for n in ports_module.body if isinstance(n, ast.ClassDef)}

    drawn: set[str] = set()
    for diagram in DIAGRAMS:
        drawn |= classes_in_diagram(diagram)

    missing = sorted(ports - drawn - PORTS_NOT_DRAWN)
    assert not missing, f"port chưa được vẽ ở sơ đồ nào: {missing}"


def test_every_adapter_of_a_port_appears_on_a_diagram() -> None:
    """An interface with one visible implementation reads as pointless indirection.

    Showing the alternatives is what makes the seam legible: two queue adapters
    on the page is the evidence that swapping one in is real.
    """
    expected = {
        "SoundFileDecoder",
        "FfmpegDecoder",
        "FirstMatchDecoder",
        "WhisperEngine",
        "FakeAsrEngine",
        "SileroVad",
        "EnergyVad",
        "RidgeScorer",
        "Repository",
        "LocalBlobStore",
        "InProcessJobQueue",
        "InlineJobQueue",
        "InMemoryRateLimiter",
    }
    drawn: set[str] = set()
    for diagram in DIAGRAMS:
        drawn |= classes_in_diagram(diagram)
    missing = sorted(expected - drawn - ADAPTERS_NOT_DRAWN)
    assert not missing, f"adapter chưa được vẽ: {missing}"


# Cu phap thanh vien UML: `+/-/# ten: Kieu` cho thuoc tinh,
# `+/-/# ten(tham so: Kieu): KieuTra` cho thao tac. Tap hop viet
# `List<X>`, anh xa viet `Map<K, V>`. KHONG ghi boi so trong thuoc
# tinh -- boi so noi so luong giua HAI thuc the, la khai niem cua DAU LIEN
# KET, nen no nam tren canh (chu du an nhac lai ngay 29/10/2026).
MEMBER = re.compile(r"^[+\-#] \w+(\([^)]*\))?: \w+(<[\w, ]+>)?$")


def typed_members(path: pathlib.Path) -> list[tuple[str, str]]:
    """Moi dong thuoc tinh/thao tac cua tung hop KHONG phai enum.

    Hop enum bi bo qua: dong cua no la ten hang so (`STUDENT`), khong phai
    thuoc tinh, nen khong co kieu -- dung nhu chuan UML.
    """
    import xml.etree.ElementTree as ET

    cells = list(ET.parse(path).getroot().iter("mxCell"))
    # id cua hop -> ten lop, chi giu hop khong phai enum
    boxes = {
        c.get("id"): (c.get("value") or "").split("<br>")[-1]
        for c in cells
        if "swimlane" in (c.get("style") or "") and "«enumeration»" not in (c.get("value") or "")
    }
    # draw.io ve nhan bang HTML nen mot dau `<` tho phai escape hai lan. Doc
    # nguoc lai mot lan de so voi cu phap UML.
    import html as _html

    return [
        (boxes[c.get("parent")], _html.unescape((c.get("value") or "").strip()))
        for c in cells
        if c.get("parent") in boxes and "swimlane" not in (c.get("style") or "")
    ]


@pytest.mark.parametrize("diagram", DIAGRAMS, ids=lambda p: p.name)
def test_every_member_on_the_class_diagram_carries_a_type(
    diagram: pathlib.Path,
) -> None:
    """Mot so do lop khong co kieu thi khong ra duoc code tu no.

    Ban truoc co y bo kieu "cho gon" -- va do la vi pham cu phap thuoc tinh
    cua UML (`visibility name: Type`). Giang vien huong dan bat dung cho nay.
    Thao tac cung vay: phai du tham so co kieu va du kieu tra ve.
    """
    if diagram.suffix != ".drawio":
        pytest.skip("chi ap cho so do lop")
    bad = [f"{cls}.{row}" for cls, row in typed_members(diagram) if not MEMBER.match(row)]
    assert not bad, f"thành viên thiếu kiểu, sai cú pháp UML: {bad}"


def enum_values_in_code() -> dict[str, list[str]]:
    """Ten enum -> danh sach hang so, doc tu toan bo src/."""
    found: dict[str, list[str]] = {}
    for path in SRC.rglob("*.py"):
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if not isinstance(node, ast.ClassDef):
                continue
            if not any("Enum" in ast.unparse(b) for b in node.bases):
                continue
            found[node.name] = [
                t.targets[0].id
                for t in node.body
                if isinstance(t, ast.Assign) and isinstance(t.targets[0], ast.Name)
            ]
    return found


def enum_rows_in_diagram(path: pathlib.Path) -> dict[str, list[str]]:
    """Ten enum -> cac dong da ve, doc tu tep .drawio."""
    import xml.etree.ElementTree as ET

    cells = list(ET.parse(path).getroot().iter("mxCell"))
    # Nhan dien hop enum bang TEN doi chieu voi ma nguon, khong bang nhan
    # «enumeration» tren hinh. Loc theo nhan thi neu ai do bo khuon dap di --
    # `tools/gen_class_diagram.py --no-stereotypes` lam dung viec do -- ham nay
    # tra ve rong va test DAU MOT CACH RONG. Dau rong te hon do: no bao rang
    # moi enum deu khop trong khi khong kiem cai nao.
    known = set(enum_values_in_code())
    boxes = {
        c.get("id"): (c.get("value") or "").split("<br>")[-1]
        for c in cells
        if "swimlane" in (c.get("style") or "")
        and (c.get("value") or "").split("<br>")[-1] in known
    }
    rows: dict[str, list[str]] = {name: [] for name in boxes.values()}
    for c in cells:
        if c.get("parent") in boxes and "swimlane" not in (c.get("style") or ""):
            rows[boxes[c.get("parent")]].append((c.get("value") or "").strip())
    return rows


@pytest.mark.parametrize("diagram", DIAGRAMS, ids=lambda p: p.name)
def test_every_enum_on_the_diagram_lists_all_its_values(diagram: pathlib.Path) -> None:
    """Mot hop enum ve thieu gia tri la mot hop noi doi ve chinh no.

    Ban truoc ve sau hang so cua `ReasonCode` roi ghi "... 25 mã" o dong thu
    bay. Hai loi trong mot dong: dau ba cham khong phai ky hieu UML, va con so
    dat sau sau dong da liet ke bi doc thanh "con 25 ma nua" -- tuc 31 ma,
    trong khi that ra chi co 25. Khong co gi kiem tra nen no ton tai rat lau.
    """
    if diagram.suffix != ".drawio":
        pytest.skip("chi ap cho so do lop")
    that = enum_values_in_code()
    drawn = enum_rows_in_diagram(diagram)
    assert drawn, "khong doc duoc hop enum nao tu hinh -- test nay da thanh vo nghia"
    for name, rows in drawn.items():
        assert name in that, f"{name} khong phai enum co that trong mã"
        assert rows == that[name], (
            f"enum {name} vẽ {len(rows)} dòng nhưng mã có {len(that[name])} giá trị; "
            f"thiếu: {sorted(set(that[name]) - set(rows))}"
        )


@pytest.mark.parametrize("diagram", DIAGRAMS, ids=lambda p: p.name)
def test_no_placeholder_on_the_diagram(diagram: pathlib.Path) -> None:
    """Dau ba cham tren so do la cho de trong, khong phai ky hieu.

    Nguoi doc khong the biet phia sau dau ba cham con nhung gi, ma so do ton
    tai chinh la de tra loi cau hoi do.
    """
    text = diagram.read_text(encoding="utf-8")
    bad = re.findall(r'value="([^"]*(?:\.\.\.|…)[^"]*)"', text)
    assert not bad, f"{diagram.name} còn ký hiệu thay chỗ: {bad}"


def fields_by_class() -> dict[str, dict[str, str]]:
    """Ten lop -> {ten truong: kieu}, doc tu toan bo src/."""
    out: dict[str, dict[str, str]] = {}
    for path in SRC.rglob("*.py"):
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if isinstance(node, ast.ClassDef):
                out[node.name] = {
                    b.target.id: ast.unparse(b.annotation)
                    for b in node.body
                    if isinstance(b, ast.AnnAssign) and isinstance(b.target, ast.Name)
                }
    return out


def _mentions(annotation: str, cls: str) -> bool:
    """Whether a type annotation names `cls` -- as a WHOLE name, not a substring.

    `"Feature" in "FeatureSet"` is True, and that is how `Response.features:
    FeatureSet` was read as "Response contains a Feature". Both composition
    tests below then reported a shared part that does not exist. Split the
    annotation into identifiers and compare whole tokens.
    """
    return cls in re.findall(r"[A-Za-z_]\w*", annotation)


@pytest.mark.parametrize("diagram", DIAGRAMS, ids=lambda p: p.name)
def test_every_composition_has_a_real_containing_field(diagram: pathlib.Path) -> None:
    """Hinh thoi DAC noi bo phan nam BEN TRONG the. Phai co truong that.

    Hop thanh khong phai mot mui ten dep hon lien ket: no hua rang bo phan
    thuoc ve dung mot the, sinh ra cung the va mat theo the. Loi bi bat o day:
    `Response` tung duoc ve hop thanh voi `Review`, nhung `Review` khong nam
    trong `Response` -- no la bang `review_action` rieng. Do phai la lien ket.
    """
    if diagram.suffix != ".drawio":
        pytest.skip("chi ap cho so do lop")
    import xml.etree.ElementTree as ET

    cells = list(ET.parse(diagram).getroot().iter("mxCell"))
    names = {
        c.get("id"): (c.get("value") or "").split("<br>")[-1]
        for c in cells
        if "swimlane" in (c.get("style") or "")
    }
    fields = fields_by_class()
    bad = []
    for c in cells:
        style = c.get("style") or ""
        if c.get("edge") != "1" or "diamondThin" not in style:
            continue
        whole, part = names.get(c.get("source")), names.get(c.get("target"))
        if whole is None or part is None:
            continue
        if not any(_mentions(t, part) for t in fields.get(whole, {}).values()):
            bad.append(f"{whole} ◆— {part}")
    assert not bad, f"hợp thành nhưng thể không chứa bộ phận (phải là liên kết): {bad}"


@pytest.mark.parametrize("diagram", DIAGRAMS, ids=lambda p: p.name)
def test_every_composition_part_has_exactly_one_owner(diagram: pathlib.Path) -> None:
    """Hop thanh doi SO HUU DOC QUYEN: bo phan thuoc ve dung MOT the.

    Co truong chua moi la dieu kien CAN, chua du. Neu hai lop cung chua mot
    lop thu ba thi bo phan bi dung chung, va quan he dung phai la ket hop
    (hinh thoi RONG) chu khong phai hop thanh -- xoa mot the thi the con lai
    van con giu bo phan do.

    Phan con lai cua dinh nghia -- vong doi trung nhau -- la phan xet doan,
    khong tu dong kiem duoc; no ghi o SDD muc 3.2 cho tung quan he.
    """
    if diagram.suffix != ".drawio":
        pytest.skip("chi ap cho so do lop")
    import xml.etree.ElementTree as ET

    cells = list(ET.parse(diagram).getroot().iter("mxCell"))
    names = {
        c.get("id"): (c.get("value") or "").split("<br>")[-1]
        for c in cells
        if "swimlane" in (c.get("style") or "")
    }
    fields = fields_by_class()
    # Owning is a relation of the model, so the owners are looked for among
    # the classes drawn. A class of the code that only points at a part while
    # it computes -- the path composer's `Candidate` holds the `Lesson` it
    # scores -- does not own it.
    drawn = set(names.values())
    bad = []
    for c in cells:
        if c.get("edge") != "1" or "diamondThin" not in (c.get("style") or ""):
            continue
        part = names.get(c.get("target"))
        if part is None:
            continue
        owners = [
            cls
            for cls, fs in fields.items()
            if cls != part and cls in drawn and any(_mentions(t, part) for t in fs.values())
        ]
        if len(owners) > 1:
            bad.append(f"{part} bị {len(owners)} lớp chứa: {owners}")
    assert not bad, f"hợp thành nhưng bộ phận dùng chung (phải là kết hợp): {bad}"


# Boi so tren hinh phai la con so MA THI HANH, khong phai con so yeu cau
# mong muon. Hai thu nay tung lech nhau: hinh ve `evidence 0..6` theo FR-24,
# trong khi `EvidenceBuilder` cho toi da 10 (ba loai x max_per_kind=3, cong
# mot muc lexical). Ve theo yeu cau la hua mot rang buoc ma he thong khong giu.
# Boi so tren canh phai la con so MA THI HANH, khong phai con so yeu cau
# mong muon. Hai thu nay tung lech nhau: hinh ve `0..6` cho evidence theo
# FR-24, trong khi `EvidenceBuilder` cho toi da 10 (ba loai x max_per_kind=3,
# cong mot muc lexical). Ve theo yeu cau la hua mot rang buoc he thong khong giu.
BOUNDS_IN_CODE = {
    # `Lesson.steps` holds at most twelve (Field max_length), and the lesson
    # lint refuses to publish a lesson without a step.
    ("Lesson", "Step"): "1..12",
}


@pytest.mark.parametrize("diagram", DIAGRAMS, ids=lambda p: p.name)
def test_multiplicities_match_what_the_code_enforces(diagram: pathlib.Path) -> None:
    """Boi so o dau DICH cua canh phai khop gioi han that trong ma nguon."""
    if diagram.suffix != ".drawio":
        pytest.skip("chi ap cho so do lop")
    import xml.etree.ElementTree as ET

    cells = list(ET.parse(diagram).getroot().iter("mxCell"))
    names = {
        c.get("id"): (c.get("value") or "").split("<br>")[-1]
        for c in cells
        if "swimlane" in (c.get("style") or "")
    }
    # Nhan o dau dich la o con thu hai cua canh (x duong), dau nguon la x am.
    found = {}
    for c in cells:
        if c.get("edge") != "1":
            continue
        pair = (names.get(c.get("source")), names.get(c.get("target")))
        labels = [
            x
            for x in cells
            if x.get("parent") == c.get("id") and float(x.find("mxGeometry").get("x") or 0) > 0
        ]
        if labels:
            found[pair] = (labels[0].get("value") or "").strip()
    bad = [
        f"{a}->{b} là {found.get((a, b))!r}, phải là {want!r}"
        for (a, b), want in BOUNDS_IN_CODE.items()
        if found.get((a, b)) != want
    ]
    assert not bad, f"bội số trên cạnh không khớp giới hạn trong mã: {bad}"


# Kieu co san cua ngon ngu va ten bo chua: khong can hop rieng, dung nhu hinh
# nay khong ve hop cho `str`.
PRIMITIVE_TYPES = {"str", "int", "float", "bool", "List", "Map", "None"}


@pytest.mark.parametrize("diagram", DIAGRAMS, ids=lambda p: p.name)
def test_no_orphan_type_on_the_diagram(diagram: pathlib.Path) -> None:
    """Moi kieu CUA DU AN ma mot thuoc tinh nhac ten phai co hop tren hinh.

    Ve `- reasons: List<ReasonCode>` ma khong ve hop `ReasonCode` la de lai
    mot kieu MO COI: nguoi chi doc hinh khong biet no la gi, va lop khac khong
    biet minh dang dung cai gi. Hai lua chon nhat quan la ve ra, hoac bo luon
    ca thuoc tinh -- khong co trang thai nua voi.

    `str` thi khac: do la kieu co san cua ngon ngu, khong ai cho la thieu.
    """
    if diagram.suffix != ".drawio":
        pytest.skip("chi ap cho so do lop")
    import html as _html
    import xml.etree.ElementTree as ET

    cells = list(ET.parse(diagram).getroot().iter("mxCell"))
    box_ids = {c.get("id") for c in cells if "swimlane" in (c.get("style") or "")}
    drawn = {
        (c.get("value") or "").split("<br>")[-1]
        for c in cells
        if "swimlane" in (c.get("style") or "")
    }
    mentioned: set[str] = set()
    for c in cells:
        if c.get("parent") not in box_ids or "swimlane" in (c.get("style") or ""):
            continue
        row = _html.unescape(c.get("value") or "")
        if ":" not in row:
            continue
        mentioned |= set(re.findall(r"[A-Za-z_]\w*", row.split(":", 1)[1]))
    orphans = sorted(
        t for t in mentioned - PRIMITIVE_TYPES if t in classes_in_code() and t not in drawn
    )
    assert not orphans, f"kiểu mồ côi — được nhắc tên nhưng không có hộp: {orphans}"


# `camelCase` tren hinh <-> `snake_case` trong ma. Doi ten o day, khong doi hinh:
# UML dung camelCase, Python dung snake_case, ca hai deu dung trong the gioi cua no.
def _snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


# Duoc ve du khong ai goi, vi mot ly do rieng phai ghi ra o day.
OPERATIONS_WITHOUT_A_CALLER: dict[str, str] = {}


@pytest.mark.parametrize("diagram", DIAGRAMS, ids=lambda p: p.name)
def test_every_operation_on_the_diagram_has_a_caller(diagram: pathlib.Path) -> None:
    """Moi thao tac duoc ve phai co it nhat mot noi goi no ngoai cho dinh nghia.

    Mot phuong thuc khong ai goi khong phai tinh nang cua he thong, va ve no
    len la noi voi nguoi doc rang thuc the giu mot luat ma no khong giu. Hai
    truong hop that da lot qua truoc khi co test nay: `FeatureSet.isComputable()`
    -- bon noi can doc dac trung deu voi tay vao `values` truc tiep -- va
    `Assessment.isNearBoundary()`, mà luat sat ranh gioi that su nam o ham tu do
    `scoring/scorer.py`, con thuoc tinh do chi doc lai ma ly do.

    Tim theo TEN, khong theo kieu: mot `@property` duoc goi khong ngoac
    (`account.is_staff`), va phia JS doc no qua JSON cung bang chinh ten do.
    """
    if diagram.suffix != ".drawio":
        pytest.skip("chi ap cho so do lop")

    drawn = re.findall(r'value="\+ (\w+)\(', diagram.read_text(encoding="utf-8"))
    assert drawn, "khong doc duoc thao tac nao tu hinh -- test nay da thanh vo nghia"

    haystack: list[tuple[pathlib.Path, str]] = []
    for f in [*SRC.rglob("*.py"), *SRC.rglob("*.js"), *SRC.rglob("*.html")]:
        haystack.append((f, f.read_text(encoding="utf-8")))

    dead = []
    for op in drawn:
        if op in OPERATIONS_WITHOUT_A_CALLER:
            continue
        snake = _snake(op)
        callers = [
            f"{f}"
            for f, text in haystack
            if f.name != "contracts.py" and re.search(rf"\.{snake}\b", text)
        ]
        if not callers:
            dead.append(op)
    assert not dead, (
        f"thao tac duoc ve nhung khong noi nao goi: {sorted(dead)}. "
        "Bo khoi hinh, hoac them vao OPERATIONS_WITHOUT_A_CALLER kem ly do."
    )


@pytest.mark.parametrize("diagram", DIAGRAMS, ids=lambda p: p.name)
def test_each_diagram_has_a_rendered_image(diagram: pathlib.Path) -> None:
    """A source file nobody rendered is a diagram nobody will read."""
    image = pathlib.Path("docs/sdd/images") / f"{diagram.stem}.png"
    assert image.is_file(), f"chưa render {image}; chạy ./render.sh"


@pytest.mark.parametrize("diagram", DIAGRAMS, ids=lambda p: p.name)
def test_each_image_fits_on_a_page(diagram: pathlib.Path) -> None:
    """Aspect ratio, not pixel count, is what makes a diagram unreadable in print.

    An earlier version of this diagram came out five times wider than it was
    tall: every label shrank to nothing when fitted to A4.
    """
    import struct

    image = pathlib.Path("docs/sdd/images") / f"{diagram.stem}.png"
    header = image.read_bytes()[:33]
    width, height = struct.unpack(">II", header[16:24])
    ratio = width / height
    assert 0.5 <= ratio <= 2.0, f"{image.name} tỷ lệ {ratio:.2f}, không in A4 được"


# ---------------------------------------------------------------------------
# The images the documents actually show.
#
# The tests above only look at the PlantUML sources. That left a gap in both
# directions, and both showed up in one audit: the SDD embedded
# `images/01_usecase.png`, which had never been rendered, so the document had a
# broken image; meanwhile three per-actor use case images WERE rendered and
# embedded nowhere. Two stale SVGs of the old, wrong class diagram sat in the
# same folder.

IMAGES = pathlib.Path("docs/sdd/images")
EMBEDDING_DOCS = [pathlib.Path("docs/sdd/SDD.md")]


def embedded_images() -> set[str]:
    found: set[str] = set()
    for doc in EMBEDDING_DOCS:
        found |= set(re.findall(r"!\[[^\]]*\]\(images/([^)]+)\)", doc.read_text(encoding="utf-8")))
    return found


def test_every_embedded_image_exists() -> None:
    """A document that shows a broken image is worse than one that shows none."""
    missing = sorted(n for n in embedded_images() if not (IMAGES / n).is_file())
    assert not missing, f"tài liệu nhúng ảnh không tồn tại: {missing}"


def test_no_orphan_images() -> None:
    """Every rendered image is shown somewhere, so the folder stays the truth."""
    orphans = sorted(p.name for p in IMAGES.iterdir() if p.name not in embedded_images())
    assert not orphans, f"ảnh không được tài liệu nào nhúng, xoá hoặc nhúng vào: {orphans}"


@pytest.mark.parametrize("name", sorted(embedded_images()), ids=lambda n: n)
def test_embedded_image_fits_on_a_page(name: str) -> None:
    """Same A4 rule as the class diagrams, applied to the Mermaid images too.

    This is the rule that condemned the combined use case diagram: it rendered
    at a ratio of 6.55, so every label vanished when fitted to a page. Splitting
    it per actor brought all three views back into range.
    """
    import struct

    header = (IMAGES / name).read_bytes()[:33]
    width, height = struct.unpack(">II", header[16:24])
    ratio = width / height
    assert 0.5 <= ratio <= 2.0, f"{name} tỷ lệ {ratio:.2f}, không in A4 được"


def test_inline_mermaid_matches_its_source_file() -> None:
    """The SDD pastes each Mermaid source inline. The two must not drift apart.

    They already had: the deployment diagram embedded in the document showed a
    container `web-ui: static SPA va Nginx` that the source file had not
    mentioned for a long time. Whoever reads the document sees the copy; whoever
    renders the image sees the file. A test is cheaper than remembering.
    """
    sdd = pathlib.Path("docs/sdd/SDD.md").read_text(encoding="utf-8")
    pattern = re.compile(r"File: `docs/sdd/diagrams/(\w+\.mmd)`\n\n```mermaid\n(.*?)```", re.S)
    found = pattern.findall(sdd)
    assert found, "không tìm thấy khối mermaid nào trong SDD, biểu thức tìm kiếm đã lỗi thời"

    drifted = []
    for name, embedded in found:
        source = (pathlib.Path("docs/sdd/diagrams") / name).read_text(encoding="utf-8")
        if not source.endswith("\n"):
            source += "\n"
        if source != embedded:
            drifted.append(name)
    assert not drifted, f"bản dán trong SDD khác file nguồn: {drifted}"


def test_every_mermaid_source_is_rendered_and_shown() -> None:
    """Same rule the PlantUML diagrams live under, applied to the Mermaid ones."""
    for source in pathlib.Path("docs/sdd/diagrams").glob("*.mmd"):
        image = IMAGES / f"{source.stem}.png"
        assert image.is_file(), f"chưa render {image}"
        assert image.name in embedded_images(), f"{image.name} không được tài liệu nào nhúng"


# --------------------------------------------------------------- hinh hoc cua canh


def _segments(diagram: pathlib.Path):
    """Dung lai duong di THAT cua tung canh tu toa do trong XML.

    draw.io khong ghi duong di day du: no ghi cong ra, cong vao va cac diem uon,
    roi tu noi lai theo kieu vuong goc. Ham nay noi lai y het nhu vay, vi chi co
    toa do that moi tra loi duoc cau hoi "hai duong nay co de len nhau khong".

    Huong cua doan DAU TIEN do CONG quyet dinh chu khong phai mot quy uoc co
    dinh: buoc di dau tien luon vuong goc voi canh hop ma duong roi. Gia dinh
    sai o cho nay tung lam chinh phep kiem bao mot loi khong ton tai -- loai sai
    te nhat, vi no lam nguoi doc mat tin vao con so.
    """
    import xml.etree.ElementTree as ET

    cells = list(ET.parse(diagram).getroot().iter("mxCell"))
    boxes = {}
    for c in cells:
        if "swimlane" not in (c.get("style") or ""):
            continue
        g = c.find("mxGeometry")
        boxes[c.get("id")] = (
            float(g.get("x")),
            float(g.get("y")),
            float(g.get("width")),
            float(g.get("height")),
            (c.get("value") or "").split("<br>")[-1],
        )

    segs = []
    for c in cells:
        if c.get("edge") != "1" or c.get("source") not in boxes or c.get("target") not in boxes:
            continue
        st = dict(part.split("=", 1) for part in (c.get("style") or "").split(";") if "=" in part)
        ex, ey = float(st.get("exitX", 0.5)), float(st.get("exitY", 0.5))
        nx, ny = float(st.get("entryX", 0.5)), float(st.get("entryY", 0.5))
        sb, tb = boxes[c.get("source")], boxes[c.get("target")]
        name = f"{sb[4]}->{tb[4]}"
        pts = [(sb[0] + ex * sb[2], sb[1] + ey * sb[3])]
        arr = c.find("mxGeometry/Array")
        if arr is not None:
            pts += [(float(q.get("x")), float(q.get("y"))) for q in arr.findall("mxPoint")]
        pts.append((tb[0] + nx * tb[2], tb[1] + ny * tb[3]))
        vert_exit = ex not in (0.0, 1.0) and ey in (0.0, 1.0)
        vert_entry = nx not in (0.0, 1.0) and ny in (0.0, 1.0)
        for k, (a, b) in enumerate(zip(pts, pts[1:], strict=False)):
            if abs(a[0] - b[0]) < 0.5 or abs(a[1] - b[1]) < 0.5:
                segs.append((name, a, b))
                continue
            first_vertical = (k == 0 and vert_exit) or (k == len(pts) - 2 and not vert_entry)
            mid = (a[0], b[1]) if first_vertical else (b[0], a[1])
            segs.append((name, a, mid))
            segs.append((name, mid, b))
    return boxes, segs


def _span(seg):
    (x1, y1), (x2, y2) = seg[1], seg[2]
    return min(x1, x2), max(x1, x2), min(y1, y2), max(y1, y2)


@pytest.mark.parametrize("diagram", DIAGRAMS, ids=lambda p: p.name)
def test_no_edge_crosses_a_box(diagram: pathlib.Path) -> None:
    """Khong duong noi nao duoc di xuyen qua mot hop.

    Ke ca hop dau mut cua chinh no: "cham vao mep" khac "ke ngang qua long
    hop". Mot canh ra khe ben phai roi vao mep TRAI hop dich thi no bang qua ca
    be rong hop -- 300 diem. Da co muoi canh nhu vay, va phep kiem chi nhin hop
    thu ba khong he thay.
    """
    if diagram.suffix != ".drawio":
        pytest.skip("chi ap cho so do lop")
    boxes, segs = _segments(diagram)
    bad = []
    for sg in segs:
        lo_x, hi_x, lo_y, hi_y = _span(sg)
        ends = sg[0].split("->")
        for bx, by, bw, bh, bname in boxes.values():
            if bname in ends:
                inside = max(0.0, min(hi_x, bx + bw) - max(lo_x, bx))
                if inside > 40 and by + 2 < lo_y < by + bh - 2:
                    bad.append(f"{sg[0]} kẻ ngang {inside:.0f}px qua lòng hộp {bname}")
            elif lo_x < bx + bw - 2 and hi_x > bx + 2 and lo_y < by + bh - 2 and hi_y > by + 2:
                bad.append(f"{sg[0]} xuyên hộp {bname}")
    assert not bad, f"đường nối đi xuyên hộp: {sorted(set(bad))}"


@pytest.mark.parametrize("diagram", DIAGRAMS, ids=lambda p: p.name)
def test_no_two_edges_are_drawn_on_top_of_each_other(diagram: pathlib.Path) -> None:
    """Hai duong noi khong duoc nam de len nhau hay sat nhau duoi 8 diem.

    Day la phep do, khong phai cam nhan. Ban dau co 15 cap trung, nang nhat la
    `Assessment->CriterionCoverage` voi `Assessment->ReasonCode` chong nhau 755
    diem -- nguoi doc khong the lan ra canh nao noi voi hop nao.
    """
    if diagram.suffix != ".drawio":
        pytest.skip("chi ap cho so do lop")
    _boxes, segs = _segments(diagram)
    bad = []
    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            p_, q_ = segs[i], segs[j]
            if p_[0] == q_[0]:
                continue
            p_h = abs(p_[1][1] - p_[2][1]) < 0.5
            if p_h != (abs(q_[1][1] - q_[2][1]) < 0.5):
                continue
            pl, ph, pt, pb = _span(p_)
            ql, qh, qt, qb = _span(q_)
            gap = abs(pt - qt) if p_h else abs(pl - ql)
            overlap = (min(ph, qh) - max(pl, ql)) if p_h else (min(pb, qb) - max(pt, qt))
            if overlap > 2 and gap < 8:
                bad.append(f"{p_[0]} và {q_[0]}: cách {gap:.0f}px, chồng {overlap:.0f}px")
    assert not bad, f"đường nối đè lên nhau: {sorted(set(bad))}"


# ------------------------------------------------------------------ use case


USECASE_DIAGRAMS = sorted(pathlib.Path("docs/sdd/diagrams").glob("01?_usecase_*.mmd"))


def usecases_in_srs() -> dict[str, str]:
    """Ma use case -> ten, doc tu bang SRS muc 4.1. Day la nguon su that."""
    srs = pathlib.Path("docs/srs/SRS.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| (UC-\d\d) \| ([^|]+?) \|", srs, re.M)
    return {code: name.strip() for code, name in rows}


@pytest.mark.parametrize("diagram", USECASE_DIAGRAMS, ids=lambda p: p.name)
def test_every_usecase_drawn_exists_in_the_srs(diagram: pathlib.Path) -> None:
    """Ma VA ten use case tren hinh phai khop bang SRS muc 4.1.

    Ban truoc khong khop, va kieu khong khop la kieu te nhat: ba hinh tu dat
    mot he danh so rieng (UC01..UC32) TRUNG MA nhung KHAC NGHIA voi SRS. `UC05`
    tren hinh la "Xem bao cao va bang chung" cua sinh vien, con `UC-05` trong
    SRS la "Giang vien duyet bai trong hang doi". Nguoi doc doi chieu hai tai
    lieu se thay chung mau thuan nhau ma khong biet tin cai nao.
    """
    that = usecases_in_srs()
    assert that, "khong doc duoc bang use case trong SRS -- bieu thuc tim kiem da loi thoi"

    text = diagram.read_text(encoding="utf-8")
    # Nhan mot o: UC01["UC-01 Ten ...<br/>(ghi chu)"] -> lay ma va phan ten
    # truoc dau xuong dong dau tien.
    drawn = re.findall(r'\w+\["(UC-\d\d) ([^"<]+)', text)
    assert drawn, f"{diagram.name}: khong doc duoc use case nao"

    bad = []
    for code, name in drawn:
        name = name.strip()
        if code not in that:
            bad.append(f"{code} không có trong SRS")
        elif name != that[code]:
            bad.append(f"{code} vẽ là {name!r} nhưng SRS ghi {that[code]!r}")
    assert not bad, f"{diagram.name}: {bad}"


def test_every_usecase_in_the_srs_is_drawn_somewhere() -> None:
    """Chieu nguoc lai: khong use case nao cua SRS bi bo quen tren ca ba hinh.

    Thieu mot use case thi nguoi doc hinh tuong he thong khong co tinh nang do.
    """
    that = usecases_in_srs()
    drawn: set[str] = set()
    for d in USECASE_DIAGRAMS:
        drawn |= {
            c for c, _n in re.findall(r'\w+\["(UC-\d\d) ([^"<]+)', d.read_text(encoding="utf-8"))
        }
    thieu = sorted(set(that) - drawn)
    assert not thieu, f"use case có trong SRS nhưng không hình nào vẽ: {thieu}"


# Ba tac nhan cua de tai, va mot he thong ben ngoai. Khong co "He thong" trong
# danh sach nay. "Cổng thanh toán" (D034) la he thong ben ngoai -- VNPay, hoac
# cong thu thay cho no -- tac nhan phu cua UC-23: no nam ngoai ranh gioi va goi
# vao he thong (thong bao ket qua), dung dinh nghia tac nhan.
ACTORS = {"Sinh viên", "Giảng viên đánh giá", "Quản trị viên", "Cổng thanh toán"}


@pytest.mark.parametrize("diagram", USECASE_DIAGRAMS, ids=lambda p: p.name)
def test_the_system_itself_is_never_an_actor(diagram: pathlib.Path) -> None:
    """Chi ba tac nhan that duoc ve, va he thong khong nam trong so do.

    Trong so do use case, **he thong dang duoc thiet ke chinh la RANH GIOI**,
    khong phai mot tac nhan; tac nhan theo dinh nghia nam NGOAI ranh gioi do.
    Ve he thong thanh mot hinh tron ben ngoai roi cho no mui ten tro nguoc vao
    chinh minh la tu mau thuan.

    Loi nay tung co that va o CA HAI noi: bang use case trong SRS ghi "He
    thong" o cot actor cua bon dong (UC-01, UC-03, UC-05, UC-11), va ba hinh
    chep lai y nguyen. UC-03 vi the khong co tac nhan nao -- no la use case noi
    bo, chay vi UC-01 `include` no, dieu hoan toan hop le trong UML.

    Neu sau nay co he thong BEN NGOAI tham gia (LMS cua truong goi API) thi he
    thong do moi la tac nhan, va luc do them vao `ACTORS`.
    """
    ve = set(re.findall(r'^\s+\w+\(\("([^"]+)"\)\)', diagram.read_text(encoding="utf-8"), re.M))
    ve = {a.replace("<br/>", " ") for a in ve}
    la = sorted(ve - ACTORS)
    assert not la, f"{diagram.name}: tác nhân không hợp lệ {la} — hệ thống không phải actor"


def test_the_srs_never_lists_the_system_as_an_actor() -> None:
    """Chieu goc: bang use case trong SRS cung khong duoc ghi "He thong" lam actor.

    Sua hinh ma de nguyen bang thi lan sau ve lai se chep lai dung loi cu.
    """
    srs = pathlib.Path("docs/srs/SRS.md").read_text(encoding="utf-8")
    bad = [
        m.group(1)
        for m in re.finditer(r"^\| (UC-\d\d) \|[^|]+\|([^|]*)\|([^|]*)\|", srs, re.M)
        if "Hệ thống" in m.group(2) or "Hệ thống" in m.group(3)
    ]
    assert not bad, f"bảng use case SRS còn ghi 'Hệ thống' làm tác nhân: {bad}"


@pytest.mark.parametrize("diagram", USECASE_DIAGRAMS, ids=lambda p: p.name)
def test_usecase_diagrams_carry_no_progress_status(diagram: pathlib.Path) -> None:
    """So do use case la THIET KE, khong phai bang theo doi tien do.

    No mo ta he thong PHAI LAM GI. Da lam toi dau la thong tin khac loai, va
    tron vao khien nguoi doc tuong nhung o chua to mau la chua duoc hoach dinh
    -- trong khi that ra chung da duoc hoach dinh, chi la chua lam xong.

    Ban truoc to mau xanh/vang theo trang thai va ghi "(chua: ...)" vao nhan.
    Trang thai hien thuc nay nam o cot "Hien thuc" trong bang use case cua bao
    cao tuan, noi no thuoc ve.
    """
    text = diagram.read_text(encoding="utf-8")
    # Bo cac dong chu thich `%%` -- chung duoc phep nhac lai lich su.
    body = "\n".join(x for x in text.splitlines() if not x.strip().startswith("%%"))
    cam = ["classDef", "chưa", "một phần", "lệch:", "todo", "done"]
    thay = [t for t in cam if t in body]
    assert not thay, f"{diagram.name}: sơ đồ thiết kế không được mang trạng thái tiến độ {thay}"


@pytest.mark.parametrize("diagram", USECASE_DIAGRAMS, ids=lambda p: p.name)
def test_an_extending_usecase_has_no_actor_of_its_own(diagram: pathlib.Path) -> None:
    """Use case MO RONG khong duoc noi truc tiep voi tac nhan.

    Tac nhan khoi tao use case CO SO; phan mo rong duoc chen vao giua luong do
    khi co dieu kien. Noi thang tac nhan toi phan mo rong la noi rang tac nhan
    khoi tao duoc no tu con so khong -- va phep thu de nhat la doc to len:
    "sinh vien nop lai bai" ma chua tung nop thi lay dau ra bai ma nop lai;
    "giang vien sua ket qua" ma chua mo bai ra duyet thi sua cua ai.

    Ca hai loi nay deu da co that tren hinh: `SV --> UC02` va `GV --> UC06`.
    """
    text = diagram.read_text(encoding="utf-8")
    body = "\n".join(x for x in text.splitlines() if not x.strip().startswith("%%"))

    mo_rong = {m.group(1) for m in re.finditer(r"^\s*(\w+) -\. extend \.-> \w+", body, re.M)}
    if not mo_rong:
        pytest.skip("hình này không có quan hệ extend")

    tac_nhan = {m.group(1) for m in re.finditer(r'^\s*(\w+)\(\("', body, re.M)}
    sai = [
        f"{a} --> {b}"
        for a, b in re.findall(r"^\s*(\w+) --> (\w+)", body, re.M)
        if a in tac_nhan and b in mo_rong
    ]
    assert not sai, (
        f"{diagram.name}: tác nhân nối thẳng tới use case mở rộng {sai} — "
        "phải nối với use case cơ sở, phần mở rộng đi qua quan hệ extend"
    )
