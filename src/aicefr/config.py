"""Runtime configuration, read once from the environment.

Every knob that differs between a laptop, a staging box and a real deployment
lives here. Reading `os.environ` scattered through the code makes it impossible
to answer "what is this instance actually configured to do?" -- which is the
first question asked when something goes wrong at 2am.

No new dependency: a frozen dataclass built from the environment is enough, and
it keeps the settings object hashable and impossible to mutate by accident.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


def _flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _temperature(name: str) -> float | None:
    """A fixed decoding temperature in [0, 1], or None for the fallback schedule."""
    raw = (os.getenv(name) or "").strip().lower()
    if raw in {"", "fallback"}:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if 0.0 <= value <= 1.0 else None


def _names(name: str, default: str) -> tuple[str, ...]:
    """A comma-separated list, lower-cased, blanks dropped: "Stripe, x" -> (stripe, x)."""
    # Set but empty (a blank line in .env) means the same as not set.
    raw = (os.getenv(name) or "").strip() or default
    return tuple(n.strip().lower() for n in raw.split(",") if n.strip())


def _packs(name: str, default: str) -> tuple[tuple[int, int], ...]:
    """Run packs "runs:price_vnd,..." -> ((10, 19000), ...); malformed entries are dropped."""
    out = []
    for item in ((os.getenv(name) or "").strip() or default).split(","):
        runs, _, price = item.partition(":")
        if runs.strip().isdigit() and price.strip().isdigit() and int(runs) > 0:
            out.append((int(runs), int(price)))
    return tuple(sorted(set(out)))


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, ""))
    except ValueError:
        return default


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, ""))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """One instance's configuration. Built once at import, never mutated."""

    # --- identity of this deployment ---
    environment: str = field(default_factory=lambda: os.getenv("AICEFR_ENV", "development"))
    version: str = "0.1.0"

    # --- storage ---
    # A mongodb:// URL (D048). A plain path, the default, is an in-memory store
    # for a quick local run: its documents go when the process ends, and
    # production refuses it (`aicefr.storage.db.database`).
    db_path: str = field(default_factory=lambda: os.getenv("AICEFR_DB", "aicefr.db"))
    upload_dir: Path = field(default_factory=lambda: Path(os.getenv("AICEFR_UPLOADS", "uploads")))
    # D051: `s3://bucket` keeps recordings in object storage, which every
    # instance of a service can read; unset, the upload folder above.
    blob_url: str = field(default_factory=lambda: os.getenv("AICEFR_BLOBS", ""))

    # --- speech recognition ---
    asr_engine: str = field(default_factory=lambda: os.getenv("AICEFR_ASR", "fake").lower())
    whisper_model: str | None = field(default_factory=lambda: os.getenv("AICEFR_WHISPER_MODEL"))
    # Whisper's decoding temperature (HUONG_PHAT_TRIEN_TIEP §2.2). Unset or
    # "fallback": the library's schedule -- greedy first, then segments whose
    # output looks degenerate are decoded again at rising temperatures, by
    # random sampling, so the same recording can give a different transcript.
    # A number, normally 0: that temperature only, no sampling. The schedule
    # stays the default until tools/repeatability_bench.py has measured both on
    # real recordings: it is also a guard against hallucination loops.
    asr_temperature: float | None = field(
        default_factory=lambda: _temperature("AICEFR_ASR_TEMPERATURE")
    )

    # --- limits ---
    max_upload_bytes: int = field(
        default_factory=lambda: _int("AICEFR_MAX_UPLOAD", 25 * 1024 * 1024)
    )
    max_concurrent_jobs: int = field(default_factory=lambda: _int("AICEFR_MAX_JOBS", 2))
    # "threadpool" runs jobs on a bounded worker pool; "inline" runs them on the
    # calling thread. Tests use inline so they observe a finished result without
    # polling; production must not, or a submission would block the request.
    job_mode: str = field(default_factory=lambda: os.getenv("AICEFR_JOB_MODE", "threadpool"))
    job_timeout_s: int = field(default_factory=lambda: _int("AICEFR_JOB_TIMEOUT", 600))
    # Rate limit on the login endpoint, per client address. This sits in front of
    # the per-account lockout: the lockout stops an attacker grinding one
    # account, this stops them spreading the same guess across many accounts.
    login_attempts_per_minute: int = field(default_factory=lambda: _int("AICEFR_LOGIN_RATE", 10))

    # --- transport security ---
    # Off by default so http://localhost keeps working. Turn on behind TLS.
    https_only: bool = field(default_factory=lambda: _flag("AICEFR_HTTPS_ONLY"))

    # --- sign in with Google (D029) ---
    # Off unless both are set. Create an OAuth client of type "Web application"
    # in Google Cloud Console and add <public URL>/auth/google/callback as an
    # authorised redirect URI.
    google_client_id: str = field(default_factory=lambda: os.getenv("AICEFR_GOOGLE_CLIENT_ID", ""))
    google_client_secret: str = field(
        default_factory=lambda: os.getenv("AICEFR_GOOGLE_CLIENT_SECRET", "")
    )
    # Only accounts of this Google Workspace domain may sign in, e.g. hcmute.edu.vn.
    google_allowed_domain: str | None = field(
        default_factory=lambda: os.getenv("AICEFR_GOOGLE_DOMAIN") or None
    )
    # D063: a Google account linked to no account signs up as a new student
    # with a random pseudonym. AICEFR_GOOGLE_SIGNUP=0 keeps sign-in to linked
    # accounts only; AICEFR_GOOGLE_DOMAIN limits who can sign up at all.
    google_signup: bool = field(default_factory=lambda: _flag("AICEFR_GOOGLE_SIGNUP", True))
    # D065: a student opens an account with a password from /signup; a
    # forgotten one is replaced with a code sent by email from /forgot (D079).
    # Off: accounts come from an administrator (or Google, above) only.
    self_signup: bool = field(default_factory=lambda: _flag("AICEFR_SELF_SIGNUP", True))
    # D069: who writes the learner's answer one band higher -- off, groq,
    # gemini, openrouter or anthropic (aicefr.coach.providers) -- an optional
    # model name over the provider's default, and how many new upgrades one
    # student may ask for a day, which keeps a free tier within its limits.
    coach_provider: str = field(
        default_factory=lambda: os.getenv("AICEFR_COACH_PROVIDER", "off").strip().lower()
    )
    coach_model: str = field(default_factory=lambda: os.getenv("AICEFR_COACH_MODEL", "").strip())
    coach_daily: int = field(default_factory=lambda: _int("AICEFR_COACH_DAILY", 5))
    # D072: requests to the provider for everyone together in the provider's
    # day (aicefr.coach.usage), failures and retries included, under its free
    # daily quota (Gemini 3.5 Flash-Lite: 500).
    coach_global_daily: int = field(default_factory=lambda: _int("AICEFR_COACH_GLOBAL_DAILY", 475))
    # On a paid tier: a daily budget in USD replaces the request cap when set,
    # spent at these prices per million tokens (Gemini 3.5 Flash-Lite's list
    # prices by default; output includes thinking tokens).
    coach_budget_usd: float = field(
        default_factory=lambda: _float("AICEFR_COACH_DAILY_BUDGET_USD", 0.0)
    )
    coach_price_input_usd: float = field(
        default_factory=lambda: _float("AICEFR_COACH_PRICE_INPUT_USD", 0.30)
    )
    coach_price_output_usd: float = field(
        default_factory=lambda: _float("AICEFR_COACH_PRICE_OUTPUT_USD", 2.50)
    )
    # The address people reach this instance at, e.g. https://cefr.example.edu.vn.
    # Builds the Google redirect URI behind a proxy; unset, the request's own
    # address is used, which is right for localhost.
    public_url: str | None = field(default_factory=lambda: os.getenv("AICEFR_PUBLIC_URL") or None)

    # --- email (D079) ---
    # `resend` sends through Resend from a verified domain; `outbox` keeps the
    # messages in memory (tests, a machine without a key); `off` sends nothing.
    email_provider: str = field(
        default_factory=lambda: os.getenv("AICEFR_EMAIL_PROVIDER", "off").strip().lower()
    )
    resend_api_key: str = field(default_factory=lambda: os.getenv("AICEFR_RESEND_API_KEY", ""))
    # e.g. "SpeakUp <no-reply@ten-mien-cua-ban.vn>", on the verified domain.
    email_from: str = field(default_factory=lambda: os.getenv("AICEFR_EMAIL_FROM", ""))
    # When the daily study reminder goes out, Vietnam time (hour 0-23); -1 is off.
    reminder_hour: int = field(
        default_factory=lambda: int(os.getenv("AICEFR_REMINDER_HOUR", "19") or 19)
    )

    # --- payments (D035, D075) ---
    # The payment gateways that sell run packs. Off by default: nothing is
    # sold until a deployment opts in. No service plans any more (D075).
    billing_enabled: bool = field(default_factory=lambda: _flag("AICEFR_BILLING"))
    # The gateways offered, in the order the buyer sees them (D035, D075):
    # "stripe" with the keys below, and "sandbox", a payment page inside the
    # app where no money moves. See aicefr.billing.registry for the rules.
    payment_gateways: tuple[str, ...] = field(
        default_factory=lambda: _names("AICEFR_PAYMENT_GATEWAYS", "sandbox")
    )
    # A gateway that moves real money runs only with this on.
    payments_live: bool = field(default_factory=lambda: _flag("AICEFR_PAYMENTS_LIVE"))
    # Stripe: the secret key (sk_test_... for test mode) and the signing secret
    # of the webhook endpoint (whsec_...), from Stripe's dashboard or
    # `stripe listen`.
    stripe_secret_key: str = field(
        default_factory=lambda: os.getenv("AICEFR_STRIPE_SECRET_KEY", "").strip()
    )
    stripe_webhook_secret: str = field(
        default_factory=lambda: os.getenv("AICEFR_STRIPE_WEBHOOK_SECRET", "").strip()
    )

    # --- services (D043, D044) ---
    # Where the core service keeps its documents: a mongodb:// URL naming its
    # database (D048). Unset, AICEFR_DB, as on one machine. The speech and web
    # services keep none.
    stores: dict[str, str] = field(
        default_factory=lambda: {
            "core": os.getenv("AICEFR_CORE_DB", ""),
            # D049, D051: the ledger and the learning part may each have a
            # database of their own (database per service); unset, the core's.
            "metering": os.getenv("AICEFR_METERING_DB", "") or os.getenv("AICEFR_CORE_DB", ""),
            "learning": os.getenv("AICEFR_LEARNING_DB", "") or os.getenv("AICEFR_CORE_DB", ""),
        }
    )
    # D049: charge per use. Only the deployment for the NetID channel turns it
    # on; the school and research deployment never does (BR-29, BR-30).
    metering_enabled: bool = field(default_factory=lambda: _flag("AICEFR_METERING"))
    # D056: guided listening with random control moments. Off unless switched
    # on; labels are analysed only for learners who accepted the terms (D058).
    guided_replay: bool = field(default_factory=lambda: _flag("AICEFR_GUIDED_REPLAY"))
    # D057: the seller's prices, in runs: a recording up to one minute, every
    # further started minute, the share a practice attempt pays, and what one
    # run is in IDPoint on NetID (team decision 24/10/2026, 1 IDPoint = 1 VND).
    price_first_minute_runs: float = field(
        default_factory=lambda: _float("AICEFR_PRICE_FIRST_MINUTE_RUNS", 1.0)
    )
    price_extra_minute_runs: float = field(
        default_factory=lambda: _float("AICEFR_PRICE_EXTRA_MINUTE_RUNS", 0.7)
    )
    price_practice_factor: float = field(
        default_factory=lambda: _float("AICEFR_PRICE_PRACTICE_FACTOR", 0.5)
    )
    idpoint_per_run: int = field(default_factory=lambda: _int("AICEFR_IDPOINT_PER_RUN", 2000))
    # D072: what one upgraded answer (D069) costs on the metered channel, in runs.
    price_upgrade_runs: float = field(
        default_factory=lambda: _float("AICEFR_PRICE_UPGRADE_RUNS", 0.3)
    )
    # Run packs a learner buys on the metered channel (D053): runs and price in
    # VND. Paid through the billing gateways, credited to the learner's wallet.
    credit_packs: tuple[tuple[int, int], ...] = field(
        default_factory=lambda: _packs("AICEFR_CREDIT_PACKS", "10:19000,30:49000,100:149000")
    )
    # "inline" runs events, work and calls in this process; a redis:// URL
    # sends them through Redis: BullMQ for work, Streams for events (D050).
    bus_url: str = field(default_factory=lambda: os.getenv("AICEFR_BUS", "inline"))
    # The key internal calls and the gateway's account header carry. Must be
    # the same long random string on every service of a deployment.
    internal_token: str = field(default_factory=lambda: os.getenv("AICEFR_INTERNAL_TOKEN", ""))
    # The key the gateway puts beside the account it forwards. Separate from the
    # internal key: the gateway holds this one only, and the speech service,
    # which parses audio from the internet, holds neither.
    gateway_token: str = field(default_factory=lambda: os.getenv("AICEFR_GATEWAY_TOKEN", ""))
    # Where the core service answers, e.g. http://core:8000, for the web
    # service. Unset: it is in this process (aicefr.api.main).
    service_urls: dict[str, str] = field(
        default_factory=lambda: {"core": os.getenv("AICEFR_CORE_URL", "")}
    )

    def store(self, service: str) -> str:
        """The store of one service: its own setting, else the shared one."""
        return self.stores.get(service) or self.db_path

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def asr_is_real(self) -> bool:
        return self.asr_engine != "fake"

    @property
    def google_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """The one settings instance. Cached so every module sees the same values."""
    return Settings()
