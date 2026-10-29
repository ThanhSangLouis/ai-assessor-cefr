"""Turn measurements into sentences a student can act on. FR-25 and FR-26.

Two rules shape everything here, and both exist because the easy version of
this module is actively harmful.

**A sentence with no evidence does not get written.** It is trivial to generate
four fluent sentences for any recording; it is the fluency that makes them
dangerous, because a student cannot tell a measured claim from a generated one.
So every comment carries the ids of the evidence it stands on, and a report with
three honest sentences beats one with four where the fourth is decoration.

**Priorities come from the model's own arithmetic, not from an opinion.** The
scorer is linear: the predicted score is `intercept + Σ coef_i · z_i`. So the
measurement dragging a response down the most is simply the one with the most
negative `coef_i · z_i`, expressed in points on the 0-6 scale. That number is
shown to the teacher. Nothing here invents a pedagogical theory -- it reports
which measurement the model itself weighted against this speaker.

Note on what this is NOT: `docs/plan/SPEC_HOAN_THIEN.md` originally described
picking the feature furthest from the median of the band above. That needs
per-band feature distributions, which the artifact does not carry. Using the
model's own contribution answers the same question -- "what is costing this
speaker points" -- with data we actually have, instead of inventing medians.
"""

from __future__ import annotations

from dataclasses import dataclass

from aicefr.contracts import (
    Comment,
    Criterion,
    Evidence,
    EvidenceKind,
    FeatureSet,
    Priority,
    ReasonCode,
)

# Below this, the report stops making claims about the speaker. FR-26 AC-26.3.
LOW_CONFIDENCE = 0.50

MAX_PRIORITIES = 2

# Goi y bai luyen tiep theo cho tieu chi yeu nhat (D022). Luat minh bach, mot
# cau co dinh cho moi tieu chi -- khong sinh tu do, de giang vien doc truoc duoc
# moi dieu he thong co the noi voi sinh vien.
NEXT_TASK_HINTS: dict[Criterion, str] = {
    Criterion.RANGE: (
        "Kể lại một trải nghiệm gần đây trong 60 giây, cố gắng dùng ít nhất ba từ "
        "bạn chưa dùng trong bài trước."
    ),
    Criterion.ACCURACY: (
        "Đọc to chậm một đoạn văn ngắn rồi kể lại bằng lời của mình, chú ý phát âm rõ từng từ."
    ),
    Criterion.FLUENCY: (
        "Nói liên tục 60 giây về một chủ đề quen thuộc; khi bí, dùng cụm nối "
        "(well, I mean) thay vì dừng hẳn."
    ),
    Criterion.COHERENCE: (
        "Trả lời theo khung: ý chính, hai lý do, một ví dụ, kết luận — dùng từ nối "
        "(first, because, for example, so)."
    ),
    Criterion.PHONOLOGY: (
        "Shadowing: nghe một câu mẫu, nhắc lại ngay với cùng nhịp và trọng âm, lặp lại ba lần."
    ),
}

# A measurement has to cost at least this many points before it is worth telling
# somebody to work on it. Without a floor, every report ends with two priorities
# even when the speaker is doing fine -- and advice that appears whatever you do
# is advice nobody acts on.
MIN_IMPACT = 0.05


@dataclass(frozen=True)
class Advice:
    """What to say when a given measurement is what is holding a speaker back."""

    text: str
    criterion: Criterion


# Only measurements a student can actually change appear here. `total_dur` and
# `n_words` are two views of "say more", so they share one piece of advice
# rather than producing two priorities that mean the same thing.
ADVICE: dict[str, Advice] = {
    "vad_pause_per_min": Advice(
        "Giảm số lần ngừng giữa chừng: chuẩn bị ý trước khi bấm ghi âm, và khi bí từ"
        " thì nói tiếp bằng từ đơn giản hơn thay vì dừng lại tìm từ đúng.",
        Criterion.FLUENCY,
    ),
    "vad_long_pause_ratio": Advice(
        "Cắt bớt những quãng lặng dài: thà nói một câu ngắn gọn còn hơn im lặng vài giây giữa câu.",
        Criterion.FLUENCY,
    ),
    "vad_silence_ratio": Advice(
        "Tăng thời gian thực sự nói trong bài: hiện phần lớn thời lượng là im lặng.",
        Criterion.FLUENCY,
    ),
    "words_per_sec": Advice(
        "Nói liền mạch hơn một chút. Không cần nói nhanh, chỉ cần bớt kéo dài"
        " từng từ và bớt ngập ngừng giữa các cụm từ.",
        Criterion.FLUENCY,
    ),
    "vad_articulation_rate": Advice(
        "Phát âm gọn hơn trong từng đoạn nói, tránh kéo dài nguyên âm cuối từ.",
        Criterion.PHONOLOGY,
    ),
    "n_words": Advice(
        "Nói dài hơn và triển khai ý: mỗi bài nên đủ 40–60 giây, có mở đầu,"
        " một hai ý chính kèm ví dụ, rồi kết.",
        Criterion.COHERENCE,
    ),
    "ttr": Advice(
        "Dùng nhiều từ khác nhau hơn: hiện bài lặp lại một nhóm từ nhỏ."
        " Thử thay vài từ lặp bằng từ đồng nghĩa.",
        Criterion.RANGE,
    ),
    "log_uniq": Advice(
        "Mở rộng vốn từ dùng trong bài, đặc biệt là động từ và tính từ.",
        Criterion.RANGE,
    ),
    "mean_word_len": Advice(
        "Thử dùng thêm từ dài và cụ thể hơn thay cho từ chung chung như good, thing, very.",
        Criterion.RANGE,
    ),
    "asr_conf_mean": Advice(
        "Phát âm rõ hơn và thu ở nơi yên tĩnh: nhiều từ trong bài nghe không rõ,"
        " nên cả người nghe lẫn máy đều phải đoán.",
        Criterion.PHONOLOGY,
    ),
    "asr_conf_geo": Advice(
        "Chú ý những từ bị nuốt âm cuối — đó là chỗ người nghe mất dấu nhất.",
        Criterion.PHONOLOGY,
    ),
}


def _refs(evidence: list[Evidence], *kinds: str, criterion: Criterion | None = None) -> list[str]:
    """Ids of evidence of the requested kinds (and criterion, when given)."""
    out = []
    for e in evidence:
        if kinds and e.kind not in kinds:
            continue
        if criterion is not None and e.criterion is not criterion:
            continue
        if e.evidence_id:
            out.append(e.evidence_id)
    return out


class CommentBuilder:
    """Builds the sentences and the practice priorities of one report."""

    def __init__(self, low_confidence: float = LOW_CONFIDENCE) -> None:
        self.low_confidence = low_confidence

    # ---------- FR-25 ----------

    def comments(
        self,
        features: FeatureSet,
        evidence: list[Evidence],
        confidence: float | None,
        reasons: list[ReasonCode],
    ) -> list[Comment]:
        """Up to four sentences. Fewer when the measurements are not there."""
        out: list[Comment] = []

        pause_refs = _refs(evidence, EvidenceKind.PAUSE)
        pauses = features.value_of("vad_pause_per_min")
        if pauses is not None and pause_refs:
            out.append(
                Comment(
                    criterion=Criterion.FLUENCY,
                    text=(
                        f"Bài có khoảng {pauses:.0f} lần ngừng mỗi phút; những chỗ ngừng dài"
                        " nhất được đánh dấu trong bằng chứng bên dưới."
                    ),
                    evidence_refs=pause_refs,
                )
            )

        lex_refs = _refs(evidence, EvidenceKind.LEXICAL)
        ttr = features.value_of("ttr")
        if ttr is not None and lex_refs:
            out.append(
                Comment(
                    criterion=Criterion.RANGE,
                    text=(
                        f"Tỷ lệ từ khác nhau trên tổng số từ là {ttr:.2f}."
                        " Con số càng thấp nghĩa là bài càng lặp lại một nhóm từ nhỏ."
                    ),
                    evidence_refs=lex_refs,
                )
            )

        words, wps = features.value_of("n_words"), features.value_of("words_per_sec")
        dur = features.value_of("total_dur")
        if words is not None and wps is not None and dur is not None:
            # This one stands on the measurements themselves rather than on an
            # excerpt, so it cites whatever evidence is present. If the report
            # has no evidence at all, the sentence is not written.
            any_ref = _refs(evidence)
            if any_ref:
                out.append(
                    Comment(
                        # Speed is fluency. Length is not coherence (D061).
                        criterion=Criterion.FLUENCY,
                        text=(
                            f"Bài dài {dur:.0f} giây với {words:.0f} từ,"
                            f" tốc độ khoảng {wps:.1f} từ mỗi giây."
                        ),
                        evidence_refs=any_ref[:1],
                    )
                )

        # D061: the kinds of connectors, never their rate, and no claim about
        # whether they join the right ideas -- the machine cannot hear that.
        conn_refs = _refs(evidence, EvidenceKind.CONNECTOR)
        if conn_refs:
            out.append(
                Comment(
                    criterion=Criterion.COHERENCE,
                    text=(
                        "Từ nối cho người nghe biết các ý liên quan với nhau thế nào. Thử thêm"
                        ' những kiểu bạn chưa dùng, như "for example" để minh hoạ,'
                        ' "however" để nêu ý trái lại, "as a result" để nói hệ quả.'
                        " Máy chỉ đếm từ nối, không biết bạn dùng có đúng ý hay không."
                    ),
                    evidence_refs=conn_refs,
                )
            )

        conf_refs = _refs(evidence, EvidenceKind.LOW_CONFIDENCE_WORD)
        if confidence is not None and confidence < self.low_confidence:
            out.append(
                Comment(
                    criterion=None,
                    text=(
                        "Độ tin cậy của kết quả thấp, nên bài này cần giảng viên xác nhận"
                        " trước khi dùng điểm. Không kết luận trình độ từ con số hiện tại."
                    ),
                    evidence_refs=conf_refs or _refs(evidence)[:1],
                )
            )
        elif ReasonCode.ASR_VERSION_MISMATCH in reasons:
            out.append(
                Comment(
                    criterion=None,
                    text=(
                        "Bộ nhận dạng tiếng nói đang chạy khác bộ đã dùng lúc huấn luyện"
                        " mô hình, nên điểm chỉ mang tính tham khảo và được chuyển giảng"
                        " viên duyệt."
                    ),
                    evidence_refs=_refs(evidence)[:1],
                )
            )

        # The invariant FR-25 exists for. Kept as a filter rather than an
        # assertion: a missing citation must cost the sentence, not the report.
        return [c for c in out if c.evidence_refs]

    # ---------- FR-26 ----------

    def priorities(
        self,
        contributions: dict[str, float],
        confidence: float | None,
    ) -> list[Priority]:
        """At most two things to practise, ranked by what the model penalised.

        `contributions` comes from the scorer through the port, in points on the
        0-6 scale; negative means the measurement cost the speaker points.

        Returns nothing when confidence is low: advice derived from a
        measurement the system does not trust is worse than silence, because
        the student cannot tell the difference.
        """
        if confidence is not None and confidence < self.low_confidence:
            return []

        scored: list[Priority] = []
        seen: set[str] = set()
        for name, impact in contributions.items():
            advice = ADVICE.get(name)
            if advice is None or impact >= -MIN_IMPACT:
                continue
            if advice.text in seen:  # two measurements, one piece of advice
                continue
            seen.add(advice.text)
            scored.append(
                Priority(feature_name=name, text=advice.text, impact=round(abs(impact), 3))
            )

        scored.sort(key=lambda p: p.impact, reverse=True)
        return scored[:MAX_PRIORITIES]
