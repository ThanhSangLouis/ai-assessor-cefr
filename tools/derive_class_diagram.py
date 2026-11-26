"""Derive the class diagrams from Nguyên's A4 page, changing content only.

    D=docs/sdd/diagrams/class
    .venv/bin/python tools/derive_class_diagram.py \
        $D/detailed/02_class_a4_ngang.drawio $D/detailed/02_class_detailed.drawio
    .venv/bin/python tools/derive_class_diagram.py --level core \
        $D/detailed/02_class_a4_ngang.drawio $D/02_class_core.drawio

The A4 page (`class/detailed/02_class_a4_ngang.drawio`) is the official layout and is
never edited here. Both pages keep its boxes, frames and edge waypoints, so
the report's two figures look alike; only the content changes:

  * `--level detailed` (default, Hình 2c): every business field and each
    entity's id (`orderId`, `responseId`, ...), no technical-only one
    (timestamps no rule depends on, gateway references, OTP codes, the review
    lock); business rows the code has added; two fixes (`DrillPassage.drills`,
    `Response.criterionIndicators`).
  * `--level core` (Hình 2a): the main attributes only -- the id, every
    attribute that holds a relation, the business state, the fields a rule
    depends on.
  * Both (D110): `Order.buyer` (the code's `buyer_id`); no `AuditEntry`,
    `LedgerEntry` and their enums (technical records, kept on the ERD); a
    passage gathers `1..*` drills.
  * Both: end markers set by the relationship rules -- composition (a part
    lives and dies with its whole) a filled diamond; aggregation (the holder
    gathers MANY independent parts in a List) a hollow diamond at the holder;
    every other reference, an enum-typed attribute included, an association
    arrow from the holder; no dependency, since every one of those types is
    stored. The lock edge removed; three relations the code has added.

Ports keep their absolute position; a port that falls off a shrunk box moves
up and a short jog beside the box takes the line back to its old height, so
the rest of the route is untouched. `tests/test_class_diagram_in_code.py`
checks both pages against the code and the relationship rules.
"""

import copy
import html
import re
import sys
import xml.etree.ElementTree as ET

ARGS = sys.argv[1:]
LEVEL = "detailed"
if "--level" in ARGS:
    LEVEL = ARGS.pop(ARGS.index("--level") + 1)
    ARGS.remove("--level")
SRC, OUT = ARGS
# Least gap between two ports on one box side, and between two jogs beside it.
PORT_GAP, JOG_DX = 20, 12
TITLE, ROW = 46, 22

DROP = {
    "Account": ["identities", "emailCodes", "reminderSentOn", "isStaff"],
    "Achievement": ["unlockedAt"],
    "CoachUpgrade": ["createdAt"],
    "DrillPassage": ["takes", "createdAt"],
    "Lesson": ["versions", "media"],
    "Order": [
        "createdAt",
        "creditedAt",
        "checkoutRef",
        "reference",
        "settledAt",
        "events",
    ],
    "PriceList": ["changedAt"],
    "Response": [
        "durationMs",
        "replayLabels",
        "createdAt",
        "lockedBy",
        "lockedUntil",
    ],
    "StepAttempt": ["lessonVersion", "createdAt"],
    "WordDrill": ["takes", "createdAt"],
}
# Replace one row with one or more rows, in place.
REPLACE = {
    ("DrillPassage", "words"): ["- drills: List<WordDrill>", "- words: List<str>"],
    ("Response", "criterionScores"): ["- criterionIndicators: List<float>"],
    ("Response", "modelVersion"): ["- modelVersion: str", "- configVersion: str"],
    ("Lesson", "title"): ["- title: str", "- summary: str", "- keywords: List<str>"],
    ("LessonPath", "title"): ["- title: str", "- description: str"],
    ("Order", "createdBy"): ["- buyer: Account"],
    ("ReviewItem", "drill"): ["- drill: WordDrill", "- step: Step"],
    ("ReviewItem", "dueDate"): ["- dueDate: date", "- done: bool"],
    ("StepAttempt", "result"): [
        "- result: List<str>",
        "- override: Map<str, str>",
        "- overriddenBy: Account",
        "- reviewItem: ReviewItem",
    ],
}
# Step: every business field of the code class, in a reading order.
STEP_ROWS = [
    "- stepId: str", "- kind: StepKind", "- title: str", "- instruction: str", "- text: str",
    "- hintWords: List<str>", "- answers: List<str>", "- keywords: List<str>",
    "- starter: str", "- outline: List<str>",
    "- useAtLeast: int", "- minWords: int", "- prepSeconds: int", "- showSeconds: int",
    "- minSeconds: int", "- maxSeconds: int", "- rounds: List<int>", "- strictness: str",
    "- modelAudio: str", "- image: str", "- tip: str",
]  # fmt: skip

# Relationship rules. Composition stays; aggregation = the holder gathers MANY
# independent parts (a List of them); every other reference is an association
# (holder -> referenced); an enum-typed attribute is stored, so it is an
# association too, not a dependency.
# `--level core`: the main attributes of each class, every relation kept.
CORE_ROWS = {
    "Account": ["- accountId: str", "- email: str", "- emailVerified: bool", "- fullName: str",
                "- role: Role", "- dailyGoalS: int"],
    "Task": ["- taskId: str", "- title: str", "- promptText: str", "- topicKeywords: List<str>",
             "- band: Band"],
    "Response": ["- responseId: str", "- speaker: Account", "- task: Task",
                 "- status: ResponseStatus", "- transcript: str", "- overall06: float",
                 "- overallBand: Band", "- feedback: List<str>", "- reviews: List<Review>",
                 "- upgrade: CoachUpgrade"],
    "Review": ["- reviewId: int", "- reviewer: Account", "- oldBand: Band", "- newBand: Band",
               "- reason: str"],
    "CoachUpgrade": ["- fromBand: Band", "- toBand: Band", "- upgraded: str"],
    "Classroom": ["- classId: str", "- name: str", "- joinCode: str", "- teachers: List<Account>",
                  "- members: List<Account>", "- invited: List<Account>", "- archived: bool"],
    "LessonPath": ["- pathId: str", "- title: str", "- bandFrom: Band", "- bandTo: Band",
                   "- status: PathStatus", "- units: List<Unit>"],
    "Unit": ["- unitId: str", "- title: str", "- band: Band", "- criterion: Criterion",
             "- lessons: List<Lesson>"],
    "Lesson": ["- lessonId: str", "- title: str", "- band: Band", "- criterion: Criterion",
               "- passRatio: float", "- steps: List<Step>"],
    "Step": ["- stepId: str", "- kind: StepKind", "- text: str", "- prepSeconds: int"],
    "StepAttempt": ["- attemptId: str", "- learner: Account", "- step: Step", "- round: int",
                    "- passed: bool", "- overriddenBy: Account", "- reviewItem: ReviewItem"],
    "WordDrill": ["- drillId: str", "- learner: Account", "- response: Response", "- word: str",
                  "- passed: bool"],
    "DrillPassage": ["- passageId: str", "- learner: Account", "- drills: List<WordDrill>",
                     "- text: str"],
    "ReviewItem": ["- itemId: str", "- learner: Account", "- lesson: Lesson", "- drill: WordDrill",
                   "- step: Step", "- dueDate: date", "+ isDue(today: date): bool"],
    "Achievement": ["- code: str", "- learner: Account"],
    "LearningPlan": ["- planId: str", "- owner: Account", "- goal: str", "- audience: Role",
                     "- lessons: List<Lesson>"],
    "Order": ["- orderId: str", "- runs: int", "- amountVnd: int", "- status: OrderStatus",
              "- buyer: Account"],
    "Wallet": ["- owner: Account", "- balance: int", "+ available(): int"],
    "PriceList": ["- version: str", "- freeRuns: float", "- packs: List<str>"],
}  # fmt: skip

# Not drawn: technical records, not business concepts. `AuditEntry` (audit_log)
# is a log of who did what; `LedgerEntry` (ledger) is how a run is held,
# charged or given back exactly once -- the business sees the wallet's balance.
# Their two enums go with them. Both stay on the ERD and in the data dictionary.
REMOVED = {"AuditEntry", "LedgerEntry", "LedgerState", "MeteredAction"}
# Multiplicity labels changed: a passage gathers many drills, the 3..5 its
# writer picks is a rule of `coach/passage.py`, not a bound of the relation.
RELABEL = {("DrillPassage", "WordDrill", "3..5"): "1..*"}

AGGREGATION = {("Classroom", "Account"), ("LearningPlan", "Lesson"), ("DrillPassage", "WordDrill")}

tree = ET.parse(SRC)
root = tree.getroot()
model_root = root.find(".//root")
cells = {c.get("id"): c for c in root.iter("mxCell")}


def text(c):
    """A cell's text: the label unescaped, HTML tags turned into spaces."""
    return re.sub(r"<[^>]+>", " ", html.unescape(html.unescape(c.get("value") or ""))).strip()


boxes = {}  # id -> name
for cid, c in cells.items():
    if "swimlane" in (c.get("style") or ""):
        boxes[cid] = text(c).replace("«entity»", "").replace("«enumeration»", "").strip()
by_name = {n: i for i, n in boxes.items()}

# --- classes not drawn: their boxes, rows, edges and edge labels go
gone = {bid for bid, n in boxes.items() if n in REMOVED}
gone |= {
    c.get("id")
    for c in model_root
    if c.get("edge") == "1" and (c.get("source") in gone or c.get("target") in gone)
}
for c in list(model_root):
    if c.get("id") in gone or c.get("parent") in gone:
        model_root.remove(c)
for bid in gone:
    boxes.pop(bid, None)
    cells.pop(bid, None)
by_name = {n: i for i, n in boxes.items()}


def rows_of(bid):
    rows = [c for c in model_root if c.get("parent") == bid and c.get("vertex") == "1"]
    return sorted(rows, key=lambda c: float(c.find("mxGeometry").get("y")))


def attr(c):
    m = re.match(r"[-+#~]\s*(\w+)", text(c))
    return m.group(1) if m else None


def new_row(template, value, n):
    r = copy.deepcopy(template)
    r.set("id", f"{template.get('parent')}-r{n}")
    r.set("value", html.escape(value))
    return r


old_h = {bid: float(cells[bid].find("mxGeometry").get("height")) for bid in boxes}
serial = 0
for bid, name in boxes.items():
    rows = rows_of(bid)
    if not rows:
        continue
    template = rows[0]
    out = []
    if LEVEL == "core" and name in CORE_ROWS:
        out = [new_row(template, v, (serial := serial + 1)) for v in CORE_ROWS[name]]
    elif name == "Step":
        keep_ops = [r for r in rows if text(r).startswith("+")]
        out = [new_row(template, v, (serial := serial + 1)) for v in STEP_ROWS] + keep_ops
    else:
        for r in rows:
            a = attr(r)
            if a in DROP.get(name, []):
                continue
            if (name, a) in REPLACE:
                for v in REPLACE[(name, a)]:
                    serial += 1
                    out.append(new_row(template, v, serial))
            else:
                out.append(r)
    for r in rows:
        model_root.remove(r)
    insert_at = list(model_root).index(cells[bid]) + 1
    for k, r in enumerate(out):
        r.find("mxGeometry").set("y", str(TITLE + k * ROW))
        model_root.insert(insert_at + k, r)
    cells[bid].find("mxGeometry").set("height", str(TITLE + len(out) * ROW))

new_h = {bid: float(cells[bid].find("mxGeometry").get("height")) for bid in boxes}
geo = {
    bid: tuple(float(cells[bid].find("mxGeometry").get(k)) for k in ("x", "y", "width"))
    for bid in boxes
}


def style_dict(st):
    return dict(p.split("=", 1) for p in st.split(";") if "=" in p)


def style_str(d):
    return ";".join(f"{k}={v}" for k, v in d.items()) + ";"


# --- drop the lock edge (Response -> Account with target "0..1")
for c in list(model_root):
    if (
        c.get("edge") == "1"
        and boxes.get(c.get("source")) == "Response"
        and boxes.get(c.get("target")) == "Account"
    ):
        labels = [x for x in model_root if x.get("parent") == c.get("id")]
        if any("0..1" in (x.get("value") or "") for x in labels):
            for x in labels:
                model_root.remove(x)
            model_root.remove(c)

# --- ports: keep absolute positions; pull up a port that fell off a shrunk box
clamped = {}
# Ports that stay where they were, per box side: a port pulled up must keep
# clear of them, or its line runs right beside theirs.
staying: dict[tuple[str, float], list[float]] = {}
for c in [x for x in model_root if x.get("edge") == "1"]:
    d = style_dict(c.get("style") or "")
    for key_x, key_y, bid in (
        ("exitX", "exitY", c.get("source")),
        ("entryX", "entryY", c.get("target")),
    ):
        if bid in boxes and key_y in d:
            fx, fy = float(d[key_x]), float(d[key_y])
            if fx in (0.0, 1.0) and fy * old_h[bid] <= new_h[bid] - 12:
                staying.setdefault((bid, fx), []).append(fy * old_h[bid])


def free_offset(bid, fx, h1):
    """The lowest point on this side at least PORT_GAP from every other port."""
    taken = staying.setdefault((bid, fx), [])
    off = h1 - 14
    while off > 14 and any(abs(off - t) < PORT_GAP for t in taken):
        off -= 2
    taken.append(off)
    return off


for c in [x for x in model_root if x.get("edge") == "1"]:
    d = style_dict(c.get("style") or "")
    pts = c.find("mxGeometry").find("Array")
    plist = list(pts) if pts is not None else []
    for end, key_x, key_y, bid in (
        ("exit", "exitX", "exitY", c.get("source")),
        ("entry", "entryX", "entryY", c.get("target")),
    ):
        if bid not in boxes or key_y not in d:
            continue
        fx, fy = float(d[key_x]), float(d[key_y])
        h0, h1 = old_h[bid], new_h[bid]
        x, y, w = geo[bid]
        if fy in (0.0, 1.0) and fx not in (0.0, 1.0):
            continue  # top or bottom side: keeps its x; the segment just gets longer or shorter
        off = fy * h0
        if off > h1 - 12:
            k = clamped.setdefault((bid, fx), 0)
            clamped[(bid, fx)] += 1
            old_abs = y + off
            off = free_offset(bid, fx, h1)
            # Keep the old route: a short jog 20 points beside the box takes the
            # line from the new port back to the height it used to run at.
            side_x = x + w + 20 + JOG_DX * k if fx == 1.0 else x - 20 - JOG_DX * k
            jog = [(side_x, y + off), (side_x, old_abs)]
            if end == "entry":
                jog.reverse()
            if pts is None:
                pts = ET.SubElement(c.find("mxGeometry"), "Array", {"as": "points"})
            items = list(pts)
            for p in items:
                pts.remove(p)
            new_pts = [ET.Element("mxPoint", {"x": str(jx), "y": str(jy)}) for jx, jy in jog]
            items = new_pts + items if end == "exit" else items + new_pts
            for p in items:
                pts.append(p)
            plist = items
        d[key_y] = f"{off / h1:.4f}"
    # --- markers per the relationship rules
    s, t = boxes.get(c.get("source")), boxes.get(c.get("target"))
    if d.get("startArrow") == "diamondThin" and d.get("startFill") == "1":
        pass  # composition stays
    elif (s, t) in AGGREGATION:
        d.pop("strokeWidth", None)
        d.update(
            {
                "startArrow": "diamondThin",
                "startFill": "0",
                "startSize": "14",
                "endArrow": "none",
                "endFill": "0",
            }
        )
    else:  # association, including the attribute typed with an enum
        d.pop("dashed", None)
        d.pop("strokeWidth", None)
        d.update({"startArrow": "none", "endArrow": "open", "endSize": "10"})
        d.pop("startFill", None)
        d.pop("startSize", None)
    c.set("style", style_str(d))

for c in [x for x in model_root if x.get("edge") == "1"]:
    s_t = (boxes.get(c.get("source")), boxes.get(c.get("target")))
    for lab in [x for x in model_root if x.get("parent") == c.get("id")]:
        if (*s_t, lab.get("value")) in RELABEL:
            lab.set("value", RELABEL[(*s_t, lab.get("value"))])

# --- three new relations, routed in free space
template = next(
    x
    for x in model_root
    if x.get("edge") == "1"
    and boxes.get(x.get("source")) == "StepAttempt"
    and boxes.get(x.get("target")) == "Account"
)
tlabels = [x for x in model_root if x.get("parent") == template.get("id")]


def add_edge(eid, src, dst, exit_xy, entry_xy, points, src_mult, dst_mult, like=None):
    e = copy.deepcopy(template)
    e.set("id", eid)
    e.set("source", by_name[src])
    e.set("target", by_name[dst])
    d = style_dict(e.get("style"))
    d.update(
        {
            "exitX": f"{exit_xy[0]:.4f}",
            "exitY": f"{exit_xy[1]:.4f}",
            "entryX": f"{entry_xy[0]:.4f}",
            "entryY": f"{entry_xy[1]:.4f}",
        }
    )
    e.set("style", style_str(d))
    g = e.find("mxGeometry")
    for a in g.findall("Array"):
        g.remove(a)
    if points:
        arr = ET.SubElement(g, "Array", {"as": "points"})
        for px, py in points:
            ET.SubElement(arr, "mxPoint", {"x": str(px), "y": str(py)})
    model_root.append(e)
    ref = template
    if like:  # borrow the label placement of an existing edge running the same way
        ref = next(
            x
            for x in model_root
            if x.get("edge") == "1"
            and boxes.get(x.get("source")) == like[0]
            and boxes.get(x.get("target")) == like[1]
        )
    rlabels = [x for x in model_root if x.get("parent") == ref.get("id")]
    for lab, val in zip(
        sorted(rlabels, key=lambda x: float(x.find("mxGeometry").get("x"))),
        (src_mult, dst_mult),
        strict=True,
    ):
        l2 = copy.deepcopy(lab)
        l2.set("id", f"{eid}-{'s' if val is src_mult else 't'}")
        l2.set("parent", eid)
        l2.set("value", val)
        model_root.append(l2)


def frac_y(name, y):
    return (y - geo[by_name[name]][1]) / new_h[by_name[name]]


def frac_x(name, x):
    return (x - geo[by_name[name]][0]) / geo[by_name[name]][2]


ra, ri, st, ac = (geo[by_name[n]] for n in ("StepAttempt", "ReviewItem", "Step", "Account"))
# StepAttempt -> ReviewItem: straight up, attempt top to item bottom
add_edge(
    "n1",
    "StepAttempt",
    "ReviewItem",
    (0.78, 0.0),
    (0.78, 1.0),
    [],
    "0..*",
    "0..1",
    like=("ReviewItem", "WordDrill"),
)
# ReviewItem -> Step: item right side to the top of Step's left side; straight
# across when the two boxes overlap in height, else one bend in the gutter
# between them (on the core page the item's box ends above Step's top).
y = st[1] + 20
ri_bottom = ri[1] + new_h[by_name["ReviewItem"]]
y_out, bend = y, []
if y > ri_bottom - 14:
    y_out = ri_bottom - 16
    gutter = (ri[0] + ri[2] + st[0]) / 2
    bend = [(gutter, y_out), (gutter, y)]
add_edge(
    "n2",
    "ReviewItem",
    "Step",
    (1.0, frac_y("ReviewItem", y_out)),
    (0.0, frac_y("Step", y)),
    bend,
    "0..*",
    "0..1",
    like=("ReviewItem", "Lesson"),
)
# StepAttempt -> Account (overriddenBy): right of the learner edge, up into Account's bottom
y0 = 1550  # 20 below the learner edge; lane x=1730 is free (1740.. are taken)
# x=1730 above y=900 is WordDrill's; turn left at 930, enter Account's bottom at 1695.
add_edge(
    "n3",
    "StepAttempt",
    "Account",
    (0.0, frac_y("StepAttempt", y0)),
    (frac_x("Account", 1695), 1.0),
    [(1730, y0), (1730, 930), (1695, 930)],
    "0..*",
    "0..1",
)

# --- frames grow to hold the tallest box
bottom = max(geo[b][1] + new_h[b] for b in boxes) + 40
for c in model_root:
    if (c.get("id") or "").startswith("zone-"):
        g = c.find("mxGeometry")
        y0, h0 = float(g.get("y")), float(g.get("height"))
        if y0 + h0 < bottom and y0 + h0 > 1700:
            g.set("height", str(bottom - y0))

for d in root.iter("diagram"):
    d.set("name", "So do lop gon" if LEVEL == "core" else "So do lop chi tiet")
tree.write(OUT, encoding="utf-8", xml_declaration=False)
print(
    "written",
    OUT,
    "| rows:",
    sum(1 for c in model_root if c.get("parent") in boxes and c.get("vertex") == "1"),
    "| edges:",
    sum(1 for c in model_root if c.get("edge") == "1"),
)
