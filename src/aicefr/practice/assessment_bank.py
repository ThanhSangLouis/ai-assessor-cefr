"""The assessment prompts by CEFR band (D076): what a learner answers on "Nộp bài".

Two parts only, P3 (give an opinion) and P4 (describe a process or a change),
40-60 seconds: the scoring model was trained on these two parts at that
length, so a prompt of another kind or length would be scored outside what the
model knows. What changes from band to band is the topic and how abstract it
is -- oneself and one's day at A1, policy and society at C2 -- never the kind
of task.

`topic_keywords` are English words a response on topic is very likely to say
(D022): broad on purpose, single words, nothing a talk on anything would say.

Seeded once into the `task` collection; teachers add, edit and retire prompts
on screen afterwards (`teach/tasks`), so the bank here only fills what is
missing and never overwrites. The two prompts the system started with, P3 and
P4, are the bank's B1 first prompts.
"""

from __future__ import annotations

from dataclasses import dataclass

from aicefr.contracts import Band, TaskPart

MIN_SECONDS, MAX_SECONDS = 40, 60
TITLES = {TaskPart.P3: "Nêu quan điểm", TaskPart.P4: "Mô tả một quy trình"}


@dataclass(frozen=True)
class Prompt:
    task_id: str
    band: Band
    part: TaskPart
    prompt_text: str
    topic_keywords: str

    @property
    def title(self) -> str:
        return TITLES[self.part]


def _p(task_id: str, part: str, text: str, keywords: str) -> Prompt:
    return Prompt(task_id, Band(task_id[:2]), TaskPart(part), text, keywords)


ASSESSMENT_PROMPTS: tuple[Prompt, ...] = (
    # ---------------------------------------------------------------- A1
    _p("A1-P3-1", "P3", "Bạn thích ở nhà hay đi chơi vào cuối tuần? Vì sao?",
       "weekend, home, house, out, park, friend, friends, family, movie, play, relax, "
       "saturday, sunday, shopping, game"),
    _p("A1-P3-2", "P3", "Bạn thích mùa nào nhất trong năm? Hãy nói lý do.",
       "season, summer, winter, spring, autumn, fall, weather, hot, cold, warm, rain, "
       "sunny, snow, beach, holiday"),
    _p("A1-P3-3", "P3", "Bạn thích ăn món gì nhất? Vì sao bạn thích món đó?",
       "food, eat, dish, rice, noodle, noodles, pho, chicken, fish, meat, vegetable, "
       "fruit, cook, restaurant, delicious, taste"),
    _p("A1-P4-1", "P4", "Hãy kể các việc bạn làm vào buổi sáng, từ lúc thức dậy đến lúc đi học "
       "hoặc đi làm.",
       "morning, wake, breakfast, shower, brush, teeth, dress, clothes, school, class, "
       "work, bus, bike, leave, first, then"),
    _p("A1-P4-2", "P4", "Hãy tả căn phòng của bạn: trong phòng có những gì và đặt ở đâu.",
       "room, bed, desk, table, chair, window, door, wall, lamp, book, shelf, closet, "
       "wardrobe, computer, picture"),
    _p("A1-P4-3", "P4", "Hãy giới thiệu gia đình bạn: có những ai và mỗi người làm gì.",
       "family, father, mother, dad, mom, brother, sister, parents, grandmother, "
       "grandfather, job, work, teacher, student, house"),
    # ---------------------------------------------------------------- A2
    _p("A2-P3-1", "P3", "Bạn thích đi du lịch một mình hay với bạn bè? Vì sao?",
       "travel, trip, alone, friend, friends, group, holiday, vacation, fun, safe, plan, "
       "place, visit, hotel, money"),
    _p("A2-P3-2", "P3", "Theo bạn, sinh viên có nên đi làm thêm không? Vì sao?",
       "job, work, money, student, students, study, time, experience, skill, skills, "
       "salary, earn, busy, university, school"),
    _p("A2-P3-3", "P3", "Bạn thích đọc sách giấy hay đọc trên điện thoại? Hãy giải thích.",
       "book, books, read, reading, paper, phone, screen, online, ebook, eyes, carry, "
       "library, cheap, story, stories"),
    _p("A2-P4-1", "P4", "Hãy kể cách bạn nấu một món ăn đơn giản, từng bước một.",
       "cook, cooking, food, dish, egg, eggs, rice, noodles, water, pan, pot, cut, boil, "
       "fry, salt, minutes, first, then"),
    _p("A2-P4-2", "P4", "Hãy tả đường đi từ nhà bạn đến trường hoặc nơi làm việc.",
       "home, house, school, university, work, office, road, street, turn, left, right, "
       "bus, motorbike, bike, walk, minutes, traffic"),
    _p("A2-P4-3", "P4", "Hãy kể lại một ngày cuối tuần gần đây của bạn đã diễn ra thế nào.",
       "weekend, saturday, sunday, morning, afternoon, evening, went, visited, watched, "
       "played, ate, friend, friends, family, last"),
    # ---------------------------------------------------------------- B1 (P3, P4 first)
    _p("B1-P3-2", "P3", "Bạn nghĩ mạng xã hội có ích hay có hại cho người trẻ? Hãy nêu lý do.",
       "social, media, facebook, tiktok, instagram, internet, online, young, teenagers, "
       "friends, news, information, time, addicted, connect, phone, share"),
    _p("B1-P3-3", "P3", "Có nên dùng điện thoại trong lớp học không? Nêu quan điểm và ví dụ.",
       "phone, phones, smartphone, mobile, class, classroom, lesson, teacher, student, "
       "students, rule, distract, study, learn, dictionary, focus"),
    _p("B1-P4-2", "P4", "Hãy mô tả cách bạn lên kế hoạch cho một chuyến du lịch, từ đầu đến cuối.",
       "travel, trip, plan, book, ticket, tickets, hotel, flight, bus, budget, money, "
       "place, destination, search, pack, luggage, first, next"),
    _p("B1-P4-3", "P4", "Hãy mô tả cách bạn chuẩn bị cho một buổi thuyết trình trên lớp.",
       "presentation, present, slide, slides, topic, research, information, practice, "
       "practise, audience, speak, prepare, group, powerpoint, teacher, first"),
    # ---------------------------------------------------------------- B2
    _p("B2-P3-1", "P3", "Làm việc từ xa có hiệu quả bằng làm việc ở văn phòng không? Hãy lập luận.",
       "remote, home, office, work, working, company, colleagues, productivity, "
       "productive, commute, flexible, meeting, meetings, online, manager, communication"),
    _p("B2-P3-2", "P3", "Thành phố có nên hạn chế xe máy để giảm ùn tắc không? Nêu quan điểm "
       "của bạn.",
       "city, motorbike, motorbikes, traffic, jam, congestion, transport, bus, metro, "
       "pollution, road, roads, government, limit, ban, air"),
    _p("B2-P3-3", "P3", "Bằng đại học có còn cần thiết để thành công không? Giải thích quan "
       "điểm của bạn.",
       "university, degree, college, education, success, successful, job, career, skill, "
       "skills, experience, knowledge, employer, employers, study, course"),
    _p("B2-P4-1", "P4", "Hãy mô tả quá trình xin một công việc, từ tìm việc đến phỏng vấn.",
       "job, apply, application, cv, resume, interview, company, employer, position, "
       "search, website, letter, prepare, questions, skills, first, finally"),
    _p("B2-P4-2", "P4", "Hãy mô tả cách một sản phẩm quen thuộc được làm ra, ví dụ cà phê "
       "hoặc bánh mì.",
       "coffee, beans, bread, flour, make, made, process, produce, factory, farm, farmers, "
       "roast, grind, bake, oven, step, first"),
    _p("B2-P4-3", "P4", "Hãy mô tả nơi bạn sống đã thay đổi thế nào trong mười năm qua.",
       "city, town, village, change, changed, building, buildings, road, roads, "
       "population, people, traffic, shops, houses, years, ago, now"),
    # ---------------------------------------------------------------- C1
    _p("C1-P3-1", "P3", "Trí tuệ nhân tạo sẽ thay thế hay hỗ trợ con người trong công việc? "
       "Hãy lập luận có ví dụ.",
       "artificial, intelligence, ai, robot, robots, automation, machine, machines, job, "
       "jobs, worker, workers, replace, support, technology, future, human"),
    _p("C1-P3-2", "P3", "Có nên đánh thuế cao các sản phẩm có hại cho sức khoẻ, như đồ uống có "
       "đường? Nêu quan điểm.",
       "tax, taxes, government, sugar, sugary, drink, drinks, soda, health, healthy, "
       "obesity, price, prices, consumers, policy, unhealthy, products"),
    _p("C1-P3-3", "P3", "Du lịch đại trà mang lại lợi ích hay gây hại cho người dân địa phương? "
       "Phân tích hai mặt.",
       "tourism, tourist, tourists, travel, local, locals, community, economy, income, "
       "jobs, environment, pollution, culture, crowded, destination, business"),
    _p("C1-P4-1", "P4", "Hãy mô tả cách bạn đưa ra một quyết định quan trọng mà bạn từng trải "
       "qua, từng bước một.",
       "decision, decide, decided, choose, choice, option, options, consider, advice, "
       "risk, risks, result, important, career, study, first, finally"),
    _p("C1-P4-2", "P4", "Hãy mô tả cách một nhóm làm việc hiệu quả thực hiện một dự án, từ lập "
       "kế hoạch đến đánh giá.",
       "team, group, project, plan, planning, task, tasks, deadline, role, roles, members, "
       "meeting, communicate, review, evaluate, goal, feedback"),
    _p("C1-P4-3", "P4", "Hãy mô tả một xu hướng bạn thấy trong xã hội và giải thích nguyên "
       "nhân của nó.",
       "trend, society, increase, increasing, decrease, rise, change, cause, causes, "
       "reason, young, people, technology, social, generation, effect"),
    # ---------------------------------------------------------------- C2
    _p("C2-P3-1", "P3", "Có nên giới hạn tự do ngôn luận trên mạng để chống tin giả không? Hãy "
       "lập luận chặt chẽ.",
       "freedom, speech, expression, online, internet, fake, news, misinformation, "
       "censorship, platform, platforms, government, regulation, democracy, truth, "
       "responsibility"),
    _p("C2-P3-2", "P3", "Tăng trưởng kinh tế và bảo vệ môi trường có thể song hành không? Nêu "
       "quan điểm có dẫn chứng.",
       "economy, economic, growth, environment, environmental, climate, pollution, "
       "sustainable, sustainability, energy, renewable, industry, development, carbon, "
       "emissions, policy"),
    _p("C2-P3-3", "P3", "Giáo dục nên ưu tiên kiến thức hàn lâm hay kỹ năng thực tiễn? Phân "
       "tích rồi kết luận.",
       "education, school, schools, university, academic, knowledge, theory, practical, "
       "skill, skills, curriculum, students, critical, thinking, creativity, career"),
    _p("C2-P4-1", "P4", "Hãy mô tả cách một chính sách công được hình thành, từ vấn đề ban đầu "
       "đến khi thực thi.",
       "policy, policies, government, problem, issue, research, data, law, laws, public, "
       "consultation, implement, implementation, evaluate, citizens, budget"),
    _p("C2-P4-2", "P4", "Hãy mô tả một quá trình khoa học hoặc công nghệ bạn hiểu rõ, giải "
       "thích từng giai đoạn.",
       "process, science, scientific, technology, research, experiment, data, test, "
       "results, stage, stages, step, develop, design, analysis, hypothesis"),
    _p("C2-P4-3", "P4", "Hãy mô tả quan điểm của bạn về một vấn đề quan trọng đã thay đổi theo "
       "thời gian như thế nào, và vì sao.",
       "opinion, view, views, perspective, change, changed, believe, believed, experience, "
       "issue, time, years, realize, realized, reason, influence"),
)  # fmt: skip
