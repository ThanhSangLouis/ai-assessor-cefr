"""La chan hop le: nghi lac de va nghi doc lai de bai. D022.

Vi sao can. Mo hinh cham chu yeu bang do troi chay va do tin cay nhan dang;
no gan nhu khong nhin noi dung. Nhom Aalto (SLaTE 2025) do duoc: trao cau tra
loi giua cac phan de thi diem gan nhu khong doi (delta = 0,000). Nghia la mot
bai noi troi chay ve chu de khac, hoac doc to lai nguyen van de bai, van co the
nhan diem cao.

Hai phep do o day co tinh DON GIAN va GIAI THICH DUOC:

  * `keyword_relevance`: ty le tu khoa chu de (tieng Anh, gan voi tung de)
    co xuat hien trong loi noi, sau khi gop bien the -s/-ed/-ing. Bang 0 voi
    mot bai du dai nghia la nguoi noi khong cham toi chu de nao cua de. Phai
    dung danh sach tu khoa vi de bai trong he thong viet bang TIENG VIET.
  * `prompt_copy_ratio`: ty le cum 3 tu lien tiep cua loi noi trung nguyen van
    voi de bai. Cao nghia la doc lai de thay vi tra loi. Chi ap dung khi de bai
    viet bang tieng Anh (`is_english`); doc lai de tieng Viet thi LID da chan.

Ca hai CHI GAN CO va chuyen giang vien; KHONG tru diem. May chi nghi ngo, nguoi
quyet. Nguong dat than trong (xem ResponseProcessor) de khong phat nham bai A2
ngan, va chua duoc hieu chinh tren bai cua nguoi hoc Viet -- do la viec cua dot
thu du lieu.
"""

from __future__ import annotations

import re
from typing import Protocol

# Nguong than trong (D022). Chua hieu chinh tren bai nguoi hoc Viet.
MIN_WORDS_FOR_OFF_TOPIC = 30  # bai ngan qua thi khong du can cu de noi la lac de
MIN_WORDS_FOR_COPY = 10
COPY_RATIO_FLAG = 0.5


class TaskLike(Protocol):
    """Phan cua mot de bai ma la chan can. Khong phu thuoc tang luu tru."""

    prompt_text: str
    topic_keywords: tuple[str, ...]


_WORD = re.compile(r"[a-z]+(?:'[a-z]+)?")


def _stem(word: str) -> str:
    """Gop bien the hay gap nhat. Co y tho -- chi de 'travel/travelled/travelling'
    va 'favourite/favorite' khop nhau, khong phai mot bo tach goc tu day du."""
    word = word.replace("our", "or")
    for suffix in ("ing", "ed", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            word = word[: -len(suffix)]
            break
    if len(word) >= 4 and word[-1] == word[-2]:  # travell -> travel
        word = word[:-1]
    if len(word) >= 4 and word.endswith("e"):  # place/places, prepare/prepared
        word = word[:-1]
    return word


def tokens(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def keyword_relevance(transcript: str, keywords: tuple[str, ...]) -> float | None:
    """Ty le tu khoa chu de co mat trong loi noi. None khi de khong co tu khoa (de mo)."""
    wanted = {_stem(k.lower()) for k in keywords if k.strip()}
    if not wanted:
        return None
    said = {_stem(t) for t in tokens(transcript)}
    return len(wanted & said) / len(wanted)


def is_english(text: str, threshold: float = 0.9) -> bool:
    """De bai co viet bang tieng Anh khong -- chi khi do moi kiem doc lai de."""
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return False
    return sum(ch.isascii() for ch in letters) / len(letters) >= threshold


def prompt_copy_ratio(transcript: str, prompt: str, n: int = 3) -> float | None:
    """Ty le cum n tu cua loi noi trung nguyen van voi de bai. None neu bai qua ngan."""
    said = tokens(transcript)
    if len(said) < n:
        return None
    asked = tokens(prompt)
    prompt_grams = {tuple(asked[i : i + n]) for i in range(len(asked) - n + 1)}
    grams = [tuple(said[i : i + n]) for i in range(len(said) - n + 1)]
    return sum(g in prompt_grams for g in grams) / len(grams)


def validity_flags(transcript: str, task: TaskLike) -> list[str]:
    """Ten cac co hop le cho mot bai da cham. Rong neu khong co nghi ngo nao."""
    n = len(tokens(transcript))
    flags: list[str] = []
    rel = keyword_relevance(transcript, task.topic_keywords)
    if rel is not None and rel == 0 and n >= MIN_WORDS_FOR_OFF_TOPIC:
        flags.append("OFF_TOPIC_SUSPECTED")
    if is_english(task.prompt_text) and n >= MIN_WORDS_FOR_COPY:
        ratio = prompt_copy_ratio(transcript, task.prompt_text)
        if ratio is not None and ratio >= COPY_RATIO_FLAG:
            flags.append("PROMPT_COPY_SUSPECTED")
    return flags
