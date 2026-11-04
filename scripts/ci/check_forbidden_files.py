"""Chặn commit audio, model, cơ sở dữ liệu và file bí mật (AGENTS.md)."""

import fnmatch
import subprocess
import sys

FORBIDDEN = [
    "*.wav",
    "*.mp3",
    "*.m4a",
    "*.flac",
    "*.ogg",
    "*.webm",
    "*.bin",
    "*.pt",
    "*.pth",
    "*.onnx",
    "*.safetensors",
    "*.ckpt",
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.p12",
]
ALLOWED = [
    ".env.example",
    ".env.production.example",
    # Synthetic (text-to-speech) clips for the landing demo, no learner voice.
    "demo_a2.mp3",
    "demo_b1.mp3",
    "demo_b2.mp3",
]


def main() -> int:
    files = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, check=True
    ).stdout.split("\n")
    hits = [
        f
        for f in files
        if f
        and f.split("/")[-1] not in ALLOWED
        and any(fnmatch.fnmatch(f.split("/")[-1], p) for p in FORBIDDEN)
    ]
    if hits:
        print("File không được commit (audio/model/DB/bí mật):")
        print("\n".join(f"  {h}" for h in hits))
        return 1
    print(f"Đã kiểm tra {len([f for f in files if f])} file: không có file bị cấm.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
