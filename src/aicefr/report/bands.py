"""What a band describes, and what the machine actually measures of it (D028).

A learner who reads "B1" on a report deserves to know what B1 means in terms of
speaking, and -- the half most products leave out -- which of those behaviours
this system observed at all. The descriptors are paraphrased in Vietnamese in
the spirit of the CEFR qualitative aspects of spoken language use (Council of
Europe, Companion Volume 2020); they are not a translation of the official
scales and are waiting for review by the Foreign Languages teachers (A-03).

Every aspect carries one of two labels, so the page cannot imply that the
machine heard grammar when its measurements are lengths, counts, word variety,
the kinds of connectors used (D061), recogniser confidence and pause statistics:

* measured indirectly -- some measurement touches this aspect;
* not measured        -- the machine has no measurement of it at all.

Interaction is not listed (D062): a monologue holds no turn to observe, and a
row that can only ever say "not assessed" was read as a missing feature.

The scorer has ONE output, an overall estimate. Nothing here suggests five
separate criterion scores.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from aicefr.contracts import Band


class Provenance(str, Enum):
    MEASURED_INDIRECTLY = "indirect"
    NOT_MEASURED = "not_measured"


PROVENANCE_NAMES = {
    Provenance.MEASURED_INDIRECTLY: "Máy đo gián tiếp",
    Provenance.NOT_MEASURED: "Máy không đo",
}


@dataclass(frozen=True)
class Aspect:
    """One aspect of speaking and how much of it the system can see."""

    key: str
    name: str
    provenance: Provenance
    # What the machine uses, in words a learner understands; empty when nothing.
    measured_by: str
    # What it cannot see of the aspect, said plainly.
    blind_to: str


ASPECTS: tuple[Aspect, ...] = (
    Aspect(
        "range",
        "Vốn từ (Range)",
        Provenance.MEASURED_INDIRECTLY,
        "số từ khác nhau, độ đa dạng từ, độ dài trung bình của từ",
        "không biết từ dùng có đúng ngữ cảnh không, không đo độ phong phú của cấu trúc câu",
    ),
    # D061: an automatic grammar checker run over transcripts was tried and
    # left out -- its error counts barely followed the errors examiners
    # corrected, on machine and on human transcripts alike. A number that does
    # not track grammar must not be shown as grammar.
    Aspect(
        "accuracy",
        "Ngữ pháp (Accuracy)",
        Provenance.NOT_MEASURED,
        "",
        "không có phép đo nào về lỗi ngữ pháp hay lỗi dùng từ. Nhóm đã thử chạy bộ kiểm tra ngữ "
        "pháp tự động trên bản chép lời và so với lỗi do người sửa: kết quả gần như không khớp, "
        'một phần có thể vì máy nhận dạng tự "sửa" câu nói sai thành câu đúng. Vì vậy hệ thống '
        "không đưa ra con số ngữ pháp; giảng viên nghe bài mới đánh giá được tiêu chí này",
    ),
    Aspect(
        "fluency",
        "Độ trôi chảy (Fluency)",
        Provenance.MEASURED_INDIRECTLY,
        "tốc độ nói, số chỗ ngừng mỗi phút, độ dài chỗ ngừng, tỷ lệ chỗ ngừng dài",
        "không phân biệt ngừng để suy nghĩ với ngừng vì nói lắp hay vì lý do sức khoẻ",
    ),
    Aspect(
        "coherence",
        "Mạch lạc (Coherence)",
        Provenance.MEASURED_INDIRECTLY,
        'số kiểu từ nối khác nhau trong bản chép lời (ví dụ "because", "for example", "however", '
        '"on the other hand")',
        "chỉ đếm từ nối, không biết từ nối có nối đúng ý không, không đánh giá cách sắp xếp ý "
        "của cả bài; máy nhận dạng nghe sót từ nào thì từ đó không được đếm. Độ dài bài nói "
        "không phải là mạch lạc",
    ),
    Aspect(
        "phonology",
        "Phát âm dễ nghe (Phonology)",
        Provenance.MEASURED_INDIRECTLY,
        "mức máy nhận dạng nghe chắc chắn các từ, tỷ lệ khoảng lặng",
        "không chấm giọng; máy nghe kém có thể do micro, tiếng ồn hay giọng lạ chứ không phải do "
        "phát âm sai. Không đo ngữ điệu và trọng âm",
    ),
)

# Paraphrased descriptors, one line per aspect and band.
DESCRIPTORS: dict[Band, dict[str, str]] = {
    Band.A1: {
        "range": (
            "Dùng được một số từ và cụm từ rất đơn giản về bản thân và những thứ cụ thể quanh mình."
        ),
        "accuracy": (
            "Kiểm soát rất hạn chế vài cấu trúc đơn giản đã học thuộc; lỗi cơ bản xuất hiện thường "
            "xuyên."
        ),
        "fluency": (
            "Nói những câu rất ngắn, rời rạc, thường dừng lâu để tìm từ hoặc phát âm từ lạ."
        ),
        "coherence": 'Nối từ hay cụm từ bằng những từ nối rất cơ bản như "and", "then".',
        "phonology": (
            "Phát âm một số ít từ đã học; người nghe quen với người học tiếng Việt mới hiểu được, "
            "phải cố gắng nhiều."
        ),
    },
    Band.A2: {
        "range": (
            "Dùng các mẫu câu cơ bản và cụm từ quen thuộc để nói về bản thân, gia đình, việc "
            "hằng ngày; vốn từ đủ cho nhu cầu đơn giản."
        ),
        "accuracy": (
            "Dùng đúng một số cấu trúc đơn giản nhưng vẫn lặp lại lỗi cơ bản như lẫn thì, quên "
            "chia động từ; ý chính vẫn hiểu được."
        ),
        "fluency": ("Nói được những câu ngắn; ngập ngừng rõ, hay dừng để tìm từ hoặc nói lại câu."),
        "coherence": 'Nối ý bằng những từ nối đơn giản nhất như "and", "but", "because".',
        "phonology": (
            "Phát âm nhìn chung đủ rõ để hiểu dù mang giọng tiếng Việt; người nghe đôi khi phải "
            "hỏi lại."
        ),
    },
    Band.B1: {
        "range": (
            "Đủ từ và cấu trúc để nói về hầu hết chủ đề quen thuộc như học tập, sở thích, du lịch; "
            "khi thiếu từ thì nói vòng được."
        ),
        "accuracy": (
            "Dùng khá chính xác các mẫu câu thông dụng trong tình huống quen thuộc; còn lỗi nhưng "
            "thường không làm sai ý."
        ),
        "fluency": (
            "Giữ được một lượt nói khá dài và dễ theo dõi, dù còn những chỗ dừng để sắp ý hay sửa "
            "lời."
        ),
        "coherence": "Kể hay trình bày thành một chuỗi ý nối tiếp, theo trình tự rõ ràng.",
        "phonology": (
            "Phát âm rõ, dễ hiểu dù còn giọng và vài âm chưa chuẩn; ngữ điệu đôi chỗ chưa tự nhiên."
        ),
    },
    Band.B2: {
        "range": (
            "Vốn từ và cấu trúc đủ rộng để mô tả rõ, nêu và bảo vệ quan điểm về nhiều chủ đề mà ít "
            "phải dừng tìm từ; dùng được câu phức."
        ),
        "accuracy": ("Kiểm soát ngữ pháp khá tốt; lỗi ít khi gây hiểu lầm và thường tự sửa được."),
        "fluency": (
            "Nói với nhịp khá đều, duy trì được đoạn dài; chỗ ngừng để cân nhắc cách nói ít "
            "khi kéo dài."
        ),
        "coherence": (
            "Dùng nhiều cách liên kết để gắn các ý thành bài nói rõ ràng, mạch lạc; đoạn dài đôi "
            "khi còn hơi rời."
        ),
        "phonology": (
            "Phát âm và ngữ điệu rõ, người nghe không phải cố gắng; giọng không phải vấn đề khi đã "
            "dễ hiểu."
        ),
    },
    Band.C1: {
        "range": (
            "Vốn từ rộng, chọn được cách diễn đạt phù hợp để nói trôi chảy về chủ đề phức tạp mà "
            "hầu như không phải giới hạn điều muốn nói."
        ),
        "accuracy": "Giữ độ chính xác ngữ pháp cao một cách ổn định; lỗi hiếm và khó nhận ra.",
        "fluency": (
            "Diễn đạt trôi chảy, tự nhiên, gần như không phải dừng; chỉ chủ đề khó về khái niệm "
            "mới làm mạch nói chậm lại."
        ),
        "coherence": (
            "Bài nói rõ ràng, chặt chẽ, dùng thành thạo các cách tổ chức ý, từ nối và phương tiện "
            "liên kết."
        ),
        "phonology": (
            "Thay đổi ngữ điệu và trọng âm câu đúng để diễn tả sắc thái nghĩa; giọng gốc gần như "
            "không ảnh hưởng tới việc hiểu."
        ),
    },
    Band.C2: {
        "range": (
            "Nắm vững thành ngữ và cách nói thông tục, diễn đạt chính xác những sắc thái nghĩa "
            "tinh tế một cách linh hoạt."
        ),
        "accuracy": (
            "Kiểm soát ngữ pháp nhất quán ngay cả khi tập trung vào việc khác như lên kế hoạch hay "
            "theo dõi phản ứng người nghe."
        ),
        "fluency": (
            "Nói dài, tự nhiên, không ngập ngừng; chỉ dừng để chọn đúng từ diễn đạt ý tưởng, người "
            "nghe khó nhận ra."
        ),
        "coherence": (
            "Bài nói mạch lạc, có cấu trúc logic giúp người nghe nhận ra và nhớ các điểm "
            "quan trọng."
        ),
        "phonology": (
            "Dùng toàn bộ các đặc điểm âm vị để diễn đạt chính xác ý muốn nói; luôn rõ ràng, dễ "
            "hiểu."
        ),
    },
}


def page_rows() -> list[dict]:
    """One row per aspect: its label, what the machine uses, and the three bands."""
    rows = []
    for a in ASPECTS:
        rows.append(
            {
                "key": a.key,
                "name": a.name,
                "provenance": a.provenance.value,
                "provenance_name": PROVENANCE_NAMES[a.provenance],
                "measured_by": a.measured_by,
                "blind_to": a.blind_to,
                "bands": {b.value: DESCRIPTORS[b].get(a.key, "") for b in DESCRIPTORS},
            }
        )
    return rows
