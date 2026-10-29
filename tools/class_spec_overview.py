"""The v3 class diagram as a compact object model, for `gen_class_diagram.py --spec overview`.

This is the page the code is decomposed from: each class carries its main
state and the few operations that are its responsibility, roles are
subclasses of `Actor`, wholes own their parts by composition, and the payment
gateways sit behind one interface. Attribute-level detail -- reason codes,
provenance, QC measurements, mission checks -- stays in the full design,
`tools/class_spec_v3.py`, and every class drawn here is a class there
(`tests/test_target_design.py`).

Notation as in the full design: `- name: Type`, `+ operation(arg: Type): Type`,
`List<X>`, `Map<K, V>`, and `[0..1]` for what may be empty.
"""

BR = "@@"

CLASSES = [
    # --- People: one abstract account, one subclass per role ----------------------
    (
        "Actor",
        "«abstract»" + BR + "Actor",
        [
            "- actorId: str",
            "- pseudonym: str",
            "- disabled: bool",
            "+ canSee(response: ResponseRecord): bool",
        ],
    ),
    (
        "Student",
        "«entity»" + BR + "Student",
        [
            "- dailyGoalSeconds: int",
            "- consents: List<ConsentRecord>",
            "+ submit(task: Task): ResponseRecord",
            "+ practise(step: Step): StepAttempt",
        ],
    ),
    (
        "Teacher",
        "«entity»" + BR + "Teacher",
        [
            "+ review(response: ResponseRecord): Review",
            "+ rate(assignment: RatingAssignment): bool",
            "+ publish(lesson: Lesson): int",
        ],
    ),
    (
        "Admin",
        "«entity»" + BR + "Admin",
        [
            "+ createAccounts(count: int): List<Actor>",
            "+ purchase(plan: Plan, seats: int): Order",
        ],
    ),
    (
        "Consent",
        "«value object»" + BR + "ConsentRecord",
        [
            "- consentVersion: str",
            "- audioStorageAllowed: bool",
            "- researchUseAllowed: bool",
            "+ maySubmit(): bool",
        ],
    ),
    # --- A spoken response and what the pipeline makes of it ------------------------
    (
        "Task",
        "«entity»" + BR + "Task",
        [
            "- taskId: str",
            "- promptText: str",
            "- minSeconds: int",
            "- maxSeconds: int",
            "+ accepts(seconds: float): bool",
        ],
    ),
    (
        "Resp",
        "«entity»" + BR + "ResponseRecord",
        [
            "- responseId: str",
            "- status: Status",
            "- qc: QCResult [0..1]",
            "- transcript: Transcript [0..1]",
            "- features: FeatureSet [0..1]",
            "- assessment: Assessment [0..1]",
            "- report: DiagnosticReport [0..1]",
            "+ moveTo(status: Status): bool",
        ],
    ),
    (
        "Qc",
        "«value object»" + BR + "QCResult",
        ["- durationMs: int", "+ passed(): bool"],
    ),
    (
        "Asr",
        "«value object»" + BR + "Transcript",
        ["- text: str", "- language: str", "+ wordCount(): int"],
    ),
    (
        "Feat",
        "«value object»" + BR + "FeatureSet",
        ["- featureVersion: str", "- values: Map<str, float>", "+ valueOf(name: str): float"],
    ),
    (
        "Asmt",
        "«entity»" + BR + "Assessment",
        [
            "- overallScore: float [0..1]",
            "- overallBand: Band [0..1]",
            "- modelVersion: str",
            "+ needsReview(): bool",
        ],
    ),
    (
        "Rep",
        "«entity»" + BR + "DiagnosticReport",
        ["- evidence: List<Evidence>", "- teacherVerified: bool", "+ priorities(): List<str>"],
    ),
    (
        "Ev",
        "«value object»" + BR + "Evidence",
        ["- startS: float", "- endS: float", "- snippet: str"],
    ),
    (
        "Review",
        "«entity»" + BR + "Review",
        ["- action: str", "- newBand: Band [0..1]", "- reason: str", "- createdAt: datetime"],
    ),
    # --- Lessons and practice ------------------------------------------------------------
    (
        "Path",
        "«entity»" + BR + "LessonPath",
        [
            "- title: str",
            "- units: List<LessonUnit>",
            "+ nextLesson(student: Student): Lesson [0..1]",
        ],
    ),
    ("Unit", "«entity»" + BR + "LessonUnit", ["- title: str", "- lessons: List<Lesson>"]),
    (
        "Lesson",
        "«entity»" + BR + "Lesson",
        ["- title: str", "- band: Band", "- publishedVersion: int [0..1]", "- steps: List<Step>"],
    ),
    (
        "Step",
        "«value object»" + BR + "Step",
        ["- kind: str", "- text: str", "+ evaluate(transcript: Transcript): StepAttempt"],
    ),
    (
        "Attempt",
        "«entity»" + BR + "StepAttempt",
        ["- passed: bool", "- speakingSeconds: float", "- createdAt: datetime"],
    ),
    (
        "Ach",
        "«entity»" + BR + "Achievement",
        ["- code: str", "- unlockedAt: datetime"],
    ),
    # --- Blind double rating ----------------------------------------------------------------
    (
        "Batch",
        "«entity»" + BR + "RatingBatch",
        [
            "- name: str",
            "- assignments: List<RatingAssignment>",
            "+ assign(responses: List<ResponseRecord>): int",
        ],
    ),
    (
        "Asg",
        "«entity»" + BR + "RatingAssignment",
        ["- slot: int", "- band: Band [0..1]", "- submittedAt: datetime [0..1]"],
    ),
    # --- Service plans and payment ------------------------------------------------------------
    (
        "Ord",
        "«entity»" + BR + "Order",
        [
            "- plan: Plan",
            "- seats: int",
            "- amountVnd: int",
            "- status: str",
            "+ markPaid(reference: str): License",
        ],
    ),
    (
        "Lic",
        "«entity»" + BR + "License",
        [
            "- organization: str",
            "- plan: Plan",
            "- seats: int",
            "- validTo: datetime",
            "+ allows(feature: str): bool",
        ],
    ),
    (
        "Gateway",
        "«interface»" + BR + "PaymentGateway",
        ["+ checkout(order: Order): str", "+ verify(query: Map<str, str>): bool"],
    ),
]

ENUMS = [
    (
        "Status",
        "«enumeration»" + BR + "Status",
        ["QUEUED", "RUNNING", "COMPLETED", "REVIEW_REQUIRED", "REJECTED", "FAILED"],
    ),
    ("Band", "«enumeration»" + BR + "Band", ["A2", "B1", "B2"]),
    ("Plan", "«enumeration»" + BR + "Plan", ["FREE", "TRIAL", "STANDARD", "ADVANCED"]),
]

# (source, target, "source multiplicity : target multiplicity", kind)
EDGES = [
    ("Student", "Actor", "", "gen"),
    ("Teacher", "Actor", "", "gen"),
    ("Admin", "Actor", "", "gen"),
    ("Student", "Consent", "1 : 0..*", "comp"),
    ("Student", "Resp", "1 : 0..*", "assoc"),
    ("Task", "Resp", "1 : 0..*", "assoc"),
    ("Teacher", "Review", "1 : 0..*", "assoc"),
    ("Resp", "Review", "1 : 0..*", "assoc"),
    ("Resp", "Qc", "1 : 0..1", "comp"),
    ("Resp", "Asr", "1 : 0..1", "comp"),
    ("Resp", "Feat", "1 : 0..1", "comp"),
    ("Resp", "Asmt", "1 : 0..1", "comp"),
    ("Resp", "Rep", "1 : 0..1", "comp"),
    ("Rep", "Ev", "1 : 0..10", "comp"),
    ("Path", "Unit", "1 : 0..*", "comp"),
    ("Unit", "Lesson", "1 : 0..*", "comp"),
    ("Lesson", "Step", "1 : 1..12", "comp"),
    ("Step", "Attempt", "1 : 0..*", "assoc"),
    ("Student", "Attempt", "1 : 0..*", "assoc"),
    ("Student", "Ach", "1 : 0..*", "assoc"),
    ("Batch", "Asg", "1 : 1..*", "comp"),
    ("Asg", "Resp", "0..* : 1", "assoc"),
    ("Admin", "Ord", "1 : 0..*", "assoc"),
    ("Ord", "Lic", "0..1 : 0..1", "assoc"),
    ("Ord", "Gateway", "0..* : 1", "assoc"),
    ("Resp", "Status", "", "enum"),
    ("Asmt", "Band", "", "enum"),
    ("Lesson", "Band", "", "enum"),
    ("Ord", "Plan", "", "enum"),
]

# Left to right: people -> a response and its pipeline -> its report and rating
# -> lessons -> plans and payment.
COLUMN_IDS = [
    ["Actor", "Student", "Consent", "Teacher", "Admin"],
    ["Task", "Resp", "Status", "Review", "Ach"],
    ["Qc", "Asr", "Feat", "Asmt", "Band"],
    ["Rep", "Ev", "Batch", "Asg"],
    ["Path", "Unit", "Lesson", "Step", "Attempt"],
    ["Ord", "Lic", "Plan", "Gateway"],
]

PAGE_NAME = "So do lop v3"
OUT = "docs/sdd/diagrams/target/02_class_v3_overview.drawio"
LABEL_NUDGE: dict = {}
