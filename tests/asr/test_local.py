from types import ModuleType, SimpleNamespace

import numpy as np
import pytest
from tests.asr.fixtures import audio

from aicefr.asr.local import _SMALL_MODEL_SHA256, FasterWhisperEngine
from aicefr.asr.service import AsrService, ModelUnavailableError
from aicefr.contracts import QCResult, QCStatus, ReasonCode


def model_dir(tmp_path):
    for filename in ("model.bin", "config.json", "tokenizer.json", "vocabulary.txt"):
        (tmp_path / filename).write_text("fixture")
    return tmp_path


def mock_small_hashes(monkeypatch, mismatched=()):
    calls = []

    def fake_hash(path):
        calls.append(path.name)
        if path.name in mismatched:
            return "0" * 64
        return _SMALL_MODEL_SHA256[path.name]

    monkeypatch.setattr("aicefr.asr.local._sha256_file", fake_hash)
    return calls


def test_missing_local_model_refuses_without_import_or_download(tmp_path):
    engine = FasterWhisperEngine(tmp_path / "absent")
    with pytest.raises(ModelUnavailableError):
        engine.transcribe(audio())


def test_local_adapter_passes_offline_english_word_timestamp_options(monkeypatch, tmp_path):
    seen = {}
    mock_small_hashes(monkeypatch)

    class Model:
        def transcribe(self, samples, **kwargs):
            seen["options"] = kwargs
            word = SimpleNamespace(word=" hello", start=0.1, end=0.4, probability=0.91)
            return iter([SimpleNamespace(text=" hello", words=[word])]), object()

    def constructor(path, **kwargs):
        seen["path"] = path
        seen["constructor"] = kwargs
        return Model()

    module = ModuleType("faster_whisper")
    module.WhisperModel = constructor
    monkeypatch.setitem(__import__("sys").modules, "faster_whisper", module)
    monkeypatch.setattr("importlib.metadata.version", lambda _: "1.2.3")
    result = FasterWhisperEngine(model_dir(tmp_path)).transcribe(audio())
    assert seen["constructor"]["local_files_only"] is True
    assert seen["constructor"]["cpu_threads"] == 1
    assert seen["options"]["language"] == "en"
    assert seen["options"]["word_timestamps"] is True
    assert seen["options"]["condition_on_previous_text"] is False
    assert result.engine_version == "1.2.3" and result.weight_name == "Systran/faster-whisper-small"
    assert result.test_only is False
    assert (result.words[0].text, result.words[0].prob) == (" hello", 0.91)


def test_language_detection_is_independent_and_does_not_decode_segments(monkeypatch, tmp_path):
    calls = []
    mock_small_hashes(monkeypatch)

    class Model:
        def transcribe(self, samples, **kwargs):
            calls.append((samples.size, kwargs))
            if kwargs["language"] is None:
                return object(), SimpleNamespace(language="vi", language_probability=0.93)
            word = SimpleNamespace(word=" hello", start=0.1, end=0.4, probability=0.91)
            return iter([SimpleNamespace(text=" hello", words=[word])]), object()

    module = ModuleType("faster_whisper")
    module.WhisperModel = lambda *_args, **_kwargs: Model()
    monkeypatch.setitem(__import__("sys").modules, "faster_whisper", module)
    monkeypatch.setattr("importlib.metadata.version", lambda _: "1.2.3")
    long_audio = audio()
    samples = np.zeros(16_000 * 31, dtype=np.float32)
    long_audio = long_audio.model_copy(update={"samples": samples, "duration_s": 31.0})

    result = FasterWhisperEngine(model_dir(tmp_path)).transcribe(long_audio)

    assert calls[0][0] == 16_000 * 30
    assert calls[0][1]["language"] is None
    assert calls[0][1]["word_timestamps"] is False
    assert (result.language, result.language_probability) == ("vi", 0.93)
    assert result.language_method == "faster-whisper-detect-v1"
    assert calls[1][1]["language"] == "en"


def test_unknown_weight_identity_is_preserved_for_refusal(monkeypatch, tmp_path):
    class Model:
        def transcribe(self, *_args, **_kwargs):
            return iter(()), object()

    module = ModuleType("faster_whisper")
    module.WhisperModel = lambda *_args, **_kwargs: Model()
    monkeypatch.setitem(__import__("sys").modules, "faster_whisper", module)
    monkeypatch.setattr("importlib.metadata.version", lambda _: "1.0")
    result = FasterWhisperEngine(model_dir(tmp_path), weight_name="small.en").transcribe(audio())
    assert result.weight_name == "Systran/faster-whisper-small.en"


def test_small_weight_hash_mismatch_refuses_before_engine_import(monkeypatch, tmp_path):
    model_dir(tmp_path)
    calls = mock_small_hashes(monkeypatch, mismatched=("model.bin",))
    with pytest.raises(ModelUnavailableError, match="provenance mismatch"):
        FasterWhisperEngine(tmp_path).transcribe(audio())
    assert calls == ["model.bin"]


def test_small_weight_is_hashed_once_and_loaded_once(monkeypatch, tmp_path):
    hashes = mock_small_hashes(monkeypatch)
    loads = []

    class Model:
        def transcribe(self, *_args, **_kwargs):
            return iter(()), object()

    module = ModuleType("faster_whisper")
    module.WhisperModel = lambda *_args, **_kwargs: loads.append(True) or Model()
    monkeypatch.setitem(__import__("sys").modules, "faster_whisper", module)
    monkeypatch.setattr("importlib.metadata.version", lambda _: "1.2.3")
    engine = FasterWhisperEngine(model_dir(tmp_path))
    engine.transcribe(audio())
    engine.transcribe(audio())
    assert hashes == list(_SMALL_MODEL_SHA256)
    assert len(loads) == 1


def test_noncanonical_identity_never_gets_small_alias(monkeypatch, tmp_path):
    model_dir(tmp_path)
    module = ModuleType("faster_whisper")
    module.WhisperModel = lambda *_args, **_kwargs: SimpleNamespace(
        transcribe=lambda *_args, **_kwargs: (iter(()), object())
    )
    monkeypatch.setitem(__import__("sys").modules, "faster_whisper", module)
    monkeypatch.setattr("importlib.metadata.version", lambda _: "1.2.3")
    engine = FasterWhisperEngine(tmp_path, weight_name="small.en")
    raw = engine.transcribe(audio())
    assert raw.weight_name == "Systran/faster-whisper-small.en"
    assert raw.weight_name != "Systran/faster-whisper-small"
    transcript = AsrService(lambda: engine, trained_asr_model="whisper-small").transcribe(
        "r-unknown", audio(), QCResult(status=QCStatus.PASS, qc_config_version="test")
    )
    assert transcript.asr_model is None
    assert ReasonCode.ASR_VERSION_MISMATCH in transcript.reasons


def test_asr_engine_exception_message_and_traceback_are_not_logged(caplog):
    secret = "TRANSCRIPT-SECRET-9981"

    class Broken:
        def transcribe(self, _audio):
            raise RuntimeError(secret)

    result = AsrService(lambda: Broken(), trained_asr_model="whisper-small").transcribe(
        "r-safe", audio(), QCResult(status=QCStatus.PASS, qc_config_version="test")
    )
    assert result.status.value == "ASR_FAILED"
    assert secret not in caplog.text
    assert "Traceback" not in caplog.text and "response_id=r-safe" in caplog.text
