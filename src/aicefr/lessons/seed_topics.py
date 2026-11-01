"""Sample lessons of the topic units added to the sample path (D027).

Thirteen lessons, five at A2, four at B1 and four at B2, each laid out by
`build_lesson` from one model text, its key words and a free-speaking prompt on
a parallel topic. All of it is SAMPLE content: written by the development team,
marked `sample`, and waiting for a teacher of the Faculty of Foreign Languages
to review it before it is used with real students. Texts use American spelling
and no digits, so the linter has nothing to warn about.

Key words are ordered on purpose: the first three become the key-word step, and
the first two that are not blanked become the distractors of the gap step, so
they are chosen not to fit its blanks.

Ids are fixed strings so that re-seeding never duplicates a lesson and every
stored attempt keeps pointing at its step.
"""

from __future__ import annotations

from aicefr.contracts import Band
from aicefr.lessons.generate import build_lesson
from aicefr.lessons.model import Lesson


def _sample(lesson: Lesson, lesson_id: str) -> Lesson:
    """Mark a built lesson as sample content, with a fixed id and fixed step ids."""
    lesson.lesson_id = lesson_id
    lesson.built_in = True
    for i, step in enumerate(lesson.steps, 1):
        step.step_id = f"{lesson_id}-s{i}"
    return lesson


# ---------------------------------------------------------------- A2


def _a2_school() -> Lesson:
    text = (
        "I usually arrive at school at seven in the morning. I have three or four classes "
        "before noon. My favorite subject is history, because the teacher tells great stories. "
        "At noon, I have lunch with my friends in the cafeteria. We eat rice with chicken and "
        "talk a lot. After that, I study in the library. Finally, I go home at five, tired but "
        "happy."
    )
    keywords = ["favorite", "subject", "lunch", "cafeteria", "classes", "library"]
    prompt = "Kể về một ngày cuối tuần bình thường của bạn: bạn làm gì, ở đâu và với ai?"
    lesson = build_lesson(
        "Một ngày ở trường",
        Band.A2,
        text,
        keywords,
        prompt,
        summary=(
            "Kể một ngày ở trường của bạn: các tiết học, môn học yêu thích, bạn bè và bữa trưa."
        ),
    )
    return _sample(lesson, "lesson-a2-school")


def _a2_breakfast() -> Lesson:
    text = (
        "I usually have breakfast at a small food stall near my house. My favorite dish is beef "
        "noodle soup. Sometimes I eat sticky rice or a sandwich instead. I always drink a glass "
        "of iced coffee with milk. My sister often comes with me, and we talk about our plans. "
        "I like this breakfast because it is hot, tasty, and cheap."
    )
    keywords = ["breakfast", "stall", "tasty", "cheap", "noodle", "coffee"]
    prompt = "Tả bữa tối thường ngày ở nhà bạn: ăn gì, với ai và món nào bạn thích nhất?"
    lesson = build_lesson(
        "Bữa sáng của tôi",
        Band.A2,
        text,
        keywords,
        prompt,
        summary="Tả bữa sáng của bạn: ăn gì, ở đâu, với ai và vì sao bạn thích.",
    )
    return _sample(lesson, "lesson-a2-breakfast")


def _a2_beach() -> Lesson:
    text = (
        "Last summer, I spent three days at the beach with my family. We stayed in a small "
        "hotel near the water. Every morning, we swam in the sea and relaxed on the sand. For "
        "lunch, we ate fresh seafood at a local restaurant. In the evening, we walked along the "
        "beach and watched the sunset. It was a short trip, but I enjoyed every minute."
    )
    keywords = ["beach", "sunset", "seafood", "enjoyed", "swam", "sand"]
    prompt = "Kể về một chuyến đi ngắn bạn nhớ nhất: đi đâu, với ai, làm gì?"
    lesson = build_lesson(
        "Kỳ nghỉ ở biển",
        Band.A2,
        text,
        keywords,
        prompt,
        summary="Kể lại một chuyến đi biển ngắn: đi với ai, ở đâu, đã làm gì và bạn thấy thế nào.",
    )
    return _sample(lesson, "lesson-a2-beach")


def _a2_dream_job() -> Lesson:
    text = (
        "My dream job is to be a tour guide. I love traveling, and I enjoy meeting people from "
        "other countries. A guide shows visitors around the city and tells them about its "
        "history. The job is not easy, because you often work on weekends. But the work is "
        "never boring, and each tour is different. Now I practice speaking every day to get "
        "ready."
    )
    keywords = ["dream", "weekends", "boring", "guide", "visitors", "practice"]
    prompt = (
        "Kể về công việc của một người trong gia đình bạn: họ làm nghề gì, công việc thế nào, "
        "bạn có muốn làm nghề đó không?"
    )
    lesson = build_lesson(
        "Công việc mơ ước",
        Band.A2,
        text,
        keywords,
        prompt,
        summary="Nói về công việc bạn mơ ước: đó là nghề gì, vì sao bạn thích và công việc ra sao.",
    )
    return _sample(lesson, "lesson-a2-dream-job")


def _a2_healthy() -> Lesson:
    text = (
        "I want to stay healthy, so I have a few simple habits. First, I sleep for seven or "
        "eight hours every night. I also drink a lot of water and eat vegetables with every "
        "meal. I do not drink soda, and I rarely eat fast food. Finally, I go jogging in the "
        "park three times a week. After a run, I feel fresh and full of energy."
    )
    keywords = ["sleep", "jogging", "water", "vegetables", "healthy", "habits"]
    prompt = (
        "Kể về một thói quen chưa tốt của bạn, như thức khuya hay ít vận động: vì sao bạn muốn "
        "thay đổi và bạn sẽ làm gì?"
    )
    lesson = build_lesson(
        "Thói quen lành mạnh",
        Band.A2,
        text,
        keywords,
        prompt,
        summary=(
            "Nói về các thói quen giữ sức khoẻ của bạn: giấc ngủ, nước uống, rau xanh và tập "
            "thể dục."
        ),
    )
    return _sample(lesson, "lesson-a2-healthy")


# ---------------------------------------------------------------- B1


def _b1_club() -> Lesson:
    text = (
        "Last year, I joined the volunteer club at my university. At first, I felt shy because "
        "I did not know anyone. Then we started to visit a village school every month and teach "
        "the children games and songs. After that, we collected old books and clothes for poor "
        "families. These activities taught me how to plan events and work in a team. In the "
        "end, I made many friends and became much more confident."
    )
    keywords = ["joined", "shy", "confident", "volunteer", "activities", "team"]
    prompt = (
        "Kể về một hoạt động ngoại khóa hay một nhóm bạn từng tham gia: bạn đã làm gì ở đó và "
        "học được điều gì?"
    )
    lesson = build_lesson(
        "Câu lạc bộ ở trường",
        Band.B1,
        text,
        keywords,
        prompt,
        summary=(
            "Kể về câu lạc bộ bạn tham gia: vì sao bạn vào, các bạn làm gì và bạn học được gì."
        ),
    )
    return _sample(lesson, "lesson-b1-club")


def _b1_part_time() -> Lesson:
    text = (
        "In my second year, I worked part-time at a coffee shop near campus. To begin with, the "
        "job was hard because I had to remember many drinks and serve customers quickly. Then "
        "the late shifts started to affect my studies, and I often felt tired in class. "
        "However, the job also had good points. I earned my own money and learned to manage my "
        "time. I also became more patient with difficult customers. In the end, I think a "
        "part-time job is a useful experience for students."
    )
    keywords = ["earned", "manage", "customers", "patient", "shifts", "tired"]
    prompt = (
        "Kể về một lần bạn kiếm tiền hoặc phụ giúp gia đình, như dạy kèm hay bán hàng: việc gì "
        "vui, việc gì khó và bạn học được gì?"
    )
    lesson = build_lesson(
        "Công việc làm thêm",
        Band.B1,
        text,
        keywords,
        prompt,
        summary="Kể về một công việc làm thêm: công việc thế nào, có điểm gì tốt và chưa tốt.",
    )
    return _sample(lesson, "lesson-b1-part-time")


def _b1_home_dish() -> Lesson:
    text = (
        "My hometown is famous for a crispy pancake made from rice flour. First, my mother "
        "mixes the flour with water and a little yellow spice. Then she pours the mixture into "
        "a hot pan and adds shrimp and pork. After that, she folds the pancake in half. "
        "Finally, we wrap each piece in fresh herbs and dip it in fish sauce. People in my "
        "hometown often eat this dish on rainy afternoons. To me, it always tastes like home."
    )
    keywords = ["famous", "sauce", "herbs", "crispy", "mixture", "rainy"]
    prompt = (
        "Kể về lần đầu bạn tự nấu một món ăn: đó là món gì, bạn làm từng bước ra sao và kết "
        "quả thế nào?"
    )
    lesson = build_lesson(
        "Món ăn quê hương",
        Band.B1,
        text,
        keywords,
        prompt,
        summary=(
            "Giới thiệu một món ăn truyền thống của quê bạn: món gì, làm thế nào và người ta "
            "ăn khi nào."
        ),
    )
    return _sample(lesson, "lesson-b1-home-dish")


def _b1_phone() -> Lesson:
    text = (
        "I use my phone for studying almost every day. First, I look up new words in a "
        "dictionary app and listen to their pronunciation. In online groups, my classmates and "
        "I share notes and ask questions. However, my phone can also be a big distraction. When "
        "a message arrives, I start scrolling, and then I forget about my homework. That is why "
        "I made some rules for myself. Now I turn off notifications so that I can focus. "
        "Finally, I only check messages during my breaks."
    )
    keywords = ["distraction", "focus", "rules", "notifications", "dictionary", "pronunciation"]
    prompt = (
        "Kể về một lần mạng xã hội hay trò chơi trực tuyến làm bạn mất nhiều thời gian: chuyện "
        "gì đã xảy ra và sau đó bạn thay đổi thế nào?"
    )
    lesson = build_lesson(
        "Điện thoại và việc học",
        Band.B1,
        text,
        keywords,
        prompt,
        summary=(
            "Nói về cách bạn dùng điện thoại để học, những rắc rối nó gây ra và quy tắc bạn tự đặt."
        ),
    )
    return _sample(lesson, "lesson-b1-phone")


# ---------------------------------------------------------------- B2


def _b2_ai() -> Lesson:
    text = (
        "Many students now use artificial intelligence tools for their homework. In my "
        "opinion, these tools can be useful if we use them wisely. First of all, they give "
        "instant feedback. For example, a chatbot can explain a difficult grammar point or "
        "suggest a better structure for an essay. On the other hand, there are real risks. If "
        "students simply copy the answers, they stop thinking for themselves, and the tools "
        "sometimes give wrong information. As a result, teachers should show students how to "
        "check every answer carefully. In conclusion, artificial intelligence should be a "
        "tutor, not a replacement for our own effort."
    )
    keywords = ["feedback", "risks", "effort", "copy", "replacement", "wisely"]
    prompt = (
        "Theo bạn, sinh viên có nên dùng công cụ dịch tự động khi học ngoại ngữ không? Nêu lý "
        "do, ví dụ, một ý phản biện và kết luận."
    )
    lesson = build_lesson(
        "Trí tuệ nhân tạo trong lớp học",
        Band.B2,
        text,
        keywords,
        prompt,
        summary=(
            "Nêu lợi ích và rủi ro của công cụ trí tuệ nhân tạo với sinh viên, rồi đưa ra kết luận."
        ),
    )
    return _sample(lesson, "lesson-b2-ai")


def _b2_plastic() -> Lesson:
    text = (
        "Plastic waste is one of the most serious environmental problems in my city. First of "
        "all, we use far too much packaging. Every day, people buy drinks in plastic cups and "
        "carry their food home in plastic bags. As a result, rivers and beaches are covered "
        "with trash, and tiny pieces of plastic end up in the fish we eat. However, the "
        "situation is not hopeless. Individuals can bring their own bottles and bags and say "
        "no to straws. At the same time, cities should improve recycling and make shops charge "
        "for plastic bags. In conclusion, small daily choices, supported by clear rules, can "
        "make a real difference."
    )
    keywords = ["waste", "packaging", "recycling", "individuals", "choices", "difference"]
    prompt = (
        "Theo bạn, giảm ô nhiễm ở thành phố là việc của mỗi người dân hay của chính quyền? Nêu "
        "lý do, ví dụ, một ý phản biện và kết luận."
    )
    lesson = build_lesson(
        "Rác thải nhựa",
        Band.B2,
        text,
        keywords,
        prompt,
        summary=(
            "Nói về rác thải nhựa: nguyên nhân, hậu quả và điều mỗi người cũng như thành phố "
            "có thể làm."
        ),
    )
    return _sample(lesson, "lesson-b2-plastic")


def _b2_remote() -> Lesson:
    text = (
        "More and more companies now let their employees work from home. First of all, remote "
        "work has obvious benefits. Employees save the time and money they used to spend on "
        "commuting, and they can organize their day in a more flexible way. On the other hand, "
        "working alone every day can feel isolating. Without meeting colleagues in person, it "
        "is harder to build trust and share ideas. Some people also find it difficult to stop "
        "working in the evening. Overall, I believe a hybrid model offers the best balance. "
        "Employees could spend a few days in the office and the rest of the week at home."
    )
    keywords = ["commuting", "flexible", "isolating", "colleagues", "hybrid", "balance"]
    prompt = (
        "Theo bạn, sinh viên nên sống ở ký túc xá hay ở cùng gia đình? Nêu ưu điểm, nhược điểm "
        "của mỗi cách và một kết luận cân bằng."
    )
    lesson = build_lesson(
        "Làm việc từ xa",
        Band.B2,
        text,
        keywords,
        prompt,
        summary="Nêu ưu điểm và nhược điểm của làm việc từ xa, rồi đưa ra một kết luận cân bằng.",
    )
    return _sample(lesson, "lesson-b2-remote")


def _b2_stress() -> Lesson:
    text = (
        "Academic stress is a common problem among university students. First of all, it has "
        "several causes. Many students take too many courses, study for exams at the last "
        "minute, and worry about their parents' expectations. As a result, they sleep badly "
        "and find it hard to concentrate in class. Some even lose interest in subjects they "
        "used to love. However, there are many ways to cope with pressure. Students can break "
        "big tasks into smaller steps, exercise regularly, and talk to friends or a counselor. "
        "In conclusion, stress is normal, but students should ask for support early, before it "
        "becomes serious."
    )
    keywords = ["pressure", "expectations", "concentrate", "cope", "counselor", "support"]
    prompt = (
        "Theo bạn, có nên thay kỳ thi cuối kỳ bằng nhiều bài kiểm tra nhỏ để sinh viên bớt áp "
        "lực không? Nêu lý do, ví dụ, một ý phản biện và kết luận."
    )
    lesson = build_lesson(
        "Áp lực học tập",
        Band.B2,
        text,
        keywords,
        prompt,
        summary="Nói về áp lực học tập: nguyên nhân, ảnh hưởng tới sinh viên và cách vượt qua.",
    )
    return _sample(lesson, "lesson-b2-stress")


def topic_lessons() -> dict[str, Lesson]:
    """The thirteen topic lessons by lesson id, A2 to B2, in path order."""
    lessons = [
        _a2_school(),
        _a2_breakfast(),
        _a2_beach(),
        _a2_dream_job(),
        _a2_healthy(),
        _b1_club(),
        _b1_part_time(),
        _b1_home_dish(),
        _b1_phone(),
        _b2_ai(),
        _b2_plastic(),
        _b2_remote(),
        _b2_stress(),
    ]
    return {lesson.lesson_id: lesson for lesson in lessons}
