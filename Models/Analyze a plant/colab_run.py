# colab_run.py
# ═══════════════════════════════════════════════════════════════════════════
# COLAB DRIVER — runs the entire Plant Diagnosis v2 pipeline cell by cell.
# Copy each CELL into its own Colab cell and run them in order.
# ═══════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────────────────
# CELL 0 — Verify GPU and data before doing anything
# ─────────────────────────────────────────────────────────────────────────────
import os, subprocess, sys

print("═" * 70)
print("  PRE-FLIGHT CHECK")
print("═" * 70)

# GPU
try:
    out = subprocess.check_output(["nvidia-smi", "--query-gpu=name,memory.total",
                                   "--format=csv,noheader"]).decode().strip()
    print(f"  GPU: {out}")
except Exception as e:
    print(f"  ⚠ No GPU detected ({e}). Switch runtime → Change runtime type → GPU.")

# Data sanity
DATA_ROOT = "/content/plant_data_v2"
expected = ["disease", "pest", "deficiency"]
print(f"\n  Data root: {DATA_ROOT}")
if not os.path.isdir(DATA_ROOT):
    print(f"  ❌ {DATA_ROOT} not found. Upload/extract your data there first.")
else:
    for cat in expected:
        p = os.path.join(DATA_ROOT, cat)
        if os.path.isdir(p):
            n_classes = len([d for d in os.listdir(p)
                             if os.path.isdir(os.path.join(p, d))])
            n_imgs = sum(len(files) for _, _, files in os.walk(p))
            print(f"    ✓ {cat:<11}: {n_classes:>3} classes, {n_imgs:>7,} files")
        else:
            print(f"    ❌ {cat:<11}: missing at {p}")

# Mount Drive (for checkpoint mirroring)
print("\n  Mounting Google Drive ...")
try:
    from google.colab import drive
    drive.mount("/content/drive", force_remount=False)
    print("  ✓ Drive mounted at /content/drive")
except Exception as e:
    print(f"  ⚠ Drive mount skipped ({e}). Per-epoch backups will be local only.")

print("═" * 70)


# ─────────────────────────────────────────────────────────────────────────────
# CELL 1 — Install dependencies
# ─────────────────────────────────────────────────────────────────────────────
# CRITICAL: Pillow must be pinned to 10.4.0 BEFORE other imports, then we
# force a kernel restart so the pinned version is actually used.

import subprocess, sys, os

print("→ Installing dependencies ...")
subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                "Pillow==10.4.0",
                "timm>=1.0.7",
                "tqdm>=4.66",
                "matplotlib>=3.7"], check=False)

# Force restart only if Pillow is wrong (avoids infinite restart loop).
import PIL
if not PIL.__version__.startswith("10.4"):
    print(f"  Current Pillow: {PIL.__version__}  →  restarting runtime to apply 10.4.0 ...")
    os.kill(os.getpid(), 9)   # Colab will auto-restart; rerun cells from CELL 1
else:
    print(f"  ✓ Pillow {PIL.__version__}")
    print("  ✓ Dependencies ready.")


# ─────────────────────────────────────────────────────────────────────────────
# CELL 2 — Imports & config + ensure project files are in place
# ─────────────────────────────────────────────────────────────────────────────
import os, sys

PROJECT_DIR = "/content/plant_diagnosis_v2"
os.makedirs(PROJECT_DIR, exist_ok=True)

# Make project files importable. Colab strips sys.path on restart, so this
# line is required after every fresh runtime.
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

required_files = [
    "config.py", "datasets.py", "model.py", "metrics.py",
    "trainer.py", "interpretability.py", "inference.py",
    "main.py", "requirements.txt",
]
missing = [f for f in required_files
           if not os.path.isfile(os.path.join(PROJECT_DIR, f))]
if missing:
    print(f"❌ Missing project files in {PROJECT_DIR}: {missing}")
    print("   Upload them (config.py, datasets.py, model.py, ...) before continuing.")
    raise SystemExit
else:
    print(f"✓ All {len(required_files)} project files present in {PROJECT_DIR}")

import torch
import config as cfg

cfg.ensure_dirs()
cfg.print_config()


# ─────────────────────────────────────────────────────────────────────────────
# CELL 3 — Build dataloaders (single dataset scan)
# ─────────────────────────────────────────────────────────────────────────────
from datasets import build_dataloaders

train_loader, val_loader, meta = build_dataloaders()
print(f"\n✓ Dataloaders ready — {meta['num_fine']} fine classes")


# ─────────────────────────────────────────────────────────────────────────────
# CELL 4 — Build model
# ─────────────────────────────────────────────────────────────────────────────
from model import build_model

model = build_model(num_fine=meta["num_fine"])

# Quick forward-pass smoke test on one batch (catches dim issues fast).
imgs, cy, fy = next(iter(val_loader))
imgs = imgs.to(cfg.DEVICE)
with torch.no_grad():
    cl, fl = model(imgs)
print(f"  Forward smoke test → cat_logits {tuple(cl.shape)}, "
      f"fine_logits {tuple(fl.shape)}")
del imgs, cl, fl


# ─────────────────────────────────────────────────────────────────────────────
# CELL 5 — Train
# ─────────────────────────────────────────────────────────────────────────────
from trainer import Trainer

trainer = Trainer(model, train_loader, val_loader, meta)
summary = trainer.fit()
print("\n✓ Training finished")
print(f"  Best epoch     : {summary['best_epoch']}")
print(f"  Best fine F1   : {summary['best_fine_f1']:.4f}")


# ─────────────────────────────────────────────────────────────────────────────
# CELL 6 — Export best model (TorchScript + ONNX)
# ─────────────────────────────────────────────────────────────────────────────
from inference import (
    load_model_for_inference, export_torchscript, export_onnx,
)

best_model, fine_class_names = load_model_for_inference()
export_torchscript(best_model)
try:
    export_onnx(best_model)
except Exception as e:
    print(f"  [warn] ONNX export skipped: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# CELL 7 — Run a single inference (with Top-K and confidence-gap warning)
# ─────────────────────────────────────────────────────────────────────────────
from inference import predict, format_result

# Replace this with any image path you want to test.
TEST_IMAGE = "/content/plant_data_v2/disease/tomato___blight"

# Pick the first image in the chosen folder (for a sanity check).
import os
if os.path.isdir(TEST_IMAGE):
    candidates = [f for f in os.listdir(TEST_IMAGE)
                  if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    if candidates:
        TEST_IMAGE = os.path.join(TEST_IMAGE, candidates[0])

if os.path.isfile(TEST_IMAGE):
    result = predict(best_model, TEST_IMAGE, fine_class_names)
    print(format_result(result))
else:
    print(f"⚠ Test image not found: {TEST_IMAGE} — set TEST_IMAGE to a valid file.")


# ─────────────────────────────────────────────────────────────────────────────
# CELL 8 — Interpretability (Grad-CAM + Saliency + Feature maps)
# ─────────────────────────────────────────────────────────────────────────────
from interpretability import visualize

if os.path.isfile(TEST_IMAGE):
    out_png = visualize(
        best_model, TEST_IMAGE, fine_class_names,
        save_dir=cfg.INTERPRET_DIR, tag="demo",
    )
    print(f"  Explanation saved → {out_png}")
    # Display inline in Colab
    try:
        from IPython.display import Image as IPyImage, display
        display(IPyImage(out_png))
    except Exception:
        pass
else:
    print("⚠ Skipping visualization — no test image.")


# ─────────────────────────────────────────────────────────────────────────────
# CELL 9 — (Optional) Re-mirror best checkpoint to Drive
# ─────────────────────────────────────────────────────────────────────────────
import shutil

local_best = os.path.join(cfg.CHECKPOINT_DIR, "best_model.pt")
if os.path.isfile(local_best) and os.path.isdir(cfg.DRIVE_PROJECT_DIR):
    os.makedirs(cfg.DRIVE_PROJECT_DIR, exist_ok=True)
    shutil.copy2(local_best, cfg.DRIVE_BEST_MODEL)
    print(f"  ✓ Mirrored best model → {cfg.DRIVE_BEST_MODEL}")
else:
    print("  (skipped — local checkpoint or Drive directory missing)")
