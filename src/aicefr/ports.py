"""Abstractions the business layer depends on. Ports in the ports-and-adapters sense.

Every port is declared *here*, inside the business layer, and implemented out in
the infrastructure layer. That direction is the whole point: the business layer
never names a concrete technology, so on the class diagram every arrow crossing
the package boundary points inward.

    "Depend upon Abstractions. Do not depend upon concretions."
    -- Robert C. Martin, Design Principles and Design Patterns, 2000

    "code pertaining to the inside part should not leak into the outside part"
    -- Alistair Cockburn, Hexagonal Architecture

Concretely: `ResponseProcessor` talks to `AsrEngine`, never to `WhisperEngine`.
Swapping Whisper for another recogniser, or for the fake used in tests, touches
no business code at all.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np

from aicefr.billing.payments import Ack, Checkout, Incoming, PaymentResult
from aicefr.contracts import Assessment, FeatureSet, Response, Status, Transcript


@runtime_checkable
class AsrEngine(Protocol):
    """Turns audio into a transcript with word timings."""

    name: str

    def transcribe(self, pcm: np.ndarray, sr: int) -> Transcript: ...


@runtime_checkable
class VoiceActivityDetector(Protocol):
    """Splits audio into speech segments, as (start, end) pairs in seconds.

    A port rather than a plain helper because the choice of detector changes the
    numbers the model was trained on: the same detector must be used for
    training and for inference, so it has to be swappable and explicit.
    """

    name: str

    def segments(self, pcm: np.ndarray, sr: int) -> list[tuple[float, float]]: ...


@runtime_checkable
class AudioDecoder(Protocol):
    """Turns uploaded bytes into mono PCM.

    A port because the two submission routes need different machinery: an
    uploaded .wav is read in-process, while a browser recording is WebM or MP4
    and needs ffmpeg. The API asks the port, not the format.
    """

    name: str

    def can_decode(self, filename: str) -> bool: ...

    def decode(self, data: bytes, filename: str) -> tuple[np.ndarray, int]: ...


@runtime_checkable
class Scorer(Protocol):
    """Turns a feature set into an assessment."""

    model_version: str

    def score(self, features: FeatureSet) -> Assessment: ...

    def contributions(self, features: FeatureSet) -> dict[str, float]:
        """How many points each measurement added to or took from the score.

        Exposed on the port rather than letting callers read the model file,
        so the advice layer never learns what shape the artifact has. A scorer
        that cannot explain itself returns an empty mapping, and the report
        simply carries no practice priorities -- which is the honest outcome.
        """
        ...


@runtime_checkable
class BlobStore(Protocol):
    """Stores the audio itself, separately from the metadata about it.

    A port because this is the first thing that breaks when the system stops
    being one machine. Today recordings sit on local disk, which is correct and
    cheap for one process. The moment a second instance runs, that instance
    cannot read them: the review queue shows a response and the player returns
    404, on one node out of two, intermittently.

    Swapping to object storage then touches this adapter and nothing else --
    not the endpoints, not the pipeline, not the repository.
    """

    def put(self, key: str, data: bytes) -> str: ...

    def get(self, key: str) -> bytes: ...

    def local_path(self, key: str) -> Path | None:
        """A real file path when one exists, so audio can be streamed with Range.

        Returns None for backends that have no local file, and the caller falls
        back to streaming the bytes.
        """
        ...

    def delete(self, key: str) -> None: ...

    def exists(self, key: str) -> bool: ...

    def size(self, key: str) -> int | None: ...

    def keys(self) -> Iterator[str]:
        """Every stored key, for the orphan sweep."""
        ...


@runtime_checkable
class JobQueue(Protocol):
    """Hands work to whatever runs it.

    Today that is Starlette's background tasks, in this process. That choice is
    right for one machine and wrong for two: the work is invisible to any other
    instance, it dies with the process, and there is no retry.

    Declaring it as a port now means moving to a real broker later is a new
    adapter plus a worker entry point -- the endpoint that enqueues does not
    change, and neither does anything it calls.
    """

    name: str

    def enqueue(self, func, /, *args, **kwargs) -> None: ...


@runtime_checkable
class RateLimiter(Protocol):
    """Counts events per key inside a time window.

    In memory today. That is not merely a scaling limit but a correctness one
    once there are several instances: a limit of ten per minute becomes ten per
    minute *per instance*, so the protection weakens exactly as the deployment
    grows. A shared counter fixes it, and only this adapter changes.
    """

    def hit(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        """Record one event. Returns False when the caller is over the limit."""
        ...


@runtime_checkable
class ResponseStore(Protocol):
    """Persists processing reports and answers questions about them.

    HAY DOC KY GIOI HAN NAY TRUOC KHI TIN VAO NO.

    Ba phuong thuc duoi day la tat ca nhung gi mot bai nop can de di tu luc
    nhan toi luc co ket qua, va `tests/test_ports.py` ghim rang `Repository`
    thoa chung. Nhung day KHONG phai mot seam co the thay the duoc hom nay:

    * `pipeline.py` khong cham vao luu tru chut nao -- no nhan PCM va tra ve
      mot Response. Nguoi goi ba phuong thuc nay la tang web.
    * `api/main.py` khoi tao `repo = Repository()` bang kieu CU THE, va goi
      hon hai muoi phuong thuc khac khong nam trong cong nay: apply_review,
      queue_with_locks, cohort_stats, erase_speaker, write_audit...

    Nghia la doi kho du lieu khong phai "viet mot bo chuyen doi ba phuong thuc"
    ma la viet lai gan nhu toan bo `Repository` -- dung nhu D048 da lam khi
    chuyen sang MongoDB. So do kien truc
    vi the KHONG ve cong nay nhu mot seam -- ve nhu the la hua mot thu chua co.

    Doi chung cho mot cong that su dung duoc: `BlobStore`, duoc khai kieu
    tuong minh tai `blobs: BlobStore = LocalBlobStore(...)`.
    """

    def save(
        self,
        report: Response,
        speaker_id: str,
        task_id: str,
        account_id: str | None = None,
        audio_path: str | None = None,
    ) -> None: ...

    def get(self, response_id: str) -> Response | None: ...

    def set_status(self, response_id: str, status: Status, reasons: list | None = None) -> None: ...


@runtime_checkable
class PaymentGateway(Protocol):
    """Where an institution pays for a plan (D033, D035).

    Four adapters: `SandboxGateway`, a page inside the app where no money
    moves; `VnpayGateway` and `MomoGateway`, the Vietnamese gateways, which
    sign their results into an address; `StripeGateway`, whose page is opened
    through its API and whose events come signed to a webhook. A deployment may
    offer several at once and the administrator picks one per order. Another
    gateway is one more adapter: the order, the licence it buys and the checks
    on the result do not change.
    """

    name: str  # in addresses and on each order: "stripe"
    title: str  # what the administrator reads: "Stripe"
    methods: str  # how the payer pays there, in a few words
    live: bool  # True when real money moves
    note: str  # how to pay in the gateway's test environment; "" when live

    def checkout(
        self,
        order_id: str,
        amount_vnd: int,
        description: str,
        return_url: str,
        notify_url: str,
        client_ip: str,
        now: datetime,
    ) -> Checkout:
        """Where to send the payer's browser to pay this order.

        Raises GatewayError when the gateway, asked first, will not open it.
        """
        ...

    def return_reference(self, query: Mapping[str, str]) -> str | None:
        """The checkout a return address names, when its result must be asked for (Stripe).

        None when the address carries the signed result itself. The service
        asks the gateway only about a checkout one of its orders opened.
        """
        ...

    def verify_return(self, query: Mapping[str, str]) -> PaymentResult | None:
        """The result the browser's return address stands for; None when it is not the gateway's.

        May ask the gateway (Stripe) and raise GatewayError when it cannot.
        """
        ...

    def verify_notification(self, message: Incoming, now: datetime) -> PaymentResult | None:
        """The result a message from the gateway's server carries; None when not signed by it."""
        ...

    def acknowledge(self, what: str) -> Ack:
        """The answer the gateway's server expects, for what `BillingService.settle` did."""
        ...
