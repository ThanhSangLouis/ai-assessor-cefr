"""The practice task bank: 5 criteria x 3 bands = 15 tasks. D023.

How a task is written, and why:

* **Each task practises ONE criterion at ONE band.** Like a short lesson in a
  language-learning app: done in about a minute, and the learner knows at once
  what they managed. Assessment tasks (P3/P4/P5) measure the whole response;
  a practice task aims at a single skill.
* **Every mission is something the learner can check for themselves.** "Use
  at least 3 linking words", not "be more coherent": listening back to the
  recording is enough to see whether the machine counted right. The scoring
  model only learns the overall label, so the system has no criterion score to
  promise; what can be measured is behaviour, and behaviour is what practice
  changes.
* **Word lists are shown BEFORE speaking.** A vocabulary mission activates
  words the learner already knows; it is not a quiz.
* **Pronunciation is practised by reading aloud.** The share of words in a
  reference passage that the recogniser gets right measures intelligibility
  without penalising a Vietnamese accent: nothing is compared with a native
  voice, the only question is whether the machine recognised the words the
  learner meant to say. Passages avoid numbers, proper names and words with
  two spellings (British/American), because the recogniser may write them
  differently even when the reader made no mistake.
* **No topic overlaps an assessment task.** Practising the exam prompt is
  rehearsal, not practice; P3 (online learning) and P4 (exam preparation) do
  not appear here.

The content is the team's draft, written against the CEFR Companion Volume
2020 descriptors. It must be approved by a lecturer of the Faculty of Foreign
Languages before use with real students (outline section 2.5, step 3:
suggestions "from approved templates").
"""

from __future__ import annotations

from dataclasses import dataclass

from aicefr.contracts import Band, Criterion, Mission, MissionKind, TaskPart

# Order of the learning path, which is also the order of suggestions before any
# assessment exists. Fluency comes first: it is measured by VAD on the waveform
# and depends least on the recogniser, so an awkward first recording still
# gets feedback that can be trusted.
PATH_ORDER: tuple[Criterion, ...] = (
    Criterion.FLUENCY,
    Criterion.COHERENCE,
    Criterion.RANGE,
    Criterion.ACCURACY,
    Criterion.PHONOLOGY,
)

BAND_ORDER: tuple[Band, ...] = (Band.A2, Band.B1, Band.B2)

CRITERION_NAMES: dict[Criterion, str] = {
    Criterion.FLUENCY: "Độ trôi chảy",
    Criterion.COHERENCE: "Mạch lạc",
    Criterion.RANGE: "Vốn từ",
    Criterion.ACCURACY: "Ngữ pháp",
    Criterion.PHONOLOGY: "Phát âm dễ nghe",
}


@dataclass(frozen=True)
class PracticeSeed:
    """One practice task as written in the bank, before it goes into the `task` table."""

    task_id: str
    criterion: Criterion
    band: Band
    title: str
    prompt_text: str
    missions: tuple[Mission, ...]
    tips: tuple[str, ...]
    min_seconds: int
    max_seconds: int
    # Closest speaking format (P3 opinion, P4 description/narration). Practice
    # is never scored, so `part` here selects no scoring path.
    part: TaskPart
    reference_text: str | None = None
    prompt_version: str = "v1"


def _speak(seconds: int) -> Mission:
    return Mission(
        kind=MissionKind.SPEAK_SECONDS,
        target=seconds,
        label=f"Nói ít nhất {seconds} giây (không tính im lặng ở đầu và cuối)",
    )


def _max_pause(seconds: float) -> Mission:
    shown = f"{seconds:g}".replace(".", ",")
    return Mission(
        kind=MissionKind.MAX_PAUSE,
        target=seconds,
        label=f"Không có khoảng lặng nào dài quá {shown} giây",
    )


def _use(n: int, words: tuple[str, ...], what: str) -> Mission:
    # The word list is shown as chips right under the mission on the task page;
    # repeating it in the sentence would double its length and add nothing.
    return Mission(
        kind=MissionKind.USE_WORDS, target=n, words=words, label=f"Dùng ít nhất {n} {what}"
    )


def _read(ratio: float) -> Mission:
    return Mission(
        kind=MissionKind.READ_ALOUD,
        target=ratio,
        label=f"Máy nhận ra ít nhất {round(ratio * 100)}% số từ trong đoạn văn",
    )


PRACTICE_TASKS: tuple[PracticeSeed, ...] = (
    # ------------------------------------------------------------ fluency
    PracticeSeed(
        task_id="PR-FLU-A2",
        criterion=Criterion.FLUENCY,
        band=Band.A2,
        title="Nói liền mạch về một ngày của bạn",
        prompt_text=(
            "Kể về một ngày bình thường của bạn: buổi sáng, ở trường, buổi tối. "
            "Cố nói liên tục, câu ngắn cũng được."
        ),
        missions=(_speak(30), _max_pause(3.0)),
        tips=(
            "Bí từ thì nói “well…” hoặc “let me think…” thay vì im lặng.",
            "Câu ngắn và đơn giản vẫn tốt hơn một câu dài bị đứt quãng.",
        ),
        min_seconds=30,
        max_seconds=60,
        part=TaskPart.P4,
    ),
    PracticeSeed(
        task_id="PR-FLU-B1",
        criterion=Criterion.FLUENCY,
        band=Band.B1,
        title="Kể một chuyến đi đáng nhớ",
        prompt_text=(
            "Kể về một chuyến đi hoặc một ngày đáng nhớ: bạn đi đâu, với ai, chuyện gì "
            "đã xảy ra và bạn cảm thấy thế nào."
        ),
        missions=(_speak(45), _max_pause(2.0)),
        tips=(
            "Nghĩ trước ba ý: đi đâu, chuyện gì xảy ra, cảm nghĩ của bạn.",
            "Dùng cụm câu giờ tự nhiên: “you know”, “I mean”, “the thing is”.",
        ),
        min_seconds=45,
        max_seconds=75,
        part=TaskPart.P4,
    ),
    PracticeSeed(
        task_id="PR-FLU-B2",
        criterion=Criterion.FLUENCY,
        band=Band.B2,
        title="Giữ nhịp khi nêu quan điểm",
        prompt_text=(
            "Sinh viên có nên đi làm thêm khi đang học không? Nêu quan điểm, giải thích "
            "và cho ví dụ."
        ),
        missions=(_speak(60), _max_pause(1.5)),
        tips=(
            "Nói ý chính trước, chi tiết sau, để không phải dừng lại tìm ý.",
            "Khi cần nghĩ, nối bằng “what I mean is…” thay vì ngừng hẳn.",
        ),
        min_seconds=60,
        max_seconds=90,
        part=TaskPart.P3,
    ),
    # ------------------------------------------------------------ coherence
    PracticeSeed(
        task_id="PR-COH-A2",
        criterion=Criterion.COHERENCE,
        band=Band.A2,
        title="Nối ý bằng and, but, because",
        prompt_text=("Nói về một món ăn bạn thích và một món bạn không thích. Giải thích vì sao."),
        missions=(
            _use(3, ("and", "but", "because", "so", "also"), "từ nối khác nhau"),
            _speak(30),
        ),
        tips=(
            "Mỗi lý do nối bằng “because”, mỗi ý trái ngược nối bằng “but”.",
            "Kết bằng “so” để nói điều bạn rút ra.",
        ),
        min_seconds=30,
        max_seconds=60,
        part=TaskPart.P3,
    ),
    PracticeSeed(
        task_id="PR-COH-B1",
        criterion=Criterion.COHERENCE,
        band=Band.B1,
        title="Hướng dẫn theo từng bước",
        prompt_text="Hướng dẫn cách nấu một món ăn bạn biết làm, nói lần lượt từng bước.",
        missions=(
            _use(
                3,
                ("first", "second", "then", "next", "after that", "finally"),
                "từ chỉ trình tự khác nhau",
            ),
            _speak(40),
        ),
        tips=(
            "Mở đầu bằng tên món và nguyên liệu, rồi mới vào các bước.",
            "Kết thúc bằng “finally” để người nghe biết đã hết các bước.",
        ),
        min_seconds=40,
        max_seconds=75,
        part=TaskPart.P4,
    ),
    PracticeSeed(
        task_id="PR-COH-B2",
        criterion=Criterion.COHERENCE,
        band=Band.B2,
        title="Lập luận hai mặt rồi kết luận",
        prompt_text=(
            "Sau khi tốt nghiệp, nên sống ở thành phố lớn hay ở quê? Nêu cả hai mặt rồi "
            "đưa ra kết luận của bạn."
        ),
        missions=(
            _use(
                2,
                ("however", "on the other hand", "although", "whereas", "in contrast"),
                "cụm đối lập khác nhau",
            ),
            _use(1, ("in conclusion", "to sum up", "overall", "all in all"), "cụm kết luận"),
            _speak(50),
        ),
        tips=(
            "Bố cục gợi ý: mặt lợi → “however” → mặt hại → “in conclusion”.",
            "Câu kết luận nói rõ bạn chọn bên nào và vì sao.",
        ),
        min_seconds=50,
        max_seconds=90,
        part=TaskPart.P3,
    ),
    # ------------------------------------------------------------ range
    PracticeSeed(
        task_id="PR-RAN-A2",
        criterion=Criterion.RANGE,
        band=Band.A2,
        title="Tả căn phòng của bạn",
        prompt_text=(
            "Tả căn phòng của bạn: có những đồ vật gì, chúng ở đâu, bạn thích điều gì ở "
            "căn phòng đó."
        ),
        missions=(
            _use(
                5,
                (
                    "bed",
                    "desk",
                    "window",
                    "chair",
                    "lamp",
                    "shelf",
                    "wardrobe",
                    "wall",
                    "door",
                    "comfortable",
                    "quiet",
                    "bright",
                ),
                "từ trong danh sách gợi ý",
            ),
            Mission(kind=MissionKind.UNIQUE_WORDS, target=35, label="Dùng ít nhất 35 từ khác nhau"),
        ),
        tips=(
            "Nói vị trí bằng “next to”, “in front of”, “on the left”.",
            "Thêm một tính từ cho mỗi đồ vật: “a small desk”, “a bright lamp”.",
        ),
        min_seconds=30,
        max_seconds=60,
        part=TaskPart.P4,
    ),
    PracticeSeed(
        task_id="PR-RAN-B1",
        criterion=Criterion.RANGE,
        band=Band.B1,
        title="Tả một người bạn ngưỡng mộ",
        prompt_text=(
            "Tả một người bạn ngưỡng mộ: người đó là ai, tính cách thế nào và vì sao bạn ngưỡng mộ."
        ),
        missions=(
            _use(
                4,
                (
                    "friendly",
                    "generous",
                    "patient",
                    "honest",
                    "confident",
                    "creative",
                    "reliable",
                    "helpful",
                    "admire",
                    "inspire",
                ),
                "từ trong danh sách gợi ý",
            ),
            Mission(kind=MissionKind.UNIQUE_WORDS, target=55, label="Dùng ít nhất 55 từ khác nhau"),
        ),
        tips=(
            "Mỗi tính từ đi kèm một ví dụ nhỏ: “She is patient. For example, …”.",
            "Tránh lặp “very good”; chọn từ chính xác hơn trong danh sách.",
        ),
        min_seconds=40,
        max_seconds=75,
        part=TaskPart.P4,
    ),
    PracticeSeed(
        task_id="PR-RAN-B2",
        criterion=Criterion.RANGE,
        band=Band.B2,
        title="Mạng xã hội và cách người trẻ giao tiếp",
        prompt_text=(
            "Mạng xã hội đang thay đổi cách người trẻ giao tiếp như thế nào? Nêu tác "
            "động tích cực và tiêu cực."
        ),
        missions=(
            _use(
                5,
                (
                    "influence",
                    "impact",
                    "interaction",
                    "platform",
                    "privacy",
                    "isolated",
                    "addicted",
                    "benefit",
                    "drawback",
                    "essential",
                    "constantly",
                ),
                "từ trong danh sách gợi ý",
            ),
            Mission(kind=MissionKind.UNIQUE_WORDS, target=75, label="Dùng ít nhất 75 từ khác nhau"),
        ),
        tips=(
            "Thay từ quen bằng từ chính xác hơn: “good” → “beneficial”, “bad” → “harmful”.",
            "Mỗi tác động kèm một ví dụ cụ thể từ trải nghiệm của bạn.",
        ),
        min_seconds=50,
        max_seconds=90,
        part=TaskPart.P3,
    ),
    # ------------------------------------------------------------ accuracy
    PracticeSeed(
        task_id="PR-ACC-A2",
        criterion=Criterion.ACCURACY,
        band=Band.A2,
        title="Kể lại cuối tuần (thì quá khứ)",
        prompt_text="Kể lại cuối tuần vừa rồi bạn đã làm những gì, theo thứ tự thời gian.",
        missions=(
            Mission(
                kind=MissionKind.PAST_VERBS,
                target=5,
                label="Dùng ít nhất 5 động từ khác nhau ở thì quá khứ (went, had, watched…)",
            ),
            _speak(30),
        ),
        tips=(
            "Động từ có quy tắc thêm -ed: watched, played; bất quy tắc: went, had, saw.",
            "Mở đầu bằng “Last weekend, I…” để giữ thì quá khứ cho cả bài.",
        ),
        min_seconds=30,
        max_seconds=60,
        part=TaskPart.P4,
    ),
    PracticeSeed(
        task_id="PR-ACC-B1",
        criterion=Criterion.ACCURACY,
        band=Band.B1,
        title="Nếu… thì… (câu điều kiện)",
        prompt_text=(
            "Nếu bạn có một tháng nghỉ và đủ tiền, bạn sẽ làm gì? Nếu kế hoạch đó không "
            "thành thì bạn sẽ làm gì thay?"
        ),
        missions=(
            Mission(
                kind=MissionKind.CONDITIONALS,
                target=2,
                label="Dùng ít nhất 2 câu điều kiện có “if” đi kèm will, would hoặc could",
            ),
            _speak(40),
        ),
        tips=(
            "“If I had a month off, I would travel…”: vế “if” lùi về quá khứ, vế kia dùng “would”.",
            "Câu điều kiện có thật thì dùng “will”: “If it rains, I will stay at home.”",
        ),
        min_seconds=40,
        max_seconds=75,
        part=TaskPart.P3,
    ),
    PracticeSeed(
        task_id="PR-ACC-B2",
        criterion=Criterion.ACCURACY,
        band=Band.B2,
        title="Câu phức: kể một quyết định khó",
        prompt_text=(
            "Kể về một quyết định khó khăn bạn từng đưa ra: điều gì khiến bạn phân vân "
            "và bạn đã học được gì."
        ),
        missions=(
            _use(
                3,
                ("although", "even though", "unless", "whereas", "which", "who", "whose"),
                "từ nối mệnh đề khác nhau",
            ),
            _speak(50),
        ),
        tips=(
            "Ghép hai câu đơn thành một câu phức: “I chose IT, although my parents wanted "
            "me to study business.”",
            "Dùng “which” để nói thêm về điều vừa kể: “…, which made me nervous.”",
        ),
        min_seconds=50,
        max_seconds=90,
        part=TaskPart.P4,
    ),
    # ------------------------------------------------------------ phonology
    PracticeSeed(
        task_id="PR-PHO-A2",
        criterion=Criterion.PHONOLOGY,
        band=Band.A2,
        title="Đọc to: giới thiệu bản thân",
        prompt_text="Đọc to, rõ đoạn văn dưới đây với tốc độ bình thường.",
        missions=(_read(0.80),),
        tips=(
            "Đọc chậm và rõ từng từ, nhất là âm cuối: “lives”, “watched”.",
            "Không cần giống giọng bản ngữ; chỉ cần máy nghe ra đúng từ.",
        ),
        min_seconds=30,
        max_seconds=75,
        part=TaskPart.P4,
        reference_text=(
            "My name is Lan, and I am a first-year student. I live with my family in a "
            "small house near the market. Every morning, I take the bus to school. I like "
            "English because I enjoy watching films and listening to songs in English. In "
            "my free time, I play badminton with my friends or help my mother cook dinner. "
            "On Sundays, we often visit my grandparents."
        ),
    ),
    PracticeSeed(
        task_id="PR-PHO-B1",
        criterion=Criterion.PHONOLOGY,
        band=Band.B1,
        title="Đọc to: thông báo của câu lạc bộ",
        prompt_text="Đọc to, rõ đoạn thông báo dưới đây như đang nói trước cả lớp.",
        missions=(_read(0.85),),
        tips=(
            "Ngắt hơi ở dấu phẩy và dấu chấm, không ngắt giữa cụm từ.",
            "Nhấn rõ từ mang nội dung: “Thursday”, “library”, “notebook”.",
        ),
        min_seconds=30,
        max_seconds=75,
        part=TaskPart.P4,
        reference_text=(
            "Hello everyone, and welcome to the English speaking club. This month, we are "
            "going to meet every Thursday evening in the library on the second floor. Each "
            "meeting starts with a short game, and then we talk in small groups. If you "
            "cannot join a meeting, please send a message to the club leader before "
            "Wednesday. Remember to bring a notebook, because we will share useful "
            "expressions at the end of each session."
        ),
    ),
    PracticeSeed(
        task_id="PR-PHO-B2",
        criterion=Criterion.PHONOLOGY,
        band=Band.B2,
        title="Đọc to: đoạn báo ngắn",
        prompt_text="Đọc to đoạn báo dưới đây, giữ nhịp đều ở những câu dài.",
        missions=(_read(0.90),),
        tips=(
            "Đọc liền một cụm: “which means we wake up less rested”.",
            "Bật rõ âm cuối /s/, /t/, /d/: “screens”, “concerned”, “increasingly”.",
        ),
        min_seconds=30,
        max_seconds=90,
        part=TaskPart.P4,
        reference_text=(
            "Many young people now spend several hours a day on their phones, and "
            "researchers are increasingly concerned about the effect on sleep. Bright "
            "screens late at night can delay the moment our body feels tired, which means "
            "we wake up less rested. However, the solution is not necessarily to give up "
            "technology altogether. Simple habits, such as switching off notifications in "
            "the evening or keeping the phone outside the bedroom, can make a noticeable "
            "difference within a few weeks."
        ),
    ),
)


def practice_task_id(criterion: Criterion, band: Band) -> str:
    """Practice task id for one criterion at one band. The bank fills all 15 cells."""
    return next(t.task_id for t in PRACTICE_TASKS if t.criterion is criterion and t.band is band)
