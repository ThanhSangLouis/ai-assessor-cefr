"""Turning an uploaded file into PCM the pipeline can read. Implements FR-03, FR-39.

Two decoders, because the two ways a student can submit produce different
formats and only one of them is readable directly:

    file upload      .wav .flac        libsndfile reads these
    browser recorder .webm .mp4 .m4a   libsndfile does NOT read these

`MediaRecorder` produces WebM/Opus on Chrome and Firefox and MP4/AAC on Safari.
Neither is a format `soundfile` can open, so the recording path needs ffmpeg to
transcode first. That makes ffmpeg a system dependency of FR-39 and of nothing
else: without it the upload path still works perfectly, and the interface must
hide the record button rather than let a student talk for two minutes and then
fail.
"""

from __future__ import annotations

import io
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

import numpy as np
import soundfile as sf

from aicefr.contracts import ReasonCode

TARGET_SR = 16_000
FFMPEG_TIMEOUT_S = 30

# Hard ceilings for transcoding. A 24 MiB Opus file encoded at 6 kbps holds
# roughly nine hours of audio: ffmpeg will happily expand that into a gigabyte
# of WAV, and `soundfile` turns it into two gigabytes of float32 -- all before
# the quality check ever gets to say "too long". Both limits are enforced by
# ffmpeg itself, so nothing oversized is written or read.
MAX_DECODE_SECONDS = 330  # a little above the 300 s the quality check allows
MAX_OUTPUT_BYTES = 24 * 1024 * 1024  # 330 s of 16 kHz mono PCM is about 10 MiB
# Header vuot qua hai nguong nay la file hong hoac co y tan cong; QC von tu choi
# tren 2 kenh, va 192 kHz la tan so cao nhat cua thiet bi thu am pho thong.
MAX_CHANNELS = 8
MAX_SAMPLE_RATE = 192_000

# What each decoder is willing to open, by file extension.
NATIVE_SUFFIXES = {".wav", ".flac", ".ogg", ".aiff", ".au"}
COMPRESSED_SUFFIXES = {".webm", ".mp4", ".m4a", ".mp3", ".aac", ".opus", ".3gp"}


# Magic bytes, so the server decides what a file is instead of believing the
# extension the browser sent. An attacker renaming payload.exe to voice.wav
# gets rejected here rather than handed to ffmpeg.
MAGIC: tuple[tuple[bytes, int, str], ...] = (
    (b"RIFF", 0, "wav"),  # RIFF....WAVE
    (b"fLaC", 0, "flac"),
    (b"OggS", 0, "ogg"),
    (b"\x1a\x45\xdf\xa3", 0, "webm"),  # EBML header, used by WebM and MKV
    (b"ftyp", 4, "mp4"),  # ISO base media: MP4, M4A
    (b"ID3", 0, "mp3"),
)
SNIFF_BYTES = 16


def sniff(head: bytes) -> str | None:
    """Identify the container from its first bytes, or None if unrecognised."""
    for magic, offset, name in MAGIC:
        if head[offset : offset + len(magic)] == magic:
            return name
    # A bare MPEG frame has no ID3 tag: 11 set bits start the sync word.
    if len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0:
        return "mp3"
    return None


class DecodeError(Exception):
    """The bytes could not be turned into audio. Carries a message for the student."""


class DecodeBudgetExceeded(DecodeError):
    """SEC-02: header hua mot mang PCM lon hon ngan sach bo nho, nen khong giai ma.

    Mot file nen nho (FLAC im lang, header 192 kHz x 8 kenh) co the doi ~1,9 GiB
    float32 truoc khi QC kip noi "qua dai". Ket luan nay tinh tu header, truoc
    khi cap phat, va mang du so lieu de ghi log -- khong bao gio mang byte audio
    hay ten file goc.
    """

    reason = ReasonCode.AUDIO_TOO_LARGE

    def __init__(
        self, *, channels: int, sample_rate: int, frames: int, needed_bytes: int, budget_bytes: int
    ) -> None:
        self.channels = channels
        self.sample_rate = sample_rate
        self.declared_seconds = frames / sample_rate if sample_rate else 0.0
        self.needed_bytes = needed_bytes
        self.budget_bytes = budget_bytes
        super().__init__(
            "bản ghi giải mã ra quá lớn "
            f"({channels} kênh, {sample_rate} Hz, {self.declared_seconds:.0f} giây). "
            "Hãy nộp bản ghi mono hoặc stereo, tối đa 48 kHz."
        )

    def log_fields(self) -> str:
        """Chuoi `key=value` cho log `audio.decode_rejected`; khong co du lieu ca nhan."""
        return (
            f"reason=decoded_budget_exceeded channels={self.channels} rate={self.sample_rate} "
            f"declared_s={self.declared_seconds:.1f} needed={self.needed_bytes} "
            f"threshold={self.budget_bytes}"
        )


def _default_budget() -> int:
    from aicefr.config import get_settings

    return get_settings().max_decoded_pcm_bytes


def check_budget(channels: int, sample_rate: int, frames: int, budget_bytes: int) -> None:
    """Tu choi neu `frames` khung float32 MONO vuot `budget_bytes`.

    `frames` la so khung header khai, da cat o MAX_DECODE_SECONDS (phan vuot
    khong bao gio duoc doc). Bo giai ma tron ve mono theo tung khoi ~1 giay, nen
    mang giu lai la mono: ngan sach do dung phan do, khong nhan so kenh (kenh
    chi ton them mot khoi, va MAX_CHANNELS da chan header vo ly). `channels` giu
    lai de ghi log. Ham khong cap phat gi.
    """
    needed = max(0, frames) * 4
    if needed > budget_bytes:
        raise DecodeBudgetExceeded(
            channels=channels,
            sample_rate=sample_rate,
            frames=frames,
            needed_bytes=needed,
            budget_bytes=budget_bytes,
        )


def probe_budget(data, budget_bytes: int | None = None) -> None:
    """Chi doc header (WAV/FLAC/OGG...) roi kiem ngan sach; `data` la bytes hoac duong dan.

    Cho phia nhan file (core) tu choi som, truoc khi luu blob va xep hang. Header
    khong doc duoc thi bo qua: viec do cua bo giai ma o may cham, khong phai o day.
    """
    budget = _default_budget() if budget_bytes is None else budget_bytes
    try:
        with sf.SoundFile(io.BytesIO(data) if isinstance(data, bytes) else str(data)) as f:
            channels, rate, frames = f.channels, f.samplerate, f.frames
    except Exception:  # noqa: BLE001 - header la, de bo giai ma ket luan
        return
    if channels <= 0 or rate <= 0:
        return
    check_budget(channels, rate, min(max(frames, 0), int(MAX_DECODE_SECONDS * rate)), budget)


@lru_cache(maxsize=1)
def ffmpeg_available() -> bool:
    """Whether ffmpeg is on PATH.

    Cached: the answer cannot change while the process runs, and the interface
    asks on every page render.
    """
    return shutil.which("ffmpeg") is not None


def _to_mono(pcm: np.ndarray) -> np.ndarray:
    return pcm.mean(axis=1) if pcm.ndim > 1 else pcm


def _resample_to_target(pcm: np.ndarray, sr: int) -> tuple[np.ndarray, int]:
    """Bring any sample rate down to 16 kHz.

    44.1 kHz and 48 kHz are what phones and laptops actually record. Without
    this, an uploaded .wav at either rate was rejected outright with
    WRONG_SAMPLE_RATE, while the very same audio recorded in the browser sailed
    through -- because that path goes via ffmpeg, which resamples. Two ways of
    submitting the same recording behaved differently under one requirement.

    Linear interpolation rather than a windowed filter: the features that matter
    here are durations, pauses and word counts, none of which depend on faithful
    reproduction above 8 kHz. A proper anti-aliasing filter would be better for
    audio quality and would add a dependency for no measurable gain.
    """
    if sr == TARGET_SR or pcm.size == 0:
        return pcm, sr
    duration = pcm.size / sr
    target_length = int(duration * TARGET_SR)
    if target_length < 1:
        return pcm, sr
    source_positions = np.linspace(0.0, pcm.size - 1, target_length)
    return np.interp(source_positions, np.arange(pcm.size), pcm).astype(np.float32), TARGET_SR


class SoundFileDecoder:
    """Reads the formats libsndfile understands, with no external process."""

    name = "soundfile"

    def __init__(self, max_pcm_bytes: int | None = None) -> None:
        # None: doc AICEFR_MAX_DECODED_BYTES luc giai ma (SEC-02).
        self.max_pcm_bytes = max_pcm_bytes

    def can_decode(self, filename: str) -> bool:
        return Path(filename).suffix.lower() in NATIVE_SUFFIXES

    def decode(self, data: bytes, filename: str) -> tuple[np.ndarray, int]:
        budget = _default_budget() if self.max_pcm_bytes is None else self.max_pcm_bytes
        # Doc thang tu bo nho thay vi file tam: libsndfile mo duoc file-like, va
        # tren Windows mot NamedTemporaryFile dang mo khong mo lai duoc lan hai.
        try:
            f = sf.SoundFile(io.BytesIO(data))
        except Exception as e:
            raise DecodeError(f"không đọc được file audio: {e}") from e
        with f:
            channels, rate = f.channels, f.samplerate
            # FLAC/OGG nen rat manh: 600 giay im lang chi nang 28 KB, nen mot file
            # 25 MiB co the bung ra hang chuc GB float32 truoc khi QC kip noi "qua
            # dai" -- du de OOM-kill ca server. Gioi han nhu duong ffmpeg: doc toi
            # da MAX_DECODE_SECONDS, tu choi header vo ly ngay tu dau.
            if channels > MAX_CHANNELS or not 0 < rate <= MAX_SAMPLE_RATE:
                raise DecodeError(f"header audio bất thường ({channels} kênh, {rate} Hz)")
            cap = int(MAX_DECODE_SECONDS * rate)
            # SEC-02: kiem ngan sach tu so khung header khai, TRUOC khi cap phat.
            check_budget(channels, rate, min(max(f.frames, 0), cap), budget)
            # Doc tung khoi ~1 giay va tron ve mono ngay: dinh bo nho la mang mono
            # cong mot khoi, khong phai ca mang da kenh. Header co the noi doi so
            # khung, nen van dem tich luy va dung khi vuot ngan sach.
            parts: list[np.ndarray] = []
            total = 0
            try:
                while total < cap:
                    block = f.read(min(rate, cap - total), dtype="float32", always_2d=True)
                    if not len(block):
                        break
                    total += len(block)
                    check_budget(channels, rate, total, budget)
                    parts.append(_to_mono(block) if channels > 1 else block[:, 0].copy())
            except DecodeError:
                raise
            except Exception as e:
                raise DecodeError(f"không đọc được file audio: {e}") from e
        pcm = np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)
        return _resample_to_target(pcm, rate)


class FfmpegDecoder:
    """Transcodes anything ffmpeg understands into 16 kHz mono WAV.

    Resamples to 16 kHz here rather than later because the quality checks and
    the feature extractor both assume that rate, and a mismatch shows up as a
    wrong duration rather than as an error.
    """

    name = "ffmpeg"

    def __init__(self, max_pcm_bytes: int | None = None) -> None:
        self.max_pcm_bytes = max_pcm_bytes

    def can_decode(self, filename: str) -> bool:
        if not ffmpeg_available():
            return False
        return Path(filename).suffix.lower() in COMPRESSED_SUFFIXES

    def decode(self, data: bytes, filename: str) -> tuple[np.ndarray, int]:
        if not ffmpeg_available():
            raise DecodeError("máy chủ chưa cài ffmpeg nên không đọc được định dạng này")
        suffix = Path(filename).suffix.lower() or ".webm"
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / f"in{suffix}"
            dst = Path(d) / "out.wav"
            src.write_bytes(data)
            try:
                subprocess.run(
                    # -vn drops any video track a browser may have attached;
                    # -ac 1 mixes to mono; -ar sets the sample rate; -t and -fs
                    # cap how much audio and how many bytes may come out.
                    [
                        "ffmpeg",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-y",
                        "-i",
                        str(src),
                        "-vn",
                        "-ac",
                        "1",
                        "-ar",
                        str(TARGET_SR),
                        # Hard ceilings, enforced by ffmpeg so nothing oversized
                        # is ever written to disk or read into memory.
                        "-t",
                        str(MAX_DECODE_SECONDS),
                        "-fs",
                        str(MAX_OUTPUT_BYTES),
                        "-f",
                        "wav",
                        str(dst),
                    ],
                    check=True,
                    capture_output=True,
                    timeout=FFMPEG_TIMEOUT_S,
                )
            except subprocess.TimeoutExpired as e:
                raise DecodeError("chuyển mã quá lâu, bản ghi có thể bị hỏng") from e
            except subprocess.CalledProcessError as e:
                detail = e.stderr.decode("utf-8", "replace").strip().splitlines()
                raise DecodeError(
                    f"không chuyển mã được bản ghi: {detail[-1] if detail else 'lỗi không rõ'}"
                ) from e
            # Dau ra da bi -t/-fs chan (16 kHz mono, <= 24 MiB), nhung van kiem
            # cung mot ngan sach de hai duong giai ma co mot quy tac (SEC-02).
            try:
                out = sf.info(str(dst))
            except Exception as e:
                raise DecodeError(f"không đọc được bản chuyển mã: {e}") from e
            budget = _default_budget() if self.max_pcm_bytes is None else self.max_pcm_bytes
            check_budget(out.channels, out.samplerate, out.frames, budget)
            pcm, sr = sf.read(str(dst), dtype="float32")
        return _to_mono(np.asarray(pcm)), sr


class FirstMatchDecoder:
    """Hands the file to the first decoder that claims it.

    A composite so the API has one thing to call and does not have to know
    which formats need an external process. Adding a third decoder later means
    adding it to the list, not editing the endpoint.
    """

    name = "first-match"

    def __init__(self, decoders: list | None = None, max_pcm_bytes: int | None = None) -> None:
        self.decoders = (
            decoders
            if decoders is not None
            else [SoundFileDecoder(max_pcm_bytes), FfmpegDecoder(max_pcm_bytes)]
        )

    def can_decode(self, filename: str) -> bool:
        return any(d.can_decode(filename) for d in self.decoders)

    def decode(self, data: bytes, filename: str) -> tuple[np.ndarray, int]:
        """Try each decoder that claims the name, and keep going if one fails.

        Falling through matters because a file name lies more often than you
        would think. The browser recorder produces WebM/Opus; a student who
        downloads it and re-uploads it hands us `recording.wav` containing a
        Matroska stream. The name routes it to `soundfile`, which cannot read
        Matroska -- and before this loop kept going, that single failure was the
        end of it, even though ffmpeg two lines below handles the file fine.
        """
        tried: list[str] = []
        first_error: Exception | None = None
        for d in self.decoders:
            if not d.can_decode(filename):
                continue
            try:
                return d.decode(data, filename)
            except DecodeBudgetExceeded:
                # Doc duoc header va no qua lon: day la ket luan, khong phai loi
                # dinh dang -- dua sang ffmpeg chi ton them CPU (SEC-02).
                raise
            except DecodeError as e:
                tried.append(d.name)
                first_error = first_error or e

        # Last resort: the name has now proved itself wrong, so stop trusting it
        # and offer the bytes to the decoders that did not claim them. ffmpeg
        # reads the container header rather than the extension, which is exactly
        # what is needed once the extension is known to be a lie.
        if first_error is not None:
            for d in self.decoders:
                if d.can_decode(filename):
                    continue
                try:
                    return d.decode(data, filename)
                except DecodeBudgetExceeded:
                    raise
                except DecodeError:
                    tried.append(d.name)

            raise DecodeError(
                f"không giải mã được bằng {', '.join(tried)}: {first_error}"
            ) from first_error

        raise DecodeError(
            f"định dạng {Path(filename).suffix or 'không rõ'} không được hỗ trợ. "
            "Hãy nộp file wav hoặc flac."
        )
