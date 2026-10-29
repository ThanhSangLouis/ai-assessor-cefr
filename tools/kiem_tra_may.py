#!/usr/bin/env python3
"""Kiểm tra máy này fine-tune được model nào.
Chạy:  python3 tools/kiem_tra_may.py
Không cần cài gì trước; script tự báo thiếu gì.
"""

import platform
import shutil
import subprocess
import sys


def ok(b):
    return "CO" if b else "KHONG"


print("=" * 62)
print("KIEM TRA MAY - du dieu kien fine-tune khong?")
print("=" * 62)
print(f"He dieu hanh : {platform.system()} {platform.release()} ({platform.machine()})")
print(f"Python       : {sys.version.split()[0]}")

try:
    import torch
except ImportError:
    print("\nChua cai PyTorch. Cai bang:  pip install torch")
    print("Cai xong chay lai script nay.")
    sys.exit(0)

print(f"PyTorch      : {torch.__version__}")
cuda = torch.cuda.is_available()
mps = getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()
print(f"CUDA (NVIDIA): {ok(cuda)}")
print(f"MPS (Apple)  : {ok(mps)}")

vram = 0.0
if cuda:
    p = torch.cuda.get_device_properties(0)
    vram = p.total_memory / 1024**3
    print(f"GPU          : {p.name}, {vram:.1f} GB VRAM")
elif mps:
    try:
        out = subprocess.check_output(["sysctl", "-n", "hw.memsize"]).decode().strip()
        vram = int(out) / 1024**3
        print(f"GPU          : Apple Silicon, dung chung {vram:.0f} GB RAM he thong")
    except Exception:
        vram = 8.0
else:
    print("GPU          : khong co, chi chay CPU")

print(f"ffmpeg       : {ok(shutil.which('ffmpeg'))}")

print("\n" + "=" * 62)
print("KET LUAN")
print("=" * 62)


def verdict(name, need, note=""):
    if cuda and vram >= need:
        s = "CHAY DUOC"
    elif mps and vram >= need * 3:
        s = "CHAY DUOC (cham hon CUDA ~2-3 lan)"
    elif cuda or mps:
        s = f"KHONG DU (can >= {need} GB)"
    else:
        s = "KHONG (chi co CPU)"
    print(f"  {name:44s} {s}")
    if note:
        print(f"      -> {note}")


verdict(
    "1. Fine-tune BERT/DeBERTa base (transcript)",
    6,
    "Day la fine-tune BAT BUOC cua de tai. Batch 16, 3 epoch, ~3000 mau.",
)
verdict(
    "2. Fine-tune wav2vec2-base (am thanh)",
    10,
    "Nang hon nhieu. Neu khong du thi dung Kaggle P100 (16 GB, 30 gio/tuan mien phi).",
)
verdict("3. Chay Whisper large-v3-turbo suy luan", 6, "Chi suy luan, khong huan luyen.")

print("\nGoi y:")
if cuda and vram >= 10:
    print("  May nay du de fine-tune ca hai nhanh. Chay local duoc.")
elif cuda and vram >= 6:
    print("  Fine-tune nhanh van ban duoc. Nhanh am thanh nen dung Kaggle.")
elif mps:
    print("  Mac chay duoc nhung cham. Khuyen dung Colab T4 cho huan luyen,")
    print("  may nay de viet code va chay thu file le.")
else:
    print("  Dung Google Colab (T4 mien phi) hoac Kaggle (P100, 30 gio/tuan).")
    print("  May nay chi de viet code va chay script test.")
print()
