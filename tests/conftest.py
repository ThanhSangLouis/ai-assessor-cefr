from __future__ import annotations

import os
import shutil
import subprocess

import pytest


@pytest.fixture
def make_symlink_or_skip():
    def create(link, target, *, target_is_directory=False):
        try:
            link.symlink_to(target, target_is_directory=target_is_directory)
        except NotImplementedError as error:
            pytest.skip(f"symlink creation is unavailable: {error}")
        except OSError as error:
            if os.name == "nt" and getattr(error, "winerror", None) == 1314:
                pytest.skip("symlink creation requires Windows Developer Mode or privilege")
            raise

    return create


@pytest.fixture
def grant_everyone_read_access():
    def grant(path):
        if os.name != "nt":
            raise AssertionError("grant_everyone_read_access is Windows-only")
        icacls = shutil.which("icacls")
        if icacls is None:
            pytest.skip("icacls is unavailable for Windows ACL test")
        result = subprocess.run(
            [icacls, str(path), "/grant", "*S-1-1-0:(R)"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr or result.stdout

    return grant

FEATURE_ORDER_V2 = (
    "n_words", "words_per_sec", "total_dur", "mean_word_len", "ttr", "log_uniq",
    "asr_conf_mean", "asr_conf_geo", "vad_silence_ratio", "vad_mean_pause",
    "vad_pause_per_min", "vad_long_pause_ratio", "vad_pause_sd", "vad_mean_seg_len",
    "vad_n_seg_per_min", "vad_articulation_rate", "vad_onset_delay", "vad_speech_sec",
)  # fmt: skip


@pytest.fixture
def feature_order_v2():
    """Đúng 18 tên đặc trưng của ridge_resp_v2, theo thứ tự artifact."""
    return FEATURE_ORDER_V2
