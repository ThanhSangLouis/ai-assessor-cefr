"""Deterministic 5-criterion × 3-band practice catalogue."""

from __future__ import annotations

from aicefr.contracts import Band, Criterion
from aicefr.practice.contracts import MissionGoal, MissionKind, PracticeMission
from aicefr.practice.rules import MISSION_RULES_VERSION

RULES_VERSION = MISSION_RULES_VERSION
PROMPT_VERSION = "practice-prompts-v1"


def _goal(
    goal_id: str,
    kind: MissionKind,
    target: float,
    *,
    words: tuple[str, ...] = (),
    reference_text: str | None = None,
) -> MissionGoal:
    return MissionGoal(
        goal_id=goal_id,
        kind=kind,
        target=target,
        words=words,
        reference_text=reference_text,
    )


_SEEDS: tuple[PracticeMission, ...] = (
    PracticeMission(
        mission_id="PR-FLU-A2",
        criterion=Criterion.FLUENCY,
        target_band=Band.A2,
        title="Kể về một ngày bình thường",
        prompt="Nói về buổi sáng, ở trường và buổi tối.",
        goals=(
            _goal("speaking_time", MissionKind.SPEAK_SECONDS, 30),
            _goal("long_pause", MissionKind.MAX_PAUSE, 3.0),
        ),
        prompt_version=PROMPT_VERSION,
        rules_version=RULES_VERSION,
    ),
    PracticeMission(
        mission_id="PR-FLU-B1",
        criterion=Criterion.FLUENCY,
        target_band=Band.B1,
        title="Kể một chuyến đi đáng nhớ",
        prompt="Kể nơi bạn đến, chuyện đã xảy ra và cảm xúc.",
        goals=(
            _goal("speaking_time", MissionKind.SPEAK_SECONDS, 45),
            _goal("long_pause", MissionKind.MAX_PAUSE, 2.0),
        ),
        prompt_version=PROMPT_VERSION,
        rules_version=RULES_VERSION,
    ),
    PracticeMission(
        mission_id="PR-FLU-B2",
        criterion=Criterion.FLUENCY,
        target_band=Band.B2,
        title="Giữ nhịp khi nêu quan điểm",
        prompt="Nêu ý kiến về việc sinh viên đi làm thêm.",
        goals=(
            _goal("speaking_time", MissionKind.SPEAK_SECONDS, 60),
            _goal("long_pause", MissionKind.MAX_PAUSE, 1.5),
        ),
        prompt_version=PROMPT_VERSION,
        rules_version=RULES_VERSION,
    ),
    PracticeMission(
        mission_id="PR-COH-A2",
        criterion=Criterion.COHERENCE,
        target_band=Band.A2,
        title="Nối ý bằng từ quen thuộc",
        prompt="Nói về món ăn bạn thích và không thích, có lý do.",
        goals=(
            _goal(
                "linkers", MissionKind.USE_WORDS, 3, words=("and", "but", "because", "so", "also")
            ),
            _goal("speaking_time", MissionKind.SPEAK_SECONDS, 30),
        ),
        prompt_version=PROMPT_VERSION,
        rules_version=RULES_VERSION,
    ),
    PracticeMission(
        mission_id="PR-COH-B1",
        criterion=Criterion.COHERENCE,
        target_band=Band.B1,
        title="Hướng dẫn theo từng bước",
        prompt="Hướng dẫn cách nấu một món ăn.",
        goals=(
            _goal(
                "sequence_words",
                MissionKind.USE_WORDS,
                3,
                words=("first", "second", "then", "next", "after that", "finally"),
            ),
            _goal("speaking_time", MissionKind.SPEAK_SECONDS, 40),
        ),
        prompt_version=PROMPT_VERSION,
        rules_version=RULES_VERSION,
    ),
    PracticeMission(
        mission_id="PR-COH-B2",
        criterion=Criterion.COHERENCE,
        target_band=Band.B2,
        title="Lập luận hai mặt rồi kết luận",
        prompt="So sánh sống ở thành phố lớn hay ở quê.",
        goals=(
            _goal(
                "contrast",
                MissionKind.USE_WORDS,
                2,
                words=("however", "on the other hand", "although", "whereas", "in contrast"),
            ),
            _goal(
                "conclusion",
                MissionKind.USE_WORDS,
                1,
                words=("in conclusion", "to sum up", "overall", "all in all"),
            ),
            _goal("speaking_time", MissionKind.SPEAK_SECONDS, 50),
        ),
        prompt_version=PROMPT_VERSION,
        rules_version=RULES_VERSION,
    ),
    PracticeMission(
        mission_id="PR-RAN-A2",
        criterion=Criterion.RANGE,
        target_band=Band.A2,
        title="Tả căn phòng của bạn",
        prompt="Tả đồ vật, vị trí và điều bạn thích ở căn phòng.",
        goals=(
            _goal(
                "vocabulary",
                MissionKind.USE_WORDS,
                5,
                words=(
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
            ),
            _goal("unique_words", MissionKind.UNIQUE_WORDS, 35),
        ),
        prompt_version=PROMPT_VERSION,
        rules_version=RULES_VERSION,
    ),
    PracticeMission(
        mission_id="PR-RAN-B1",
        criterion=Criterion.RANGE,
        target_band=Band.B1,
        title="Tả một người bạn ngưỡng mộ",
        prompt="Mô tả tính cách và lý do bạn ngưỡng mộ người đó.",
        goals=(
            _goal(
                "vocabulary",
                MissionKind.USE_WORDS,
                4,
                words=(
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
            ),
            _goal("unique_words", MissionKind.UNIQUE_WORDS, 55),
        ),
        prompt_version=PROMPT_VERSION,
        rules_version=RULES_VERSION,
    ),
    PracticeMission(
        mission_id="PR-RAN-B2",
        criterion=Criterion.RANGE,
        target_band=Band.B2,
        title="Mạng xã hội và người trẻ",
        prompt="Nêu tác động tích cực và tiêu cực của mạng xã hội.",
        goals=(
            _goal(
                "vocabulary",
                MissionKind.USE_WORDS,
                5,
                words=(
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
            ),
            _goal("unique_words", MissionKind.UNIQUE_WORDS, 75),
        ),
        prompt_version=PROMPT_VERSION,
        rules_version=RULES_VERSION,
    ),
    PracticeMission(
        mission_id="PR-ACC-A2",
        criterion=Criterion.ACCURACY,
        target_band=Band.A2,
        title="Kể lại cuối tuần",
        prompt="Kể lại những việc bạn đã làm cuối tuần vừa rồi.",
        goals=(
            _goal("past_verbs", MissionKind.PAST_VERBS, 5),
            _goal("speaking_time", MissionKind.SPEAK_SECONDS, 30),
        ),
        prompt_version=PROMPT_VERSION,
        rules_version=RULES_VERSION,
    ),
    PracticeMission(
        mission_id="PR-ACC-B1",
        criterion=Criterion.ACCURACY,
        target_band=Band.B1,
        title="Nếu có một tháng nghỉ",
        prompt="Nói bạn sẽ làm gì nếu có một tháng nghỉ và đủ tiền.",
        goals=(
            _goal("conditionals", MissionKind.CONDITIONALS, 2),
            _goal("speaking_time", MissionKind.SPEAK_SECONDS, 40),
        ),
        prompt_version=PROMPT_VERSION,
        rules_version=RULES_VERSION,
    ),
    PracticeMission(
        mission_id="PR-ACC-B2",
        criterion=Criterion.ACCURACY,
        target_band=Band.B2,
        title="Kể một quyết định khó",
        prompt="Nói về quyết định khó và điều bạn học được.",
        goals=(
            _goal(
                "complex_linkers",
                MissionKind.USE_WORDS,
                3,
                words=("although", "even though", "unless", "whereas", "which", "who", "whose"),
            ),
            _goal("speaking_time", MissionKind.SPEAK_SECONDS, 50),
        ),
        prompt_version=PROMPT_VERSION,
        rules_version=RULES_VERSION,
    ),
    PracticeMission(
        mission_id="PR-PHO-A2",
        criterion=Criterion.PHONOLOGY,
        target_band=Band.A2,
        title="Đọc to: giới thiệu bản thân",
        prompt="Đọc to rõ đoạn văn tham chiếu.",
        goals=(
            _goal(
                "read_aloud",
                MissionKind.READ_ALOUD,
                0.80,
                reference_text=(
                    "My name is Lan, and I am a first-year student. I live with my family in a "
                    "small house near the market. Every morning, I take the bus to school. I like "
                    "English because I enjoy watching films and listening to songs in English. In "
                    "my free time, I play badminton with my friends or help my mother cook dinner. "
                    "On Sundays, we often visit my grandparents."
                ),
            ),
        ),
        prompt_version=PROMPT_VERSION,
        rules_version=RULES_VERSION,
    ),
    PracticeMission(
        mission_id="PR-PHO-B1",
        criterion=Criterion.PHONOLOGY,
        target_band=Band.B1,
        title="Đọc to: thông báo câu lạc bộ",
        prompt="Đọc to như đang nói trước cả lớp.",
        goals=(
            _goal(
                "read_aloud",
                MissionKind.READ_ALOUD,
                0.85,
                reference_text=(
                    "Hello everyone, and welcome to the English speaking club. This month, we are "
                    "going to meet every Thursday evening in the library on the second floor. Each "
                    "meeting starts with a short game, and then we talk in small groups. If you "
                    "cannot join a meeting, please send a message to the club leader before "
                    "Wednesday. Remember to bring a notebook, because we will share useful "
                    "expressions at the end of each session."
                ),
            ),
        ),
        prompt_version=PROMPT_VERSION,
        rules_version=RULES_VERSION,
    ),
    PracticeMission(
        mission_id="PR-PHO-B2",
        criterion=Criterion.PHONOLOGY,
        target_band=Band.B2,
        title="Đọc to: đoạn báo ngắn",
        prompt="Đọc đoạn văn, giữ nhịp ở câu dài.",
        goals=(
            _goal(
                "read_aloud",
                MissionKind.READ_ALOUD,
                0.90,
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
        ),
        prompt_version=PROMPT_VERSION,
        rules_version=RULES_VERSION,
    ),
)

PRACTICE_MISSIONS: tuple[PracticeMission, ...] = _SEEDS
_MISSION_BY_ID = {mission.mission_id: mission for mission in PRACTICE_MISSIONS}


def list_missions() -> tuple[PracticeMission, ...]:
    return PRACTICE_MISSIONS


def get_mission(mission_id: str) -> PracticeMission:
    try:
        return _MISSION_BY_ID[mission_id]
    except KeyError as exc:
        raise KeyError(f"unknown practice mission: {mission_id}") from exc


def mission_catalogue_hash() -> str:
    """Stable hash of the canonical JSON catalogue, including rule/prompt versions."""
    import hashlib
    import json

    payload = [mission.model_dump(mode="json") for mission in PRACTICE_MISSIONS]
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


if len(PRACTICE_MISSIONS) != 15 or len(_MISSION_BY_ID) != 15:  # pragma: no cover
    raise RuntimeError("practice catalogue must contain exactly 15 unique missions")
