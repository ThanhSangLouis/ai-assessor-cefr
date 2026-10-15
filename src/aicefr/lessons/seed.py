"""Stable sample learning path and idempotent catalogue seed."""

from __future__ import annotations

from datetime import datetime

from aicefr.contracts import Band
from aicefr.lessons.generate import build_lesson
from aicefr.lessons.model import LearningPath, LearningUnit, Lesson, Topic
from aicefr.lessons.seed_topics import topic_lessons
from aicefr.practice.bank import PRACTICE_MISSIONS
from aicefr.storage.learning import LearningRepository

SAMPLE_PATH_ID = "path-sample"
SAMPLE_LAYOUT = 2
SAMPLE_SEED_VERSION = "sample-layout-2"

SAMPLE_PATH = LearningPath(
    path_id=SAMPLE_PATH_ID,
    title="Lộ trình mẫu: Nói tiếng Anh A2 → B2",
    description=(
        "Ba cấp độ đi qua chủ đề đời sống, học tập, công việc, công nghệ và sức khỏe. "
        "Mỗi bài đi từ bài mẫu đến phần nói tự do. Nội dung mẫu cần giảng viên rà soát "
        "trước khi dùng trong lớp học chính thức."
    ),
    band_from=Band.A2,
    band_to=Band.B2,
    content_version=SAMPLE_SEED_VERSION,
)

_UNIT_ROWS = (
    (
        "unit-sample-a2",
        Band.A2,
        Topic.DAILY_LIFE,
        "Đời sống hằng ngày",
        "Tả nơi ở, kể một ngày và thói quen của bạn",
        ("lesson-a2-neighborhood", "lesson-pr-flu-a2", "lesson-pr-ran-a2", "lesson-pr-acc-a2"),
    ),
    (
        "unit-a2-education",
        Band.A2,
        Topic.EDUCATION,
        "Trường lớp",
        "Kể về ngày học, môn học và bạn cùng lớp",
        ("lesson-a2-school", "lesson-pr-pho-a2"),
    ),
    (
        "unit-a2-food",
        Band.A2,
        Topic.FOOD,
        "Ăn uống",
        "Nói về món ăn và bữa ăn bạn thích",
        ("lesson-a2-breakfast", "lesson-pr-coh-a2"),
    ),
    (
        "unit-a2-travel",
        Band.A2,
        Topic.TRAVEL,
        "Đi chơi",
        "Kể một chuyến đi ngắn bằng câu đơn",
        ("lesson-a2-beach",),
    ),
    (
        "unit-a2-career",
        Band.A2,
        Topic.CAREER,
        "Công việc",
        "Nói về nghề bạn muốn làm",
        ("lesson-a2-dream-job",),
    ),
    (
        "unit-a2-health",
        Band.A2,
        Topic.HEALTH,
        "Sức khỏe",
        "Nói về thói quen ăn, ngủ và tập luyện",
        ("lesson-a2-healthy",),
    ),
    (
        "unit-sample-b1",
        Band.B1,
        Topic.TRAVEL,
        "Du lịch",
        "Kể một trải nghiệm theo trình tự, có cảm xúc",
        ("lesson-b1-trip", "lesson-pr-flu-b1"),
    ),
    (
        "unit-b1-education",
        Band.B1,
        Topic.EDUCATION,
        "Học tập cùng nhau",
        "Kể về hoạt động nhóm và điều bạn học được",
        ("lesson-b1-club", "lesson-pr-pho-b1"),
    ),
    (
        "unit-b1-career",
        Band.B1,
        Topic.CAREER,
        "Kinh nghiệm nghề nghiệp",
        "Cân bằng việc học và công việc",
        ("lesson-b1-part-time", "lesson-pr-acc-b1"),
    ),
    (
        "unit-b1-food",
        Band.B1,
        Topic.FOOD,
        "Món ăn và gia đình",
        "Chia sẻ câu chuyện về món ăn quen thuộc",
        ("lesson-b1-home-dish", "lesson-pr-coh-b1"),
    ),
    (
        "unit-b1-people",
        Band.B1,
        Topic.PEOPLE,
        "Con người",
        "Mô tả điểm mạnh và cách mọi người học hỏi",
        ("lesson-pr-ran-b1",),
    ),
    (
        "unit-b1-technology",
        Band.B1,
        Topic.TECHNOLOGY,
        "Công nghệ",
        "Nói về cách dùng thiết bị có chủ đích",
        ("lesson-b1-phone",),
    ),
    (
        "unit-sample-b2",
        Band.B2,
        Topic.SOCIETY,
        "Truyền thông trực tuyến",
        "Đánh giá lợi ích và giới hạn của thông tin trực tuyến",
        ("lesson-b2-online", "lesson-pr-flu-b2"),
    ),
    (
        "unit-b2-technology",
        Band.B2,
        Topic.TECHNOLOGY,
        "Công nghệ mới",
        "Cân nhắc ảnh hưởng của công nghệ đến việc học",
        ("lesson-b2-ai", "lesson-pr-ran-b2"),
    ),
    (
        "unit-b2-environment",
        Band.B2,
        Topic.ENVIRONMENT,
        "Môi trường",
        "Đề xuất thay đổi để giảm tác động đến môi trường",
        ("lesson-b2-plastic",),
    ),
    (
        "unit-b2-career",
        Band.B2,
        Topic.CAREER,
        "Nơi làm việc",
        "Cân nhắc tính linh hoạt và phối hợp công việc",
        ("lesson-b2-remote", "lesson-pr-acc-b2"),
    ),
    (
        "unit-b2-society",
        Band.B2,
        Topic.SOCIETY,
        "Xã hội",
        "Trình bày quan điểm và hỗ trợ lý do bằng ví dụ",
        ("lesson-pr-coh-b2", "lesson-pr-pho-b2"),
    ),
    (
        "unit-b2-health",
        Band.B2,
        Topic.HEALTH,
        "Sức khỏe",
        "Nói về áp lực và các nguồn hỗ trợ",
        ("lesson-b2-stress",),
    ),
)


def sample_units() -> tuple[LearningUnit, ...]:
    return tuple(
        LearningUnit(
            unit_id=unit_id,
            path_id=SAMPLE_PATH_ID,
            ordinal=index,
            title=title,
            band=band,
            topic=topic,
            learning_function=function,
            lesson_ids=lesson_ids,
        )
        for index, (unit_id, band, topic, title, function, lesson_ids) in enumerate(
            _UNIT_ROWS, start=1
        )
    )


def _authored_core_lessons() -> tuple[tuple[str, Lesson], ...]:
    return (
        (
            "unit-sample-a2",
            build_lesson(
                lesson_id="lesson-a2-neighborhood",
                title="Miêu tả khu phố",
                summary="Nói về một nơi quen thuộc, hoạt động và cảm nhận của bạn.",
                band=Band.A2,
                model_text=(
                    "I live on a quiet street near a small park. In the morning, neighbors walk"
                    "to the market and greet one another. I like the park because I can read"
                    "under a tree. The area feels friendly and easy to explore."
                ),
                free_prompt="Describe a place in your neighborhood that you enjoy.",
                keywords=("street", "park", "neighbors", "friendly"),
            ),
        ),
        (
            "unit-sample-b1",
            build_lesson(
                lesson_id="lesson-b1-trip",
                title="Một chuyến đi đáng nhớ",
                summary="Kể trải nghiệm theo trình tự và giải thích điều làm nó đáng nhớ.",
                band=Band.B1,
                model_text=(
                    "During a weekend trip, my friends and I visited a coastal town. The train"
                    "was delayed, so we changed our plan and explored a local market first."
                    "Later, we walked beside the water and watched the sunset. The unexpected"
                    "change made the trip more memorable."
                ),
                free_prompt="Tell a story about a trip that changed your plans.",
                keywords=("journey", "market", "unexpected", "memorable"),
            ),
        ),
        (
            "unit-sample-b2",
            build_lesson(
                lesson_id="lesson-b2-online",
                title="Thông tin trên mạng",
                summary="Đánh giá thông tin trực tuyến và nêu cách kiểm tra nguồn.",
                band=Band.B2,
                model_text=(
                    "Online platforms make it possible to encounter ideas from many communities."
                    "However, popular posts are not automatically reliable, and brief headlines"
                    "can hide important context. Readers can compare independent sources, check"
                    "when a claim was published, and distinguish evidence from opinion before"
                    "sharing it."
                ),
                free_prompt="How can people judge whether online information is reliable?",
                keywords=("platforms", "reliable", "context", "evidence"),
            ),
        ),
    )


def _practice_lessons() -> tuple[tuple[str, Lesson], ...]:
    result: list[tuple[str, Lesson]] = []
    for mission in PRACTICE_MISSIONS:
        band_text = {
            Band.A2: (
                "I practise speaking about familiar places and people. I use clear words and"
                "short sentences. I add one detail to help a listener understand my idea."
            ),
            Band.B1: (
                "I explain a familiar experience and connect my ideas with useful details. I"
                "can give a reason, describe a change, and say how I felt about the result."
            ),
            Band.B2: (
                "I develop a clear position by connecting reasons, examples, and relevant"
                "limits. I consider how the issue affects different people before reaching a"
                "conclusion."
            ),
        }[mission.target_band]
        prompt = mission.prompt
        words = tuple(word for goal in mission.goals for word in goal.words)[:3]
        if len(words) < 3:
            words = ("idea", "reason", "example")
        result.append(
            (
                "unit-sample-a2"
                if mission.target_band is Band.A2
                and mission.criterion.value != "coherence"
                and mission.criterion.value not in {"phonology"}
                else "unit-a2-education"
                if mission.mission_id == "PR-PHO-A2"
                else "unit-a2-food"
                if mission.mission_id == "PR-COH-A2"
                else "unit-sample-b1"
                if mission.mission_id == "PR-FLU-B1"
                else "unit-b1-education"
                if mission.mission_id == "PR-PHO-B1"
                else "unit-b1-career"
                if mission.mission_id == "PR-ACC-B1"
                else "unit-b1-food"
                if mission.mission_id == "PR-COH-B1"
                else "unit-b1-people"
                if mission.mission_id == "PR-RAN-B1"
                else "unit-sample-b2"
                if mission.mission_id == "PR-FLU-B2"
                else "unit-b2-technology"
                if mission.mission_id == "PR-RAN-B2"
                else "unit-b2-career"
                if mission.mission_id == "PR-ACC-B2"
                else "unit-b2-society",
                build_lesson(
                    lesson_id=f"lesson-{mission.mission_id.lower()}",
                    title=mission.title,
                    summary=prompt,
                    band=mission.target_band,
                    model_text=band_text,
                    free_prompt=prompt,
                    keywords=words,
                ),
            )
        )
    return tuple(result)


def sample_catalogue() -> tuple[
    LearningPath, tuple[LearningUnit, ...], tuple[tuple[str, Lesson], ...]
]:
    units = sample_units()
    lessons = _authored_core_lessons() + topic_lessons() + _practice_lessons()
    lesson_ids = {lesson.lesson_id for _, lesson in lessons}
    if len(units) != 18 or len(lessons) != 31:
        raise RuntimeError("sample catalogue must contain eighteen units and thirty-one lessons")
    if any(set(unit.lesson_ids) - lesson_ids for unit in units):
        raise RuntimeError("sample catalogue unit references an unknown lesson")
    path = SAMPLE_PATH.model_copy(update={"units": units})
    return path, units, lessons


def seed_sample(repository: LearningRepository, *, now: datetime) -> str:
    path, units, lessons = sample_catalogue()
    return repository.seed_sample_catalogue(
        path,
        units,
        lessons,
        layout=SAMPLE_LAYOUT,
        seed_version=SAMPLE_SEED_VERSION,
        now=now,
    )
