#!/usr/bin/env bash
# Dung moi truong thu tren localhost: MongoDB, artifact mo hinh, tai khoan demo, roi chay may chu.
set -euo pipefail
cd "$(dirname "$0")"

PY=.venv/bin/python
[ -x "$PY" ] || { echo "Chua co .venv. Chay: python3.12 -m venv .venv && .venv/bin/pip install -e '.[dev,vad]'" >&2; exit 1; }

# Khoa va cau hinh rieng cua may nay, neu co (khong commit; xem .env.example).
if [ -f .env ]; then set -a; . ./.env; set +a; fi

# --- MongoDB (D048) ---------------------------------------------------------
# Khong dat AICEFR_DB thi kho chi nam trong bo nho cua tung tien trinh: tai
# khoan tao o buoc duoi se mat truoc khi may chu mo len. Nen mac dinh dung mot
# MongoDB 7 trong Docker, du lieu giu trong volume aicefr-demo-mongo.
if [ -z "${AICEFR_DB:-}" ]; then
  command -v docker >/dev/null && docker info >/dev/null 2>&1 || {
    echo "Can Docker dang chay de dung MongoDB (hoac tu dat AICEFR_DB=mongodb://...)." >&2; exit 1; }
  PORT="${AICEFR_DEMO_MONGO_PORT:-27019}"
  if ! docker ps --format '{{.Names}}' | grep -qx aicefr-demo-mongo; then
    docker rm -f aicefr-demo-mongo >/dev/null 2>&1 || true
    docker run -d --name aicefr-demo-mongo -p "127.0.0.1:$PORT:27017" \
      -v aicefr-demo-mongo:/data/db mongo:7 >/dev/null
    echo "Da chay MongoDB trong Docker (aicefr-demo-mongo, cong $PORT)."
  fi
  export AICEFR_DB="mongodb://localhost:$PORT/aicefr"
  for _ in $(seq 1 30); do
    docker exec aicefr-demo-mongo mongosh --quiet --eval 'db.runCommand({ping:1}).ok' >/dev/null 2>&1 && break
    sleep 1
  done
fi

# --- Artifact mo hinh (W7-S01) ----------------------------------------------
# Artifact that suy tu Speak & Improve, khong nam trong repo: mac dinh thu muc
# anh em ../aicefr-models. May chua co thi dung artifact GIA LAP cua bo test
# (tools/make_fake_models.py) de chay duoc tron vong -- diem khi do vo nghia.
export AICEFR_MODEL_DIR="${AICEFR_MODEL_DIR:-$(cd .. && pwd)/aicefr-models}"
if [ ! -f "$AICEFR_MODEL_DIR/ridge_resp_v2.json" ]; then
  echo "CANH BAO: khong thay artifact that o $AICEFR_MODEL_DIR." >&2
  echo "          Dung artifact GIA LAP trong tests/fixtures/models: diem va band KHONG co y nghia." >&2
  echo "          Xin thu muc aicefr-models tu Sang (khong dua len Git), dat canh repo roi chay lai." >&2
  export AICEFR_MODEL_DIR="$PWD/tests/fixtures/models"
  AICEFR_MODEL_PINS="$(awk '{sub(/\.json$/, "", $2); printf "%s%s=%s", sep, $2, $1; sep=","}' \
    "$AICEFR_MODEL_DIR/SHA256SUMS")"
  export AICEFR_MODEL_PINS
fi

# --- May nhan dang (ASR) ----------------------------------------------------
# AICEFR_ASR=whisper ma chua cai nhom [asr] thi moi bai nop deu FAILED
# (ASR_FAILED). Bao ngay o day thay vi de nguoi dung doan.
if [ "${AICEFR_ASR:-fake}" = "whisper" ]; then
  if [ "$(uname -s)-$(uname -m)" = "Darwin-arm64" ]; then mod=mlx_whisper; else mod=faster_whisper; fi
  $PY -c "import $mod" 2>/dev/null || {
    echo "AICEFR_ASR=whisper nhung chua cai $mod. Chay: .venv/bin/pip install -e '.[dev,asr,vad]'" >&2
    exit 1; }
fi

# --- Tai khoan demo ---------------------------------------------------------
for a in "SV-001:student" "SV-002:student" "GV-01:teacher" "QT-01:admin"; do
  $PY -m aicefr.accounts_cli them --but-danh "${a%%:*}" --vai-tro "${a##*:}" \
    --mat-khau matkhau123 >/dev/null 2>&1 || true  # da co thi bo qua
done
echo "Tai khoan demo: SV-001, SV-002, GV-01, QT-01 -- mat khau matkhau123"

if [ -n "${AICEFR_GOOGLE_CLIENT_ID:-}" ] && [ -n "${AICEFR_GOOGLE_CLIENT_SECRET:-}" ]; then
  echo "Dang nhap Google: BAT (callback http://localhost:8000/auth/google/callback)"
else
  echo "Dang nhap Google: TAT -- .env thieu AICEFR_GOOGLE_CLIENT_ID/SECRET (xin Sang qua kenh rieng)"
fi
echo "Mo http://localhost:8000"
echo "Che do ASR: ${AICEFR_ASR:-fake}  (dat AICEFR_ASR=whisper de cham that)"
exec .venv/bin/uvicorn aicefr.api.main:app --reload --port 8000
