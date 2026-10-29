"""Connectors as the Coherence evidence (D061).

What is under test: the count is of KINDS of connectors, a phrase counts once
and not as its words, a word inside another word is not a connector, and the
report never presents grammar as measured.
"""

from __future__ import annotations

from conftest import feature_set

from aicefr.contracts import Criterion, EvidenceKind, Transcript, Word
from aicefr.report.bands import ASPECTS, Provenance
from aicefr.report.comments import CommentBuilder
from aicefr.report.connectors import connectors_used
from aicefr.report.evidence import MIN_WORDS_FOR_CONNECTORS, EvidenceBuilder


def _words(text: str) -> list[Word]:
    return [Word(text=t, start_s=i * 0.4, end_s=i * 0.4 + 0.3) for i, t in enumerate(text.split())]


def _transcript(text: str) -> Transcript:
    return Transcript(text=text, words=_words(text), engine="fake", model_version="t")


def test_dem_kieu_tu_noi_khong_dem_so_lan() -> None:
    used = connectors_used(_words("I like it and and and I also cook because it is fun"))
    assert list(used) == ["and", "also", "because"]


def test_cum_tu_noi_dem_mot_lan_va_uu_tien_cum_dai() -> None:
    used = connectors_used(_words("On the other hand, as a result of that, we stayed."))
    assert used == {"on the other hand": "advanced", "as a result": "advanced"}


def test_tu_nam_trong_tu_khac_khong_phai_tu_noi() -> None:
    assert connectors_used(_words("Sorry, the brand android is mine")) == {}


def test_bang_chung_tu_noi_cho_mach_lac() -> None:
    text = "I think online learning is useful because it saves time. " * 3 + (
        "However, for example, some students feel lonely, so classes still matter."
    )
    nwords = float(len(text.split()))
    assert nwords >= MIN_WORDS_FOR_CONNECTORS
    ev = EvidenceBuilder().build(
        _transcript(text), feature_set({"n_words": nwords, "log_uniq": 3.0}), []
    )
    conn = [e for e in ev if e.kind is EvidenceKind.CONNECTOR]
    assert len(conn) == 1 and conn[0].criterion is Criterion.COHERENCE
    assert '"because"' in conn[0].note and '"however"' in conn[0].note

    comments = CommentBuilder().comments(
        feature_set({"n_words": nwords, "log_uniq": 3.0}), ev, 0.9, []
    )
    coh = [c for c in comments if c.criterion is Criterion.COHERENCE]
    assert coh and conn[0].evidence_id in coh[0].evidence_refs


def test_bai_qua_ngan_khong_ket_luan_ve_tu_noi() -> None:
    text = "I like cats and dogs"
    ev = EvidenceBuilder().build(_transcript(text), feature_set({"n_words": 5.0}), [])
    assert not [e for e in ev if e.kind is EvidenceKind.CONNECTOR]


def test_bai_khong_co_tu_noi_van_noi_ro() -> None:
    text = " ".join(["word"] * 30)
    ev = EvidenceBuilder().build(_transcript(text), feature_set({"n_words": 30.0}), [])
    conn = [e for e in ev if e.kind is EvidenceKind.CONNECTOR]
    assert conn and "không thấy từ nối" in conn[0].note


def test_trang_bands_mach_lac_do_gian_tiep_ngu_phap_khong_do() -> None:
    by_key = {a.key: a for a in ASPECTS}
    assert by_key["coherence"].provenance is Provenance.MEASURED_INDIRECTLY
    assert "từ nối" in by_key["coherence"].measured_by
    assert by_key["accuracy"].provenance is Provenance.NOT_MEASURED
    assert by_key["interaction"].provenance is Provenance.NOT_ASSESSED
