"""Shared fixtures. Synthetic data only, never real human audio."""

import os
import uuid
from pathlib import Path

import numpy as np
import pytest

# Tests observe a finished result instead of polling, so jobs run on the calling
# thread. Set before any import of the application, because the queue adapter is
# chosen once at module import.
os.environ.setdefault("AICEFR_JOB_MODE", "inline")

# The real scoring artifacts stay outside Git (W7-S01). Tests always score with
# the synthetic ones from tools/make_fake_models.py, pinned by their own hashes,
# even when the machine running them has AICEFR_MODEL_DIR set to the real folder.
os.environ["AICEFR_MODEL_DIR"] = str(Path(__file__).parent / "fixtures" / "models")
os.environ["AICEFR_MODEL_PINS"] = ",".join(
    f"{name.removesuffix('.json')}={digest}"
    for digest, name in (
        line.split()
        for line in (Path(os.environ["AICEFR_MODEL_DIR"]) / "SHA256SUMS").read_text().splitlines()
        if line
    )
)

from aicefr.contracts import Feature, FeatureSet, ReasonCode, Word

SR = 16_000


@pytest.fixture(autouse=True)
def _isolated_environment(tmp_path, monkeypatch):
    """Moi test co CSDL va thu muc upload rieng, bat ke may dang dat bien gi.

    main.py doc AICEFR_DB/AICEFR_UPLOADS. Neu nguoi chay test con de bien do tro
    toi CSDL that (vi du trong container, AICEFR_DB=/data/aicefr.db), fixture
    `app` chi chdir thi KHONG cach ly duoc: test se ghi tai khoan GV-01 voi mat
    khau nam trong source vao CSDL that.
    """
    from aicefr import config

    monkeypatch.setenv("AICEFR_UPLOADS", str(tmp_path / "uploads"))
    # The core service's store (D044), which is also AICEFR_DB. With
    # AICEFR_TEST_MONGO set (a mongodb:// URL), every test gets a database of
    # its own on that server, dropped when the run ends; otherwise an
    # in-memory one, named by this test's own path.
    server = os.getenv(MONGO_ENV)
    databases = []
    if server:
        name = f"t_{uuid.uuid4().hex[:12]}"
        databases.append(name)
        target = f"{server.rstrip('/')}/{name}"
    else:
        target = str(tmp_path / "aicefr.db")
    monkeypatch.setenv("AICEFR_DB", target)
    monkeypatch.setenv("AICEFR_CORE_DB", target)
    for name in ("AICEFR_ASR", "AICEFR_FAKE_TRANSCRIPT", "AICEFR_FAKE_LANGUAGE", "AICEFR_BUS"):
        monkeypatch.delenv(name, raising=False)
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()
    # Dropped now, not when the run ends: a server holding a database per test
    # of a whole run -- some forty indexes each -- runs out of memory. A module
    # that built the application at import and keeps using this database finds
    # it recreated on its next write; the caches that skip index creation are
    # cleared so its indexes come back with it.
    if databases:
        from pymongo import MongoClient

        from aicefr.storage import db as storage_db
        from aicefr.storage import migrations

        with MongoClient(server) as client:
            for name in databases:
                client.drop_database(name)
        storage_db.forget_indexes()
        migrations.forget_current()


MONGO_ENV = "AICEFR_TEST_MONGO"
on_server = bool(os.getenv(MONGO_ENV))


def feature_set(values: dict[str, float | None], version: str = "v3") -> FeatureSet:
    """Build a FeatureSet from a plain name-to-number mapping.

    A convenience for ARRANGING tests, not a door back into the old design. The
    dictionary is a compact way to write a fixture; `FeatureSet` itself keeps
    `Feature` objects, so a value of None must carry a reason -- this helper
    supplies FEATURE_NOT_COMPUTABLE, which is what the extractor supplies too.
    """
    return FeatureSet(
        items=[
            Feature(
                name=name,
                value=value,
                reason=None if value is not None else ReasonCode.FEATURE_NOT_COMPUTABLE,
            )
            for name, value in values.items()
        ],
        feature_version=version,
    )


@pytest.fixture
def sr() -> int:
    return SR


@pytest.fixture
def tone() -> np.ndarray:
    """40 seconds of a sine tone at moderate amplitude, used as a valid response.

    It must be at least 30 seconds. SRS FR-07 puts 20-29 seconds in the REVIEW zone,
    so a 20-second recording is no longer "valid" but "scorable yet still requiring a
    teacher to look at it".
    """
    t = np.arange(SR * 40) / SR
    return (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)


@pytest.fixture
def words() -> list[Word]:
    return [
        Word(text=f"word{i}", start_s=i * 0.4, end_s=i * 0.4 + 0.35, prob=0.9) for i in range(40)
    ]


@pytest.fixture
def segments() -> list[tuple[float, float]]:
    return [(0.5, 8.0), (9.2, 16.0), (17.5, 20.0)]
