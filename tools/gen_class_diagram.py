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
    phap UML `+/-/# ten: Kieu [boi so]` va `+ ten(thamso: Kieu): KieuTra`.
    Mot so do lop khong co kieu thi khong ra duoc code tu no.
  * dien dat TINH TUY CHON bang BOI SO UML `[0..1]`, tap hop bang `[*]` --
    KHONG dung `X | None` hay `list[X]`. Hai cach sau la cu phap chu thich
    kieu cua Python, khong phai UML; tron chung vao mot so do lop la sai
    chuan. `float [0..1]` va `float | None` noi cung mot dieu, nhung chi cai
    dau la thu nguoi doc UML mong doi.
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


CLASSES = [
    (
        "Account",
        "«entity»" + BR + "Account",
        [
            "- accountId: str",
            "- pseudonym: str",
            "- role: Role",
            "- mustChangePassword: bool",
            "- avatarIcon: str",
            "- avatarColor: str",
            "- dailyGoalS: int",
            "+ isTeacher(): bool",
        ],
    ),
    (
        "Consent",
        "«entity»" + BR + "Consent",
        [
            "- consentId: str",
            "- accountId: str",
            "- consentVersion: str",
            "- audioStorageAllowed: bool",
            "- researchUseAllowed: bool",
            "- signedAt: str",
            "- withdrawnAt: str",
            "+ maySubmit(): bool",
        ],
    ),
    (
        "Review",
        "«entity»" + BR + "Review",
        [
            "- reviewerId: str",
            "- oldScore: float",
            "- newScore: float",
            "- oldBand: Band",
            "- newBand: Band",
            "- reason: str",
            "- createdAt: str",
        ],
    ),
    (
        "Task",
        "«entity»" + BR + "Task",
        [
            "- taskId: str",
            "- title: str",
            "- promptText: str",
            "- promptVersion: str",
            "- part: TaskPart",
            "- minSeconds: int",
            "- maxSeconds: int",
            "- topicKeywords: List<str>",
            "- purpose: TaskPurpose",
            "- criterion: Criterion",
            "- band: Band",
            "- missions: List<Mission>",
            "- tips: List<str>",
            "- referenceText: str",
        ],
    ),
    (
        "Report",
        "«entity»" + BR + "Response",
        [
            "- responseId: str",
            "- status: Status",
            "- qc: QcResult",
            "- asr: Transcript",
            "- features: FeatureSet",
            "- assessment: Assessment",
            "- reasons: List<ReasonCode>",
            "- configVersion: str",
            "- promptVersion: str",
            "- consentVersion: str",
            "- practice: PracticeResult",
        ],
    ),
    (
        "Qc",
        "«value object»" + BR + "QcResult",
        [
            "- durationMs: int",
            "- sampleRateHz: int",
            "- channels: int",
            "- silenceRatio: float",
            "- clippingRatio: float",
            "- snrDb: float",
            "- qcStatus: QcStatus",
            "- qcConfigVersion: str",
            "- reasons: List<ReasonCode>",
            "+ passed(): bool",
        ],
    ),
    (
        "Asr",
        "«value object»" + BR + "Transcript",
        [
            "- text: str",
            "- words: List<Word>",
            "- engine: str",
            "- modelVersion: str",
            "- hasWordTimestamps: bool",
            "- isVerbatim: bool",
            "- language: str",
            "- languageProbability: float",
            "- outputTokens: int",
        ],
    ),
    (
        "Word",
        "«value object»" + BR + "Word",
        [
            "- text: str",
            "- startS: float",
            "- endS: float",
            "- prob: float",
            "+ isUncertain(): bool",
        ],
    ),
    (
        "Feat",
        "«value object»" + BR + "FeatureSet",
        [
            "- items: List<Feature>",
            "- featureVersion: str",
            "+ valueOf(name: str): float",
            "+ vector(order: List<str>): List<float>",
        ],
    ),
    (
        "Ftr",
        "«value object»" + BR + "Feature",
        ["- name: str", "- value: float", "- reason: ReasonCode"],
    ),
    (
        "Win",
        "«value object»" + BR + "AnalysisWindow",
        [
            "- index: int",
            "- startS: float",
            "- endS: float",
            "- overall06: float",
            "- band: Band",
            "- reasons: List<ReasonCode>",
        ],
    ),
    (
        "Cov",
        "«value object»" + BR + "CriterionCoverage",
        ["- criterion: Criterion", "- coverage: float", "- reasons: List<ReasonCode>"],
    ),
    (
        "Asmt",
        "«entity»" + BR + "Assessment",
        [
            "- overall06: float",
            "- overallBand: Band",
            "- criteria: List<CriterionCoverage>",
            "- evidence: List<Evidence>",
            "- modelVersion: str",
            "- featureVersion: str",
            "- bandMapVersion: str",
            "- calibrationVersion: str",
            "- scoredAt: str",
            "- reasons: List<ReasonCode>",
            "- comments: List<Comment>",
            "- priorities: List<Priority>",
            "- windows: List<AnalysisWindow>",
            "- windowSpread: float",
            "- outOfRange: List<Map>",
            "- teacherVerified: bool",
            "- interval: ScoreInterval",
            "- indicators: List<CriterionIndicator>",
            "- weakestCriteria: List<Criterion>",
            "+ isCalibrated(): bool",
        ],
    ),
    (
        "Ev",
        "«value object»" + BR + "Evidence",
        [
            "- evidenceId: str",
            "- criterion: Criterion",
            "- kind: EvidenceKind",
            "- startS: float",
            "- endS: float",
            "- snippet: str",
            "- note: str",
        ],
    ),
    (
        "Cmt",
        "«value object»" + BR + "Comment",
        ["- criterion: Criterion", "- text: str", "- evidenceRefs: List<str>"],
    ),
    (
        "Pri",
        "«value object»" + BR + "Priority",
        ["- featureName: str", "- text: str", "- impact: float"],
    ),
    (
        "Intv",
        "«value object»" + BR + "ScoreInterval",
        [
            "- low: float",
            "- high: float",
            "- bandSet: List<Band>",
            "- coverage: float",
            "- method: str",
            "- calibrationVersion: str",
            "+ isSingleBand(): bool",
        ],
    ),
    (
        "Ind",
        "«value object»" + BR + "CriterionIndicator",
        [
            "- criterion: Criterion",
            "- feature: str",
            "- value: float",
            "- percentile: float",
            "- higherIsBetter: bool",
        ],
    ),
    (
        "Mis",
        "«value object»" + BR + "Mission",
        ["- kind: MissionKind", "- target: float", "- label: str", "- words: List<str>"],
    ),
    (
        "Prac",
        "«value object»" + BR + "PracticeResult",
        ["- taskId: str", "- checks: List<MissionCheck>", "- rulesVersion: str"],
    ),
    (
        "MChk",
        "«value object»" + BR + "MissionCheck",
        [
            "- kind: MissionKind",
            "- label: str",
            "- target: float",
            "- measured: float",
            "- met: bool",
            "- hits: List<MissionHit>",
            "- reason: ReasonCode",
        ],
    ),
    ("MHit", "«value object»" + BR + "MissionHit", ["- text: str", "- startS: float"]),
    # D057: what the metered channel charges, and what a recording used.
    (
        "Price",
        "«value object»" + BR + "PriceList",
        [
            "- firstMinuteRuns: float",
            "- extraMinuteRuns: float",
            "- practiceFactor: float",
            "- idpointPerRun: int",
            "- version: str",
        ],
    ),
    (
        "Tok",
        "«value object»" + BR + "TokenUsage",
        ["- inputTokens: int", "- outputTokens: int", "- estimated: bool"],
    ),
    # D056: a moment of a recording to listen to again; D055: a reminder.
    (
        "Mom",
        "«value object»" + BR + "Moment",
        [
            "- momentId: str",
            "- startS: float",
            "- endS: float",
            "- source: str",
            "- kind: str",
        ],
    ),
    (
        "Nud",
        "«value object»" + BR + "Nudge",
        ["- kind: str", "- text: str", "- href: str", "- urgent: bool"],
    ),
]

# Chi ve PHAN LOAI DONG dinh hinh mo hinh. `ReasonCode` la tu vung chan doan
# 22 gia tri -- xem docstring dau tep.
ENUMS = [
    ("Role", "«enumeration»" + BR + "Role", ["STUDENT", "TEACHER", "ADMIN"]),
    (
        "Status",
        "«enumeration»" + BR + "Status",
        ["QUEUED", "RUNNING", "COMPLETED", "REVIEW_REQUIRED", "REJECTED", "FAILED"],
    ),
    ("QcStatus", "«enumeration»" + BR + "QcStatus", ["PASS", "REVIEW", "REJECT"]),
    (
        "EvKind",
        "«enumeration»" + BR + "EvidenceKind",
        ["PAUSE", "FILLER", "LOW_CONFIDENCE_WORD", "LEXICAL"],
    ),
    ("TaskPart", "«enumeration»" + BR + "TaskPart", ["P3", "P4", "P5"]),
    ("TaskPurpose", "«enumeration»" + BR + "TaskPurpose", ["ASSESSMENT", "PRACTICE"]),
    (
        "MissionKind",
        "«enumeration»" + BR + "MissionKind",
        [
            "SPEAK_SECONDS",
            "MAX_PAUSE",
            "USE_WORDS",
            "UNIQUE_WORDS",
            "PAST_VERBS",
            "CONDITIONALS",
            "READ_ALOUD",
        ],
    ),
    ("Action", "«enumeration»" + BR + "Action", ["ASSESS", "PRACTICE"]),
    (
        "ReasonCode",
        "«enumeration»" + BR + "ReasonCode",
        [
            "AUDIO_UNSUPPORTED",
            "AUDIO_TOO_LARGE",
            "AUDIO_TOO_LONG",
            "AUDIO_TOO_SHORT",
            "CONSENT_MISSING",
            "HIGH_SILENCE_RATIO",
            "CLIPPING_DETECTED",
            "LOW_SNR",
            "WRONG_SAMPLE_RATE",
            "ASR_FAILED",
            "ASR_EMPTY_TRANSCRIPT",
            "ASR_LOW_CONFIDENCE",
            "ASR_HALLUCINATION",
            "FEATURE_NOT_COMPUTABLE",
            "TOO_FEW_WORDS",
            "SCORE_NEAR_BOUNDARY",
            "SCORE_AGGREGATED",
            "MODEL_VERSION_MISSING",
            "OUT_OF_DISTRIBUTION",
            "PROCESSING_INTERRUPTED",
            "ASR_VERSION_MISMATCH",
            "VAD_VERSION_MISMATCH",
            "LANGUAGE_NOT_ENGLISH",
            "OFF_TOPIC_SUSPECTED",
            "PROMPT_COPY_SUSPECTED",
        ],
    ),
    ("Band", "«enumeration»" + BR + "Band", ["A2", "B1", "B2"]),
    (
        "Criterion",
        "«enumeration»" + BR + "Criterion",
        ["RANGE", "ACCURACY", "FLUENCY", "COHERENCE", "PHONOLOGY"],
    ),
]

# (nguon, dich, "boi so nguon : boi so dich", kieu)
EDGES = [
    ("Account", "Consent", "1 : 0..*", "assoc"),
    ("Account", "Report", "1 : 0..*", "assoc"),
    ("Account", "Review", "1 : 0..*", "assoc"),
    ("Task", "Report", "1 : 0..*", "assoc"),
    ("Report", "Qc", "1 : 0..1", "comp"),
    ("Report", "Asr", "1 : 0..1", "comp"),
    ("Report", "Feat", "1 : 0..1", "comp"),
    ("Feat", "Ftr", "1 : 1..*", "comp"),
    ("Report", "Asmt", "1 : 0..1", "comp"),
    ("Report", "Review", "1 : 0..*", "assoc"),
    ("Asr", "Word", "1 : 0..*", "comp"),
    ("Asmt", "Cov", "1 : 5", "comp"),
    ("Asmt", "Win", "1 : 0..10", "comp"),
    ("Asmt", "Ev", "1 : 0..10", "comp"),
    ("Asmt", "Cmt", "1 : 0..4", "comp"),
    ("Asmt", "Pri", "1 : 0..2", "comp"),
    ("Cmt", "Ev", "0..* : 1..*", "nn"),
    ("Account", "Role", "", "enum"),
    ("Report", "ReasonCode", "", "enum"),
    ("Qc", "ReasonCode", "", "enum"),
    ("Asmt", "ReasonCode", "", "enum"),
    ("Win", "ReasonCode", "", "enum"),
    ("Cov", "ReasonCode", "", "enum"),
    ("Ftr", "ReasonCode", "", "enum"),
    ("Report", "Status", "", "enum"),
    ("Qc", "QcStatus", "", "enum"),
    ("Asmt", "Band", "", "enum"),
    ("Cov", "Criterion", "", "enum"),
    ("Win", "Band", "", "enum"),
    ("Ev", "Criterion", "", "enum"),
    ("Ev", "EvKind", "", "enum"),
    ("Task", "TaskPart", "", "enum"),
    ("Cmt", "Criterion", "", "enum"),
    ("Review", "Band", "", "enum"),
    ("Report", "Prac", "1 : 0..1", "comp"),
    ("Prac", "MChk", "1 : 0..*", "comp"),
    # Shared with the lesson steps (`Step`, `StepResult`): association, not composition.
    ("MChk", "MHit", "1 : 0..*", "assoc"),
    ("Task", "Mis", "1 : 0..*", "assoc"),
    ("Asmt", "Intv", "1 : 0..1", "comp"),
    ("Asmt", "Ind", "1 : 0..*", "comp"),
    ("Task", "TaskPurpose", "", "enum"),
    ("Mis", "MissionKind", "", "enum"),
    ("MChk", "MissionKind", "", "enum"),
    ("MChk", "ReasonCode", "", "enum"),
    ("Intv", "Band", "", "enum"),
    ("Ind", "Criterion", "", "enum"),
    ("Asmt", "Criterion", "", "enum"),
]

# Bon cot, doc tu trai sang phai theo luong nghiep vu. Enum dat canh lop dung
# no nhieu nhat de duong phu thuoc ngan.
COLUMNS = [
    (40, ["Account", "Role", "Consent", "Review", "Price", "Tok", "Action"]),
    (40 + COL_DX, ["Task", "TaskPart", "TaskPurpose", "Mis", "MissionKind", "Mom", "Nud"]),
    (40 + 2 * COL_DX, ["Status", "Report", "Qc", "QcStatus", "Prac", "MChk", "MHit"]),
    (40 + 3 * COL_DX, ["Asr", "Word", "Feat", "Ftr", "Win", "Cov", "ReasonCode"]),
    (40 + 4 * COL_DX, ["Asmt", "Intv", "Ind", "Ev", "Cmt", "Pri", "Band", "Criterion", "EvKind"]),
]

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
GEO: dict[str, tuple[int, int, int]] = {}
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
            f'<mxCell id="{cid}-{i}" value="{label(text)}" '
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


ROUTES = build_routes()


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


def main() -> None:
    cells: list[str] = []
    for c in CLASSES:
        cells += box(c[0], c[1], c[2], BOX)
    for e in ENUMS:
        cells += box(e[0], e[1], e[2], ENUMBOX)
    for i, (src, dst, label, kind) in enumerate(EDGES):
        cells += edge(i, src, dst, label, kind)

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
