"""Authored sample lesson content for topic-focused sample units."""

from __future__ import annotations

from aicefr.contracts import Band
from aicefr.lessons.generate import build_lesson
from aicefr.lessons.model import Lesson

_TOPICS = (
    (
        "lesson-a2-school",
        "unit-a2-education",
        Band.A2,
        "Một ngày ở trường",
        "Kể về môn học, giờ học và một người bạn cùng lớp.",
        (
            "I study at a small school near my home. My favorite class is English because"
            "we speak and play games. At lunch, I sit with my friends. We talk about our"
            "lessons and help each other."
        ),
        "Describe a school day that you enjoy.",
        ("school", "class", "friend", "lesson"),
    ),
    (
        "lesson-a2-breakfast",
        "unit-a2-food",
        Band.A2,
        "Bữa sáng yêu thích",
        "Nói về món ăn buổi sáng và thói quen của bạn.",
        (
            "I usually eat breakfast with my family. We have fruit, bread, and eggs. I"
            "like a warm meal because it gives me energy for school. On busy mornings, I"
            "prepare something simple."
        ),
        "What do you like to eat in the morning, and why?",
        ("breakfast", "family", "fruit", "energy"),
    ),
    (
        "lesson-a2-beach",
        "unit-a2-travel",
        Band.A2,
        "Một ngày ở bãi biển",
        "Miêu tả một chuyến đi ngắn và hoạt động bạn thích.",
        (
            "Last summer, I went to the beach with my cousins. We walked by the water and"
            "collected small shells. The weather was warm, so we swam before lunch. I"
            "felt relaxed on the way home."
        ),
        "Tell a friend about a short trip you would like to take.",
        ("beach", "water", "cousin", "relaxed"),
    ),
    (
        "lesson-a2-dream-job",
        "unit-a2-career",
        Band.A2,
        "Công việc mơ ước",
        "Nói về một nghề bạn quan tâm và lý do bạn chọn nghề đó.",
        (
            "I would like to become a nurse. I want to help people feel better and stay"
            "healthy. I enjoy science, and I am patient when I listen. I know this job"
            "takes study and care."
        ),
        "Describe a job that interests you and explain why.",
        ("nurse", "help", "healthy", "patient"),
    ),
    (
        "lesson-a2-healthy",
        "unit-a2-health",
        Band.A2,
        "Thói quen khỏe mạnh",
        "Nói về cách ăn, nghỉ ngơi và vận động thường ngày.",
        (
            "I try to take care of my health every day. I drink water, eat vegetables,"
            "and walk with my neighbor. I also rest when I feel tired. These small habits"
            "help me feel ready for class."
        ),
        "Which healthy habit would you like to keep, and why?",
        ("health", "water", "walk", "habit"),
    ),
    (
        "lesson-b1-club",
        "unit-b1-education",
        Band.B1,
        "Tham gia câu lạc bộ",
        "Giải thích một hoạt động ngoại khóa và điều bạn học được.",
        (
            "When I joined the photography club, I expected to learn about cameras. I"
            "also learned to plan with other students and give helpful feedback. Our"
            "first project was difficult, but the group stayed patient and finished it"
            "together."
        ),
        "Describe a club or group that could help students learn together.",
        ("club", "project", "feedback", "patient"),
    ),
    (
        "lesson-b1-part-time",
        "unit-b1-career",
        Band.B1,
        "Công việc bán thời gian",
        "Nêu lợi ích và thách thức khi vừa học vừa làm.",
        (
            "A part-time job can teach students how to manage time and speak with"
            "customers. It also provides some money for daily needs. However, students"
            "should protect their study time and rest. A clear weekly plan can make the"
            "balance easier."
        ),
        "Do you think students should have part-time jobs? Give reasons.",
        ("students", "time", "customers", "balance"),
    ),
    (
        "lesson-b1-home-dish",
        "unit-b1-food",
        Band.B1,
        "Món ăn của gia đình",
        "Kể cách một món ăn gắn với gia đình hoặc quê hương.",
        (
            "My grandmother makes a vegetable soup that everyone knows. She chooses fresh"
            "ingredients and cooks them slowly. While we eat, she tells stories about"
            "learning the recipe from her mother. The meal reminds me that food can"
            "connect generations."
        ),
        "Talk about a dish that is meaningful to your family.",
        ("recipe", "ingredients", "family", "connect"),
    ),
    (
        "lesson-b1-phone",
        "unit-b1-technology",
        Band.B1,
        "Điện thoại và thời gian tập trung",
        "Trình bày cách thiết bị ảnh hưởng đến việc học của bạn.",
        (
            "A phone helps me check class messages and look up new words. At the same"
            "time, alerts can interrupt my reading. I put the phone in my bag when I need"
            "to focus. This simple choice makes my study time more useful."
        ),
        "How can people use phones without losing focus?",
        ("phone", "alerts", "focus", "useful"),
    ),
    (
        "lesson-b2-ai",
        "unit-b2-technology",
        Band.B2,
        "Trí tuệ nhân tạo trong lớp học",
        "Đánh giá lợi ích và giới hạn của công cụ AI cho người học.",
        (
            "Artificial intelligence can give learners quick explanations and help them"
            "practise at their own pace. Yet a fluent answer is not always accurate, and"
            "students may stop checking sources. Teachers can present AI as a tool for"
            "comparison rather than a replacement for careful reading."
        ),
        (
            "Should students use artificial intelligence for schoolwork? Explain your"
            "view and address a concern."
        ),
        ("learners", "sources", "compare", "careful"),
    ),
    (
        "lesson-b2-plastic",
        "unit-b2-environment",
        Band.B2,
        "Giảm rác thải nhựa",
        "Đề xuất thay đổi thực tế và giải thích vai trò của cộng đồng.",
        (
            "Single-use plastic is convenient, but it can remain in the environment long"
            "after a meal is finished. Shops, schools, and local groups can make reusable"
            "choices easier by providing refill stations. Individual habits matter most"
            "when public spaces support them."
        ),
        "What practical steps can a community take to reduce plastic waste?",
        ("plastic", "reusable", "community", "environment"),
    ),
    (
        "lesson-b2-remote",
        "unit-b2-career",
        Band.B2,
        "Làm việc từ xa",
        "Cân nhắc tính linh hoạt, phối hợp và ranh giới trong công việc.",
        (
            "Remote work gives employees more control over where they complete focused"
            "tasks. It can also make quick collaboration harder when teams rely only on"
            "messages. Clear meeting routines and protected personal time help"
            "organizations gain flexibility without extending the workday."
        ),
        "Is remote work better for most employees? Discuss both sides before deciding.",
        ("remote", "employees", "collaboration", "flexibility"),
    ),
    (
        "lesson-b2-stress",
        "unit-b2-health",
        Band.B2,
        "Quản lý căng thẳng",
        "Giải thích cách nhận biết áp lực và lựa chọn hỗ trợ phù hợp.",
        (
            "Stress can help people respond to a challenge, but constant pressure can"
            "make ordinary decisions exhausting. Regular sleep, movement, and honest"
            "conversations can reduce some strain. When the problem continues, seeking"
            "professional support is a practical act of care."
        ),
        "How should schools or workplaces support people experiencing stress?",
        ("stress", "pressure", "support", "practical"),
    ),
)


def topic_lessons() -> tuple[tuple[str, Lesson], ...]:
    """Return the thirteen stable authored topic lessons in pinned order."""
    return tuple(
        (
            unit_id,
            build_lesson(
                lesson_id=lesson_id,
                title=title,
                summary=summary,
                band=band,
                model_text=text,
                free_prompt=prompt,
                keywords=keywords,
            ),
        )
        for lesson_id, unit_id, band, title, summary, text, prompt, keywords in _TOPICS
    )
