# main.py
# ═══════════════════════════════════════════════════════════════════════════
# End-to-end orchestration: setup → data → model → train → export.
# ═══════════════════════════════════════════════════════════════════════════

import os
import sys
import random
import argparse

import numpy as np
import torch

import config as cfg
from datasets import build_dataloaders
from model    import build_model
from trainer  import Trainer
from inference import (
    load_model_for_inference, predict, format_result,
    export_torchscript, export_onnx,
)


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = True   # faster on fixed input sizes


def run_train() -> dict:
    cfg.ensure_dirs()
    cfg.print_config()
    set_seed(cfg.SEED)

    train_loader, val_loader, meta = build_dataloaders()
    print()
    model = build_model(num_fine=meta["num_fine"])

    trainer = Trainer(model, train_loader, val_loader, meta)
    summary = trainer.fit()
    return summary


def run_export() -> None:
    print("\n→ Exporting best model ...")
    model, _ = load_model_for_inference()
    export_torchscript(model)
    try:
        export_onnx(model)
    except Exception as e:
        print(f"  [warn] ONNX export failed: {e}")


def run_predict(image_path: str) -> None:
    if not os.path.isfile(image_path):
        print(f"Image not found: {image_path}")
        sys.exit(1)
    model, fine_class_names = load_model_for_inference()
    result = predict(model, image_path, fine_class_names)
    print(format_result(result))


def main() -> None:
    parser = argparse.ArgumentParser(description="Plant Diagnosis v2")
    parser.add_argument("--mode",
                        choices=["train", "export", "predict", "all"],
                        default="all")
    parser.add_argument("--image", type=str, default=None,
                        help="Image path (only used with --mode predict)")
    args = parser.parse_args()

    if args.mode in ("train", "all"):
        run_train()
    if args.mode in ("export", "all"):
        run_export()
    if args.mode == "predict":
        if args.image is None:
            print("Use --image PATH for prediction mode."); sys.exit(1)
        run_predict(args.image)


if __name__ == "__main__":
    main()
