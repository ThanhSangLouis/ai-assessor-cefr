# Two images from one file (D043):
#
#   target `service` -- identity, assessment, learning, billing, web. Python and
#                       the services extra (PostgreSQL, RabbitMQ); which service
#                       runs is AICEFR_SERVICE.
#   target `speech`  -- the speech worker: adds ffmpeg and the recogniser, the
#                       only image that carries them.
#
# Both run as an unprivileged user: the speech image hands files that arrive
# from the internet to ffmpeg.

FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install ".[services]"

FROM builder AS builder-speech
# faster-whisper (MIT) for the real recogniser; the energy detector is used when
# Silero (torch, about 2 GB) is not installed. Build with --build-arg VAD=1 to add it.
ARG VAD=0
RUN /opt/venv/bin/pip install ".[services,asr]" \
 && if [ "$VAD" = "1" ]; then /opt/venv/bin/pip install ".[vad]"; fi

# ---------------------------------------------------------------------------

FROM python:3.12-slim AS base

# libsndfile1 is what `soundfile` binds to; curl for the health checks.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libsndfile1 curl \
 && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --uid 10001 aicefr \
 && mkdir -p /data/uploads && chown -R aicefr:aicefr /data
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    AICEFR_ENV=production \
    AICEFR_UPLOADS=/data/uploads
WORKDIR /app
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
  CMD curl -fsS http://localhost:8000/healthz || exit 1

FROM base AS service
COPY --from=builder /opt/venv /opt/venv
USER aicefr
# No --reload in production. --proxy-headers trusts X-Forwarded-* only from
# FORWARDED_ALLOW_IPS (the gateway's address), never from everyone.
CMD ["sh", "-c", "exec uvicorn --factory aicefr.services.${AICEFR_SERVICE:?set AICEFR_SERVICE}.app:create_app --host 0.0.0.0 --port 8000 --proxy-headers"]

FROM base AS speech
# ffmpeg transcodes the browser's WebM/MP4 recordings (FR-39).
USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/*
COPY --from=builder-speech /opt/venv /opt/venv
ENV HF_HOME=/home/aicefr/.cache/huggingface
USER aicefr
CMD ["uvicorn", "--factory", "aicefr.services.speech.app:create_app", "--host", "0.0.0.0", "--port", "8000"]
