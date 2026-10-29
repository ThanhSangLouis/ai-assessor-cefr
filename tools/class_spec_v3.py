"""Dac ta so do lop THIET KE DICH v3 cho `tools/gen_class_diagram.py --spec v3`.

So do `docs/sdd/diagrams/02_class.drawio` la so do HIEN TRANG: bo test
`tests/test_diagrams.py` bat no mo ta dung ma dang chay. Tep nay la nguoc lai --
THIET KE DICH ma ma nguon phai di theo. Thiet ke la nguon chuan; ma map theo
sau. Khi ma da chuyen xong sang v3 thi v3 thay cho so do hien trang.

Chin quyet dinh D1-D9 da duoc chu du an duyet ngay 02/10/2026; ly do tung
quyet dinh va danh sach viec ma phai doi nam o
`docs/sdd/diagrams/target/README.md`.

Quy uoc ky hieu (UML 2.5, muc "property"):
  * thuoc tinh `- ten: Kieu`; tap hop `List<X>`; anh xa `Map<K, V>`;
  * thuoc tinh CO THE TRONG ghi boi so `[0..1]` sau kieu. Day la boi so cua
    chinh thuoc tinh, hop le trong UML 2.5, khong phai cu phap `X | None` cua
    Python. Nguyen tac "thieu du lieu thi None kem reason code" cua du an chi
    doc duoc tren hinh nho dong nay;
  * chi ve khai niem NGHIEP VU. Phien dang nhap, khoa tranh ghi de (revision),
    nhat ky kiem toan, bam mat khau, tham chieu blob la ha tang -- chung o ERD.
"""

BR = "@@"

CLASSES = [
    # --- Danh tinh va dong y (M08) -------------------------------------------
    # One abstract account, one subclass per role: what each role may do is
    # an operation of that subclass (code maps the subclass to a role column).
    (
        "Actor",
        "«abstract»" + BR + "Actor",
        [
            "- actorId: str",
            "- pseudonym: str",
            "- disabled: bool",
            "- identities: List<LinkedIdentity>",
            "+ canSee(response: ResponseRecord): bool",
        ],
    ),
    (
        "Student",
        "«entity»" + BR + "Student",
        [
            "- dailyGoalSeconds: int",
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
    # Sign-in with Google (D029, D036): the account keeps only a hash of the
    # provider's subject; the flow's cookie and secrets are infrastructure.
    (
        "Ident",
        "«value object»" + BR + "LinkedIdentity",
        ["- provider: str", "- subjectHash: str", "- linkedAt: datetime"],
    ),
    (
        "Consent",
        "«entity»" + BR + "ConsentRecord",
        [
            "- consentId: str",
            "- participantId: str",
            "- consentVersion: str",
            "- state: ConsentState",
            "- audioStorageAllowed: bool",
            "- researchUseAllowed: bool",
            "- signedAt: datetime",
            "- withdrawnAt: datetime [0..1]",
            "+ maySubmit(): bool",
        ],
    ),
    # --- De bai va bai nop (M01, M08) ------------------------------------------
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
            "- criterion: Criterion [0..1]",
            "- band: Band [0..1]",
            "- missions: List<Mission>",
            "- tips: List<str>",
            "- referenceText: str [0..1]",
        ],
    ),
    # Practice (D023): a practice task is a Task whose purpose is PRACTICE; it
    # trains ONE criterion at ONE band, and each mission is a fixed counting rule.
    (
        "Mission",
        "«value object»" + BR + "Mission",
        ["- kind: MissionKind", "- target: float", "- label: str", "- words: List<str>"],
    ),
    (
        "Resp",
        "«entity»" + BR + "ResponseRecord",
        [
            "- responseId: str",
            "- promptVersion: str",
            "- status: Status",
            "- reasons: List<ReasonCode>",
            "- configVersion: str",
            "- createdAt: datetime",
            "- qc: QCResult [0..1]",
            "- asr: Transcript [0..1]",
            "- features: FeatureSet [0..1]",
            "- assessment: Assessment [0..1]",
            "- report: DiagnosticReport [0..1]",
            "- practice: PracticeResult [0..1]",
        ],
    ),
    # Result of one practice attempt (D023): no score, no band, no teacher review.
    # Every measured mission points at places in the recording.
    (
        "Practice",
        "«value object»" + BR + "PracticeResult",
        ["- checks: List<MissionCheck>", "- rulesVersion: str", "- completed: bool [0..1]"],
    ),
    (
        "MCheck",
        "«value object»" + BR + "MissionCheck",
        [
            "- kind: MissionKind",
            "- label: str",
            "- target: float",
            "- measured: float [0..1]",
            "- met: bool [0..1]",
            "- hits: List<MissionHit>",
            "- reason: ReasonCode [0..1]",
        ],
    ),
    (
        "MHit",
        "«value object»" + BR + "MissionHit",
        ["- text: str", "- startS: float [0..1]"],
    ),
    # --- QC am thanh (M02) -------------------------------------------------------
    (
        "Qc",
        "«value object»" + BR + "QCResult",
        [
            "- status: QCStatus",
            "- measurements: List<QCMeasurement>",
            "- qcConfigVersion: str",
            "- reasons: List<ReasonCode>",
            "+ passed(): bool",
        ],
    ),
    (
        "QcM",
        "«value object»" + BR + "QCMeasurement",
        [
            "- name: str",
            "- value: float [0..1]",
            "- unit: str",
            "- missingReason: ReasonCode [0..1]",
        ],
    ),
    # --- Nhan dang tieng noi (M03) -----------------------------------------------
    (
        "Asr",
        "«value object»" + BR + "Transcript",
        [
            "- status: AsrStatus",
            "- text: str",
            "- words: List<Word>",
            "- asrModel: str [0..1]",
            "- engine: str",
            "- engineVersion: str",
            "- decodeConfigVersion: str",
            "- audioSha256: str",
            "- reasons: List<ReasonCode>",
            "- testOnly: bool",
            "- language: str [0..1]",
            "- languageProbability: float [0..1]",
        ],
    ),
    (
        "Word",
        "«value object»" + BR + "Word",
        [
            "- text: str",
            "- startS: float",
            "- endS: float",
            "- prob: float [0..1]",
            "+ isUncertain(): bool",
        ],
    ),
    # --- Dac trung (M04) ---------------------------------------------------------
    (
        "Feat",
        "«value object»" + BR + "FeatureSet",
        [
            "- values: List<FeatureValue>",
            "- featureVersion: str",
            "- vadName: str [0..1]",
            "- vadVersion: str [0..1]",
            "- vadThreshold: float [0..1]",
            "- vadMinSilenceMs: int [0..1]",
            "- asrModel: str [0..1]",
            "- transcriptRef: str [0..1]",
            "- audioSha256: str",
            "- reasons: List<ReasonCode>",
            "+ valueOf(name: str): float [0..1]",
            "+ vector(order: List<str>): List<float>",
        ],
    ),
    (
        "FVal",
        "«value object»" + BR + "FeatureValue",
        [
            "- name: str",
            "- value: float [0..1]",
            "- unit: str",
            "- missingReason: ReasonCode [0..1]",
        ],
    ),
    # --- Cham diem (M05) ---------------------------------------------------------
    (
        "Asmt",
        "«entity»" + BR + "Assessment",
        [
            "- status: AssessmentStatus",
            "- overallScore: float [0..1]",
            "- overallBand: Band [0..1]",
            "- criteria: List<CriterionCoverage>",
            "- interaction: Interaction",
            "- reasons: List<ReasonCode>",
            "- outOfRange: List<OutOfRangeFeature>",
            "- interval: ScoreInterval [0..1]",
            "- indicators: List<CriterionIndicator>",
            "- weakestCriteria: List<Criterion>",
            "- provenance: Provenance",
            "- teacherVerified: bool",
            "+ isCalibrated(): bool",
        ],
    ),
    (
        "Cov",
        "«value object»" + BR + "CriterionCoverage",
        [
            "- criterion: Criterion",
            "- coverage: float [0..1]",
            "- features: List<str>",
            "- reasons: List<ReasonCode>",
        ],
    ),
    (
        "Inter",
        "«value object»" + BR + "Interaction",
        ["- level: Band [0..1]", "- scoreStatus: str"],
    ),
    (
        "Prov",
        "«value object»" + BR + "Provenance",
        [
            "- modelVersion: str [0..1]",
            "- modelSha256: str [0..1]",
            "- featureVersion: str [0..1]",
            "- bandMapVersion: str [0..1]",
            "- calibrationVersion: str [0..1]",
            "- trainedWith: Map<str, Any>",
            "- unitOfInference: str [0..1]",
            "- scoredAt: str",
        ],
    ),
    (
        "Oor",
        "«value object»" + BR + "OutOfRangeFeature",
        [
            "- feature: str",
            "- value: float",
            "- acceptedLow: float",
            "- acceptedHigh: float",
            "- too: str",
        ],
    ),
    # Trust Layer (D021 bo sung 03/10/2026): khoang diem co bao dam thong ke.
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
        ],
    ),
    # Chi bao theo tieu chi: vi tri cua mot phep do trong phan bo huan luyen.
    # KHONG phai diem tieu chi -- mo hinh chi hoc nhan overall.
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
    # --- Bao cao chan doan (M06) -------------------------------------------------
    (
        "Rep",
        "«entity»" + BR + "DiagnosticReport",
        [
            "- status: ReportStatus",
            "- assessment: Assessment",
            "- evidence: List<Evidence>",
            "- comments: List<Comment>",
            "- priorities: List<Priority>",
            "- evidenceIssues: List<EvidenceIssue>",
            "- limitations: List<str>",
            "- sourceVersions: Map<str, str>",
            "- teacherFinal: TeacherFinalResult [0..1]",
            "- generatedAt: datetime",
        ],
    ),
    (
        "Ev",
        "«value object»" + BR + "Evidence",
        [
            "- evidenceId: str",
            "- source: EvidenceSource",
            "- sourceVersion: str",
            "- criterion: Criterion",
            "- kind: EvidenceKind",
            "- startS: float [0..1]",
            "- endS: float [0..1]",
            "- wordIndex: int [0..1]",
            "- snippet: str [0..1]",
            "- note: str",
        ],
    ),
    (
        "Cmt",
        "«value object»" + BR + "Comment",
        [
            "- criterion: Criterion [0..1]",
            "- template: CommentTemplate",
            "- text: str",
            "- evidenceRefs: List<str>",
        ],
    ),
    (
        "Pri",
        "«value object»" + BR + "Priority",
        ["- featureName: str", "- text: str", "- impact: float"],
    ),
    (
        "Iss",
        "«value object»" + BR + "EvidenceIssue",
        ["- evidenceId: str", "- reason: str"],
    ),
    (
        "TFin",
        "«value object»" + BR + "TeacherFinalResult",
        [
            "- action: ReviewAction",
            "- overallBand: Band [0..1]",
            "- reason: str [0..1]",
            "- recordedAt: datetime",
        ],
    ),
    # --- Giang vien duyet (M07) --------------------------------------------------
    (
        "Cand",
        "«entity»" + BR + "ReviewCandidate",
        [
            "- assessmentStatus: AssessmentStatus",
            "- proposedBand: Band [0..1]",
            "- reasons: List<ReasonCode>",
            "- sourceVersions: Map<str, str>",
            "- state: ReviewState",
            "- createdAt: datetime",
            "- updatedAt: datetime",
        ],
    ),
    (
        "Review",
        "«entity»" + BR + "Review",
        [
            "- reviewerId: str",
            "- action: ReviewAction",
            "- oldState: ReviewState",
            "- newState: ReviewState",
            "- oldScore: float [0..1]",
            "- newScore: float [0..1]",
            "- oldBand: Band [0..1]",
            "- newBand: Band [0..1]",
            "- reason: str",
            "- createdAt: datetime",
        ],
    ),
    # --- Lo trinh bai hoc (D025, D027) -------------------------------------------
    (
        "Path",
        "«entity»" + BR + "LessonPath",
        [
            "- pathId: str",
            "- title: str",
            "- description: str",
            "- bandFrom: Band [0..1]",
            "- bandTo: Band [0..1]",
            "- status: PathStatus",
            "- sample: bool",
            "- units: List<LessonUnit>",
        ],
    ),
    (
        "Unit",
        "«entity»" + BR + "LessonUnit",
        [
            "- unitId: str",
            "- title: str",
            "- function: str",
            "- band: Band [0..1]",
            "- criterion: Criterion [0..1]",
            "- topic: Topic [0..1]",
            "- position: int",
            "- lessons: List<Lesson>",
        ],
    ),
    (
        "Lesson",
        "«entity»" + BR + "Lesson",
        [
            "- lessonId: str",
            "- title: str",
            "- summary: str",
            "- band: Band",
            "- criterion: Criterion [0..1]",
            "- modelText: str",
            "- keywords: List<str>",
            "- passRatio: float",
            "- sample: bool",
            "- publishedVersion: int [0..1]",
            "- archived: bool",
            "- steps: List<Step>",
        ],
    ),
    (
        "Step",
        "«value object»" + BR + "Step",
        [
            "- stepId: str",
            "- kind: StepKind",
            "- title: str",
            "- instruction: str",
            "- text: str",
            "- hintWords: List<str>",
            "- minSeconds: int",
            "- maxSeconds: int",
            "- strictness: Strictness",
            "- missions: List<Mission>",
            "- tip: str",
        ],
    ),
    # One take of one step: what the machine measured, kept against the
    # published version of the lesson it was taken on.
    (
        "Attempt",
        "«entity»" + BR + "StepAttempt",
        [
            "- attemptId: str",
            "- lessonVersion: int",
            "- stepId: str",
            "- round: int [0..1]",
            "- passed: bool",
            "- speakingSeconds: float",
            "- rulesVersion: str",
            "- createdAt: datetime",
            "- result: StepResult",
            "- overriddenBy: str [0..1]",
        ],
    ),
    (
        "SRes",
        "«value object»" + BR + "StepResult",
        [
            "- kind: StepKind",
            "- passed: bool",
            "- measured: bool",
            "- words: List<WordMark>",
            "- gaps: List<GapMark>",
            "- found: List<MissionHit>",
            "- missing: List<str>",
            "- reasons: List<ReasonCode>",
            "- teacherReviewed: bool",
        ],
    ),
    (
        "WMark",
        "«value object»" + BR + "WordMark",
        [
            "- index: int",
            "- text: str",
            "- status: WordStatus",
            "- startSeconds: float [0..1]",
            "- said: str [0..1]",
            "- teacher: WordStatus [0..1]",
        ],
    ),
    (
        "GMark",
        "«value object»" + BR + "GapMark",
        [
            "- index: int",
            "- expected: str",
            "- said: str [0..1]",
            "- status: GapStatus",
        ],
    ),
    # Spaced review (D027): a word or step the learner comes back to.
    (
        "RItem",
        "«entity»" + BR + "ReviewItem",
        [
            "- itemId: str",
            "- kind: str",
            "- word: str",
            "- box: int",
            "- dueDate: datetime",
            "- done: bool",
        ],
    ),
    # --- Thanh tuu (D032): cong suc, khong dua vao diem ------------------------------
    (
        "Ach",
        "«value object»" + BR + "Achievement",
        ["- code: str", "- group: str", "- title: str", "- description: str", "- target: int"],
    ),
    (
        "Unl",
        "«entity»" + BR + "UnlockedAchievement",
        ["- unlockedAt: datetime", "- seenAt: datetime [0..1]"],
    ),
    # --- Cham mu kep (D030) ------------------------------------------------------------
    (
        "Batch",
        "«entity»" + BR + "RatingBatch",
        [
            "- batchId: str",
            "- name: str",
            "- seed: int",
            "- status: BatchStatus",
            "- assignments: List<RatingAssignment>",
        ],
    ),
    (
        "Asg",
        "«entity»" + BR + "RatingAssignment",
        [
            "- assignmentId: str",
            "- slot: int",
            "- position: int",
            "- openedAt: datetime [0..1]",
            "- rating: ResearchRating [0..1]",
        ],
    ),
    (
        "RRat",
        "«value object»" + BR + "ResearchRating",
        [
            "- scoreRange: float [0..1]",
            "- scoreAccuracy: float [0..1]",
            "- scoreFluency: float [0..1]",
            "- scoreCoherence: float [0..1]",
            "- scorePhonology: float [0..1]",
            "- scoreOverall: float [0..1]",
            "- band: Band [0..1]",
            "- unscorable: bool",
            "- unscorableReason: str [0..1]",
            "- submittedAt: datetime",
        ],
    ),
    # --- Goi dich vu va thanh toan (D034, D035) ----------------------------------------
    (
        "Ord",
        "«entity»" + BR + "Order",
        [
            "- orderId: str",
            "- plan: Plan",
            "- seats: int",
            "- months: int",
            "- unitPrice: int",
            "- discountVnd: int",
            "- creditVnd: int",
            "- amountVnd: int",
            "- kind: OrderKind",
            "- startsOn: datetime",
            "- endsOn: datetime",
            "- status: OrderStatus",
            "- gateway: str",
            "- live: bool",
            "- reference: str [0..1]",
            "- settledAt: datetime [0..1]",
        ],
    ),
    (
        "Lic",
        "«entity»" + BR + "License",
        [
            "- licenseId: str",
            "- organization: str",
            "- plan: Plan",
            "- seats: int",
            "- validFrom: datetime",
            "- validTo: datetime",
            "- source: LicenseSource",
        ],
    ),
    # Stripe, MoMo, VNPay and the sandbox are implementations of this one port.
    (
        "Gateway",
        "«interface»" + BR + "PaymentGateway",
        ["+ checkout(order: Order): str", "+ verify(query: Map<str, str>): bool"],
    ),
]

ENUMS = [
    ("ConsentState", "«enumeration»" + BR + "ConsentState", ["ACTIVE", "WITHDRAWN"]),
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
    (
        "Status",
        "«enumeration»" + BR + "Status",
        ["QUEUED", "RUNNING", "COMPLETED", "REVIEW_REQUIRED", "REJECTED", "FAILED"],
    ),
    ("QCStatus", "«enumeration»" + BR + "QCStatus", ["PASS", "REVIEW", "REJECT"]),
    (
        "AsrStatus",
        "«enumeration»" + BR + "AsrStatus",
        ["OK", "UNRELIABLE", "ASR_FAILED", "NOT_RUN"],
    ),
    (
        "AssessmentStatus",
        "«enumeration»" + BR + "AssessmentStatus",
        ["ESTIMATED", "REVIEW_REQUIRED", "NOT_EVALUATED"],
    ),
    # D8: mot bang ma duy nhat. Muc do (REVIEW/REJECT) nam o status, khong nam
    # trong ten ma -- vi vay khong co cap QC_SILENCE_REVIEW/QC_SILENCE_REJECT.
    (
        "ReasonCode",
        "«enumeration»" + BR + "ReasonCode",
        [
            # Nop bai (M01)
            "AUDIO_UNSUPPORTED",
            "AUDIO_TOO_LARGE",
            "EMPTY_AUDIO",
            "CONSENT_MISSING",
            "TASK_NOT_OPEN",
            "PROCESSING_INTERRUPTED",
            "REPORT_NOT_AVAILABLE",
            # QC am thanh (M02)
            "QC_DECODE_FAILED",
            "QC_TOO_MANY_CHANNELS",
            "QC_SAMPLE_RATE_LIMIT",
            "AUDIO_TOO_LONG",
            "AUDIO_TOO_SHORT",
            "HIGH_SILENCE_RATIO",
            "CLIPPING_DETECTED",
            "QC_MEASUREMENT_MISSING",
            # Nhan dang tieng noi (M03)
            "ASR_FAILED",
            "ASR_EMPTY_TRANSCRIPT",
            "ASR_HALLUCINATION",
            "ASR_VERSION_MISMATCH",
            # Dac trung (M04)
            "VAD_VERSION_MISMATCH",
            "FEATURE_NOT_COMPUTABLE",
            "TOO_FEW_WORDS",
            "FEATURE_VERSION_MISMATCH",
            # Cham diem (M05)
            "OUT_OF_DISTRIBUTION",
            "SCORE_NEAR_BOUNDARY",
            "MODEL_VERSION_MISSING",
            "MODEL_ARTIFACT_INVALID",
            # La chan hop le (M03, M04)
            "LANGUAGE_NOT_ENGLISH",
            "OFF_TOPIC_SUSPECTED",
            "PROMPT_COPY_SUSPECTED",
        ],
    ),
    ("Band", "«enumeration»" + BR + "Band", ["A1", "A2", "B1", "B2", "C1", "C2"]),
    (
        "Criterion",
        "«enumeration»" + BR + "Criterion",
        ["RANGE", "ACCURACY", "FLUENCY", "COHERENCE", "PHONOLOGY"],
    ),
    ("ReportStatus", "«enumeration»" + BR + "ReportStatus", ["PROVISIONAL", "TEACHER_VERIFIED"]),
    ("EvSource", "«enumeration»" + BR + "EvidenceSource", ["TRANSCRIPT", "FEATURE_SET"]),
    (
        "EvKind",
        "«enumeration»" + BR + "EvidenceKind",
        ["PAUSE", "FILLER", "LOW_CONFIDENCE_WORD", "LEXICAL"],
    ),
    (
        "CmtTpl",
        "«enumeration»" + BR + "CommentTemplate",
        ["WORD_TIMING_OBSERVED", "PAUSE_MEASUREMENT_OBSERVED", "FEATURE_VALUE_AVAILABLE"],
    ),
    (
        "ReviewState",
        "«enumeration»" + BR + "ReviewState",
        ["PENDING", "IN_REVIEW", "APPROVED", "OVERRIDDEN", "REJECTED"],
    ),
    ("ReviewAction", "«enumeration»" + BR + "ReviewAction", ["APPROVE", "OVERRIDE", "REJECT"]),
    ("PathStatus", "«enumeration»" + BR + "PathStatus", ["DRAFT", "PUBLISHED", "ARCHIVED"]),
    (
        "Topic",
        "«enumeration»" + BR + "Topic",
        [
            "DAILY_LIFE",
            "EDUCATION",
            "TRAVEL",
            "CAREER",
            "FOOD",
            "HEALTH",
            "TECHNOLOGY",
            "ENVIRONMENT",
            "PEOPLE",
            "SOCIETY",
        ],
    ),
    (
        "StepKind",
        "«enumeration»" + BR + "StepKind",
        ["READ_ALOUD", "REPEAT", "LOOK_UP", "GAP", "KEYWORDS", "STARTER", "PICTURE", "OUTLINE"],
    ),
    ("Strictness", "«enumeration»" + BR + "Strictness", ["EASY", "NORMAL", "STRICT"]),
    ("WordStatus", "«enumeration»" + BR + "WordStatus", ["HEARD", "MISSED", "UNSURE"]),
    (
        "GapStatus",
        "«enumeration»" + BR + "GapStatus",
        ["CORRECT", "DISTRACTOR", "OTHER", "MISSING"],
    ),
    ("BatchStatus", "«enumeration»" + BR + "BatchStatus", ["OPEN", "CLOSED"]),
    ("Plan", "«enumeration»" + BR + "Plan", ["FREE", "TRIAL", "STANDARD", "ADVANCED"]),
    (
        "OrderStatus",
        "«enumeration»" + BR + "OrderStatus",
        ["PENDING", "PAID", "FAILED", "CANCELLED", "EXPIRED"],
    ),
    (
        "OrderKind",
        "«enumeration»" + BR + "OrderKind",
        ["NEW", "RENEWAL", "UPGRADE", "DOWNGRADE"],
    ),
    ("LicenseSource", "«enumeration»" + BR + "LicenseSource", ["TRIAL", "ORDER", "KEY"]),
]

# (nguon, dich, "boi so nguon : boi so dich", kieu)
EDGES = [
    # Lien ket
    ("Student", "Actor", "", "gen"),
    ("Teacher", "Actor", "", "gen"),
    ("Admin", "Actor", "", "gen"),
    ("Student", "Consent", "1 : 0..*", "assoc"),
    ("Student", "Resp", "1 : 0..*", "assoc"),
    ("Teacher", "Review", "1 : 0..*", "assoc"),
    ("Task", "Resp", "1 : 0..*", "assoc"),
    ("Resp", "Review", "1 : 0..*", "assoc"),
    ("Resp", "Cand", "1 : 0..1", "assoc"),
    ("Rep", "Asmt", "0..1 : 1", "assoc"),
    ("Cmt", "Ev", "0..* : 1..*", "nn"),
    # Hop thanh: ResponseRecord la goc cua moi ket qua xu ly (D3)
    ("Resp", "Qc", "1 : 0..1", "comp"),
    ("Resp", "Asr", "1 : 0..1", "comp"),
    ("Resp", "Feat", "1 : 0..1", "comp"),
    ("Resp", "Asmt", "1 : 0..1", "comp"),
    ("Resp", "Rep", "1 : 0..1", "comp"),
    ("Task", "Mission", "1 : 0..*", "comp"),
    ("Resp", "Practice", "1 : 0..1", "comp"),
    ("Practice", "MCheck", "1 : 1..*", "comp"),
    ("MCheck", "MHit", "1 : 0..*", "comp"),
    ("Qc", "QcM", "1 : 0..*", "comp"),
    ("Asr", "Word", "1 : 0..*", "comp"),
    ("Feat", "FVal", "1 : 1..*", "comp"),
    ("Asmt", "Cov", "1 : 5", "comp"),
    ("Asmt", "Inter", "1 : 1", "comp"),
    ("Asmt", "Prov", "1 : 1", "comp"),
    ("Asmt", "Oor", "1 : 0..*", "comp"),
    ("Asmt", "Intv", "1 : 0..1", "comp"),
    ("Asmt", "Ind", "1 : 0..*", "comp"),
    ("Rep", "Ev", "1 : 0..10", "comp"),
    ("Rep", "Cmt", "1 : 0..4", "comp"),
    ("Rep", "Pri", "1 : 0..2", "comp"),
    ("Rep", "Iss", "1 : 0..*", "comp"),
    ("Rep", "TFin", "1 : 0..1", "comp"),
    # Phu thuoc toi kieu liet ke
    ("Consent", "ConsentState", "", "enum"),
    ("Task", "TaskPart", "", "enum"),
    ("Task", "TaskPurpose", "", "enum"),
    ("Task", "Criterion", "", "enum"),
    ("Task", "Band", "", "enum"),
    ("Mission", "MissionKind", "", "enum"),
    ("MCheck", "MissionKind", "", "enum"),
    ("MCheck", "ReasonCode", "", "enum"),
    ("Resp", "Status", "", "enum"),
    ("Resp", "ReasonCode", "", "enum"),
    ("Qc", "QCStatus", "", "enum"),
    ("Qc", "ReasonCode", "", "enum"),
    ("QcM", "ReasonCode", "", "enum"),
    ("Asr", "AsrStatus", "", "enum"),
    ("Asr", "ReasonCode", "", "enum"),
    ("Feat", "ReasonCode", "", "enum"),
    ("FVal", "ReasonCode", "", "enum"),
    ("Asmt", "AssessmentStatus", "", "enum"),
    ("Asmt", "Band", "", "enum"),
    ("Asmt", "ReasonCode", "", "enum"),
    ("Asmt", "Criterion", "", "enum"),
    ("Intv", "Band", "", "enum"),
    ("Ind", "Criterion", "", "enum"),
    ("Cov", "Criterion", "", "enum"),
    ("Cov", "ReasonCode", "", "enum"),
    ("Inter", "Band", "", "enum"),
    ("Rep", "ReportStatus", "", "enum"),
    ("Ev", "EvSource", "", "enum"),
    ("Ev", "Criterion", "", "enum"),
    ("Ev", "EvKind", "", "enum"),
    ("Cmt", "Criterion", "", "enum"),
    ("Cmt", "CmtTpl", "", "enum"),
    ("TFin", "ReviewAction", "", "enum"),
    ("TFin", "Band", "", "enum"),
    ("Cand", "AssessmentStatus", "", "enum"),
    ("Cand", "Band", "", "enum"),
    ("Cand", "ReasonCode", "", "enum"),
    ("Cand", "ReviewState", "", "enum"),
    ("Review", "ReviewAction", "", "enum"),
    ("Review", "ReviewState", "", "enum"),
    ("Review", "Band", "", "enum"),
    # --- D025..D036
    ("Actor", "Ident", "1 : 0..*", "comp"),
    ("Path", "Unit", "1 : 0..*", "comp"),
    ("Unit", "Lesson", "1 : 0..*", "comp"),
    ("Lesson", "Step", "1 : 1..12", "comp"),
    ("Step", "Mission", "0..* : 0..4", "assoc"),
    ("Student", "Attempt", "1 : 0..*", "assoc"),
    ("Lesson", "Attempt", "1 : 0..*", "assoc"),
    ("Attempt", "SRes", "1 : 1", "comp"),
    ("SRes", "WMark", "1 : 0..*", "comp"),
    ("SRes", "GMark", "1 : 0..*", "comp"),
    ("SRes", "MHit", "0..* : 0..*", "assoc"),
    ("Student", "RItem", "1 : 0..*", "assoc"),
    ("RItem", "Lesson", "0..* : 1", "assoc"),
    ("Student", "Unl", "1 : 0..*", "assoc"),
    ("Unl", "Ach", "0..* : 1", "assoc"),
    ("Batch", "Asg", "1 : 1..*", "comp"),
    ("Asg", "RRat", "1 : 0..1", "comp"),
    ("Asg", "Resp", "0..* : 1", "assoc"),
    ("Teacher", "Asg", "1 : 0..*", "assoc"),
    ("Admin", "Ord", "1 : 0..*", "assoc"),
    ("Ord", "Gateway", "0..* : 1", "assoc"),
    ("Ord", "Lic", "0..1 : 0..1", "assoc"),
    ("Path", "PathStatus", "", "enum"),
    ("Path", "Band", "", "enum"),
    ("Unit", "Topic", "", "enum"),
    ("Unit", "Criterion", "", "enum"),
    ("Lesson", "Band", "", "enum"),
    ("Step", "StepKind", "", "enum"),
    ("Step", "Strictness", "", "enum"),
    ("SRes", "StepKind", "", "enum"),
    ("SRes", "ReasonCode", "", "enum"),
    ("WMark", "WordStatus", "", "enum"),
    ("GMark", "GapStatus", "", "enum"),
    ("Batch", "BatchStatus", "", "enum"),
    ("RRat", "Band", "", "enum"),
    ("Ord", "Plan", "", "enum"),
    ("Ord", "OrderStatus", "", "enum"),
    ("Ord", "OrderKind", "", "enum"),
    ("Lic", "Plan", "", "enum"),
    ("Lic", "LicenseSource", "", "enum"),
]

# Cot doc tu trai sang phai theo luong nghiep vu:
# danh tinh -> bai nop -> QC/ASR -> dac trung -> cham -> bao cao -> duyet.
COLUMN_IDS = [
    ["Actor", "Ident", "Student", "Teacher", "Admin", "Consent", "ConsentState"],
    ["Task", "TaskPart", "TaskPurpose"],
    ["Resp", "Status", "Qc", "QCStatus", "QcM", "Mission", "MissionKind"],
    ["Asr", "AsrStatus", "Word", "Feat", "FVal", "Practice", "MCheck", "MHit"],
    ["ReasonCode"],
    ["Asmt", "AssessmentStatus", "Cov", "Inter", "Prov", "Oor", "Intv", "Ind"],
    ["Rep", "ReportStatus", "TFin", "Iss", "Band", "Criterion"],
    ["Ev", "EvSource", "EvKind", "Cmt", "CmtTpl", "Pri"],
    ["Cand", "ReviewState", "Review", "ReviewAction"],
    # D025..D036: lo trinh -> lan luyen -> on tap; cham mu kep, thanh tuu; goi dich vu.
    ["Path", "PathStatus", "Unit", "Topic", "Lesson", "Step", "StepKind", "Strictness"],
    ["Attempt", "SRes", "WMark", "WordStatus", "GMark", "GapStatus", "RItem"],
    ["Batch", "BatchStatus", "Asg", "RRat", "Unl", "Ach"],
    ["Ord", "OrderStatus", "OrderKind", "Gateway", "Lic", "LicenseSource", "Plan"],
]

PAGE_NAME = "So do lop v3"
OUT = "docs/sdd/diagrams/target/02_class_v3.drawio"
LABEL_NUDGE: dict = {}
