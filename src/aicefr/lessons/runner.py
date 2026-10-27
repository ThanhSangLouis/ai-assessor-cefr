"""Take one recorded step from audio to a measured result (D025).

The same front end as an assessment -- quality check, VAD before recognition,
the language guard, the repetition guard -- and then the step checker instead
of the scoring model. A step recording is short (a sentence takes three to six
seconds), so it gets its own quality profile: the 20-second floor exists for
the SCORING MODEL, which never sees a practice step.
"""

from __future__ import annotations

import logging

import numpy as np

from aicefr.asr.base import AsrError
from aicefr.asr.hallucination import detect_repetition
from aicefr.contracts import QcStatus, ReasonCode
from aicefr.lessons.checks import StepChecker
from aicefr.lessons.model import Step, StepResult
from aicefr.pipeline import LID_MIN_PROB, trim_to_speech
from aicefr.ports import AsrEngine, VoiceActivityDetector
from aicefr.qc.audio_qc import AudioQualityChecker, QcThresholds

logger = logging.getLogger(__name__)

PRACTICE_QC = QcThresholds(
    min_duration_s=1.0,
    review_duration_s=1.0,
    max_duration_s=200.0,
    # A short clip is mostly the pause before and after the sentence; silence
    # only rejects a recording that is essentially empty.
    review_silence_ratio=0.9,
    max_silence_ratio=0.97,
)
PRACTICE_QC_VERSION = "qc-practice-v1"

QC_TIPS = {
    ReasonCode.AUDIO_TOO_SHORT: "Bản ghi quá ngắn. Bấm ghi, nói hết câu rồi mới dừng.",
    ReasonCode.AUDIO_TOO_LONG: "Bản ghi quá dài cho bước này. Ghi lại, nói gọn hơn.",
    ReasonCode.AUDIO_TOO_LARGE: "File quá lớn. Ghi lại ngay trên trang thay vì tải file.",
    ReasonCode.CLIPPING_DETECTED: "Âm thu quá to nên bị méo. Để micro xa miệng hơn rồi ghi lại.",
    ReasonCode.HIGH_SILENCE_RATIO: "Bản ghi gần như im lặng. Kiểm tra micro rồi ghi lại.",
    ReasonCode.LOW_SNR: "Tiếng ồn nền lấn át giọng nói. Tìm chỗ yên tĩnh hơn rồi ghi lại.",
    ReasonCode.WRONG_SAMPLE_RATE: "Không đọc được bản ghi này. Ghi lại ngay trên trang.",
}


def practice_quality_checker() -> AudioQualityChecker:
    return AudioQualityChecker(PRACTICE_QC, PRACTICE_QC_VERSION)


class LessonRunner:
    """Measure one recorded step. Collaborators are injected, as in ResponseProcessor."""

    def __init__(
        self,
        asr_engine: AsrEngine,
        vad: VoiceActivityDetector,
        quality_checker: AudioQualityChecker | None = None,
        checker: StepChecker | None = None,
        lid_min_prob: float = LID_MIN_PROB,
    ) -> None:
        self.asr_engine = asr_engine
        self.vad = vad
        self.quality_checker = quality_checker or practice_quality_checker()
        self.checker = checker or StepChecker()
        self.lid_min_prob = lid_min_prob

    def _unmeasured(self, step: Step, reasons: list[ReasonCode], tip: str) -> StepResult:
        return StepResult(
            step_id=step.step_id,
            kind=step.kind,
            passed=False,
            measured=False,
            reasons=reasons,
            tip=tip,
        )

    def run(
        self,
        step: Step,
        pcm: np.ndarray,
        sr: int,
        channels: int = 1,
        size_bytes: int | None = None,
        round_index: int | None = None,
        answers: list[str] | None = None,
    ) -> StepResult:
        qc = self.quality_checker.check(pcm, sr, channels=channels, size_bytes=size_bytes)
        if qc.qc_status is QcStatus.REJECT:
            first = next((QC_TIPS[r] for r in qc.reasons if r in QC_TIPS), None)
            return self._unmeasured(step, qc.reasons, first or "Bản ghi chưa dùng được. Ghi lại.")

        segments = self.vad.segments(pcm, sr)
        if not segments:
            return self._unmeasured(
                step,
                [ReasonCode.ASR_EMPTY_TRANSCRIPT],
                "Máy chưa nghe thấy tiếng nói. Nói gần micro hơn rồi ghi lại.",
            )
        trimmed, offset_s = trim_to_speech(pcm, sr, segments)
        try:
            # Never a prompt with the expected text: it pulls the transcript
            # toward the text instead of what the learner said.
            asr = self.asr_engine.transcribe(trimmed, sr)
        except AsrError:
            logger.warning("recogniser failed on a lesson step")
            return self._unmeasured(
                step, [ReasonCode.ASR_FAILED], "Máy nhận dạng gặp lỗi. Thử ghi lại sau ít giây."
            )

        if asr.is_foreign(self.lid_min_prob):
            return self._unmeasured(
                step,
                [ReasonCode.LANGUAGE_NOT_ENGLISH],
                "Bản ghi có vẻ không phải tiếng Anh. Hãy nói lại bằng tiếng Anh.",
            )

        extra: list[ReasonCode] = []
        finding = detect_repetition(asr.words)
        if finding.detected:
            asr = asr.cut_at(finding.keep_until_index)
            extra.append(ReasonCode.ASR_HALLUCINATION)

        asr = asr.shifted(offset_s)

        result = self.checker.check(step, asr, segments, round_index=round_index, answers=answers)
        result.reasons = [*result.reasons, *qc.reasons, *extra]
        return result
