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
import urllib.error
import urllib.request
from dataclasses import dataclass

from aicefr.coach.upgrade import SCHEMA, SYSTEM, UpgradeError

logger = logging.getLogger(__name__)

TIMEOUT_S = 45


@dataclass(frozen=True)
class Preset:
    base_url: str
    key_env: str
    model: str


OPENAI_COMPATIBLE = {
    "groq": Preset(
        "https://api.groq.com/openai/v1", "AICEFR_GROQ_API_KEY", "llama-3.3-70b-versatile"
    ),
    "gemini": Preset(
        "https://generativelanguage.googleapis.com/v1beta/openai",
        "AICEFR_GEMINI_API_KEY",
        "gemini-3.5-flash-lite",
    ),
    "openrouter": Preset("https://openrouter.ai/api/v1", "AICEFR_OPENROUTER_API_KEY", ""),
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
        if self.name == "anthropic":
            return _anthropic(self.model, self.key, user)
        return _openai_compatible(OPENAI_COMPATIBLE[self.name].base_url, self.model, self.key, user)


def provider_from(settings) -> Provider | None:
    """The configured provider, or None when the feature is off or not set up."""
    name = settings.coach_provider
    if name in ("", "off") or name not in NAMES:
        return None
    if name == "anthropic":
        key, model = os.getenv(ANTHROPIC_KEY_ENV, ""), ANTHROPIC_MODEL
    else:
        preset = OPENAI_COMPATIBLE[name]
        key, model = os.getenv(preset.key_env, ""), preset.model
    model = settings.coach_model or model
    if not key or not model:
        return None
    return Provider(name, model, key)


def _openai_compatible(base_url: str, model: str, key: str, user: str) -> str:
    body = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as r:  # noqa: S310 - fixed https hosts
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # 429 is the free tier's daily or per-minute cap: say so, not "error".
        if e.code == 429:
            raise UpgradeError("nhà cung cấp mô hình đang giới hạn lượt, hãy thử lại sau") from e
        logger.warning("coach provider answered %s", e.code)
        raise UpgradeError(f"nhà cung cấp mô hình trả lỗi {e.code}") from e
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        raise UpgradeError("không liên lạc được nhà cung cấp mô hình") from e
    try:
        return data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as e:
        raise UpgradeError("câu trả lời của mô hình thiếu nội dung") from e


def _anthropic(model: str, key: str, user: str) -> str:
    try:
        import anthropic
    except ImportError as e:  # the `coach` extra is not installed
        raise UpgradeError("máy chủ chưa cài gói anthropic (nhóm coach)") from e
    client = anthropic.Anthropic(api_key=key, timeout=TIMEOUT_S, max_retries=1)
    try:
        response = client.messages.create(
            model=model,
            max_tokens=4000,
            system=SYSTEM,
            messages=[{"role": "user", "content": user}],
            # A rewrite needs little deliberation; the schema keeps the JSON valid.
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
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
    return next((b.text for b in response.content if b.type == "text"), "")
