# inference.py
# ═══════════════════════════════════════════════════════════════════════════
# Inference utilities:
#   - load_model_for_inference()  → restore weights and class names
#   - predict()                   → category + fine prediction with Top-K
#   - format_result()             → boxed text output (matches the spec)
#   - confidence_gap_warning()    → warns on visually-similar pairs
#   - export_torchscript() / export_onnx()
# ═══════════════════════════════════════════════════════════════════════════

import os
import json
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from torchvision import transforms

import config as cfg
from model import build_model


# ───────────────────────────────────────────────────────────────────────────
# Loading
# ───────────────────────────────────────────────────────────────────────────
def load_model_for_inference(checkpoint_path: Optional[str] = None):
    """Returns (model, fine_class_names) ready for eval()."""
    if checkpoint_path is None:
        checkpoint_path = os.path.join(cfg.CHECKPOINT_DIR, "best_model.pt")

    if not os.path.isfile(checkpoint_path):
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

    state = torch.load(checkpoint_path, map_location=cfg.DEVICE,
                       weights_only=False)
    fine_class_names: List[str] = state["fine_class_names"]
    num_fine = state.get("num_fine", len(fine_class_names))

    model = build_model(num_fine=num_fine)
    model.load_state_dict(state["model_state"])
    model.eval()
    return model, fine_class_names


# ───────────────────────────────────────────────────────────────────────────
# Pre-processing
# ───────────────────────────────────────────────────────────────────────────
def _eval_transform():
    return transforms.Compose([
        transforms.Resize((cfg.IMG_SIZE, cfg.IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(cfg.NORM_MEAN, cfg.NORM_STD),
    ])


def preprocess_image(image_path: str) -> torch.Tensor:
    pil = Image.open(image_path).convert("RGB")
    return _eval_transform()(pil).unsqueeze(0).to(cfg.DEVICE)


# ───────────────────────────────────────────────────────────────────────────
# Confidence-gap warning
# ───────────────────────────────────────────────────────────────────────────
def confidence_gap_warning(top_classes: List[str],
                           top_probs: List[float]) -> Optional[str]:
    """Return a warning string if the top-2 are a known confusable pair AND
    their probability gap is below the threshold."""
    if len(top_classes) < 2:
        return None
    top1, top2 = top_classes[0], top_classes[1]
    p1,   p2   = top_probs[0],   top_probs[1]

    pair = (top1, top2)
    rev  = (top2, top1)
    if pair in [tuple(x) for x in cfg.CONFUSABLE_PAIRS] or \
       rev  in [tuple(x) for x in cfg.CONFUSABLE_PAIRS]:
        gap = abs(p1 - p2)
        if gap < cfg.CONFIDENCE_GAP_THRESHOLD:
            return (f"⚠ Warning: low confidence gap ({gap*100:.1f}%) "
                    f"between visually similar classes.\n"
                    f"   Recommend expert verification.")
    return None


# ───────────────────────────────────────────────────────────────────────────
# Prediction
# ───────────────────────────────────────────────────────────────────────────
@torch.no_grad()
def predict(model, image_path: str,
            fine_class_names: List[str],
            top_k: int = cfg.TOP_K) -> Dict:
    x = preprocess_image(image_path)
    cat_logits, fine_logits = model(x)
    cat_probs  = F.softmax(cat_logits,  dim=1).cpu().numpy()[0]
    fine_probs = F.softmax(fine_logits, dim=1).cpu().numpy()[0]

    cat_idx = int(np.argmax(cat_probs))
    cat_name = cfg.CATEGORIES[cat_idx]
    cat_conf = float(cat_probs[cat_idx])

    order = np.argsort(-fine_probs)[: max(top_k, 2)]   # need ≥2 for the warning
    top_classes = [fine_class_names[i] for i in order]
    top_probs   = [float(fine_probs[i]) for i in order]

    fine_name = top_classes[0]
    fine_conf = top_probs[0]

    warning = confidence_gap_warning(top_classes, top_probs)

    return {
        "category":         cat_name,
        "category_conf":    cat_conf,
        "category_probs":   {c: float(cat_probs[i])
                             for i, c in enumerate(cfg.CATEGORIES)},
        "diagnosis":        fine_name,
        "diagnosis_conf":   fine_conf,
        "top_k":            list(zip(top_classes[:top_k], top_probs[:top_k])),
        "warning":          warning,
        "image_path":       image_path,
    }


# ───────────────────────────────────────────────────────────────────────────
# Pretty output (matches the box format from the spec)
# ───────────────────────────────────────────────────────────────────────────
def format_result(result: Dict) -> str:
    lines = [
        "┌─ Plant Diagnosis Result ──────────────────────────────",
        f"│  Category   : {result['category']} "
        f"({result['category_conf']*100:.1f}%)",
        f"│  Diagnosis  : {result['diagnosis']} "
        f"({result['diagnosis_conf']*100:.1f}%)",
        "│  Top-K:",
    ]
    for name, p in result["top_k"]:
        lines.append(f"│   {name}: {p*100:.1f}%")
    lines.append("└───────────────────────────────")
    if result.get("warning"):
        lines.append(result["warning"])
    return "\n".join(lines)


# ───────────────────────────────────────────────────────────────────────────
# Export — TorchScript + ONNX
# ───────────────────────────────────────────────────────────────────────────
def export_torchscript(model,
                       out_path: Optional[str] = None) -> str:
    if out_path is None:
        out_path = os.path.join(cfg.EXPORT_DIR, "plant_model.torchscript.pt")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    model.eval()
    example = torch.randn(1, 3, cfg.IMG_SIZE, cfg.IMG_SIZE, device=cfg.DEVICE)
    traced = torch.jit.trace(model, example, strict=False)
    traced.save(out_path)
    print(f"  TorchScript saved → {out_path}")
    return out_path


def export_onnx(model,
                out_path: Optional[str] = None,
                opset: int = 17) -> str:
    if out_path is None:
        out_path = os.path.join(cfg.EXPORT_DIR, "plant_model.onnx")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    model.eval()
    dummy = torch.randn(1, 3, cfg.IMG_SIZE, cfg.IMG_SIZE, device=cfg.DEVICE)
    torch.onnx.export(
        model, dummy, out_path,
        input_names=["input"],
        output_names=["category_logits", "fine_logits"],
        opset_version=opset,
        dynamic_axes={
            "input":           {0: "batch"},
            "category_logits": {0: "batch"},
            "fine_logits":     {0: "batch"},
        },
    )
    print(f"  ONNX saved → {out_path}")
    return out_path


# ───────────────────────────────────────────────────────────────────────────
# Convenience CLI
# ───────────────────────────────────────────────────────────────────────────
def diagnose(image_path: str,
             checkpoint_path: Optional[str] = None) -> Dict:
    model, fine_class_names = load_model_for_inference(checkpoint_path)
    result = predict(model, image_path, fine_class_names)
    print(format_result(result))
    return result
