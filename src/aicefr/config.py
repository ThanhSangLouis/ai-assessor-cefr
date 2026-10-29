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
    """A comma-separated list, lower-cased, blanks dropped: "Stripe, vnpay" -> (stripe, vnpay)."""
    # Set but empty (a blank line in .env) means the same as not set.
    raw = (os.getenv(name) or "").strip() or default
    return tuple(n.strip().lower() for n in raw.split(",") if n.strip())


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
    db_path: str = field(default_factory=lambda: os.getenv("AICEFR_DB", "aicefr.db"))
    upload_dir: Path = field(default_factory=lambda: Path(os.getenv("AICEFR_UPLOADS", "uploads")))

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
    # The address people reach this instance at, e.g. https://cefr.example.edu.vn.
    # Builds the Google redirect URI behind a proxy; unset, the request's own
    # address is used, which is right for localhost.
    public_url: str | None = field(default_factory=lambda: os.getenv("AICEFR_PUBLIC_URL") or None)

    # --- service plans and payment (D033) ---
    # Off by default: a deployment that runs the thesis' data collection must
    # never meet a limit (BR-30), and an existing deployment keeps behaving as
    # before until it opts in.
    billing_enabled: bool = field(default_factory=lambda: _flag("AICEFR_BILLING"))
    # The gateways offered, in the order the administrator sees them (D035):
    # "sandbox", a payment page inside the app where no money moves; "vnpay",
    # "stripe", "momo", each with the keys below. Every gateway defaults to its
    # own test environment; see aicefr.billing.registry for the rules.
    payment_gateways: tuple[str, ...] = field(
        default_factory=lambda: _names("AICEFR_PAYMENT_GATEWAYS", "sandbox")
    )
    # A gateway that moves real money runs only with this on.
    payments_live: bool = field(default_factory=lambda: _flag("AICEFR_PAYMENTS_LIVE"))
    vnpay_tmn_code: str = field(default_factory=lambda: os.getenv("AICEFR_VNPAY_TMN_CODE", ""))
    vnpay_hash_secret: str = field(
        default_factory=lambda: os.getenv("AICEFR_VNPAY_HASH_SECRET", "")
    )
    vnpay_url: str | None = field(default_factory=lambda: os.getenv("AICEFR_VNPAY_URL") or None)
    # Stripe: the secret key (sk_test_... for test mode) and the signing secret
    # of the webhook endpoint (whsec_...), from Stripe's dashboard or
    # `stripe listen`.
    stripe_secret_key: str = field(
        default_factory=lambda: os.getenv("AICEFR_STRIPE_SECRET_KEY", "").strip()
    )
    stripe_webhook_secret: str = field(
        default_factory=lambda: os.getenv("AICEFR_STRIPE_WEBHOOK_SECRET", "").strip()
    )
    # MoMo: what MoMo's business portal issues; the endpoint defaults to MoMo's
    # test environment.
    momo_partner_code: str = field(
        default_factory=lambda: os.getenv("AICEFR_MOMO_PARTNER_CODE", "").strip()
    )
    momo_access_key: str = field(
        default_factory=lambda: os.getenv("AICEFR_MOMO_ACCESS_KEY", "").strip()
    )
    momo_secret_key: str = field(
        default_factory=lambda: os.getenv("AICEFR_MOMO_SECRET_KEY", "").strip()
    )
    momo_endpoint: str | None = field(
        default_factory=lambda: os.getenv("AICEFR_MOMO_ENDPOINT") or None
    )
    # Signs licence keys for contracts paid outside the system. Unset: keys
    # cannot be installed.
    license_secret: str = field(default_factory=lambda: os.getenv("AICEFR_LICENSE_SECRET", ""))
    # Demonstration prices, dong per student per month: not a price list, which
    # needs the measured costs of the proposal (DE_XUAT_GOI_DICH_VU.md, mục 3).
    price_standard: int = field(default_factory=lambda: _int("AICEFR_PRICE_STANDARD", 10_000))
    price_advanced: int = field(default_factory=lambda: _int("AICEFR_PRICE_ADVANCED", 15_000))
    # The trial: every feature, for this many students and days, once.
    trial_seats: int = field(default_factory=lambda: _int("AICEFR_TRIAL_SEATS", 50))
    trial_days: int = field(default_factory=lambda: _int("AICEFR_TRIAL_DAYS", 30))

    # --- services (D043, D044) ---
    # Where the core service keeps its rows: a SQLite path or a PostgreSQL URL
    # with `?schema=core`. Unset, AICEFR_DB, as on one machine. The speech and
    # web services keep none.
    stores: dict[str, str] = field(
        default_factory=lambda: {"core": os.getenv("AICEFR_CORE_DB", "")}
    )
    # "inline" runs events, work and calls in this process; an amqp:// URL
    # sends them through RabbitMQ.
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
