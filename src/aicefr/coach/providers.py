"""Who writes the upgraded answer: a language model chosen by configuration (D069).

`AICEFR_COACH_PROVIDER` picks one; the default is `off`, and the feature is
then not offered. The choice is about cost and about where a transcript may go:

* `groq` (Llama 3.3 70B), `gemini` (Gemini 3.5 Flash-Lite: 500 free requests a
  day, where 3.8 Flash allows 20), `openrouter` (any model
  named in AICEFR_COACH_MODEL) speak the OpenAI-compatible chat API and are
  called with the standard library. Groq's free tier is the default for cost;
  Gemini's free tier lets Google use what is sent to improve its products, so
  it suits test data, not students' transcripts;
* `anthropic` (Claude Haiku 5.5) goes through the official SDK, installed with
  the `coach` extra; it is paid, cheap, and enforces the answer's JSON schema.

Each call has a timeout and raises UpgradeError on anything but a usable answer.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from aicefr.coach.upgrade import SCHEMA, SYSTEM, UpgradeError
from aicefr.coach.usage import Calls

logger = logging.getLogger(__name__)

TIMEOUT_S = 45


@dataclass(frozen=True)
class Preset:
    base_url: str
    key_env: str
    model: str


# Keyword arguments on their own lines: a model name next to an environment
# variable called *_API_KEY reads as a leaked key to the secret scanner.
OPENAI_COMPATIBLE = {
    "groq": Preset(
        base_url="https://api.groq.com/openai/v1",
        key_env="AICEFR_GROQ_API_KEY",
        model="llama-3.3-70b-versatile",
    ),
    "gemini": Preset(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        key_env="AICEFR_GEMINI_API_KEY",
        model="gemini-3.5-flash-lite",
    ),
    "openrouter": Preset(
        base_url="https://openrouter.ai/api/v1",
        key_env="AICEFR_OPENROUTER_API_KEY",
        model="",
    ),
}
ANTHROPIC_MODEL = "claude-haiku-5-5"
ANTHROPIC_KEY_ENV = "AICEFR_ANTHROPIC_API_KEY"
NAMES = ("off", *OPENAI_COMPATIBLE, "anthropic")


@dataclass(frozen=True)
class Provider:
    name: str
    model: str
    key: str

    def complete(self, user: str) -> str:
        """The model's raw answer to the upgrade request."""
        return self.complete_with_usage(user)[0]

    def complete_with_usage(
        self,
        user: str,
        calls: Calls | None = None,
        system: str = SYSTEM,
        schema: dict = SCHEMA,
    ) -> tuple[str, dict]:
        """The raw answer and the tokens the provider says it used (D072).

        `{"input_tokens": n, "output_tokens": m}`, either None when the
        provider did not say: kept with the ledger entry and the day's counters.
        `calls` counts every request sent, retries and failures included,
        as the provider's quota counts them. `system` and `schema` are the
        upgraded answer's by default; a teacher's lesson draft (D075) has its own.
        """
        calls = calls if calls is not None else Calls()
        if self.name == "anthropic":
            return _anthropic(self.model, self.key, user, calls, system, schema)
        base_url = OPENAI_COMPATIBLE[self.name].base_url
        return _openai_compatible(base_url, self.model, self.key, user, calls, system)


# D073: the key of a project with billing on, used while an administrator has
# switched the system to the paid tier. The provider and model stay the same.
PAID_KEY_ENV = "AICEFR_COACH_PAID_API_KEY"


def provider_from(settings, paid: bool = False) -> Provider | None:
    """The configured provider, or None when the feature is off or not set up.

    `paid`: with the paid tier's key; None while that key is not set.
    """
    name = settings.coach_provider
    if name in ("", "off") or name not in NAMES:
        return None
    if name == "anthropic":
        key, model = os.getenv(ANTHROPIC_KEY_ENV, ""), ANTHROPIC_MODEL
    else:
        preset = OPENAI_COMPATIBLE[name]
        key, model = os.getenv(preset.key_env, ""), preset.model
    if paid:
        key = os.getenv(PAID_KEY_ENV, "")
    model = settings.coach_model or model
    if not key or not model:
        return None
    return Provider(name, model, key)


# A busy model answers 500/502/503/504 for a moment (Gemini's free tier does,
# measured on the production host): one retry after a short wait, then give up.
RETRY_STATUSES = frozenset({500, 502, 503, 504})
RETRY_WAIT_S = 2.0


def _post(request: urllib.request.Request, calls: Calls) -> dict:
    for attempt in (1, 2):
        calls.requests += 1
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_S) as r:  # noqa: S310 - fixed https hosts
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if attempt == 2 or e.code not in RETRY_STATUSES:
                raise
            logger.info("coach provider busy (%s), retrying once", e.code)
            time.sleep(RETRY_WAIT_S)
    raise AssertionError("unreachable")  # pragma: no cover


def _usage(input_tokens, output_tokens) -> dict:
    as_int = lambda v: int(v) if isinstance(v, int | float) else None  # noqa: E731
    return {"input_tokens": as_int(input_tokens), "output_tokens": as_int(output_tokens)}


def _openai_compatible(
    base_url: str, model: str, key: str, user: str, calls: Calls, system: str = SYSTEM
) -> tuple[str, dict]:
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        data = _post(request, calls)
    except urllib.error.HTTPError as e:
        # 429 is the free tier's daily or per-minute cap: say so, not "error".
        if e.code == 429:
            raise UpgradeError("nhà cung cấp mô hình đang giới hạn lượt, hãy thử lại sau") from e
        logger.warning("coach provider answered %s", e.code)
        raise UpgradeError(f"nhà cung cấp mô hình trả lỗi {e.code}") from e
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        raise UpgradeError("không liên lạc được nhà cung cấp mô hình") from e
    try:
        text = data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as e:
        raise UpgradeError("câu trả lời của mô hình thiếu nội dung") from e
    used = data.get("usage") if isinstance(data.get("usage"), dict) else {}
    return text, _usage(used.get("prompt_tokens"), used.get("completion_tokens"))


def _anthropic(
    model: str, key: str, user: str, calls: Calls, system: str = SYSTEM, schema: dict = SCHEMA
) -> tuple[str, dict]:
    try:
        import anthropic
    except ImportError as e:  # the `coach` extra is not installed
        raise UpgradeError("máy chủ chưa cài gói anthropic (nhóm coach)") from e
    # The SDK's own retries are invisible here, so it makes none: one request, counted.
    client = anthropic.Anthropic(api_key=key, timeout=TIMEOUT_S, max_retries=0)
    calls.requests += 1
    try:
        response = client.messages.create(
            model=model,
            max_tokens=4000,
            system=system,
            messages=[{"role": "user", "content": user}],
            # A rewrite needs little deliberation; the schema keeps the JSON valid.
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}},
        )
    except anthropic.RateLimitError as e:
        raise UpgradeError("nhà cung cấp mô hình đang giới hạn lượt, hãy thử lại sau") from e
    except anthropic.APIStatusError as e:
        logger.warning("coach provider answered %s", e.status_code)
        raise UpgradeError(f"nhà cung cấp mô hình trả lỗi {e.status_code}") from e
    except anthropic.APIConnectionError as e:
        raise UpgradeError("không liên lạc được nhà cung cấp mô hình") from e
    if response.stop_reason == "refusal":
        raise UpgradeError("mô hình từ chối viết lại bài này")
    text = next((b.text for b in response.content if b.type == "text"), "")
    used = getattr(response, "usage", None)
    return text, _usage(getattr(used, "input_tokens", None), getattr(used, "output_tokens", None))
