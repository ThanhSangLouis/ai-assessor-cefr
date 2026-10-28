"""The sample path shipped with a fresh install (D025, laid out by topic in D027).

Six levels (A1 to C2, D059), each going through units on different topics. The
lessons are sixteen written in full -- three here, thirteen in `seed_topics` --
and fifteen built from the fifteen D023 practice tasks, so nothing a learner
already practised disappears. All of it is SAMPLE content: written by the
development team, marked `sample`, and waiting for a teacher of the Faculty of
Foreign Languages to review it before it is used with real students. Texts use
American spelling and no digits, so the linter has nothing to say about them.

Ids are fixed strings so that re-seeding never duplicates a lesson and every
stored attempt keeps pointing at its step.
"""

from __future__ import annotations

from aicefr.contracts import Band, MissionKind
from aicefr.lessons.generate import MARKERS, OUTLINE_POINTS, PREP_SECONDS
from aicefr.lessons.model import Lesson, Step, StepKind, Strictness, Topic
from aicefr.lessons.seed_topics import topic_lessons
from aicefr.practice.bank import PRACTICE_TASKS, PracticeSeed

SAMPLE_PATH_ID = "path-sample"
# Bump when SAMPLE_UNITS or the lessons in them change, so an installation made
# with an older layout is brought up to date once (LessonRepository.seed_sample).
# 1: one unit per band (D025). 2: units by topic within each band (D027).
# 3: the path covers A1 to C2 (D059).
SAMPLE_LAYOUT = 3
SAMPLE_PATH = {
    "path_id": SAMPLE_PATH_ID,
    "title": "Lộ trình mẫu: Nói tiếng Anh A1 → C2",
    "description": (
        "Sáu bậc từ Làm quen tới Thành thạo; mỗi bậc đi qua nhiều chủ đề như giáo dục, du "
        "lịch, nghề nghiệp, công nghệ. Mỗi bài đi từ đọc theo văn bản có từ gợi ý tới nói tự "
        "do. Nội dung mẫu, chờ giảng viên Khoa Ngoại ngữ duyệt."
    ),
    "band_from": Band.A1,
    "band_to": Band.C2,
}


def _unit(unit_id: str, band: Band, topic: Topic, title: str, function: str) -> dict:
    return {"unit_id": unit_id, "band": band, "topic": topic, "title": title, "function": function}


# The path, in order: three levels, each going through several topics, so the
# level rises steadily while the subject keeps changing. The three units of the
# first layout keep their ids, so attempts made against them stay in place.
SAMPLE_UNITS = [
    _unit(
        "unit-a1-basics",
        Band.A1,
        Topic.DAILY_LIFE,
        "Làm quen",
        "Giới thiệu bản thân, căn phòng và buổi sáng của bạn",
    ),
    _unit(
        "unit-a1-people",
        Band.A1,
        Topic.PEOPLE,
        "Gia đình và bạn bè",
        "Nói về người thân, bạn bè và những gì họ thích",
    ),
    _unit(
        "unit-sample-a2",
        Band.A2,
        Topic.DAILY_LIFE,
        "Đời sống hằng ngày",
        "Tả nơi ở, kể một ngày và thói quen của bạn",
    ),
    _unit(
        "unit-a2-education",
        Band.A2,
        Topic.EDUCATION,
        "Trường lớp",
        "Kể về ngày học, môn học và bạn cùng lớp",
    ),
    _unit("unit-a2-food", Band.A2, Topic.FOOD, "Ăn uống", "Nói về món ăn và bữa ăn bạn thích"),
    _unit("unit-a2-travel", Band.A2, Topic.TRAVEL, "Đi chơi", "Kể một chuyến đi ngắn bằng câu đơn"),
    _unit("unit-a2-career", Band.A2, Topic.CAREER, "Công việc", "Nói về nghề bạn muốn làm"),
    _unit(
        "unit-a2-health",
        Band.A2,
        Topic.HEALTH,
        "Sức khoẻ",
        "Nói về thói quen ăn, ngủ và tập luyện",
    ),
    _unit(
        "unit-sample-b1",
        Band.B1,
        Topic.TRAVEL,
        "Du lịch",
        "Kể một trải nghiệm theo trình tự, có cảm xúc",
    ),
    _unit(
        "unit-b1-education",
        Band.B1,
        Topic.EDUCATION,
        "Đời sống sinh viên",
        "Kể về hoạt động ở trường, đọc một thông báo",
    ),
    _unit(
        "unit-b1-career",
        Band.B1,
        Topic.CAREER,
        "Việc làm thêm",
        "Kể kinh nghiệm làm việc, nói về dự định",
    ),
    _unit(
        "unit-b1-food",
        Band.B1,
        Topic.FOOD,
        "Ẩm thực quê hương",
        "Giới thiệu một món ăn, hướng dẫn theo từng bước",
    ),
    _unit(
        "unit-b1-people",
        Band.B1,
        Topic.PEOPLE,
        "Con người",
        "Tả một người và nói vì sao bạn quý trọng họ",
    ),
    _unit(
        "unit-b1-technology",
        Band.B1,
        Topic.TECHNOLOGY,
        "Công nghệ",
        "Nói về điện thoại và thói quen dùng thiết bị",
    ),
    _unit(
        "unit-sample-b2",
        Band.B2,
        Topic.EDUCATION,
        "Giáo dục",
        "Nêu quan điểm về cách học, có lý do và ví dụ",
    ),
    _unit(
        "unit-b2-technology",
        Band.B2,
        Topic.TECHNOLOGY,
        "Công nghệ và xã hội",
        "Bàn về trí tuệ nhân tạo và mạng xã hội",
    ),
    _unit(
        "unit-b2-environment",
        Band.B2,
        Topic.ENVIRONMENT,
        "Môi trường",
        "Nêu vấn đề, nguyên nhân và giải pháp",
    ),
    _unit(
        "unit-b2-career",
        Band.B2,
        Topic.CAREER,
        "Thế giới việc làm",
        "Cân nhắc lợi và hại, kể một quyết định khó",
    ),
    _unit(
        "unit-b2-society",
        Band.B2,
        Topic.SOCIETY,
        "Đô thị và tin tức",
        "So sánh, lập luận hai mặt, đọc một bản tin ngắn",
    ),
    _unit(
        "unit-b2-health",
        Band.B2,
        Topic.HEALTH,
        "Sức khoẻ tinh thần",
        "Nói về áp lực học tập và cách vượt qua",
    ),
    _unit(
        "unit-c1-society",
        Band.C1,
        Topic.SOCIETY,
        "Lập luận về xã hội",
        "Trình bày, phân tích nguyên nhân và hệ quả, bảo vệ lập trường",
    ),
    _unit(
        "unit-c1-environment",
        Band.C1,
        Topic.ENVIRONMENT,
        "Môi trường và trách nhiệm",
        "Dùng từ chính xác và câu điều kiện để cân nhắc lựa chọn",
    ),
    _unit(
        "unit-c2-ideas",
        Band.C2,
        Topic.TECHNOLOGY,
        "Ý tưởng và sắc thái",
        "Tổng hợp quan điểm, diễn đạt sắc thái nghĩa tinh tế",
    ),
    _unit(
        "unit-c2-reflection",
        Band.C2,
        Topic.PEOPLE,
        "Suy ngẫm và trải nghiệm",
        "Kể và bình luận với cấu trúc nhấn mạnh, đọc văn chính luận",
    ),
]

# Which lessons go in which unit, in order. Written lessons first, then the
# lessons built from the D023 practice tasks on the same theme.
SAMPLE_LAYOUT_LESSONS: dict[str, list[str]] = {
    "unit-a1-basics": ["lesson-pr-flu-a1", "lesson-pr-ran-a1", "lesson-pr-acc-a1"],
    "unit-a1-people": ["lesson-pr-coh-a1", "lesson-pr-pho-a1"],
    "unit-sample-a2": [
        "lesson-a2-neighborhood",
        "lesson-pr-flu-a2",
        "lesson-pr-ran-a2",
        "lesson-pr-acc-a2",
    ],
    "unit-a2-education": ["lesson-a2-school", "lesson-pr-pho-a2"],
    "unit-a2-food": ["lesson-a2-breakfast", "lesson-pr-coh-a2"],
    "unit-a2-travel": ["lesson-a2-beach"],
    "unit-a2-career": ["lesson-a2-dream-job"],
    "unit-a2-health": ["lesson-a2-healthy"],
    "unit-sample-b1": ["lesson-b1-trip", "lesson-pr-flu-b1"],
    "unit-b1-education": ["lesson-b1-club", "lesson-pr-pho-b1"],
    "unit-b1-career": ["lesson-b1-part-time", "lesson-pr-acc-b1"],
    "unit-b1-food": ["lesson-b1-home-dish", "lesson-pr-coh-b1"],
    "unit-b1-people": ["lesson-pr-ran-b1"],
    "unit-b1-technology": ["lesson-b1-phone"],
    "unit-sample-b2": ["lesson-b2-online", "lesson-pr-flu-b2"],
    "unit-b2-technology": ["lesson-b2-ai", "lesson-pr-ran-b2"],
    "unit-b2-environment": ["lesson-b2-plastic"],
    "unit-b2-career": ["lesson-b2-remote", "lesson-pr-acc-b2"],
    "unit-b2-society": ["lesson-pr-coh-b2", "lesson-pr-pho-b2"],
    "unit-b2-health": ["lesson-b2-stress"],
    "unit-c1-society": ["lesson-pr-flu-c1", "lesson-pr-coh-c1", "lesson-pr-pho-c1"],
    "unit-c1-environment": ["lesson-pr-ran-c1", "lesson-pr-acc-c1"],
    "unit-c2-ideas": ["lesson-pr-flu-c2", "lesson-pr-coh-c2", "lesson-pr-ran-c2"],
    "unit-c2-reflection": ["lesson-pr-acc-c2", "lesson-pr-pho-c2"],
}


def _ids(lesson: Lesson) -> Lesson:
    """Give every step a fixed id derived from the lesson id."""
    for i, step in enumerate(lesson.steps, 1):
        step.step_id = f"{lesson.lesson_id}-s{i}"
    return lesson


def _a2_neighborhood() -> Lesson:
    text = (
        "I live in a small apartment near the city center. My street is quiet, but there are "
        "many shops and a park nearby. Every morning, I walk to the bus stop. I like my "
        "neighborhood because the people are friendly and the food is cheap. The only problem "
        "is the traffic in the evening."
    )
    keywords = ["apartment", "quiet", "nearby", "neighborhood", "friendly", "traffic"]
    prompt = (
        "Tả một nơi bạn hay đến: quán cà phê, chợ hay khuôn viên trường. Nó ở đâu, có gì, "
        "vì sao bạn thích?"
    )
    return _ids(
        Lesson(
            lesson_id="lesson-a2-neighborhood",
            title="Khu phố của tôi",
            summary="Tả nơi bạn sống: ở đâu, gần đó có gì, bạn thích và không thích điều gì.",
            band=Band.A2,
            model_text=text,
            keywords=keywords,
            sample=True,
            steps=[
                Step(
                    kind=StepKind.READ_ALOUD,
                    instruction=(
                        "Nghe giọng mẫu (nếu có) rồi đọc to cả đoạn. Từ gợi ý được tô đậm; "
                        "đọc rõ, đúng nhịp, không cần nhanh."
                    ),
                    text=text,
                    hint_words=keywords,
                    max_seconds=60,
                ),
                Step(
                    kind=StepKind.REPEAT,
                    instruction=(
                        "Nghe câu mẫu một lần rồi nhắc lại. Lần thứ hai thử không nhìn chữ."
                    ),
                    text="I like my neighborhood because the people are friendly.",
                    max_seconds=15,
                ),
                Step(
                    kind=StepKind.GAP,
                    instruction="Đọc to câu, tự chọn từ cho mỗi chỗ trống. Có từ không dùng đến.",
                    text="My street is ___, but there are many shops and a park ___.",
                    answers=["quiet", "nearby"],
                    hint_words=["quiet", "nearby", "busy", "far"],
                    max_seconds=20,
                ),
                Step(
                    kind=StepKind.LOOK_UP,
                    instruction="Đọc câu trong lúc nó còn hiện. Khi chữ ẩn đi, nói lại câu.",
                    text="The only problem is the traffic in the evening.",
                    show_seconds=5,
                    max_seconds=15,
                ),
                Step(
                    kind=StepKind.KEYWORDS,
                    instruction="Nói một câu về buổi sáng của bạn có các từ dưới đây.",
                    keywords=["morning", "walk", "bus stop"],
                    min_words=6,
                    max_seconds=25,
                ),
                Step(
                    kind=StepKind.OUTLINE,
                    instruction="Chuẩn bị một phút, rồi nói theo dàn ý. Dùng first, then, finally.",
                    text=(
                        "Where do you live? What is near your home? What do you like or dislike "
                        "about it?"
                    ),
                    outline=["Bạn sống ở đâu", "Gần nhà có gì", "Bạn thích và không thích gì"],
                    markers=MARKERS[Band.A2],
                    prep_seconds=60,
                    min_seconds=30,
                    max_seconds=60,
                ),
                Step(
                    kind=StepKind.FREE,
                    instruction=(
                        "Nói tự do, ba lượt. Mỗi lượt ngắn hơn lượt trước: nói lại cùng nội "
                        "dung, nhanh và ít ngừng hơn."
                    ),
                    text=prompt,
                    rounds=[45, 35, 25],
                    max_seconds=45,
                ),
            ],
        )
    )


def _b1_trip() -> Lesson:
    text = (
        "Last summer, I traveled to Da Lat with two of my classmates. We took a night bus, so "
        "we arrived very early in the morning. At first, the weather was cold and foggy, but "
        "the view of the hills was amazing. We spent the day visiting flower gardens and trying "
        "local food at the night market. In the evening, it started to rain heavily, and we got "
        "lost on the way back to our hotel. Luckily, a friendly shop owner showed us the way. "
        "I will never forget that trip."
    )
    keywords = ["traveled", "arrived", "weather", "visiting", "lost", "forget"]
    prompt = (
        "Kể về một chuyến đi hoặc một ngày đáng nhớ của bạn: đi đâu, với ai, chuyện gì xảy ra, "
        "bạn cảm thấy thế nào."
    )
    return _ids(
        Lesson(
            lesson_id="lesson-b1-trip",
            title="Một chuyến đi đáng nhớ",
            summary="Kể một trải nghiệm theo trình tự thời gian, có cảm xúc và kết thúc rõ.",
            band=Band.B1,
            model_text=text,
            keywords=keywords,
            sample=True,
            steps=[
                Step(
                    kind=StepKind.READ_ALOUD,
                    instruction="Đọc to cả đoạn. Chú ý các động từ ở thì quá khứ được tô đậm.",
                    text=text,
                    hint_words=keywords,
                    max_seconds=90,
                ),
                Step(
                    kind=StepKind.GAP,
                    instruction="Đọc to hai câu, tự chọn từ cho mỗi chỗ trống.",
                    text=(
                        "At first, the ___ was cold and foggy. In the evening, we got ___ on "
                        "the way back to our hotel."
                    ),
                    answers=["weather", "lost"],
                    hint_words=["weather", "lost", "traffic", "tired"],
                    max_seconds=25,
                ),
                Step(
                    kind=StepKind.LOOK_UP,
                    instruction="Đọc câu trong lúc nó còn hiện. Khi chữ ẩn đi, nói lại câu.",
                    text="We took a night bus, so we arrived very early in the morning.",
                    show_seconds=6,
                    max_seconds=18,
                ),
                Step(
                    kind=StepKind.KEYWORDS,
                    instruction="Nói hai câu về một chuyến đi của bạn có các từ dưới đây.",
                    keywords=["trip", "first", "remember"],
                    min_words=10,
                    max_seconds=35,
                ),
                Step(
                    kind=StepKind.STARTER,
                    instruction="Trả lời câu hỏi, bắt đầu bằng khung câu cho sẵn.",
                    text="How did you feel at the end of the trip?",
                    starter="At the end of the trip, I felt",
                    min_words=5,
                    max_seconds=30,
                ),
                Step(
                    kind=StepKind.OUTLINE,
                    instruction="Chuẩn bị 30 giây, rồi kể theo dàn ý. Dùng từ nối để chuyển ý.",
                    text="Tell the story of a memorable trip or day.",
                    outline=OUTLINE_POINTS[Band.B1],
                    markers=MARKERS[Band.B1],
                    prep_seconds=30,
                    min_seconds=45,
                    max_seconds=75,
                ),
                Step(
                    kind=StepKind.FREE,
                    instruction="Kể tự do, ba lượt, mỗi lượt ngắn hơn lượt trước.",
                    text=prompt,
                    rounds=[60, 45, 35],
                    max_seconds=60,
                ),
            ],
        )
    )


def _b2_online() -> Lesson:
    text = (
        "Many students now take at least some of their courses online. In my opinion, online "
        "learning has clear advantages. It saves time, because students do not need to travel, "
        "and they can watch lectures again when something is difficult. On the other hand, it "
        "can be hard to stay motivated without classmates around you, and some practical skills "
        "are difficult to learn through a screen. As a result, I believe the best solution is a "
        "combination of both. Universities should keep important discussions and practical "
        "sessions on campus, while simple lectures can be recorded and shared online."
    )
    keywords = [
        "advantages",
        "motivated",
        "on the other hand",
        "as a result",
        "combination",
        "practical",
    ]
    prompt = (
        "Nêu và bảo vệ quan điểm: có nên cho sinh viên năm nhất học phần lớn các môn trực tuyến "
        "không? Đưa ra một lý do, một ví dụ và một ý phản biện."
    )
    return _ids(
        Lesson(
            lesson_id="lesson-b2-online",
            title="Học trực tuyến hay học trên lớp",
            summary="Nêu quan điểm, đưa lý do và ví dụ, xét mặt trái rồi kết luận.",
            band=Band.B2,
            model_text=text,
            keywords=keywords,
            sample=True,
            steps=[
                Step(
                    kind=StepKind.READ_ALOUD,
                    instruction="Đọc to cả đoạn. Chú ý các cụm từ nối lập luận được tô đậm.",
                    text=text,
                    hint_words=keywords,
                    max_seconds=90,
                ),
                Step(
                    kind=StepKind.LOOK_UP,
                    instruction="Đọc câu trong lúc nó còn hiện. Khi chữ ẩn đi, nói lại câu.",
                    text="As a result, I believe the best solution is a combination of both.",
                    show_seconds=6,
                    max_seconds=18,
                ),
                Step(
                    kind=StepKind.KEYWORDS,
                    instruction="Nói hai câu nêu ý của bạn về học trực tuyến có các từ dưới đây.",
                    keywords=["advantage", "motivated", "combination"],
                    min_words=12,
                    max_seconds=40,
                ),
                Step(
                    kind=StepKind.STARTER,
                    instruction="Trả lời câu hỏi, bắt đầu bằng khung câu cho sẵn.",
                    text="What is the main disadvantage of online learning for you?",
                    starter="The main disadvantage is that",
                    min_words=8,
                    max_seconds=40,
                ),
                Step(
                    kind=StepKind.OUTLINE,
                    instruction=(
                        "Chuẩn bị 15 giây, rồi lập luận theo dàn ý: quan điểm, lý do và ví dụ, "
                        "phản biện, kết luận."
                    ),
                    text="Should first-year students take most of their courses online?",
                    outline=OUTLINE_POINTS[Band.B2],
                    markers=MARKERS[Band.B2],
                    prep_seconds=15,
                    min_seconds=60,
                    max_seconds=90,
                ),
                Step(
                    kind=StepKind.FREE,
                    instruction=(
                        "Nói tự do hai lượt cùng thời gian. Lượt hai giữ nguyên ý chính và thêm "
                        "một ví dụ hay một ý phản biện."
                    ),
                    text=prompt,
                    rounds=[75, 75],
                    max_seconds=75,
                    strictness=Strictness.NORMAL,
                ),
            ],
        )
    )


# Free-speaking prompts for the three read-aloud tasks of D023, whose own prompt
# only asks to read the passage.
_READ_FREE = {
    "PR-PHO-A2": "Giới thiệu bản thân bằng lời của bạn: tên, việc học, gia đình, sở thích.",
    "PR-PHO-B1": (
        "Thông báo một sự kiện của lớp hay câu lạc bộ của bạn: sự kiện gì, khi nào, ở đâu, "
        "cần chuẩn bị gì."
    ),
    "PR-PHO-B2": "Tóm tắt lại đoạn báo vừa đọc bằng lời của bạn, rồi nêu ý kiến của bạn về nó.",
}


def _round(x: float) -> int:
    return max(10, int(round(x / 5) * 5))


def from_practice_task(seed: PracticeSeed) -> Lesson:
    """A short lesson around one D023 task: a guided step, then its prompt as free speech."""
    steps: list[Step] = []
    kinds = {m.kind for m in seed.missions}
    words = next((m.words for m in seed.missions if m.kind is MissionKind.USE_WORDS), ())
    if seed.reference_text:
        steps.append(
            Step(
                kind=StepKind.READ_ALOUD,
                instruction="Đọc to cả đoạn, rõ và đúng nhịp.",
                text=seed.reference_text,
                max_seconds=min(180, seed.max_seconds + 30),
            )
        )
        prompt = _READ_FREE.get(seed.task_id, seed.prompt_text)
    else:
        prompt = seed.prompt_text
        if words:
            steps.append(
                Step(
                    kind=StepKind.KEYWORDS,
                    instruction="Nói hai câu ngắn về đề bài có các từ dưới đây.",
                    keywords=list(words)[:3],
                    min_words=8,
                    max_seconds=35,
                )
            )
        elif MissionKind.PAST_VERBS in kinds:
            steps.append(
                Step(
                    kind=StepKind.STARTER,
                    instruction="Trả lời câu hỏi, bắt đầu bằng khung câu cho sẵn.",
                    text="What did you do last weekend?",
                    starter="Last weekend, I",
                    min_words=6,
                    max_seconds=30,
                )
            )
        elif MissionKind.CONDITIONALS in kinds:
            steps.append(
                Step(
                    kind=StepKind.STARTER,
                    instruction="Trả lời câu hỏi, bắt đầu bằng khung câu cho sẵn.",
                    text="What would you do if you had a free day?",
                    starter="If I had a free day, I would",
                    min_words=4,
                    max_seconds=30,
                )
            )
        else:
            steps.append(
                Step(
                    kind=StepKind.OUTLINE,
                    instruction="Chuẩn bị, rồi nói theo dàn ý với từ nối để chuyển ý.",
                    text=prompt,
                    outline=OUTLINE_POINTS[seed.band],
                    markers=MARKERS[seed.band],
                    prep_seconds=PREP_SECONDS[seed.band],
                    min_seconds=seed.min_seconds,
                    max_seconds=seed.max_seconds,
                )
            )
    top = seed.max_seconds
    steps.append(
        Step(
            kind=StepKind.FREE,
            instruction=(
                "Nói tự do, ba lượt. Mỗi lượt ngắn hơn lượt trước: nói lại cùng nội dung, "
                "nhanh và ít ngừng hơn."
            ),
            text=prompt,
            rounds=[_round(top), _round(top * 0.75), _round(top * 0.55)],
            max_seconds=top,
            missions=[m for m in seed.missions if m.kind is not MissionKind.READ_ALOUD],
            tip=seed.tips[0] if seed.tips else "",
        )
    )
    return _ids(
        Lesson(
            lesson_id=f"lesson-{seed.task_id.lower()}",
            title=seed.title,
            summary=seed.prompt_text,
            band=seed.band,
            criterion=seed.criterion,
            steps=steps,
            sample=True,
        )
    )


def sample_lessons() -> dict[str, list[Lesson]]:
    """Lessons of the sample path by unit id, in path order."""
    every = {lesson.lesson_id: lesson for lesson in (_a2_neighborhood(), _b1_trip(), _b2_online())}
    every.update(topic_lessons())
    for seed in PRACTICE_TASKS:
        lesson = from_practice_task(seed)
        every[lesson.lesson_id] = lesson
    return {uid: [every[lid] for lid in ids] for uid, ids in SAMPLE_LAYOUT_LESSONS.items()}
