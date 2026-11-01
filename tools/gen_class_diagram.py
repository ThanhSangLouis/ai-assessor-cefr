"""Sinh so do lop dang .drawio tu mot dac ta gon.

    .venv/bin/python tools/gen_class_diagram.py

Can Python 3.10 tro len (dung `zip(strict=)` va cu phap kieu `X | None`).

Day la MO HINH MIEN (domain model), khong phai so do lop thiet ke. No:

  * chi ve khai niem NGHIEP VU, loai bo co che ky thuat -- phien dang nhap,
    khoa tranh ghi de, cau hinh, ban ghi nhat ky. Chung thuoc thiet ke tang
    thap; o du an nay chung da duoc ve day du o hai so do ERD 05 va 05c.
  * phan biet «entity» (co danh tinh va vong doi) voi «value object» (khong
    co danh tinh, dinh nghia hoan toan bang gia tri).
  * ghi DU kieu cho moi thuoc tinh va du chu ky cho moi thao tac, theo cu
    phap UML `+/-/# ten: Kieu` va `+ ten(thamso: Kieu): KieuTra`. Mot so do
    lop khong co kieu thi khong ra duoc code tu no.
  * BOI SO (`0..1`, `1..*`) chi noi so luong giua HAI thuc the, nen chi nam
    tren duong lien ket -- khong bao gio trong thuoc tinh (chu du an, ngay
    29/10/2026: "0..1 la quan he so luong giua 2 collection, khong phai
    min..max cua mot truong"). Tap hop viet `List<X>`. Trong dac ta, thuoc
    tinh mang kieu thuc the van ghi boi so (`lessons: Lesson [0..*]`) de
    `check_relations()` doi voi duong; khi ve, `attribute_text()` bo no ra
    khoi hop.
  * thuoc tinh co tap gia tri dong mang KIEU ENUM (`role: Role`), ca tren
    hinh lan trong code.
  * chi ghi thao tac nao la LUAT doan khong ra tu thuoc tinh.
  * GHI CA THUOC TINH THAM CHIEU lan quan he. Chuan UML cho phep chon mot
    trong hai (mot dau lien ket da la mot thuoc tinh), nhung ve ca hai thi
    nguoi doc thay ngay THE CHUA BO PHAN O TRUONG NAO -- va do la dieu phan
    biet hop thanh voi ket hop. Day cung la cach ban tham khieu cua nhom lam:
    `Order` ghi `- customer: Customer` ben trong hop, dong thoi co canh noi
    toi `Customer`.
  * ve DAY DU moi kieu liet ke ma cac lop trong hinh nhac ten. Ve mot
    thuoc tinh `List<ReasonCode>` ma khong ve hop `ReasonCode` la de lai
    mot kieu MO COI: nguoi doc hinh khong biet no la gi. Hoac ve ra de
    doi tuong khac dung duoc, hoac bo luon ca thuoc tinh -- khong co
    trang thai nua voi.

VI SAO SINH BANG SCRIPT chu khong go tay XML: chieu cao moi hop phu thuoc so
dong ben trong, va duong di cua canh phu thuoc toa do that cua moi hop. Go
tay thi moi lan them mot thuoc tinh la phai tinh lai toan bo -- da hong ba
lan vi ly do do truoc khi co tep nay.

LUU Y: chay lai script se GHI DE tep .drawio. Neu ban da keo tha sap xep lai
bang tay tren app.diagrams.net thi sua o day roi sinh lai, dung sua hai noi.
"""

from __future__ import annotations

import html
import pathlib
import re
import sys

# Duong dan tinh tu vi tri cua chinh tep nay, khong tinh tu thu muc dang dung.
# Chay `python tools/gen_class_diagram.py` tu mot thu muc khac thi duong dan
# tuong doi se tro ra ngoai repo -- hoac bao loi, hoac te hon la ghi nham cho.
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "docs/sdd/diagrams/02_class.drawio"

# `--no-stereotypes`: bo cac nhan «entity» / «value object» / «enumeration» khoi
# tieu de hop. Khong the chi xoa chu: tieu de tut tu hai dong xuong mot dong nen
# MOI hop thap di 20 diem, va toan bo bo cuc lan duong noi phai tinh lai. Day la
# ly do tuy chon nay nam trong bo sinh chu khong sua tay tren tep .drawio.
#
# `--out DUONG_DAN` de ghi ra cho khac, cho ban thu khong de len hinh chinh.
NO_STEREOTYPE = "--no-stereotypes" in sys.argv
if "--out" in sys.argv:
    OUT = pathlib.Path(sys.argv[sys.argv.index("--out") + 1]).resolve()

W, LH = 300, 22
TITLE_H = 26 if NO_STEREOTYPE else 46
COL_DX = 410  # khoang cach giua hai cot; khe doc = COL_DX - W
GAP = 60  # khoang cach doc giua hai hop cung cot
BR = "@@"  # cho xuong dong trong tieu de; doi thanh <br> sau khi escape


def label(text: str) -> str:
    """Escape HAI LAN cho nhan cua mot dong trong hop.

    draw.io ve nhan bang HTML (`html=1`). Mot dau `<` tho se bi trinh ve coi
    la the mo, va ca cum `<str, float>` bien mat khoi hinh -- im lang, khong
    bao loi. Lan escape thu nhat la cho trinh ve HTML, lan thu hai cho XML.
    """
    return html.escape(text.replace("<", "&lt;").replace(">", "&gt;"), quote=True)


def title(text: str) -> str:
    """Thay dau xuong dong TRUOC roi moi escape.

    draw.io luu HTML da escape trong thuoc tinh `value`, nen mot the `<br>`
    tho nam trong thuoc tinh se lam hong ca tep XML.
    """
    return html.escape(text.replace(BR, "<br>"), quote=True)


def _e(cid, name, lines):
    return (cid, "«entity»" + BR + name, lines)


def _v(cid, name, lines):
    return (cid, "«value object»" + BR + name, lines)


def _n(cid, name, values):
    return (cid, "«enumeration»" + BR + name, values)


# Mo hinh nghiep vu cua bai toan (chu du an chot 29/10/2026): thuc the -- lop co
# dinh danh, vong doi rieng -- va cac enumeration ma thuoc tinh cua chung lay
# kieu. Khong lop truu tuong, khong value object: phan khong co dinh danh (tu co
# moc thoi gian, phep do, nhan xet) la thuoc tinh cua thuc the so huu.
#
# QUAN HE QUA THUOC TINH (quy tac cua chu du an): moi duong noi co dung mot
# thuoc tinh o lop GIU quan he, mang kieu lop kia -- `lessons: Lesson [0..*]` o
# `Unit` thi moi co kim cuong `Unit` -> `Lesson`. Hop thanh: lop
# toan the giu danh sach phan (luu chung mot document). Ket hop: lop giu tham
# chieu (luu ma cua ben kia). Boi so cua thuoc tinh ve tren dau duong, khong ve
# trong hop. `check_relations()` duoi day bat moi duong thieu thuoc tinh.
#
# Ba database (D051): core, learning, metering. Hop thanh khong vuot database
# -- `Wallet` o metering nen la thuc the rieng tro toi `Account`, khong nhung
# vao tai khoan; thanh tuu o learning nen la `Achievement`, khong la thuoc tinh
# cua `Account`.
CLASSES = [
    _e(
        "Account",
        "Account",
        [
            "- accountId: str",
            "- email: str",
            "- emailVerified: bool",
            "- fullName: str",
            "- pseudonym: str",
            "- role: Role",
            "- mustChangePassword: bool",
            "- dailyGoalS: int",
            "- identities: List<str>",
            "- seenMarkers: List<str>",
            "- emailCodes: List<str>",
            "- emailReminders: bool",
            "- reminderSentOn: date",
            "+ isStaff(): bool",
        ],
    ),
    _e(
        "Audit",
        "AuditEntry",
        [
            "- id: int",
            "- service: str",
            "- actor: Account [0..1]",
            "- action: str",
            "- targetId: str",
            "- detail: str",
            "- createdAt: datetime",
        ],
    ),
    _e(
        "Task",
        "Task",
        [
            "- taskId: str",
            "- title: str",
            "- purpose: TaskPurpose",
            "- promptText: str",
            "- minSeconds: int",
            "- maxSeconds: int",
            "- topicKeywords: List<str>",
            "- criterion: Criterion",
            "- band: Band",
            "- referenceText: str",
            "- missions: List<str>",
            "- promptVersion: str",
        ],
    ),
    _e(
        "Resp",
        "Response",
        [
            "- responseId: str",
            "- speaker: Account [1]",
            "- task: Task [1]",
            "- purpose: TaskPurpose",
            "- status: ResponseStatus",
            "- reasonCodes: List<str>",
            "- durationMs: int",
            "- transcript: str",
            "- overall06: float",
            "- overallBand: Band",
            "- criterionScores: List<float>",
            "- intervalLow: float",
            "- intervalHigh: float",
            "- feedback: List<str>",
            "- replayLabels: List<str>",
            "- reviews: Review [0..*]",
            "- upgrade: CoachUpgrade [0..1]",
            "- reviewLock: str",
            "- reviewVisits: List<str>",
            "- modelVersion: str",
            "- teacherVerified: bool",
            "- createdAt: datetime",
            "+ isSingleBand(): bool",
        ],
    ),
    _e(
        "Review",
        "Review",
        [
            "- reviewId: int",
            "- reviewer: Account [1]",
            "- oldScore: float",
            "- newScore: float",
            "- oldBand: Band",
            "- newBand: Band",
            "- reason: str",
            "- openedAt: datetime",
            "- decidedAt: datetime",
        ],
    ),
    # D069: the learner's answer rewritten one band higher, made once on request
    # and kept with the response; D070: its phrases are the phrase book's cards.
    _e(
        "Upgrade",
        "CoachUpgrade",
        [
            "- fromBand: Band",
            "- toBand: Band",
            "- upgraded: str",
            "- changes: List<str>",
            "- phrases: PhraseCard [0..*]",
            "- provider: str",
            "- model: str",
            "- promptVersion: str",
            "- createdAt: datetime",
        ],
    ),
    _e(
        "Phrase",
        "PhraseCard",
        [
            "- phrase: str",
            "- meaningVi: str",
            "- box: int",
            "- due: datetime",
            "- reviews: int",
            "- reviewedAt: datetime",
            "+ isDue(at: datetime): bool",
        ],
    ),
    _e(
        "Class",
        "Classroom",
        [
            "- classId: str",
            "- name: str",
            "- teachers: Account [0..*]",
            "- members: Account [0..*]",
            "- archived: bool",
        ],
    ),
    _e(
        "Path",
        "LessonPath",
        [
            "- pathId: str",
            "- title: str",
            "- author: Account [0..1]",
            "- bandFrom: Band",
            "- bandTo: Band",
            "- status: PathStatus",
            "- units: Unit [0..*]",
            "- sample: bool",
        ],
    ),
    _e(
        "Unit",
        "Unit",
        [
            "- unitId: str",
            "- title: str",
            "- function: str",
            "- band: Band",
            "- criterion: Criterion",
            "- topic: str",
            "- position: int",
            "- lessons: Lesson [0..*]",
        ],
    ),
    _e(
        "Lesson",
        "Lesson",
        [
            "- lessonId: str",
            "- title: str",
            "- band: Band",
            "- criterion: Criterion",
            "- modelText: str",
            "- passRatio: float",
            "- steps: Step [1..12]",
            "- publishedVersion: int",
            "- versions: List<str>",
            "- media: List<str>",
            "- archived: bool",
        ],
    ),
    _e(
        "Step",
        "Step",
        [
            "- stepId: str",
            "- kind: StepKind",
            "- text: str",
            "- hintWords: List<str>",
            "- modelAudio: str",
            "- rounds: List<int>",
            "- strictness: str",
        ],
    ),
    _e(
        "Attempt",
        "StepAttempt",
        [
            "- attemptId: str",
            "- learner: Account [1]",
            "- step: Step [1]",
            "- lessonVersion: int",
            "- round: int",
            "- passed: bool",
            "- speakingS: float",
            "- result: List<str>",
            "- createdAt: datetime",
        ],
    ),
    _e(
        "RevItem",
        "ReviewItem",
        [
            "- itemId: str",
            "- learner: Account [1]",
            "- lesson: Lesson [1]",
            "- kind: str",
            "- word: str",
            "- box: int",
            "- dueDate: date",
            "+ isDue(today: date): bool",
        ],
    ),
    _e(
        "Achv",
        "Achievement",
        [
            "- code: str",
            "- learner: Account [1]",
            "- unlockedAt: datetime",
            "- seenAt: datetime",
        ],
    ),
    _e(
        "Plan",
        "LearningPlan",
        [
            "- planId: str",
            "- owner: Account [1]",
            "- goal: str",
            "- audience: Role",
            "- lessons: Lesson [1..*]",
            "- savedAs: LessonPath [0..1]",
            "- active: bool",
            "- modelVersion: str",
        ],
    ),
    # D075: one centre, no plans -- every order is a pack of runs for its buyer.
    _e(
        "Order",
        "Order",
        [
            "- orderId: str",
            "- runs: int",
            "- amountVnd: int",
            "- status: OrderStatus",
            "- gateway: str",
            "- live: bool",
            "- createdBy: Account [1]",
            "- createdAt: datetime",
            "- expiresAt: datetime",
            "- checkoutRef: str",
            "- reference: str",
            "- resultCode: str",
            "- settledAt: datetime",
            "- creditedAt: datetime",
            "- events: List<str>",
        ],
    ),
    _e(
        "Wallet",
        "Wallet",
        [
            "- owner: Account [1]",
            "- balance: int",
            "- freeUsed: int",
            "- period: str",
            "- grants: List<str>",
            "+ available(): int",
        ],
    ),
    # D078: the prices an administrator sets on the dashboard, one version at a
    # time; a ledger entry keeps the version it was held under (`priceVersion`).
    _e(
        "Price",
        "PriceList",
        [
            "- version: str",
            "- firstMinuteRuns: float",
            "- extraMinuteRuns: float",
            "- practiceFactor: float",
            "- upgradeRuns: float",
            "- idpointPerRun: int",
            "- freeRuns: float",
            "- packs: List<str>",
            "- changedBy: Account [1]",
            "- changedAt: datetime",
            "- history: List<str>",
        ],
    ),
    _e(
        "Ledger",
        "LedgerEntry",
        [
            "- entryId: str",
            "- wallet: Wallet [1]",
            "- response: Response [0..1]",
            "- action: MeteredAction",
            "- held: int",
            "- fromFree: int",
            "- fromWallet: int",
            "- charged: int",
            "- state: LedgerState",
            "- priceVersion: str",
        ],
    ),
]

# Chi giu enum DIEU KHIEN nghiep vu: vai tro, band va tieu chi cham, muc dich,
# trang thai vong doi cua bai noi / lo trinh / thuc nghiem / don / but toan, loai
# buoc bai hoc (quyet dinh cach cham buoc), loai don va goi dich vu. Tap gia tri
# chi la chi tiet (ma ly do, nhiem vu, chu de, cong thanh toan, nguon license, do
# chat) ghi `str`; hai trang thai thi ghi `bool`; enum trung nghia thi dung lai
# (`LedgerEntry.action: TaskPurpose`, `LearningPlan.audience: Role`).
# Ten khac code: `ResponseStatus` (code: Status).
ENUMS = [
    _n("Role", "Role", ["STUDENT", "TEACHER", "ADMIN"]),
    _n("Band", "Band", ["A1", "A2", "B1", "B2", "C1", "C2"]),
    _n("Criterion", "Criterion", ["RANGE", "ACCURACY", "FLUENCY", "COHERENCE", "PHONOLOGY"]),
    _n("Purpose", "TaskPurpose", ["ASSESSMENT", "PRACTICE"]),
    _n(
        "Status",
        "ResponseStatus",
        ["QUEUED", "RUNNING", "COMPLETED", "REVIEW_REQUIRED", "REJECTED", "FAILED"],
    ),
    _n("PathSt", "PathStatus", ["DRAFT", "PUBLISHED", "ARCHIVED"]),
    _n(
        "StepKind",
        "StepKind",
        [
            "READ_ALOUD",
            "REPEAT",
            "LOOK_UP",
            "GAP",
            "KEYWORDS",
            "STARTER",
            "PICTURE",
            "OUTLINE",
            "FREE",
        ],
    ),
    _n("OrderSt", "OrderStatus", ["PENDING", "PAID", "FAILED", "CANCELLED", "EXPIRED"]),
    _n("LedgerSt", "LedgerState", ["HELD", "CHARGED", "RELEASED"]),
    # D072: what a ledger entry paid for -- a recording, or an upgraded answer.
    _n("MeterAct", "MeteredAction", ["ASSESSMENT", "PRACTICE", "UPGRADE", "LESSON_DRAFT"]),
]

# (lop giu quan he, lop kia, "boi so lop giu : boi so lop kia", kieu). Lop giu
# co thuoc tinh mang kieu lop kia; boi so lop kia chinh la boi so cua thuoc tinh.
EDGES = [
    ("Audit", "Account", "0..* : 0..1", "assoc"),
    ("Resp", "Account", "0..* : 1", "assoc"),
    ("Resp", "Task", "0..* : 1", "assoc"),
    ("Resp", "Review", "1 : 0..*", "comp"),
    ("Resp", "Upgrade", "1 : 0..1", "comp"),
    ("Upgrade", "Phrase", "1 : 0..*", "comp"),
    ("Review", "Account", "0..* : 1", "assoc"),
    # D071: a class has its teachers and its members, both many-to-many; the
    # role name at the far end tells the two lines apart.
    ("Class", "Account", "0..* : teachers 0..*", "nn"),
    ("Class", "Account", "0..* : members 0..*", "nn"),
    ("Path", "Account", "0..* : 0..1", "assoc"),
    ("Path", "Unit", "1 : 0..*", "comp"),
    ("Unit", "Lesson", "1 : 0..*", "comp"),
    ("Lesson", "Step", "1 : 1..12", "comp"),
    ("Attempt", "Account", "0..* : 1", "assoc"),
    ("Attempt", "Step", "0..* : 1", "assoc"),
    ("RevItem", "Account", "0..* : 1", "assoc"),
    ("RevItem", "Lesson", "0..* : 1", "assoc"),
    ("Achv", "Account", "0..* : 1", "assoc"),
    ("Plan", "Account", "0..* : 1", "assoc"),
    ("Plan", "Lesson", "0..* : 1..*", "assoc"),
    ("Plan", "Path", "0..1 : 0..1", "assoc"),
    ("Order", "Account", "0..* : 1", "assoc"),
    ("Wallet", "Account", "0..1 : 1", "assoc"),
    ("Price", "Account", "0..* : 1", "assoc"),
    ("Ledger", "Wallet", "0..* : 1", "assoc"),
    # A recording and, since D072, its upgraded answer: two entries at most; a
    # teacher's lesson draft (D075) pays for no response.
    ("Ledger", "Resp", "0..2 : 0..1", "assoc"),
]

# Phu thuoc UML (net dut, mui ten mo) tu thuc the toi enum ma thuoc tinh cua no
# lay lam kieu.
EDGES += [
    (src, enum, "", "enum")
    for src, enum in [
        ("Account", "Role"),
        ("Plan", "Role"),
        ("Task", "Band"),
        ("Resp", "Band"),
        ("Review", "Band"),
        ("Upgrade", "Band"),
        ("Path", "Band"),
        ("Unit", "Band"),
        ("Lesson", "Band"),
        ("Task", "Criterion"),
        ("Lesson", "Criterion"),
        ("Unit", "Criterion"),
        ("Task", "Purpose"),
        ("Resp", "Purpose"),
        ("Resp", "Status"),
        ("Path", "PathSt"),
        ("Step", "StepKind"),
        ("Order", "OrderSt"),
        ("Ledger", "LedgerSt"),
        ("Ledger", "MeterAct"),
    ]
]

# Khung theo phan nghiep vu (`tools/zone_layout.py`). Dinh danh o giua hang tren
# vi `Account` noi toi moi khung; Danh gia o giua hang duoi vi Lop hoc, Thuong
# mai va Hoc tap deu noi vao bai noi hoac `Band`.
# (khoa, tieu de, hang, [(cot, [hop, ...])]); (hop, dy) dat hop cach dinh hang dy.
ZONES = [
    ("identity", "Định danh", 0, [(2, ["Audit", "Account"]), (3, ["Role"])]),
    ("commerce", "Thương mại: ví IDPoint, sổ lượt, đơn nạp lượt", 0,
     [(4, ["Wallet", "Ledger", "LedgerSt", "MeterAct"]), (5, ["Order"]),
      (6, ["OrderSt", "Price"])]),
    ("classroom", "Lớp học", 1, [(0, ["Class"])]),
    ("assessment", "Đánh giá", 1,
     [(1, ["Task", "Upgrade", "Phrase"]), (2, ["Resp", "Review"]),
      (3, ["Purpose", "Status", "Band", "Criterion"])]),
    ("learning", "Học tập", 1,
     [(4, ["Achv", "Plan", "RevItem", "Attempt"]), (5, ["Path", "Unit", "Lesson", "Step"]),
      (6, ["PathSt", ("StepKind", "Step")])]),
]  # fmt: skip
COLUMNS = []

# `--spec v3`: sinh THIET KE DICH tu `tools/class_spec_v3.py` thay cho so do
# hien trang o tren. Cung bo cuc, cung bo dinh tuyen canh, chi khac dac ta --
# chep ca tep sang mot ban thu hai se nhan doi 600 dong code ve hinh.
PAGE_NAME = "So do lop"
_spec = None
if "--spec" in sys.argv:
    import importlib

    sys.path.insert(0, str(ROOT / "tools"))
    _spec = importlib.import_module(f"class_spec_{sys.argv[sys.argv.index('--spec') + 1]}")
    CLASSES, ENUMS, EDGES = _spec.CLASSES, _spec.ENUMS, _spec.EDGES
    COLUMNS = [(40 + i * COL_DX, ids) for i, ids in enumerate(_spec.COLUMN_IDS)]
    PAGE_NAME = _spec.PAGE_NAME
    ZONES = None
    if "--out" not in sys.argv:
        OUT = ROOT / _spec.OUT

BOX = (
    "swimlane;fontStyle=1;align=center;verticalAlign=top;childLayout=stackLayout;"
    f"horizontal=1;startSize={TITLE_H};horizontalStack=0;resizeParent=1;resizeParentMax=0;"
    "resizeLast=0;collapsible=1;marginBottom=0;whiteSpace=wrap;html=1;"
    "fillColor=#ffffff;strokeColor=#000000;fontSize=13;"
)
ENUMBOX = BOX.replace("fillColor=#ffffff", "fillColor=#eef2f8")
LINE = (
    "text;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;"
    "spacingLeft=6;spacingRight=6;overflow=hidden;points=[[0,0.5],[1,0.5]];"
    "portConstraint=eastwest;rotatable=0;whiteSpace=wrap;html=1;fontSize=12;"
)
STYLE = {
    # Hop thanh: kim cuong dac o dau so huu.
    "comp": (
        "endArrow=none;html=1;startArrow=diamondThin;startSize=14;startFill=1;"
        "edgeStyle=orthogonalEdgeStyle;rounded=0;strokeColor=#000000;fontSize=11;"
    ),
    "assoc": (
        "endArrow=open;html=1;endSize=10;edgeStyle=orthogonalEdgeStyle;rounded=0;"
        "strokeColor=#000000;fontSize=11;"
    ),
    # Nhieu-nhieu: duong lien, khong dau mui ten, boi so o hai dau.
    "nn": (
        "endArrow=none;html=1;edgeStyle=orthogonalEdgeStyle;rounded=0;"
        "strokeColor=#000000;strokeWidth=2;fontSize=11;"
    ),
    # Generalization: hollow triangle at the parent.
    "gen": (
        "endArrow=block;endFill=0;endSize=14;html=1;edgeStyle=orthogonalEdgeStyle;"
        "rounded=0;strokeColor=#000000;fontSize=11;"
    ),
    # Phu thuoc UML: net dut, dau mui ten mo.
    "enum": (
        "endArrow=open;html=1;endSize=8;dashed=1;edgeStyle=orthogonalEdgeStyle;"
        "rounded=0;strokeColor=#000000;fontSize=10;fontColor=#000000;"
    ),
}

SPEC = {c[0]: c for c in CLASSES + ENUMS}


def check_relations() -> None:
    """Every line has its attribute, every class-typed attribute has its line.

    The owner's rule for this diagram: a relationship is drawn only where the
    class holding it has an attribute of the other class's type, and the
    multiplicity at the far end of the line is that attribute's multiplicity.
    """
    name = {c[0]: c[1].split(BR)[-1] for c in CLASSES + ENUMS}
    typed = re.compile(r"^- (\w+): (\w+)(?: \[([^\]]*)\])?$")
    problems = []
    claimed: set[tuple[str, str]] = set()
    for src, dst, label, kind in EDGES:
        lines = SPEC[src][2]
        if kind == "enum":
            hits = [ln for ln in lines if (m := typed.match(ln)) and m.group(2) == name[dst]]
            if not hits:
                problems.append(f"{name[src]} uses {name[dst]} but no attribute has that type")
            continue
        # The far end may carry the role name before its multiplicity
        # ("teachers 0..*"); then it must be the attribute that holds the line.
        far_parts = label.split(" : ")[1].split()
        far, role = far_parts[-1], (far_parts[0] if len(far_parts) > 1 else None)
        hits = [
            m.group(1)
            for ln in lines
            if (m := typed.match(ln))
            and m.group(2) == name[dst]
            and (m.group(3) or "1") == far
            and (role is None or m.group(1) == role)
            and (src, m.group(1)) not in claimed
        ]
        if not hits:
            problems.append(f"{name[src]} -> {name[dst]} [{far}]: no attribute holds it")
        else:
            claimed.add((src, hits[0]))
    classes = {name[c[0]] for c in CLASSES}
    for c in CLASSES:
        for ln in c[2]:
            m = typed.match(ln)
            if m and m.group(2) in classes and (c[0], m.group(1)) not in claimed:
                problems.append(f"{name[c[0]]}.{m.group(1)}: {m.group(2)} has no line")
    if problems:
        raise SystemExit("relations:\n  " + "\n  ".join(problems))


if ZONES:
    check_relations()
GEO: dict[str, tuple[int, int, int]] = {}
if ZONES:
    sys.path.insert(0, str(ROOT / "tools"))
    import zone_layout

    GEO, ZONE_OF, FRAMES = zone_layout.place(ZONES, lambda cid: TITLE_H + LH * len(SPEC[cid][2]), W)
for _x, _ids in COLUMNS:
    _y = 40
    for _cid in _ids:
        _h = TITLE_H + LH * len(SPEC[_cid][2])
        GEO[_cid] = (_x, _y, _h)
        _y += _h + GAP


GAPX = COL_DX - W
COL_XS = [x for x, _ in COLUMNS]
COL_OF = {cid: x for x, ids in COLUMNS for cid in ids}
ROW_OF = {cid: i for _x, ids in COLUMNS for i, cid in enumerate(ids)}
BOTTOM = max(y + h for _x, y, h in GEO.values())


# Names of the classes drawn (not the enumerations): an attribute typed with one
# of them is an association, and UML writes its multiplicity on the line, not
# in the box -- `assessment: Assessment`, with `0..1` at the end of the edge.
CLASS_NAMES = {c[1].split(BR)[-1] for c in CLASSES}
_MULTIPLICITY = re.compile(r"^([-+] \w+: (\w+)) \[[^\]]*\]$")


def attribute_text(text: str) -> str:
    """The attribute as drawn: an association's multiplicity left to its edge.

    Multiplicity belongs to a relationship between two entities and is written
    on the line. In the box the attribute keeps its name and type: the entity,
    or `List<Entity>` when the far end holds more than one.
    """
    m = _MULTIPLICITY.match(text)
    if not (m and m.group(2) in CLASS_NAMES):
        return text
    upper = text.rsplit("[", 1)[1].rstrip("]").split("..")[-1]
    if upper == "1":
        return m.group(1)
    name = m.group(1).rsplit(": ", 1)[0]
    return f"{name}: List<{m.group(2)}>"


def box(cid, box_title, lines, style):
    if NO_STEREOTYPE:
        box_title = box_title.split(BR)[-1]
    x, y, h = GEO[cid]
    out = [
        f'<mxCell id="{cid}" value="{title(box_title)}" style="{style}" vertex="1" '
        f'parent="1"><mxGeometry x="{x}" y="{y}" width="{W}" height="{h}" '
        f'as="geometry"/></mxCell>'
    ]
    for i, text in enumerate(lines):
        out.append(
            f'<mxCell id="{cid}-{i}" value="{label(attribute_text(text))}" '
            f'style="{LINE}" vertex="1" parent="{cid}">'
            f'<mxGeometry y="{TITLE_H + LH * i}" width="{W}" height="{LH}" '
            f'as="geometry"/></mxCell>'
        )
    return out


def mid_y(cid):
    _x, y, h = GEO[cid]
    return y + h / 2


def gutter(i):
    """Tam khe doc giua cot i va cot i+1."""
    return COL_XS[i] + W + GAPX / 2


def _blocked(y, col_xs, pad=12):
    return any(
        a - pad <= y <= a + h + pad for cx in col_xs for _c, (x, a, h) in GEO.items() if x == cx
    )


def free_y(col_xs, lo, hi, avoid, step=2, min_sep=30):
    """Cao do ngang di qua moi cot trong `col_xs` ma khong cham hop nao.

    `avoid` la cac cao do da co canh khac dung; hai duong ngang cach nhau
    duoi `min_sep` diem nhin ra mot duong.
    """
    lo, hi = int(lo), int(hi)
    rng = range(lo, hi, step) if hi > lo else range(lo, hi, -step)
    for y in rng:
        if not _blocked(y, col_xs) and all(abs(y - u) >= min_sep for u in avoid):
            return y
    return None


def sides(src, dst):
    """Canh nao cua hop thi duong di ra, canh nao thi di vao."""
    if COL_OF[src] == COL_OF[dst]:
        # Cung cot: di doc. Di ngang se vong ra ngoai roi vong lai, vo nghia.
        return (0.5, 1, 0.5, 0) if mid_y(dst) > mid_y(src) else (0.5, 0, 0.5, 1)
    # Khac cot: LUON di ngang. Cho di doc thi duong cham thang vao hop nam
    # ngay duoi trong cung cot.
    return (1, 0.5, 0, 0.5) if COL_OF[dst] > COL_OF[src] else (0, 0.5, 1, 0.5)


def build_routes():
    """Duong di cua canh, TINH tu toa do -- khong go tay.

    Moi con so duoi day do bang mot bo kiem tra hinh hoc: no dung lai duong di
    tu XML roi dem cac doan xuyen hop, trung nhau, va cach nhau duoi 8 diem.
    Ban dau: 15 cap trung, nang nhat la `Assessment->CriterionCoverage` voi
    `Assessment->ReasonCode` chong nhau 755 diem.

    Bon nguyen nhan goc da tim ra, moi cai la mot bai hoc rieng:

      1. Hai canh tu cung mot hop tới hai hop CUNG MOT COT deu re doc o canh
         phai cot dich -- cung mot x.
      2. Canh cung cot va canh khac cot cap toa do doc DOC LAP nhau nen hai he
         lan dam vao nhau trong cung mot khe.
      3. Cao do RA va cao do VAO cua cung mot hop duoc cap boi hai nhom rieng,
         nen chung roi trung nhau.
      4. Cap theo PHAN SO thay vi theo KHOANG CACH DIEM: hop `Response` cao gan
         gap ba hop `Comment`, nen cung mot buoc phan so cho ra hai khoang cach
         that khac nhau hoan toan.

    Thiet ke hien tai: mot bo cap lan duy nhat. Moi canh nhan lan doc rieng
    trong tung khe no di qua, cong mot cong ra va mot cong vao rieng cach nhau
    it nhat 22 diem. Duong di chi gom cac doan nam trong khe doc hoac trong
    mot dai ngang KHONG dam vao hop nao:

        hop nguon --ngang--> lan doc --doc--> dai ngang trong --ngang-->
        lan doc --doc--> cong vao --ngang--> hop dich
    """
    routes: dict[tuple[str, str], tuple] = {}
    used_bands: list[float] = []

    same_col = [
        (s, d)
        for s, d, _l, _k in EDGES
        if COL_OF[s] == COL_OF[d] and abs(ROW_OF[s] - ROW_OF[d]) != 1
    ]
    cross = [(s, d) for s, d, _l, _k in EDGES if COL_OF[s] != COL_OF[d]]
    # Cot ngoai cung ben trai khong co khe ben trai -> canh cung cot o day vong
    # ra ngoai ban ve.
    outside = [k for k in same_col if COL_OF[k[0]] == COL_XS[0]]
    routed = [k for k in same_col if k not in outside] + cross

    def col_i(cid):
        return COL_XS.index(COL_OF[cid])

    def gaps_needed(key):
        """Cac khe ma canh nay can mot lan doc, danh so theo cot ben trai khe."""
        src, dst = key
        i, j = col_i(src), col_i(dst)
        if i == j:
            return [i]  # cung cot: mot lan trong khe ben phai cot do
        if abs(i - j) == 1:
            return [min(i, j)]  # ke nhau: mot lan trong khe giua hai cot
        # Cach tu hai cot: mot lan sat hop nguon, mot lan sat hop dich.
        return [i, j - 1] if j > i else [i - 1, j]

    # ---- cap lan doc, chia deu trong tung khe
    per_gap: dict[int, list[tuple[str, str]]] = {}
    for key in routed:
        for gi in gaps_needed(key):
            per_gap.setdefault(gi, []).append(key)
    lane: dict[tuple[tuple[str, str], int], float] = {}
    for gi, keys in per_gap.items():
        left = COL_XS[gi] + W
        step = (GAPX - 24) / max(len(keys) - 1, 1)
        for n, key in enumerate(sorted(keys)):
            lane[(key, gi)] = left + 12 + n * step
    outside_lane = {k: COL_XS[0] - 30 - 30 * n for n, k in enumerate(sorted(outside))}

    def sides_of(key):
        """Phia ra va phia vao.

        Canh cung cot phai ra VA vao CUNG mot phia. Loi da mac va da do duoc:
        cho canh cung cot ra khe ben phai roi vao mep TRAI hop dich -- duong khi
        do ke ngang qua CA BE RONG hop dich, 300 diem, muoi canh nhu vay. Phep
        kiem "xuyen hop" khong thay vi no co y bo qua hai hop dau mut; phai
        them mot phep kiem rieng moi lo ra.
        """
        src, dst = key
        if COL_OF[src] == COL_OF[dst]:
            side = 0 if key in outside else 1
            return side, side
        return (1, 0) if COL_OF[dst] > COL_OF[src] else (0, 1)

    # ---- cap cong: mot hop, mot phia, cap cho CA canh ra VA canh vao mot luot
    MIN_DY = 22  # mot dong chu trong hop -- duoi muc nay hai duong nhin thanh mot
    port_y: dict[tuple[tuple[str, str], str], float] = {}
    on_side: dict[tuple[str, int], list[tuple[tuple[str, str], str]]] = {}
    for key in routed + outside:
        so, si = sides_of(key)
        on_side.setdefault((key[0], so), []).append((key, "out"))
        on_side.setdefault((key[1], si), []).append((key, "in"))
    for (bid, _side), slots in on_side.items():
        _bx, by, bh = GEO[bid]
        n, pad = len(slots), 14
        step = min(MIN_DY * 1.6, (bh - 2 * pad) / max(n - 1, 1)) if n > 1 else 0
        top = by + (bh - step * (n - 1)) / 2
        for k, slot in enumerate(sorted(slots)):
            port_y[slot] = top + k * step

    def pick_band(between, avoid):
        """Mot cao do ngang khong dam vao hop nao cua cac cot o giua.

        Noi dan khoang cach toi thieu thay vi bo cuoc, va **khong bao gio** giu
        lai mot cao do chua kiem. Hai loi da mac o day:
          - giu nguyen cao do cong khi khong tim duoc dai trong -> duong ke
            thang qua long hop `FeatureSet`, im lang;
          - viet `free_y(trong than hop) or free_y(day ban ve)` -- Python lay
            ngay ket qua o day ban ve tai muc nghiem nhat, trong khi cot giua
            con SAU dai trong chua dung. Phai vet het cac muc noi long TRUOC
            khi doi cho khac.
        """
        # Tim toi qua day ban ve 400 diem: duoi hop thap nhat luon con cho
        # trong. Hinh nhieu cot (thiet ke dich co 8 cot) co the khong con dai
        # ngang nao trong than hinh. Thu tu duyet tu tren xuong nen hinh nao
        # da tim duoc dai trong than hinh van ra dung toa do cu.
        for sep in (30, 24, 18, 12, 8):
            y = free_y(between, 40, BOTTOM + 400, avoid, min_sep=sep)
            if y is not None:
                return y
        return None

    for key in routed + outside:
        src, dst = key
        i, j = col_i(src), col_i(dst)
        sx, sy, sh = GEO[src]
        tx, ty, th = GEO[dst]
        side_out, side_in = sides_of(key)
        y_out = port_y[(key, "out")]
        y_in = port_y[(key, "in")]

        if key in outside:
            gx = outside_lane[key]
            pts = [(gx, y_out), (gx, y_in)]
        elif abs(i - j) < 2:
            gi = gaps_needed(key)[0]
            gx = lane[(key, gi)]
            pts = [(gx, y_out), (gx, y_in)]
        else:
            g_src, g_dst = gaps_needed(key)
            x1, x2 = lane[(key, g_src)], lane[(key, g_dst)]
            between = COL_XS[min(i, j) + 1 : max(i, j)]
            # Tranh CA cong cua hop nguon phia di ra VA cong cua hop dich phia
            # di vao: dai ngang ket thuc ngay canh hop dich, nen no de nam de
            # len mot canh khac cung roi hop do o phia ay. Thieu ve sau la loi
            # da do duoc -- `Response->Assessment` trung `Assessment->ReasonCode`
            # 43 diem.
            avoid = (
                used_bands
                + [port_y[t] for t in on_side.get((src, side_out), []) if t[0] != key]
                + [port_y[t] for t in on_side.get((dst, side_in), []) if t[0] != key]
            )
            band = pick_band(between, avoid)
            if band is None:
                raise SystemExit(
                    f"khong tim duoc dai ngang trong cho canh {src}->{dst}. "
                    "Noi khe giua hai cot ra, hoac doi cho hai hop cho gan nhau."
                )
            used_bands.append(band)
            pts = [(x1, y_out), (x1, band), (x2, band), (x2, y_in)]

        routes[key] = (
            side_out,
            round(min(max((y_out - sy) / sh, 0.0), 1.0), 3),
            side_in,
            round(min(max((y_in - ty) / th, 0.0), 1.0), 3),
            pts,
        )
    return routes


ROUTES = {} if ZONES else build_routes()
ZONE_ROUTES = zone_layout.route(EDGES, GEO, ZONE_OF, FRAMES, W) if ZONES else {}


# Doi mot vai nhan ra khoi cho co duong khac cat qua. Chi can khi mot canh di
# trong khe doc va nhan boi so cua canh khac roi dung vao do.
LABEL_NUDGE = {
    ("Report", "Asmt", 1): 'y="-18"',
    ("Report", "Feat", 1): 'y="-18"',
}
if _spec is not None:
    LABEL_NUDGE = _spec.LABEL_NUDGE


def edge(i, src, dst, label, kind):
    """Mot canh, kem boi so dat sat HAI DAU thay vi mot nhan o giua.

    Nhan giua duong thuong roi trung vao mot hop khac.
    """
    if (src, dst) in ROUTES:
        ex, ey, nx, ny, waypoints = ROUTES[(src, dst)]
    else:
        ex, ey, nx, ny = sides(src, dst)
        waypoints = []
    anchors = (
        f"exitX={ex};exitY={ey};exitDx=0;exitDy=0;entryX={nx};entryY={ny};entryDx=0;entryDy=0;"
    )
    pts = ""
    if waypoints:
        inner = "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in waypoints)
        pts = f'<Array as="points">{inner}</Array>'
    cells = [
        f'<mxCell id="e{i}" style="{STYLE[kind]}{anchors}" edge="1" parent="1" '
        f'source="{src}" target="{dst}">'
        f'<mxGeometry relative="1" as="geometry">{pts}</mxGeometry></mxCell>'
    ]
    if kind == "enum" or " : " not in label:
        return cells
    lab = (
        "text;html=1;align=center;verticalAlign=middle;resizable=0;points=[];"
        "labelBackgroundColor=#ffffff;fontSize=11;fontColor=#000000;"
    )
    # Nhan dat gan hai DAU canh. Dau dich lui vao 0.7 chu khong 0.85: nhan o
    # dau dich mang ca ten vai tro lan boi so ("assessment 0..1") nen dai hon,
    # de 0.85 thi no de len chinh hop dich.
    for k, (txt, pos) in enumerate(zip(label.split(" : "), (-0.85, 0.72), strict=True)):
        cells.append(
            f'<mxCell id="e{i}l{k}" value="{html.escape(txt.strip())}" style="{lab}" '
            f'vertex="1" connectable="0" parent="e{i}">'
            f'<mxGeometry x="{pos}" relative="1" as="geometry">'
            f'<mxPoint {LABEL_NUDGE.get((src, dst, k), "")} as="offset"/>'
            f"</mxGeometry></mxCell>"
        )
    return cells


ZONE_STYLE = (
    "rounded=1;arcSize=2;whiteSpace=wrap;html=1;fillColor=#f6f8fb;strokeColor=#8a96a8;"
    "verticalAlign=top;align=left;spacingLeft=14;spacingTop=8;fontStyle=1;fontSize=16;"
    "fontColor=#2b3442;"
)
LABEL_STYLE = (
    "text;html=1;align=center;verticalAlign=middle;resizable=0;points=[];"
    "labelBackgroundColor=#ffffff;fontSize=11;fontColor=#000000;spacing=0;"
)


def zone_frame(key):
    name, x, y, w, h = FRAMES[key]
    return (
        f'<mxCell id="zone-{key}" value="{html.escape(name)}" style="{ZONE_STYLE}" '
        f'vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" '
        f'as="geometry"/></mxCell>'
    )


def zone_edge(i, src, dst, label, kind):
    """An edge along its routed path, multiplicities beside the two ports.

    Each multiplicity is a label of the edge pinned to one END of the path
    (`x=-1` the source, `x=1` the target) and pushed beside the port by an
    offset. A label at a fraction of the path would land far from its box on a
    long path; a free text cell would no longer belong to the edge, and
    `tests/test_diagrams.py` reads the target's multiplicity from the edge.
    """
    pts, side_out, side_in = ZONE_ROUTES[i]
    (x0, y0), (x1, y1) = pts[0], pts[-1]
    sx, sy, sh = GEO[src]
    tx, ty, th = GEO[dst]
    anchors = (
        f"exitX={(x0 - sx) / W:.4f};exitY={(y0 - sy) / sh:.4f};exitPerimeter=0;"
        f"entryX={(x1 - tx) / W:.4f};entryY={(y1 - ty) / th:.4f};entryPerimeter=0;"
    )
    style = STYLE[kind].replace("edgeStyle=orthogonalEdgeStyle;", "edgeStyle=none;")
    inner = "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in pts[1:-1])
    cells = [
        f'<mxCell id="e{i}" style="{style}{anchors}" edge="1" parent="1" '
        f'source="{src}" target="{dst}"><mxGeometry relative="1" as="geometry">'
        f'<Array as="points">{inner}</Array></mxGeometry></mxCell>'
    ]
    if kind == "enum" or " : " not in label:
        return cells
    for k, (txt, end, side) in enumerate(
        zip(label.split(" : "), (-1, 1), (side_out, side_in), strict=True)
    ):
        txt = txt.strip()
        half = (7 * len(txt) + 6) / 2
        dx, dy = {
            "R": (half + 4, -10),
            "L": (-half - 4, -10),
            "B": (half + 3, 11),
            "T": (half + 3, -11),
        }[side]
        cells.append(
            f'<mxCell id="e{i}l{k}" value="{html.escape(txt)}" style="{LABEL_STYLE}" '
            f'vertex="1" connectable="0" parent="e{i}">'
            f'<mxGeometry x="{end}" relative="1" as="geometry">'
            f'<mxPoint x="{dx}" y="{dy}" as="offset"/></mxGeometry></mxCell>'
        )
    return cells


def main() -> None:
    cells: list[str] = []
    for key in FRAMES if ZONES else []:
        cells.append(zone_frame(key))
    for c in CLASSES:
        cells += box(c[0], c[1], c[2], BOX)
    for e in ENUMS:
        cells += box(e[0], e[1], e[2], ENUMBOX)
    for i, (src, dst, label, kind) in enumerate(EDGES):
        cells += (zone_edge if ZONES else edge)(i, src, dst, label, kind)

    body = "".join("\n        " + c for c in cells)
    page_id = PAGE_NAME.lower().replace(" ", "-")
    xml = f"""<mxfile host="app.diagrams.net" type="device">
  <diagram name="{PAGE_NAME}" id="{page_id}">
    <mxGraphModel dx="1400" dy="900" grid="1" gridSize="10" guides="1" tooltips="1"
                  connect="1" arrows="1" fold="1" page="1" pageScale="1"
                  pageWidth="1654" pageHeight="1169" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>{body}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(xml, encoding="utf-8")
    n_ent = sum(1 for c in CLASSES if "«entity»" in c[1])
    print(
        f"{OUT}: {n_ent} entity, {len(CLASSES) - n_ent} value object, "
        f"{len(ENUMS)} enumeration, {len(EDGES)} quan he, {len(xml)} byte"
    )


if __name__ == "__main__":
    main()
