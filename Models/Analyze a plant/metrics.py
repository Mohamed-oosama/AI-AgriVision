# metrics.py
# ═══════════════════════════════════════════════════════════════════════════
# Lightweight metrics — accuracy + macro precision/recall/F1 — implemented
# without scikit-learn so we don't add another dependency.
# ═══════════════════════════════════════════════════════════════════════════

from typing import Dict, List
import numpy as np
import torch


def _to_numpy(x):
    if isinstance(x, torch.Tensor):
        return x.detach().cpu().numpy()
    return np.asarray(x)


def accuracy(preds, targets) -> float:
    p = _to_numpy(preds)
    t = _to_numpy(targets)
    if len(t) == 0:
        return 0.0
    return float((p == t).mean())


def macro_prf1(preds, targets, num_classes: int) -> Dict[str, float]:
    """Macro-averaged precision/recall/F1, computed from the confusion matrix.

    Classes that never appear in `targets` are excluded from the average,
    which is the standard convention and avoids a deceptively low F1 caused
    by absent classes scoring 0.
    """
    p = _to_numpy(preds).astype(np.int64)
    t = _to_numpy(targets).astype(np.int64)

    if len(t) == 0:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    cm = np.zeros((num_classes, num_classes), dtype=np.int64)
    for ti, pi in zip(t, p):
        cm[ti, pi] += 1

    tp = np.diag(cm).astype(np.float64)
    pred_pos = cm.sum(axis=0).astype(np.float64)
    real_pos = cm.sum(axis=1).astype(np.float64)

    with np.errstate(divide="ignore", invalid="ignore"):
        prec = np.where(pred_pos > 0, tp / pred_pos, 0.0)
        rec  = np.where(real_pos > 0, tp / real_pos, 0.0)
        f1   = np.where((prec + rec) > 0, 2 * prec * rec / (prec + rec), 0.0)

    present = real_pos > 0
    if not present.any():
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    return {
        "precision": float(prec[present].mean()),
        "recall":    float(rec[present].mean()),
        "f1":        float(f1[present].mean()),
    }


class MetricTracker:
    """Accumulates predictions across a full epoch, then computes metrics."""

    def __init__(self, num_categories: int, num_fine: int):
        self.num_categories = num_categories
        self.num_fine       = num_fine
        self.reset()

    def reset(self) -> None:
        self.cat_preds:  List[int] = []
        self.cat_tgts:   List[int] = []
        self.fine_preds: List[int] = []
        self.fine_tgts:  List[int] = []

    def update(self, cat_logits, fine_logits, cat_tgt, fine_tgt) -> None:
        cp = cat_logits.argmax(dim=1).detach().cpu().numpy()
        fp = fine_logits.argmax(dim=1).detach().cpu().numpy()
        self.cat_preds.extend(cp.tolist())
        self.cat_tgts.extend(_to_numpy(cat_tgt).tolist())
        self.fine_preds.extend(fp.tolist())
        self.fine_tgts.extend(_to_numpy(fine_tgt).tolist())

    def compute(self) -> Dict[str, float]:
        cat_acc  = accuracy(self.cat_preds,  self.cat_tgts)
        fine_acc = accuracy(self.fine_preds, self.fine_tgts)
        cat_m    = macro_prf1(self.cat_preds,  self.cat_tgts,  self.num_categories)
        fine_m   = macro_prf1(self.fine_preds, self.fine_tgts, self.num_fine)
        return {
            "cat_acc":  cat_acc,
            "fine_acc": fine_acc,
            "cat_precision":  cat_m["precision"],
            "cat_recall":     cat_m["recall"],
            "cat_f1":         cat_m["f1"],
            "fine_precision": fine_m["precision"],
            "fine_recall":    fine_m["recall"],
            "fine_f1":        fine_m["f1"],
        }
