"""Shared data contracts. Cross-reference SDD section 4 and SRS section 3.

Guiding rule: no module is allowed to invent a value. When data is missing,
return None together with a reason code, never 0.
"""

from __future__ import annotations

from enum import Enum

from pydantic import AliasChoices, BaseModel, Field, computed_field, model_validator


class ResponseStatus(str, Enum):
    """State of a single processing run.

    QUEUED and RUNNING are the two NOT-YET-FINISHED states, added for FR-05 and
    QD-W3. Before them the pipeline ran synchronously inside the request, so
    there was nothing to track: SRS AC-05.1 requires returning 202 with a job id
    in under 300 ms, while NFR-01 allows the pipeline itself to take up to
    60 seconds.
    """

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"

    @property
    def is_pending(self) -> bool:
        """Still processing; no final result yet."""
        return self in (ResponseStatus.QUEUED, ResponseStatus.RUNNING)


class ReasonCode(str, Enum):
    """Vi sao mot bai khong tra ve ket qua binh thuong. Doi chieu SDD muc 4.0.

    Hai muoi hai ma la nhieu, va mot enum lon thuong la dau hieu thiet ke xau
    -- nhung chi khi nguoi tieu thu no phai RE NHANH theo tung gia tri. O day
    thi khong: `ReviewRouter` chi lay giao cua tap ly do voi mot tap kich hoat
    (`trigger`), con giao dien tra `REASON_NAMES` nhu mot tu dien. Them mot ma
    la them mot dong vao hai cau truc DU LIEU, khong dong nao vao luong dieu
    khien. Do la dieu khien mot bo tu vung lon van quan ly duoc.

    Nguoc lai, gop chung lai moi la hong: sinh vien se doc "co loi" thay vi
    "am thanh qua ngan". Ca he thong nay ton tai de moi phan xet deu co ly do
    kiem tra duoc, nen do phan giai cua ly do chinh la san pham.

    Ba ma tung ton tai ma khong noi nao sinh ra da duoc bo ngay 19/09/2026:
    `IDENTITY_FIELD_REJECTED` (het nghia tu khi `speaker_id` lay tu phien dang
    nhap, form khong con truong dinh danh nao de tu choi), `PROVENANCE_MISSING`
    va `TEACHER_REVIEW_REQUESTED` (chua bao gio duoc gan o dau).
    """

    # Dau vao va dieu kien duoc nop
    AUDIO_UNSUPPORTED = "AUDIO_UNSUPPORTED"
    AUDIO_TOO_LARGE = "AUDIO_TOO_LARGE"
    AUDIO_TOO_LONG = "AUDIO_TOO_LONG"
    AUDIO_TOO_SHORT = "AUDIO_TOO_SHORT"
    # Chat luong am thanh
    HIGH_SILENCE_RATIO = "HIGH_SILENCE_RATIO"
    CLIPPING_DETECTED = "CLIPPING_DETECTED"
    LOW_SNR = "LOW_SNR"
    WRONG_SAMPLE_RATE = "WRONG_SAMPLE_RATE"
    # Nhan dang tieng noi
    ASR_FAILED = "ASR_FAILED"
    ASR_EMPTY_TRANSCRIPT = "ASR_EMPTY_TRANSCRIPT"
    ASR_LOW_CONFIDENCE = "ASR_LOW_CONFIDENCE"
    ASR_HALLUCINATION = "ASR_HALLUCINATION"
    # Dac trung va cham diem
    FEATURE_NOT_COMPUTABLE = "FEATURE_NOT_COMPUTABLE"
    TOO_FEW_WORDS = "TOO_FEW_WORDS"
    SCORE_NEAR_BOUNDARY = "SCORE_NEAR_BOUNDARY"
    SCORE_AGGREGATED = "SCORE_AGGREGATED"
    MODEL_VERSION_MISSING = "MODEL_VERSION_MISSING"
    OUT_OF_DISTRIBUTION = "OUT_OF_DISTRIBUTION"
    # Van hanh va lech phien ban
    PROCESSING_INTERRUPTED = "PROCESSING_INTERRUPTED"
    ASR_VERSION_MISMATCH = "ASR_VERSION_MISMATCH"
    VAD_VERSION_MISMATCH = "VAD_VERSION_MISMATCH"
    # La chan hop le (D022). Ca ba deu chuyen giang vien. Ngon ngu khac thi
    # khong cham; lac de / doc lai de thi GIU diem va KHONG tru -- may chi
    # nghi ngo, nguoi quyet.
    LANGUAGE_NOT_ENGLISH = "LANGUAGE_NOT_ENGLISH"
    OFF_TOPIC_SUSPECTED = "OFF_TOPIC_SUSPECTED"
    PROMPT_COPY_SUSPECTED = "PROMPT_COPY_SUSPECTED"


class QcStatus(str, Enum):
    """Quality-check outcome, three levels as required by SRS FR-07.

    The QC module used to return only a `passed` bool, which could not express
    the middle ground: a recording good enough to score but not good enough to
    trust. That middle ground got folded into PASS, losing a warning layer that
    the SRS requires.
    """

    PASS = "PASS"
    REVIEW = "REVIEW"
    REJECT = "REJECT"


class Criterion(str, Enum):
    """The five in-scope CEFR criteria. Interaction was dropped per QD-04."""

    RANGE = "range"
    ACCURACY = "accuracy"
    FLUENCY = "fluency"
    COHERENCE = "coherence"
    PHONOLOGY = "phonology"


class Band(str, Enum):
    """The six CEFR levels, lowest first (D059). The order is meaningful."""

    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"

    @property
    def rank(self) -> int:
        """0 for A1 up to 5 for C2: what "higher band" and "lower band" compare."""
        return list(Band).index(self)


class EvidenceKind(str, Enum):
    """The kinds of evidence the builder can produce.

    Was a plain `str` with the four values written out at each construction
    site in `report/evidence.py`. That is the same primitive obsession that
    `Map<str, float>` was on `FeatureSet`: a closed set of four values spelled
    as an open type, so nothing catches a typo and the diagram could not show
    the reader what the four values are.

    Inherits `str` so the JSON the report screen already reads is unchanged --
    `EVIDENCE_KIND_NAMES[e.kind]` in `report.js` keeps working.
    """

    PAUSE = "pause"
    FILLER = "filler"
    LOW_CONFIDENCE_WORD = "low_confidence_word"
    LEXICAL = "lexical"
    # D061: the different linking words the transcript contains (Coherence).
    CONNECTOR = "connector"


class TaskPart(str, Enum):
    """Which exam part a prompt belongs to, and it is NOT a cosmetic label.

    `Task.part` was a free `str`. Writing the closed set out matters here
    because the three values do not mean the same thing to the scorer:

    - `P3` and `P4` are the parts the model was trained on. Each response in
      the training corpus is exactly one file for one of them, which is what
      makes the unit of inference line up with what a student submits.
    - `P5` is the long prompt (120-300s) and sits DELIBERATELY outside that
      range. It is scored by the windowing path in `scoring/windows.py`, gets
      `ReasonCode.SCORE_AGGREGATED`, and always goes to a teacher.

    So `part` is what decides which scoring path a response takes. A free
    string hid that behind a value nobody could enumerate.
    """

    P3 = "P3"
    P4 = "P4"
    P5 = "P5"


class TaskPurpose(str, Enum):
    """Whether a task is for ASSESSMENT or for PRACTICE. D023.

    The two purposes differ at exactly the point that decides the processing
    path. An assessment response goes through the scoring model, gets a band and
    may enter the teacher queue. A practice attempt is NEVER given a band: a
    practice task is a short constrained exercise (use given words, read a
    passage aloud) that lies outside the exam responses the model learned from,
    and the model's error is larger than the real progress made in a few weeks.
    Practice gets rule-based feedback only, with no teacher in the loop.
    """

    ASSESSMENT = "assessment"
    PRACTICE = "practice"


class MissionKind(str, Enum):
    """Seven kinds of practice mission, each one a fixed rule applied to the recording. D023.

    Each kind measures something the learner can check by listening to their own
    recording: how long they spoke, where the longest pause was, which words they
    used. None of them is a criterion score -- the model only learns the overall
    label (see `CriterionIndicator`).
    """

    SPEAK_SECONDS = "speak_seconds"
    MAX_PAUSE = "max_pause"
    USE_WORDS = "use_words"
    UNIQUE_WORDS = "unique_words"
    PAST_VERBS = "past_verbs"
    CONDITIONALS = "conditionals"
    READ_ALOUD = "read_aloud"


class QcResult(BaseModel):
    """Audio quality-check result."""

    duration_ms: int
    sample_rate_hz: int
    channels: int
    silence_ratio: float = Field(ge=0.0, le=1.0)
    clipping_ratio: float = Field(ge=0.0, le=1.0)
    snr_db: float | None = None
    qc_status: QcStatus
    qc_config_version: str = "qc-v1"
    reasons: list[ReasonCode] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Whether processing may continue.

        REVIEW still continues: the recording can be scored, but the result is
        flagged for a teacher to look at. Only REJECT stops outright, and per
        AC-07.1 the ASR step must not be called in that case.
        """
        return self.qc_status is not QcStatus.REJECT


# Nguong duoi day quyet dinh mot tu co duoc danh dau "may nghe khong ro" hay
# khong. No tung duoc viet lai o BA noi -- evidence.py, report.js va
# review_one.js -- nghia la ba cho co the lech nhau ma khong ai biet. Mot luat
# ve mot tu thi thuoc ve lop Word.
LOW_WORD_PROB = 0.50


class Word(BaseModel):
    """One word in the transcript, with its timestamps and confidence."""

    text: str
    start_s: float
    end_s: float
    prob: float | None = None

    @computed_field
    @property
    def is_uncertain(self) -> bool:
        """The recogniser was unsure of this word. FR-10, FR-16.

        A word with no probability at all is NOT uncertain: the engine simply
        did not report one, which is a fact about the engine rather than about
        the speaker. Treating missing as bad would paint a whole transcript
        orange the day the project switches recogniser.
        """
        return self.prob is not None and self.prob < LOW_WORD_PROB


class Transcript(BaseModel):
    """What the speaker said, as text plus one `Word` per word.

    Named after the thing, not after the machine that produced it: `AsrResult`
    described *which subsystem ran*, which is a fact about the architecture,
    not about the recording. The port that produces this is still called
    `AsrEngine` -- that one IS a piece of technology, and naming it after the
    technology is correct.
    """

    # `text`, not `transcript`, because the class is now called `Transcript`
    # and `transcript.transcript` reads as a stutter. Rows written before the
    # rename still carry the old key, so validation accepts both.
    text: str = Field(validation_alias=AliasChoices("text", "transcript"))
    words: list[Word] = Field(default_factory=list)
    engine: str
    model_version: str
    is_verbatim: bool = False
    # Ngon ngu bo nhan dang phat hien tren 30 giay dau (D022). Rong khi engine
    # khong phat hien duoc -- vi du model chi tieng Anh, hoac ban gia lap.
    language: str | None = None
    language_probability: float | None = Field(default=None, ge=0.0, le=1.0)
    # D057: text tokens the decoder produced, counted by the recogniser; None
    # when it cannot count them (the test double) or for a report made earlier.
    output_tokens: int | None = Field(default=None, ge=0)

    def is_foreign(self, min_probability: float) -> bool:
        """Confidently not English (D022). A recogniser forced into English
        "translates" Vietnamese speech into English text; scoring that text
        scores an answer nobody gave."""
        return (
            self.language is not None
            and self.language != "en"
            and (self.language_probability or 0.0) >= min_probability
        )

    def cut_at(self, index: int) -> Transcript:
        """The words before `index`, and the text they make: what is left once
        a repetition loop of the recogniser is cut off."""
        kept = self.words[:index]
        return self.model_copy(
            update={"words": kept, "text": " ".join(w.text for w in kept).strip()}
        )

    def shifted(self, offset_s: float) -> Transcript:
        """The timings moved by `offset_s`: back on the original recording's
        clock after the recogniser heard a trimmed copy of it."""
        if not offset_s:
            return self
        return self.model_copy(
            update={
                "words": [
                    w.model_copy(
                        update={
                            "start_s": round(w.start_s + offset_s, 3),
                            "end_s": round(w.end_s + offset_s, 3),
                        }
                    )
                    for w in self.words
                ]
            }
        )


class Feature(BaseModel):
    """One measurement: its name, its number, and -- when there is no number --
    the reason there is none.

    This used to be two parallel dictionaries on `FeatureSet`: `values` keyed by
    feature name, and `invalid` keyed by the same names. Nothing made them agree.
    A feature could sit in `values` as None with no entry in `invalid`, and one
    did: `asr_conf_mean` on a transcript carrying no per-word probabilities. The
    comment above that code said "missing data returns None with a reason code",
    and the code did not. Holding the value and the reason in ONE object turns
    that agreement from a promise in prose into something the type checks.
    """

    name: str
    value: float | None = None
    reason: ReasonCode | None = None

    @model_validator(mode="after")
    def _a_number_or_a_reason(self) -> Feature:
        if self.value is None and self.reason is None:
            raise ValueError(f"dac trung {self.name!r} khong co gia tri thi phai co ly do")
        if self.value is not None and self.reason is not None:
            raise ValueError(f"dac trung {self.name!r} co gia tri thi khong mang ly do")
        return self

    @property
    def is_computable(self) -> bool:
        """Whether this measurement is available.

        A feature with no value is not a zero and not an absent key -- it is a
        measurement that could not be taken, and every caller must read it the
        same way. This is the one place that spelling lives.
        """
        return self.value is not None


class FeatureSet(BaseModel):
    """The measurements computed for one response.

    The features are a list rather than 18 named attributes because the source
    of truth for WHICH features exist is `feature_order` inside the model
    artifact. Adding a feature means shipping a new artifact, not editing this
    class -- and a list of names copied here would be a second place to keep in
    step by hand.
    """

    # `min_length=1`: mot FeatureSet rong khong mang nghia gi, va boi so `1..*`
    # tren so do chi dung khi co thu buoc no dung.
    items: list[Feature] = Field(min_length=1)
    feature_version: str

    @model_validator(mode="after")
    def _each_name_once(self) -> FeatureSet:
        names = [f.name for f in self.items]
        if len(names) != len(set(names)):
            dup = sorted({n for n in names if names.count(n) > 1})
            raise ValueError(f"dac trung bi lap ten: {dup}")
        return self

    @property
    def names(self) -> set[str]:
        return {f.name for f in self.items}

    def feature(self, name: str) -> Feature | None:
        """The measurement by that name, or None when the extractor never produced it."""
        return next((f for f in self.items if f.name == name), None)

    def value_of(self, name: str) -> float | None:
        """The number, or None when there is none.

        Deliberately collapses two cases into one: a name the extractor never
        produced, and a name whose measurement failed. Both mean the same thing
        to every caller -- the number is not available -- and making callers
        handle both spellings is how one of them ends up handling only one.
        """
        f = self.feature(name)
        return f.value if f else None

    def vector(self, order: list[str]) -> list[float]:
        """The values in the requested order, for scoring.

        Raises rather than skipping or substituting: a scoring vector with a hole
        in it produces a number that looks like every other number. Callers that
        can degrade gracefully must check `value_of` first -- `predict_overall`
        does exactly that before calling this.
        """
        out: list[float] = []
        for name in order:
            f = self.feature(name)
            if f is None or not f.is_computable:
                raise ValueError(f"dac trung {name!r} khong tinh duoc -- khong dung de cham diem")
            assert f.value is not None  # `is_computable` vua bao dam dieu nay
            out.append(f.value)
        return out


class CriterionCoverage(BaseModel):
    """How much of one criterion the pipeline could actually measure.

    It used to be called `CriterionScore` and carried `score_0_6` and `band`.
    Both were removed because both were lies of a particular kind: the model
    has ONE output, and `RidgeScorer` wrote that same number into all five
    rows. Five copies of one number read as five independent judgements, and
    the report screen already refused to print them for exactly that reason.

    What genuinely differs per criterion is how many of its features the
    pipeline managed to compute -- so that is all this carries, and the name
    now says so.
    """

    criterion: Criterion
    # Renamed from `confidence`, which promised more than it carries: this is
    # the FRACTION OF FEATURES that could be computed, not the probability the
    # score is right. `report.js` already carried a comment saying so, which is
    # the sign a name is doing a footnote's job. The old spelling is still
    # accepted so report JSON written before the rename still loads.
    coverage: float | None = Field(
        default=None, validation_alias=AliasChoices("coverage", "confidence")
    )
    reasons: list[ReasonCode] = Field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """Every feature this criterion rests on was computable."""
        return self.coverage == 1.0


class Evidence(BaseModel):
    """Evidence backing a comment. It must always trace back to real data."""

    # Stable within one report, assigned in order by the builder ("ev-01", ...).
    # A comment cites this id, and a test checks every cited id exists: that is
    # the whole mechanism preventing a report from saying something no
    # measurement supports.
    evidence_id: str = ""
    criterion: Criterion
    kind: EvidenceKind
    start_s: float | None = None
    end_s: float | None = None
    snippet: str | None = None
    note: str


class AnalysisWindow(BaseModel):
    """One stretch of a long recording -- before and after it is scored.

    Merged from two classes that described the same stretch of time at two
    moments: `Window` in `scoring/windows.py` (the plan) and `WindowScore` here
    (the result). Keeping both forced every caller to convert one into the
    other, and to remember which one it was holding. The score is simply empty
    until the window has been scored.
    """

    index: int
    start_s: float
    end_s: float
    overall_0_6: float | None = None
    band: Band | None = None
    reasons: list[ReasonCode] = Field(default_factory=list)

    @property
    def duration_s(self) -> float:
        return self.end_s - self.start_s

    @property
    def was_scored(self) -> bool:
        return self.overall_0_6 is not None


class Comment(BaseModel):
    """One sentence of feedback, and the evidence it stands on.

    FR-25. `evidence_refs` may never be empty: a sentence with no evidence is
    the failure mode this whole design exists to prevent -- fluent, confident,
    and unfalsifiable.
    """

    criterion: Criterion | None = None
    text: str
    evidence_refs: list[str] = Field(default_factory=list)


class Priority(BaseModel):
    """One thing worth practising next. FR-26."""

    # A feature NAME, not a `Feature` object -- the name says so now. Nothing
    # here can check the name exists, because the list of features lives in the
    # model artifact; `tests/test_comments.py` pins that every name `ADVICE` can
    # emit is in that artifact's `feature_order`, which is where the check can
    # actually be made.
    feature_name: str = Field(validation_alias=AliasChoices("feature_name", "feature"))
    text: str
    # How far this measurement drags the predicted score down, in points on the
    # 0-6 scale. Kept so a teacher can see WHY this was picked over another.
    impact: float


class ScoreInterval(BaseModel):
    """Khoang diem co bao dam thong ke va tap band giao voi no. D022.

    Thay cho nguong "gan ranh gioi +-0,5" dat tay. `coverage` la muc phu DANH
    NGHIA 1 - alpha; CV+ chi bao dam >= 1 - 2*alpha ve ly thuyet, con muc phu
    thuc nghiem do duoc nam trong artifact hieu chinh (`alpha_curve`).
    """

    low: float
    high: float
    band_set: list[Band] = Field(min_length=1)
    coverage: float = Field(gt=0.0, lt=1.0)
    method: str
    calibration_version: str

    @model_validator(mode="after")
    def _ordered(self) -> ScoreInterval:
        if self.low > self.high:
            raise ValueError("can duoi lon hon can tren")
        return self

    @property
    def is_single_band(self) -> bool:
        return len(self.band_set) == 1


class CriterionIndicator(BaseModel):
    """Vi tri mot phep do trong phan bo bai noi huan luyen. KHONG phai diem.

    Mo hinh chi hoc nhan overall, nen khong co diem rieng tung tieu chi. Thu
    noi duoc mot cach trung thuc: "toc do noi cua ban cao hon 70% bai noi trong
    tap tham chieu". `higher_is_better` lay tu dau cua tuong quan voi diem.
    """

    criterion: Criterion
    feature: str
    value: float
    percentile: float = Field(ge=0.0, le=1.0)
    higher_is_better: bool

    @property
    def standing(self) -> float:
        """Phan vi da quy ve cung chieu: cao luon la tot hon."""
        return self.percentile if self.higher_is_better else 1.0 - self.percentile


class Assessment(BaseModel):
    """Scoring result together with its provenance.

    FR-27 requires every report to trace back to the exact versions that
    produced it. The fields below are read from the model artifact; they must
    not be hard-coded in the source.
    """

    overall_0_6: float | None
    overall_band: Band | None
    criteria: list[CriterionCoverage] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    model_version: str
    feature_version: str | None = None
    band_map_version: str | None = None
    calibration_version: str | None = None
    scored_at: str | None = None
    reasons: list[ReasonCode] = Field(default_factory=list)
    comments: list[Comment] = Field(default_factory=list)
    priorities: list[Priority] = Field(default_factory=list)
    # Empty for a recording short enough to score in one piece. Non-empty means
    # the score is a median across windows and carries SCORE_AGGREGATED.
    windows: list[AnalysisWindow] = Field(default_factory=list)
    # Spread between the highest and lowest window, in points. A wide spread is
    # the honest signal that one number does not describe this recording.
    window_spread: float | None = None
    # Which measurements fell outside the range the model was trained on, with
    # the numbers. Without these the report can only say "not enough reliable
    # evidence", which tells the student nothing they can act on.
    out_of_range: list[dict] = Field(default_factory=list)
    teacher_verified: bool = False
    # D022. Rong khi chua co artifact hieu chinh hoac khong co diem.
    interval: ScoreInterval | None = None
    indicators: list[CriterionIndicator] = Field(default_factory=list)
    weakest_criteria: list[Criterion] = Field(default_factory=list)

    @property
    def was_scored(self) -> bool:
        return self.overall_0_6 is not None

    @computed_field
    @property
    def is_calibrated(self) -> bool:
        """Whether the number may be read as a calibrated estimate.

        Read from the artifact rather than assumed: today every artifact says
        `chua-hieu-chuan`, and the report screen uses this to print the warning
        that goes with an uncalibrated score.
        """
        v = (self.calibration_version or "").lower()
        return bool(v) and not any(k in v for k in ("chua", "chưa", "none", "uncalib"))


class ProcessingRequest(BaseModel):
    """Pipeline input. speaker_id must be a pseudonym; it must never contain a
    student ID or a real name."""

    response_id: str
    speaker_id: str
    task_id: str
    audio_path: str
    prompt_version: str
    config_version: str


class Review(BaseModel):
    """Mot lan giang vien giu hoac sua ket qua. FR-30, FR-31.

    Truoc day `Repository.review_history` tra ve `list[dict]`, nghia la hinh
    dang cua mot quyet dinh duyet chi ton tai trong dau nguoi viet cau SQL.
    Day la thu ma ca he thong ton tai de phuc vu -- no xung dang co mot lop.

    Luu y `old_*` co the rong: mot bai ma may tu choi cham van duoc duyet, va
    khi do khong co gi de "sua tu".
    """

    reviewer_id: str
    old_score: float | None = None
    new_score: float | None = None
    old_band: Band | None = None
    new_band: Band | None = None
    reason: str
    created_at: str  # when the teacher decided
    # D060: a review is part of its response's document; numbered in the order
    # decisions were taken, and stamped with when the teacher opened it (D041).
    review_id: int | None = None
    opened_at: str | None = None


class ReviewLock(BaseModel):
    """Quyen duyet mot bai, giu trong mot khoang thoi gian. FR-30.

    Khong co no, hai giang vien mo cung mot bai se ghi de quyet dinh cua nhau
    va **ca hai deu khong biet**. Khoa het han thi doi duoc, de mot nguoi dong
    trinh duyet giua buoi khong lam bai bi treo mai mai.
    """

    response_id: str
    reviewer_id: str
    reviewer_name: str
    locked_until: str

    def is_held_by(self, reviewer_id: str) -> bool:
        return self.reviewer_id == reviewer_id

    def has_expired(self, now: str) -> bool:
        """So sanh chuoi ISO-8601 truc tiep duoc vi chung cung mui gio UTC va
        cung do chinh xac giay -- thu tu tu dien trung voi thu tu thoi gian."""
        return self.locked_until <= now


class AuditEntry(BaseModel):
    """Mot dong nhat ky kiem toan. FR-31.

    Giu AI DA LAM GI, khong giu NOI DUNG da lam. Mot dong audit mang theo ban
    sao cua bai nop hoac cua diem se bien chinh no thanh mot ban luu thu hai,
    va luc do lenh xoa du lieu ca nhan khong con xoa het.
    """

    actor_id: str
    action: str
    target_id: str | None = None
    detail: str | None = None
    created_at: str


class AppConfig(BaseModel):
    """Mot gia tri doi duoc luc dang chay. FR-08, FR-36.

    Mang theo `updated_by` va `updated_at` — thu ma bien moi truong khong mang
    duoc. Cau hoi "ai ha nguong QC xuong 15 giay, luc nao" phai tra loi duoc,
    neu khong thi moi bao cao cham truoc do mat can cu.

    Ten truong theo dung ten cot trong bang `app_config`, khong doi cho "dep"
    hon: mot lop hop dong lech ten voi luoc do la mot phep anh xa tay nua, va
    day dung la loai viec khong ai nho phai lam.
    """

    key: str
    value: str
    version: str
    updated_by: str
    updated_at: str


class AuthSession(BaseModel):
    """Mot phien dang nhap con hieu luc. FR-32, NFR-07.

    KHONG mang token. Trong CSDL chi luu ban bam cua token; giu token o day
    nghia la mot doi tuong trong bo nho co the doc duoc de mao danh nguoi khac.
    """

    account_id: str
    expires_at: str

    def has_expired(self, now: str) -> bool:
        return self.expires_at <= now


class Mission(BaseModel):
    """One mission of a practice task, written in the task bank. D023.

    `label` is the sentence the student reads BEFORE speaking, so the rule and
    the promise must be one: "use at least 3 linking words" means `target` is 3
    and `words` lists the linking words that count. `words` is used only by
    USE_WORDS; READ_ALOUD compares against the task's own reference passage.
    """

    kind: MissionKind
    target: float = Field(gt=0)
    label: str = Field(min_length=1)
    words: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _words_only_where_counted(self) -> Mission:
        if self.kind is MissionKind.USE_WORDS and not self.words:
            raise ValueError("a USE_WORDS mission needs a word list")
        if self.kind is not MissionKind.USE_WORDS and self.words:
            raise ValueError(f"a {self.kind.value} mission takes no word list")
        if self.kind is MissionKind.READ_ALOUD and self.target > 1:
            raise ValueError("READ_ALOUD is a share of matched words and must be in (0, 1]")
        return self


class MissionHit(BaseModel):
    """One place in the recording that a mission result rests on. D023.

    A word used, with its timestamp; the longest silence, with its timestamp; or a
    word of the reference passage the machine did not hear (no timestamp, since it
    does not occur in the recording). Every piece of practice feedback stands on
    places like these.
    """

    text: str
    start_s: float | None = None


class MissionCheck(BaseModel):
    """The measurement of one mission on one attempt. D023.

    Like `Feature`: when measurable it has a number and NO reason; when not, it is
    empty and MUST carry a reason. `met` is empty when nothing could be measured --
    "could not measure" is not "not yet met", and merging the two makes the
    learner blame themselves for the machine's failure.
    """

    kind: MissionKind
    label: str
    target: float
    measured: float | None = None
    met: bool | None = None
    hits: list[MissionHit] = Field(default_factory=list)
    reason: ReasonCode | None = None

    @model_validator(mode="after")
    def _a_measurement_or_a_reason(self) -> MissionCheck:
        if self.measured is None and self.reason is None:
            raise ValueError(f"an unmeasured {self.kind.value} mission must carry a reason")
        if self.measured is not None and self.reason is not None:
            raise ValueError(f"a measured {self.kind.value} mission carries no reason")
        if (self.met is None) != (self.measured is None):
            raise ValueError("only a measured mission can be met or not met")
        return self


# Version of the mission rules. Bump it whenever the counting changes (the
# past-verb lexicon, tokenisation, passage matching): old results still read
# correctly against the rules that produced them.
MISSION_RULES_VERSION = "mission-v1"


class PracticeResult(BaseModel):
    """Feedback on one practice attempt: what was measured for each mission. D023.

    `completed` is the conclusion for the WHOLE attempt. It is derived from the
    missions rather than stored separately, so the two cannot disagree: any
    mission not met means not completed; no mission unmet but some unmeasurable
    means empty.
    """

    task_id: str
    checks: list[MissionCheck] = Field(min_length=1)
    rules_version: str = MISSION_RULES_VERSION

    @computed_field
    @property
    def completed(self) -> bool | None:
        if any(c.met is False for c in self.checks):
            return False
        if any(c.met is None for c in self.checks):
            return None
        return True

    @computed_field
    @property
    def met_count(self) -> int:
        return sum(1 for c in self.checks if c.met)


class PhraseCard(BaseModel):
    """One phrase of an upgraded answer and where it is in its reviews (D070).

    A card of the phrase book: `box` is its Leitner box, `due` when it comes
    back. Part of the upgrade it came from (`CoachUpgrade ◆ PhraseCard`).
    """

    phrase: str
    meaning_vi: str = ""
    box: int = 0
    due: str | None = None
    reviews: int = 0
    reviewed_at: str | None = None

    def is_due(self, at: str) -> bool:
        """A card never reviewed is due at once."""
        return (self.due or "") <= at


class CoachUpgrade(BaseModel):
    """The learner's answer rewritten one band higher (D069), made once and kept.

    Part of the response (`Response ◆ CoachUpgrade`): it is made from the
    response's transcript and goes with it. `provider` and `model` say which
    language model wrote it.
    """

    from_band: Band
    to_band: Band
    upgraded: str
    changes: list[dict] = Field(default_factory=list)
    phrases: list[PhraseCard] = Field(default_factory=list)
    provider: str
    model: str
    prompt_version: str
    created_at: str


class Response(BaseModel):
    """The pipeline's single output."""

    response_id: str
    status: ResponseStatus
    qc: QcResult | None = None
    asr: Transcript | None = None
    features: FeatureSet | None = None
    assessment: Assessment | None = None
    reasons: list[ReasonCode] = Field(default_factory=list)
    config_version: str
    # Ban de sinh vien da thay khi nop (truy vet). Co tren ProcessingRequest
    # tu lau nhung khong duoc luu vao ket qua, nen bao cao khong noi duoc sinh
    # vien da tra loi ban de nao. Rong o ban ghi cu.
    prompt_version: str | None = None
    # D023. Only on practice attempts; empty for assessment responses.
    practice: PracticeResult | None = None
    # D060: the teachers' decisions on this response, oldest first. Part of the
    # response (`Response ◆ Review`): they live and go with it. Kept out of the
    # stored report -- the repository keeps them beside it and fills them in.
    reviews: list[Review] = Field(default_factory=list)
    # D069: the upgraded answer, when its owner asked for one. Kept beside the
    # stored report like the reviews, and filled in by the repository.
    upgrade: CoachUpgrade | None = None

    @property
    def was_scored(self) -> bool:
        return self.assessment is not None and self.assessment.was_scored

    @property
    def needs_teacher(self) -> bool:
        return self.status is ResponseStatus.REVIEW_REQUIRED
