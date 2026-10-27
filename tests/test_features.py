"""Feature extraction tests. Cross-reference FR-14 to FR-17."""

from aicefr.contracts import ReasonCode, Word
from aicefr.features.extract import (
    ALL_FEATURES,
    PAUSE_MIN_S,
    FeatureExtractor,
    text_features,
    vad_features,
)


def test_returns_the_full_feature_set(words, segments):
    fs = FeatureExtractor().extract(words, segments, 21.0)
    assert fs.names == set(ALL_FEATURES)
    assert fs.feature_version == "v3"


def test_word_count_and_speech_rate(words):
    t = text_features(words, 20.0)
    assert t["n_words"] == 40
    assert t["words_per_sec"] == 2.0


def test_punctuation_stripped_when_counting_unique_words():
    ws = [
        Word(text="Hello,", start_s=0, end_s=0.3),
        Word(text="hello.", start_s=0.4, end_s=0.7),
    ]
    assert text_features(ws, 1.0)["ttr"] == 0.5


def test_filler_ratio(words):
    ws = words + [Word(text="um", start_s=20, end_s=20.2, prob=0.5)]
    assert text_features(ws, 21.0)["filler_ratio"] > 0


def test_pauses_measured_from_gaps_between_segments(segments):
    v = vad_features(segments, 21.0, 40)
    assert v["vad_silence_ratio"] > 0
    assert v["vad_mean_pause"] > PAUSE_MIN_S
    assert v["vad_onset_delay"] == 0.5


def test_no_speech_segments_yields_none_features(words):
    fs = FeatureExtractor().extract(words, [], 20.0)
    f = fs.feature("vad_silence_ratio")
    assert f is not None and not f.is_computable
    assert f.reason == ReasonCode.FEATURE_NOT_COMPUTABLE


def test_too_few_words_makes_lexical_features_none(segments):
    ws = [Word(text="hi", start_s=0, end_s=0.2, prob=0.9)]
    fs = FeatureExtractor().extract(ws, segments, 20.0)
    f = fs.feature("ttr")
    assert f is not None and not f.is_computable
    assert f.reason == ReasonCode.TOO_FEW_WORDS


def test_never_divides_by_zero():
    fs = FeatureExtractor().extract([], [], 0.0)
    assert all(f.value is None or isinstance(f.value, float) for f in fs.items)


def test_articulation_rate_exceeds_speech_rate(words, segments):
    fs = FeatureExtractor().extract(words, segments, 21.0)
    assert fs.value_of("vad_articulation_rate") > fs.value_of("words_per_sec")


def test_no_measurement_is_missing_without_a_reason(segments):
    """Khong mot dac trung nao duoc phep vang so ma khong noi vi sao.

    Truoc refactor, `text_features` tra `asr_conf_mean = None` khi khong tu nao
    mang xac suat, va khong ghi ly do vao dau ca -- trong khi chu thich ngay
    tren dong do viet "missing data returns None with a reason code". Loi nay
    song duoc vi gia tri va ly do nam o hai bang khac nhau.
    """
    khong_co_xac_suat = [
        Word(text=f"w{i}", start_s=i * 0.4, end_s=i * 0.4 + 0.3) for i in range(30)
    ]
    fs = FeatureExtractor().extract(khong_co_xac_suat, segments, 20.0)
    assert fs.feature("asr_conf_mean") is not None
    for f in fs.items:
        if not f.is_computable:
            assert f.reason is not None, f"dac trung {f.name!r} vang so ma khong co ly do"
