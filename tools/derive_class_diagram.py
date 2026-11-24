"""Derive the class diagrams from Nguyên's A4 page, changing content only.

    D=docs/sdd/diagrams/class
    .venv/bin/python tools/derive_class_diagram.py \
        $D/detailed/02_class_a4_ngang.drawio $D/detailed/02_class_detailed.drawio
    .venv/bin/python tools/derive_class_diagram.py --level core \
        $D/detailed/02_class_a4_ngang.drawio $D/02_class_core.drawio

The A4 page (`class/detailed/02_class_a4_ngang.drawio`) is the official layout and is
never edited here. Both pages keep its boxes, frames and edge waypoints, so
the report's two figures look alike; only the content changes:

  * `--level detailed` (default, Hình 2c): every business field, no
    technical-only one (generated ids, timestamps no rule depends on, gateway
    references, OTP codes, the review lock); business rows the code has added;
    two fixes (`DrillPassage.drills`, `Response.criterionIndicators`).
  * `--level core` (Hình 2a): the main attributes only -- every attribute
    that holds a relation, the business state, the fields a rule depends on.
  * Both: every class keyed by an identifier shows it on top under its code name; the
    audit log is left out (a technical record); `Order.buyer`; a passage
    holds 1..* words. End markers by the owner's rule: an attribute of
    another class is an aggregation (hollow diamond at the holder), or a
    composition (filled) when the part lives and dies with its whole; a
    field typed by an enum is a dashed line with an open arrow at the enum;
    association is kept for a relation with no attribute (a ledger entry and
    the response it paid for, D112). The lock edge removed; three relations the
    code has added.

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
    "Account": ["accountId", "identities", "emailCodes", "reminderSentOn", "isStaff"],
    "Achievement": ["unlockedAt"],
    "Classroom": ["classId"],
    "CoachUpgrade": ["createdAt"],
    "DrillPassage": ["passageId", "takes", "createdAt"],
    "LearningPlan": ["planId"],
    "LedgerEntry": ["entryId", "day"],
    "Lesson": ["lessonId", "versions", "media"],
    "LessonPath": ["pathId"],
    "Order": [
        "orderId",
        "createdAt",
        "creditedAt",
        "checkoutRef",
        "reference",
        "settledAt",
        "events",
    ],
    "PriceList": ["changedAt"],
    "Response": [
        "responseId",
        "durationMs",
        "replayLabels",
        "createdAt",
        "lockedBy",
        "lockedUntil",
    ],
    "Review": ["reviewId"],
    "ReviewItem": ["itemId"],
    "Step": ["stepId"],
    "StepAttempt": ["attemptId", "lessonVersion", "createdAt"],
    "Task": ["taskId"],
    "Unit": ["unitId"],
    "WordDrill": ["drillId", "takes", "createdAt"],
}
# Replace one row with one or more rows, in place.
REPLACE = {
    ("DrillPassage", "words"): ["- drills: List<WordDrill>", "- words: List<str>"],
    ("Order", "createdBy"): ["- buyer: Account"],
    ("Response", "criterionScores"): ["- criterionIndicators: List<float>"],
    ("Response", "modelVersion"): ["- modelVersion: str", "- configVersion: str"],
    ("Lesson", "title"): ["- title: str", "- summary: str", "- keywords: List<str>"],
    ("LessonPath", "title"): ["- title: str", "- description: str"],
    ("LedgerEntry", "state"): ["- state: LedgerState", "- period: str"],
    # D112: what the entry paid for -- a response, its upgrade ("upgrade-<id>"),
    # a lesson recording, a draft or a passage -- so a key, not a Response.
    ("LedgerEntry", "response"): ["- key: str"],
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
    "- kind: StepKind", "- title: str", "- instruction: str", "- text: str",
    "- hintWords: List<str>", "- answers: List<str>", "- keywords: List<str>",
    "- starter: str", "- outline: List<str>",
    "- useAtLeast: int", "- minWords: int", "- prepSeconds: int", "- showSeconds: int",
    "- minSeconds: int", "- maxSeconds: int", "- rounds: List<int>", "- strictness: str",
    "- modelAudio: str", "- image: str", "- tip: str",
]  # fmt: skip

# `--level core`: the main attributes of each class, every relation kept.
CORE_ROWS = {
    "Account": ["- email: str", "- emailVerified: bool", "- fullName: str", "- role: Role",
                "- dailyGoalS: int"],
    "Task": ["- title: str", "- promptText: str", "- topicKeywords: List<str>", "- band: Band"],
    "Response": ["- speaker: Account", "- task: Task", "- status: ResponseStatus",
                 "- transcript: str", "- overall06: float", "- overallBand: Band",
                 "- feedback: List<str>", "- reviews: List<Review>", "- upgrade: CoachUpgrade"],
    "Review": ["- reviewer: Account", "- oldBand: Band", "- newBand: Band", "- reason: str"],
    "CoachUpgrade": ["- fromBand: Band", "- toBand: Band", "- upgraded: str"],
    "Classroom": ["- name: str", "- joinCode: str", "- teachers: List<Account>",
                  "- members: List<Account>", "- invited: List<Account>", "- archived: bool"],
    "LessonPath": ["- title: str", "- bandFrom: Band", "- bandTo: Band", "- status: PathStatus",
                   "- units: List<Unit>"],
    "Unit": ["- title: str", "- band: Band", "- criterion: Criterion", "- lessons: List<Lesson>"],
    "Lesson": ["- title: str", "- band: Band", "- criterion: Criterion", "- passRatio: float",
               "- steps: List<Step>"],
    "Step": ["- kind: StepKind", "- text: str", "- prepSeconds: int"],
    "StepAttempt": ["- learner: Account", "- step: Step", "- round: int", "- passed: bool",
                    "- overriddenBy: Account", "- reviewItem: ReviewItem"],
    "WordDrill": ["- learner: Account", "- response: Response", "- word: str", "- passed: bool"],
    "DrillPassage": ["- learner: Account", "- drills: List<WordDrill>", "- text: str"],
    "ReviewItem": ["- learner: Account", "- lesson: Lesson", "- drill: WordDrill", "- step: Step",
                   "- dueDate: date", "+ isDue(today: date): bool"],
    "Achievement": ["- code: str", "- learner: Account"],
    "LearningPlan": ["- owner: Account", "- goal: str", "- audience: Role",
                     "- lessons: List<Lesson>"],
    "Order": ["- runs: int", "- amountVnd: int", "- status: OrderStatus", "- buyer: Account"],
    "Wallet": ["- owner: Account", "- balance: int", "+ available(): int"],
    "PriceList": ["- version: str", "- freeRuns: float", "- packs: List<str>"],
    "LedgerEntry": ["- wallet: Wallet", "- key: str", "- action: MeteredAction",
                    "- charged: int", "- state: LedgerState"],
}  # fmt: skip

# The identifier each class's collection is keyed by (`account_id`, `response_id`...),
# drawn on top of the box under its name in the code (camel case, like every other
# attribute: `class_id` -> `classId`). Achievement and CoachUpgrade got theirs in
# D111, Wallet and PriceList in D112: every class drawn has one.
ID_FIELD = {
    "Account": "accountId: str", "Task": "taskId: str", "Response": "responseId: str",
    "Review": "reviewId: int", "Classroom": "classId: str", "LessonPath": "pathId: str",
    "Unit": "unitId: str", "Lesson": "lessonId: str", "Step": "stepId: str",
    "StepAttempt": "attemptId: str", "WordDrill": "drillId: str",
    "DrillPassage": "passageId: str", "ReviewItem": "itemId: str",
    "LearningPlan": "planId: str", "Order": "orderId: str", "LedgerEntry": "entryId: str",
    "Achievement": "achievementId: str", "CoachUpgrade": "upgradeId: str",
    "Wallet": "walletId: str", "PriceList": "priceListId: str",
}  # fmt: skip
# Related with no attribute in either class (owner's rule: association). A
# ledger entry names what it paid for by its key; for a scored recording or its
# upgrade, that is a response.
ASSOCIATION = {("LedgerEntry", "Response")}
# Not drawn: the audit log is a technical record (who did what), like the sessions.
NOT_DRAWN = {"AuditEntry"}
# A relation drawn with a stored attribute of the other class is an aggregation
# (hollow diamond at the class that holds it), or a composition (filled) when
# the part lives and dies with its whole. Owner's rule, 24/11/2026: association
# is kept for a relation with no attribute (`ASSOCIATION`). A field
# typed by an enum is drawn as a dashed line with an open arrow at the enum.

tree = ET.parse(SRC)
root = tree.getroot()
model_root = root.find(".//root")
cells = {c.get("id"): c for c in root.iter("mxCell")}


def text(c):
    """A cell's text: the label unescaped, HTML tags turned into spaces."""
    return re.sub(r"<[^>]+>", " ", html.unescape(html.unescape(c.get("value") or ""))).strip()


boxes = {}  # id -> name
enum_ids = set()
for cid, c in cells.items():
    if "swimlane" in (c.get("style") or ""):
        boxes[cid] = text(c).replace("«entity»", "").replace("«enumeration»", "").strip()
        if "«enumeration»" in text(c):
            enum_ids.add(cid)
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


for bid in [b for b, n in boxes.items() if n in NOT_DRAWN]:
    gone = {bid} | {c.get("id") for c in model_root if c.get("parent") == bid}
    edges = {
        c.get("id")
        for c in model_root
        if c.get("edge") == "1" and bid in (c.get("source"), c.get("target"))
    }
    for c in list(model_root):
        if c.get("id") in gone | edges or c.get("parent") in edges:
            model_root.remove(c)
    del boxes[bid]
by_name = {n: i for i, n in boxes.items()}

# The words of a passage are many (owner, 24/11/2026): 1..*, no fixed count.
for c in [x for x in model_root if x.get("edge") == "1"]:
    if (boxes.get(c.get("source")), boxes.get(c.get("target"))) == ("DrillPassage", "WordDrill"):
        for lab in [x for x in model_root if x.get("parent") == c.get("id")]:
            if (lab.get("value") or "").strip() == "3..5":
                lab.set("value", "1..*")

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
    if name in ID_FIELD:
        out.insert(0, new_row(template, f"- {ID_FIELD[name]}", (serial := serial + 1)))
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
    elif c.get("target") in enum_ids:  # a field typed by an enum: dashed, open arrow
        d.pop("strokeWidth", None)
        d.pop("endSize", None)
        d.update(
            {
                "dashed": "1",
                "startArrow": "none",
                "startFill": "0",
                "endArrow": "open",
                "endFill": "0",
                # Routes run 10 points beside Band and Role: a short head and no
                # jump arcs keep the arrow clear of the lines it crosses there.
                "endSize": "8",
                "jumpStyle": "none",
            }
        )
        d.pop("startSize", None)
    elif (s, t) in ASSOCIATION:  # related, but no attribute holds the other: a plain line
        for k in ("strokeWidth", "dashed", "endSize", "startSize"):
            d.pop(k, None)
        d.update({"startArrow": "none", "startFill": "0", "endArrow": "none", "endFill": "0"})
    else:  # the holder keeps an attribute of the other class: aggregation
        d.pop("strokeWidth", None)
        d.pop("dashed", None)
        d.pop("endSize", None)
        d.update(
            {
                "startArrow": "diamondThin",
                "startFill": "0",
                "startSize": "14",
                "endArrow": "none",
                "endFill": "0",
            }
        )
    c.set("style", style_str(d))

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
# draw.io draws a jump arc on the edge drawn later: put the enum edges last so
# no arc lands on their arrow heads beside Band and Role.
for c in [x for x in model_root if x.get("edge") == "1" and x.get("target") in enum_ids]:
    model_root.remove(c)
    model_root.append(c)

tree.write(OUT, encoding="utf-8", xml_declaration=False)
print(
    "written",
    OUT,
    "| rows:",
    sum(1 for c in model_root if c.get("parent") in boxes and c.get("vertex") == "1"),
    "| edges:",
    sum(1 for c in model_root if c.get("edge") == "1"),
)
