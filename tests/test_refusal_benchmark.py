"""Co che cua refusal benchmark (D022). So do that can model Whisper va clip that."""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "refusal_benchmark", pathlib.Path("tools/refusal_benchmark.py")
)
bench = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(bench)


@pytest.mark.parametrize(
    ("k", "n", "expected"),
    [
        (0, 10, (0.0, 0.2775)),  # 0/10 van chua phai "khong bao gio": tran 27,8%
        (5, 10, (0.2366, 0.7634)),
        (100, 100, (0.963, 1.0)),
    ],
)
def test_wilson_interval(k, n, expected) -> None:
    assert bench.wilson(k, n) == pytest.approx(expected, abs=1e-3)


def test_wilson_on_an_empty_group_is_undefined() -> None:
    assert bench.wilson(0, 0) is None


def test_silence_and_too_short_clips_are_never_issued(tmp_path) -> None:
    bench.synthesize(tmp_path, n=2)
    result = bench.run(tmp_path, bench.build_processor("fake"))
    cats = result["per_category"]
    assert set(cats) == {"silence", "noise", "music", "too_short"}
    for cat in ("silence", "too_short"):
        assert cats[cat]["n"] == 2 and cats[cat]["issued"] == 0 and cats[cat]["scored"] == 0
    fsr = result["false_score_rate"]
    assert fsr["n"] == 8 and fsr["wilson95"] is not None
    # Khong co nhom hop le thi ty le tu choi nham khong xac dinh, khong phai 0.
    assert result["false_refusal_rate"]["rate"] is None


def test_unknown_folders_are_ignored(tmp_path) -> None:
    bench.synthesize(tmp_path, n=1)
    (tmp_path / "linh_tinh").mkdir()
    result = bench.run(tmp_path, bench.build_processor("fake"))
    assert "linh_tinh" not in result["per_category"]
