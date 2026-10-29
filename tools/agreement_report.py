"""Write the agreement report of one blind-rating batch as Markdown and JSON (D030).

The same numbers as the administrator's screen -- both come from
`aicefr.research.agreement` -- in a form a thesis chapter can quote and a
committee can watch being re-run:

    python tools/agreement_report.py --db aicefr.db --list
    python tools/agreement_report.py --db aicefr.db --batch <id> --out bao_cao_dong_thuan.md

Only responses whose owner accepted the terms of use (D058) are included, as on
the screen. The output names no student and holds no transcript, but it is a
research result about real people: it is written where you point it and is
never committed by default (`docs/reports/` is the place for a summary, not
for the raw table).
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import UTC, datetime
from pathlib import Path

from aicefr.config import get_settings
from aicefr.research.agreement import BANDS, agreement_report
from aicefr.storage.auth_repository import AuthRepository
from aicefr.storage.rating_repository import RatingRepository, rated_responses

PLAN_TARGETS = {"qwk_band": 0.70, "icc_overall": 0.75}
CRITERION = {
    "range": "Vốn từ (Range)",
    "accuracy": "Ngữ pháp (Accuracy)",
    "fluency": "Độ trôi chảy (Fluency)",
    "coherence": "Mạch lạc (Coherence)",
    "phonology": "Phát âm dễ nghe (Phonology)",
}


def _f(value, digits: int = 3) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def _metric(entry: dict) -> str:
    value = _f(entry.get("value"))
    ci = entry.get("ci")
    return f"{value} [{_f(ci[0])}; {_f(ci[1])}]" if ci else value


def _confusion(matrix: list[list[int]], rows: str, cols: str) -> list[str]:
    out = [f"| {rows} \\ {cols} | " + " | ".join(BANDS) + " |", "|---|" + "---:|" * len(BANDS)]
    for band, row in zip(BANDS, matrix, strict=True):
        out.append(f"| {band} | " + " | ".join(str(n) for n in row) + " |")
    return out


def markdown(batch: dict, payload: dict) -> str:
    r = payload["report"]
    c, h, m, routing = r["counts"], r["human_human"], r["machine_human"], r["routing"]
    icc = h["icc_overall"]
    lines = [
        f"# Báo cáo đồng thuận — {batch['name']}",
        "",
        f"- Đợt: `{batch['batch_id']}`, tạo lúc {batch['created_at']}, hạt giống {batch['seed']}",
        f"- Lập lúc: {payload['generated_at']}",
        f"- Khoảng tin cậy 95% lấy mẫu lại theo người nói: {r['bootstrap']['n_boot']} lần,"
        f" hạt giống {r['bootstrap']['seed']}",
        f"- Bỏ ra vì người học đã rút đồng thuận: {payload['withdrawn']} bài",
        "- Mốc so sánh lấy từ kế hoạch khảo sát (§6.3), **chưa ký**: kappa band ≥ 0,70;"
        " ICC ≥ 0,75. Số dưới đây là số đo, không phải kết luận.",
        "",
        "## Số bài",
        "",
        "| Mục | Số |",
        "|---|---:|",
    ]
    names = {
        "responses": "Bài trong đợt",
        "rated_twice": "Bài đủ hai phiếu",
        "both_scorable": "Hai phiếu đều chấm được",
        "adjudication_needed": "Cần phân xử",
        "adjudicated": "Đã phân xử",
        "pending": "Chờ phân xử",
        "unscorable": "Không chấm được",
        "speakers": "Người nói",
    }
    lines += [f"| {names.get(k, k)} | {v} |" for k, v in c.items()]
    lines += [
        "",
        f"## 1. Hai giám khảo với nhau ({h['n']} bài, {h['speakers']} người nói)",
        "",
        "| Chỉ số | Giá trị [KTC 95%] |",
        "|---|---|",
        f"| Kappa có trọng số bậc hai, band | {_metric(h['qwk_band'])} |",
        f"| {icc['kind'] or 'ICC'} trên điểm tổng 0–6 | {_f(icc['value'])} |",
        f"| Trùng band tuyệt đối | {_metric(h['exact_band_agreement'])} |",
        f"| Kappa trên điểm tổng làm tròn nửa điểm | {_metric(h['qwk_overall_half_points'])} |",
        f"| Tương quan Pearson, điểm tổng | {_f(h['pearson_overall'])} |",
        f"| Chênh lệch tuyệt đối trung bình | {_f(h['mean_abs_diff'])} |",
        "",
        *_confusion(h["confusion_band"], "Giám khảo 1", "Giám khảo 2"),
        "",
        "| Tiêu chí | Pearson giữa hai giám khảo | Số bài |",
        "|---|---:|---:|",
    ]
    lines += [
        f"| {CRITERION.get(k, k)} | {_f(v['pearson'])} | {v['n']} |"
        for k, v in h["per_criterion"].items()
    ]
    kinds = m["reference_kinds"]
    lines += [
        "",
        f"## 2. Máy so với điểm đối chiếu của người ({m['n']} bài, {m['speakers']} người nói)",
        "",
        f"Điểm đối chiếu: trung bình hai giám khảo ({kinds.get('mean_of_two', 0)} bài) hoặc trung"
        f" vị ba người khi có phân xử ({kinds.get('median_of_three', 0)} bài). Điểm máy là kết quả"
        " của máy trước mọi quyết định của giảng viên.",
        "",
        "| Chỉ số | Giá trị [KTC 95%] |",
        "|---|---|",
        f"| Pearson | {_metric(m['pearson'])} |",
        f"| RMSE | {_metric(m['rmse'])} |",
        f"| Kappa có trọng số bậc hai, band | {_metric(m['qwk_band'])} |",
        "",
        *_confusion(m["confusion_band"], "Người", "Máy"),
        "",
        "| Band | Số bài (người) | Recall | Precision |",
        "|---|---:|---:|---:|",
    ]
    lines += [
        f"| {band} | {v['support']} | {_f(v['recall'])} | {_f(v['precision'])} |"
        for band, v in m["per_band"].items()
    ]
    ttr = payload["time_to_rate"]
    lines += [
        "",
        "## 3. Cờ chuyển giảng viên (RQ4)",
        "",
        "| Nhóm | Số bài | Sai số tuyệt đối trung bình |",
        "|---|---:|---:|",
        f"| Máy chuyển giảng viên | {routing['flagged']['n']} |"
        f" {_f(routing['flagged']['mean_abs_error'])} |",
        f"| Máy tự kết luận | {routing['not_flagged']['n']} |"
        f" {_f(routing['not_flagged']['mean_abs_error'])} |",
        "",
        f"Thời gian chấm một bài, trung vị: {_f(ttr['median_s'], 1)} giây ({ttr['n']} phiếu).",
    ]
    if r["notes"]:
        lines += ["", "## Ghi chú", ""] + [f"- `{note}`" for note in r["notes"]]
    return "\n".join(lines) + "\n"


def build(db: str, batch_id: str) -> tuple[dict, dict]:
    ratings = RatingRepository(db)
    batch = ratings.batch(batch_id)
    if batch is None:
        raise SystemExit(f"không có đợt {batch_id!r}")
    allowed = AuthRepository(db).active_account_ids()
    everyone = ratings.analysis_rows(batch_id, allowed=None)
    rows = ratings.analysis_rows(batch_id, allowed)
    times = ratings.times_to_rate(batch_id)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "withdrawn": len(everyone) - len(rows),
        "time_to_rate": {
            "n": len(times),
            "median_s": statistics.median(times) if times else None,
        },
        "plan_targets": PLAN_TARGETS,
        "report": agreement_report(rated_responses(rows)),
    }
    return dict(batch), payload


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Báo cáo đồng thuận của một đợt chấm mù (D030)")
    ap.add_argument(
        "--db", default=get_settings().store("core"), help="cơ sở dữ liệu của dịch vụ core"
    )
    ap.add_argument("--batch", help="mã đợt chấm")
    ap.add_argument("--list", action="store_true", help="liệt kê các đợt chấm")
    ap.add_argument("--out", help="tệp Markdown; bản JSON nằm cạnh với đuôi .json")
    args = ap.parse_args(argv)

    if args.list:
        for b in RatingRepository(args.db).batches():
            progress = f"{b['done']}/{b['assignments']} phiếu"
            print(f"{b['batch_id']}  {b['status']:6}  {progress}  {b['name']}")
        return 0
    if not args.batch:
        ap.error("cần --batch hoặc --list")
    batch, payload = build(args.db, args.batch)
    text = markdown(batch, payload)
    if not args.out:
        sys.stdout.write(text)
        return 0
    out = Path(args.out)
    out.write_text(text, encoding="utf-8")
    out.with_suffix(".json").write_text(
        json.dumps({"batch": batch, **payload}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Đã ghi {out} và {out.with_suffix('.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
