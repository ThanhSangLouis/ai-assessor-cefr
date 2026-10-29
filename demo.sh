#!/usr/bin/env bash
# Dung moi truong thu tren localhost: tao tai khoan demo roi chay may chu.
set -euo pipefail
cd "$(dirname "$0")"

PY=.venv/bin/python

# Khoa va cau hinh rieng cua may nay, neu co (khong commit; xem .env.example).
if [ -f .env ]; then set -a; . ./.env; set +a; fi
[ -x "$PY" ] || { echo "Chua co .venv. Chay: python3.12 -m venv .venv && .venv/bin/pip install -e '.[dev]'" >&2; exit 1; }

if [ ! -f aicefr.db ]; then
  for a in "SV-001:student" "SV-002:student" "GV-01:teacher" "QT-01:admin"; do
    $PY -m aicefr.accounts_cli them --but-danh "${a%%:*}" --vai-tro "${a##*:}" --mat-khau matkhau123 >/dev/null
  done
  echo "Da tao 4 tai khoan demo, mat khau matkhau123"
fi

echo "Mo http://localhost:8000"
echo "Che do ASR: ${AICEFR_ASR:-fake}  (dat AICEFR_ASR=whisper de cham that)"
exec .venv/bin/uvicorn aicefr.api.main:app --reload --port 8000
