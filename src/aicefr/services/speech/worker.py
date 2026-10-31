"""The speech service: the only place a recogniser runs (D043).

Two kinds of work, both from the bus:

* **scoring** (`speech.score`, a work queue): an assessment or practice
  response. The message names the recording's key in the blob store and carries
  everything the pipeline needs that would otherwise come from a database --
  the task, the QC thresholds in force, the scoring model's name -- so this
  service keeps no store. It reports back on `assessment.scoring`: once when it
  starts, once with the report or the reason it failed.
* **a lesson step** (`speech.step`, request-reply): the learner is waiting, so
  the learning service asks and blocks for the measured `StepResult`.

Nothing escapes a handler. A response that started must end, scored or failed;
a step that cannot be read answers with the reason, which the learning
service turns into the 415 the learner sees.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Callable

from aicefr.asr.fake import FakeAsrEngine
from aicefr.audio.decoder import DecodeError, FirstMatchDecoder
from aicefr.config import Settings
from aicefr.contracts import ProcessingRequest, ReasonCode, ResponseStatus
from aicefr.observability import observe
from aicefr.pipeline import ResponseProcessor
from aicefr.ports import BlobStore
from aicefr.qc import audio_qc
from aicefr.storage.task_repository import Task, task_from_message

logger = logging.getLogger(__name__)

SCORE_QUEUE = "speech.score"
STEP_QUEUE = "speech.step"
PROBE_QUEUE = "speech.probe"
RESULT_QUEUE = "assessment.scoring"
STEP_TIMEOUT_S = 120.0


def fake_engine_from_env() -> FakeAsrEngine:
    """Engine gia lap, chinh duoc qua bien moi truong de tai hien tung tinh huong.

    AICEFR_FAKE_TRANSCRIPT: cau chep gia lap (mac dinh 24 tu -- qua ngan de duoc
    cham voi bai 40-60 giay, nen moi bai deu ra "chua cham"). AICEFR_FAKE_LANGUAGE:
    ket qua doan ngon ngu dang `vi:0.95`. Chi dung cho chay thu va demo du phong;
    diem tu ban chep gia lap KHONG co y nghia.
    """
    language, prob = None, None
    raw = os.getenv("AICEFR_FAKE_LANGUAGE", "").strip()
    if raw:
        code, _, p = raw.partition(":")
        try:
            language, prob = code.strip() or None, float(p) if p else None
        except ValueError:
            # Sai dinh dang thi bo qua co chu dich: neu nem loi o day, MOI bai nop
            # deu thanh FAILED vi engine duoc tao luc chay job dau tien.
            logger.warning("AICEFR_FAKE_LANGUAGE sai dinh dang %r, can dang vi:0.95", raw)
            language, prob = None, None
    return FakeAsrEngine(
        transcript=os.getenv("AICEFR_FAKE_TRANSCRIPT") or None,
        language=language,
        language_probability=prob,
    )


class SpeechWorker:
    """The recogniser and what is built on it, once per process."""

    def __init__(
        self,
        settings: Settings,
        blobs: BlobStore,
        report: Callable[[dict], None],
        decoder: FirstMatchDecoder | None = None,
    ) -> None:
        self.settings = settings
        self.blobs = blobs
        self.report = report  # sends one message to the assessment service
        self.decoder = decoder or FirstMatchDecoder()
        # Cap on how many recordings are transcribed at once, scoring and steps
        # together. Dozens of Whisper copies competing for memory swap the
        # machine and stall everything; one student with a loop is enough.
        self.slots = threading.Semaphore(settings.max_concurrent_jobs)
        self._engine = None
        self._processors: dict[tuple[str, str], ResponseProcessor] = {}
        self._tasks: dict[str, Task] = {}
        # Built on first use; a test swaps in its own (`LessonRunner` with a fake engine).
        self.runner = None

    # ------------------------------------------------------------ what runs

    def engine(self):
        """Load the engine once, selected through the AICEFR_ASR environment variable.

        The default is the fake engine so tests run fast and need no model
        download. For a demo or a real run, AICEFR_ASR=whisper must be set;
        otherwise the transcript is a fixed string and the scores mean NOTHING.
        """
        if self._engine is None:
            if self.settings.asr_engine == "whisper":
                from aicefr.asr.whisper_adapter import WhisperEngine, threads_per_job

                self._engine = WhisperEngine(
                    model=self.settings.whisper_model or None,
                    temperature=self.settings.asr_temperature,
                    cpu_threads=threads_per_job(self.settings.max_concurrent_jobs),
                )
            else:
                self._engine = fake_engine_from_env()
        return self._engine

    def warm_up(self) -> None:
        """Load the recogniser before the first recording arrives (D066).

        Runs in the background at start-up; a failure is logged and left to
        the first real job, which reports it the usual way.
        """
        engine = self.engine()
        if not hasattr(engine, "warm_up"):
            return
        try:
            engine.warm_up()
            logger.info("recogniser loaded: %s", getattr(engine, "model", "?"))
        except Exception:  # noqa: BLE001 - the first job will say what is wrong
            logger.warning("could not load the recogniser ahead of time", exc_info=True)

    def processor(self, qc: dict, model: str) -> ResponseProcessor:
        """The pipeline for these thresholds and this model, built once and reused.

        Building it per job would reload the scoring artifact and the voice
        activity model every time. A new QC version or model name -- an
        administrator's change -- builds a new one.
        """
        key = (qc["version"], model)
        if key not in self._processors:
            from aicefr.scoring.scorer import RidgeScorer

            self._processors[key] = ResponseProcessor(
                self.engine(),
                quality_checker=audio_qc.AudioQualityChecker(
                    audio_qc.QcThresholds(**qc["thresholds"]), qc["version"]
                ),
                scorer=RidgeScorer(model),
                task_lookup=self._tasks.get,
            )
        return self._processors[key]

    def lesson_runner(self):
        """The pipeline front end for lesson steps (D025), built once like the processor.

        The detector is looked up on `aicefr.pipeline` at build time, so a test
        that swaps it there swaps it for lesson steps too.
        """
        if self.runner is None:
            from aicefr import pipeline as _pipeline
            from aicefr.lessons.runner import LessonRunner

            self.runner = LessonRunner(self.engine(), _pipeline.default_vad())
        return self.runner

    # ------------------------------------------------------------ scoring

    def score(self, job: dict) -> None:
        """Score one response. Never let an exception escape.

        If one escapes, the response stays at RUNNING and the submitter waits
        for a page that never changes.
        """
        rid = job["response_id"]
        purpose = "practice" if job.get("priority", 1) > 1 else "assessment"
        # D051: how long the job waited for a free worker -- the number to watch
        # when deciding to run a second speech instance.
        if isinstance(job.get("enqueued_at"), (int, float)):
            observe("job_queue_wait_seconds", max(0.0, time.time() - job["enqueued_at"]),
                    queue="speech.score", purpose=purpose)  # fmt: skip
        with self.slots:
            start = time.perf_counter()
            outcome = "ok"
            try:
                self._score(job)
            except BaseException:
                outcome = "error"
                # A missing recording raises FileNotFoundError, which is not a
                # DecodeError; whatever it is, the response is closed out.
                logger.exception("scoring failed for %s", rid)
                try:
                    self.report(
                        {"response_id": rid, "failed": ReasonCode.PROCESSING_INTERRUPTED.value}
                    )
                except Exception:  # noqa: BLE001 - the assessment service's sweep closes it
                    logger.exception("could not report the failure of %s", rid)
            finally:
                # What one run costs in time, the base of its price (D049, D051).
                observe("job_seconds", time.perf_counter() - start, queue="speech.score",
                        purpose=purpose, outcome=outcome)  # fmt: skip

    def _score(self, job: dict) -> None:
        rid = job["response_id"]
        self.report({"response_id": rid, "status": ResponseStatus.RUNNING.value})
        try:
            # Decoding happens here, not where the recording was received:
            # transcoding a five-minute WebM through ffmpeg takes seconds, and
            # the submission answers "202" within 300 ms.
            pcm, sr = self.decoder.decode(self.blobs.get(job["audio_key"]), job["audio_key"])
        except (DecodeError, OSError) as e:
            logger.warning("decode failed for %s: %s", rid, e)
            self.report({"response_id": rid, "failed": ReasonCode.AUDIO_UNSUPPORTED.value})
            return
        task = task_from_message(job["task"])
        self._tasks[task.task_id] = task
        request = ProcessingRequest.model_validate(job["request"])
        try:
            report = self.processor(job["qc"], job["model"]).process(request, pcm, sr)
        except Exception:  # noqa: BLE001 - catching everything is intentional, see `score`
            logger.exception("pipeline hỏng khi chấm bài %s", rid)
            self.report({"response_id": rid, "failed": ReasonCode.PROCESSING_INTERRUPTED.value})
            return
        self.report(
            {
                "response_id": rid,
                "report": report.model_dump(mode="json"),
                "speaker_id": job["speaker_id"],
                "task_id": job["task_id"],
                "account_id": job["account_id"],
            }
        )

    # ------------------------------------------------------------ lesson steps

    def step(self, req: dict) -> dict:
        """Measure one recorded lesson step; `{"result": ...}` or `{"error": ...}`."""
        from aicefr.lessons.model import Step

        try:
            pcm, sr = self.decoder.decode(self.blobs.get(req["audio_key"]), req["audio_key"])
        except (DecodeError, OSError) as e:
            return {"error": "decode", "detail": str(e)}
        step = Step.model_validate(req["step"])
        with self.slots:
            result = self.lesson_runner().run(
                step,
                pcm,
                sr,
                size_bytes=req.get("size"),
                round_index=req.get("round_index"),
                answers=req.get("answers"),
            )
        return {"result": result.model_dump(mode="json")}

    def probe(self, req: dict) -> dict:
        """Can this recording be read? `{"seconds": ...}` or `{"error": "decode"}`.

        For a recording that is stored rather than measured -- a teacher's model
        audio -- so nothing unplayable is ever attached to a lesson.
        """
        try:
            pcm, sr = self.decoder.decode(self.blobs.get(req["audio_key"]), req["audio_key"])
        except (DecodeError, OSError) as e:
            return {"error": "decode", "detail": str(e)}
        return {"seconds": round(len(pcm) / sr, 2)}

    # ------------------------------------------------------------ health

    def health(self) -> dict:
        from aicefr.audio.decoder import ffmpeg_available

        eng = self.engine()
        return {
            "asr_engine": eng.name,
            "asr_is_real": eng.name != "fake",
            # "fallback" or a fixed temperature; None for the fake engine.
            "asr_decoding": getattr(eng, "decoding", None),
            "recording_enabled": ffmpeg_available(),
        }
