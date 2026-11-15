"""DeBERTa-v3 + LoRA: an overall score read from the transcript alone.

The text half of the fusion scorer (`aicefr.scoring.fusion`). Fine-tuned on
Speak & Improve 2025 train P3+P4 transcripts (LoRA r=16 on query/value plus a
regression head). Its accuracy is reported in the internal chapter
"Thực nghiệm", not here: corpus statistics stay out of this repository.

Files, all outside Git in `AICEFR_MODEL_DIR` and checked against the SHA-256
values the fusion artifact pins:

* `deberta-v3-base/`: `config.json` and `model.safetensors` of
  microsoft/deberta-v3-base at a pinned revision (MIT licence);
* `deberta_lora_s42/`: the adapter (LoRA matrices, pooler, head, a few MB) and
  the tokenizer. Derived from the corpus, so never published.

The LoRA update is merged into the base weights here, W + (alpha/r) * B @ A,
the same arithmetic as peft's `merge_and_unload`, so the service needs torch
and transformers but not peft. Heavy imports and the weights load on the
first prediction, not at construction: building a scorer to read its version
(readiness check, admin activation) must not pull 700 MB into that process.
"""

from __future__ import annotations

import hashlib
import logging
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

ADAPTER_PREFIX = "base_model.model."


class TextModelError(RuntimeError):
    """The text model cannot run: files missing, hashes wrong, or libraries absent."""


class DebertaTextModel:
    """Loads the pinned base model plus adapter once, then scores transcripts."""

    def __init__(self, spec: dict, folder: Path) -> None:
        self.version: str = spec["version"]
        self._base = folder / spec["base_dir"]
        self._adapter = folder / spec["adapter_dir"]
        self._base_sha: dict[str, str] = spec["base_sha256"]
        self._adapter_sha: dict[str, str] = spec["adapter_sha256"]
        self._scaling = float(spec["lora_alpha"]) / float(spec["lora_r"])
        self._max_length = int(spec["max_length"])
        self._mu, self._sd = (float(v) for v in spec["target_norm"])
        self._lock = threading.Lock()
        self._model = None
        self._tokenizer = None

    def missing_files(self) -> list[str]:
        """Files the artifact names that are not on disk. Cheap: no hashing, no loading."""
        expected = [self._base / f for f in self._base_sha] + [
            self._adapter / f for f in self._adapter_sha
        ]
        return [str(p) for p in expected if not p.is_file()]

    def _verify(self) -> None:
        for folder, pins in ((self._base, self._base_sha), (self._adapter, self._adapter_sha)):
            for name, expected in pins.items():
                path = folder / name
                if not path.is_file():
                    raise TextModelError(f"không tìm thấy {path}")
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                if digest != expected:
                    raise TextModelError(
                        f"SHA-256 của {path} là {digest}, khác giá trị ghim {expected}"
                    )

    def _load(self) -> None:
        self._verify()
        try:
            import torch
            from safetensors.torch import load_file
            from transformers import (
                AutoTokenizer,
                DebertaV2Config,
                DebertaV2ForSequenceClassification,
            )
        except ImportError as e:  # the optional `text` extra is not installed
            raise TextModelError(f"thiếu thư viện cho mô hình văn bản: {e}") from e

        config = DebertaV2Config.from_json_file(str(self._base / "config.json"))
        config.num_labels = 1
        model = DebertaV2ForSequenceClassification(config)
        state = {k: v.float() for k, v in load_file(str(self._base / "model.safetensors")).items()}
        adapter = load_file(str(self._adapter / "adapter_model.safetensors"))

        # LoRA: fold B @ A into the frozen weight it was trained against.
        for key in [k for k in adapter if k.endswith(".lora_A.weight")]:
            module = key.removeprefix(ADAPTER_PREFIX).removesuffix(".lora_A.weight")
            a, b = adapter[key].float(), adapter[key.replace("lora_A", "lora_B")].float()
            state[f"{module}.weight"] = state[f"{module}.weight"] + self._scaling * (b @ a)
        # The pooler and the regression head were trained in full (modules_to_save).
        for key, value in adapter.items():
            if "lora_" not in key:
                state[key.removeprefix(ADAPTER_PREFIX)] = value.float()

        result = model.load_state_dict(state, strict=False)
        if result.missing_keys:
            raise TextModelError(
                f"thiếu trọng số khi nạp mô hình văn bản: {result.missing_keys[:5]}"
            )
        model.eval()
        self._tokenizer = AutoTokenizer.from_pretrained(str(self._adapter))
        self._model = model
        self._torch = torch
        logger.info("text model %s loaded", self.version)

    def predict(self, text: str) -> float:
        """The model's raw score on the 1-6 scale, not clipped (the fusion was fitted on it raw)."""
        with self._lock:
            if self._model is None:
                self._load()
        enc = self._tokenizer(
            text, truncation=True, max_length=self._max_length, return_tensors="pt"
        )
        with self._torch.inference_mode():
            logit = self._model(**enc).logits.squeeze().item()
        return float(logit * self._sd + self._mu)
