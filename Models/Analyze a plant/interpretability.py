"""
Interpretability utilities:
  - Grad-CAM heatmap on the finegrained head
  - Simple gradient saliency map
  - Feature map ("x-ray") visualization from a chosen backbone layer
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from torchvision import transforms

import config as cfg


# ── Helpers ────────────────────────────────────────────────────────────────
def _load_image_tensor(img_path):
    tf = transforms.Compose([
        transforms.Resize(int(cfg.IMG_SIZE * 1.15)),
        transforms.CenterCrop(cfg.IMG_SIZE),
        transforms.ToTensor(),
        transforms.Normalize(cfg.NORM_MEAN, cfg.NORM_STD),
    ])
    img = Image.open(str(img_path)).convert("RGB")
    return tf(img).unsqueeze(0), img


def _unnormalize(t: torch.Tensor) -> np.ndarray:
    mean = torch.tensor(cfg.NORM_MEAN).view(3, 1, 1)
    std  = torch.tensor(cfg.NORM_STD).view(3, 1, 1)
    img  = t.detach().cpu() * std + mean
    return img.clamp(0, 1).permute(1, 2, 0).numpy()


def _last_conv_module(model: torch.nn.Module) -> torch.nn.Module:
    """Find the last Conv2d-producing module in the backbone (for Grad-CAM hook)."""
    last = None
    for m in model.modules():
        if isinstance(m, torch.nn.Conv2d):
            last = m
    if last is None:
        raise RuntimeError("No Conv2d layer found in model.")
    return last


# ── Grad-CAM ───────────────────────────────────────────────────────────────
class GradCAM:
    def __init__(self, model: torch.nn.Module,
                 target_layer: Optional[torch.nn.Module] = None):
        self.model = model.eval()
        self.target_layer = target_layer or _last_conv_module(model)
        self.activations = None
        self.gradients   = None
        self._handles = [
            self.target_layer.register_forward_hook(self._fwd_hook),
            self.target_layer.register_full_backward_hook(self._bwd_hook),
        ]

    def _fwd_hook(self, _m, _i, output):
        self.activations = output.detach()

    def _bwd_hook(self, _m, _gin, grad_out):
        self.gradients = grad_out[0].detach()

    def remove(self):
        for h in self._handles:
            h.remove()

    def __call__(self, x: torch.Tensor, target_class: int) -> np.ndarray:
        """Returns a (H, W) heatmap in [0, 1] using the finegrained head."""
        x = x.requires_grad_(True)
        _, fine_logits = self.model(x)
        score = fine_logits[0, target_class]
        self.model.zero_grad()
        score.backward(retain_graph=False)

        weights = self.gradients.mean(dim=(2, 3), keepdim=True)
        cam     = (weights * self.activations).sum(dim=1, keepdim=True)
        cam     = F.relu(cam)
        cam     = F.interpolate(cam, size=x.shape[-2:], mode="bilinear",
                                align_corners=False)
        cam     = cam.squeeze().cpu().numpy()
        if cam.max() > 0:
            cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)
        return cam


# ── Saliency ───────────────────────────────────────────────────────────────
def saliency_map(model: torch.nn.Module, x: torch.Tensor,
                 target_class: int) -> np.ndarray:
    model.eval()
    # Build a fresh leaf tensor that DEFINITELY tracks gradients, regardless
    # of the autograd state of the input we were handed.
    x = x.detach().clone().requires_grad_(True)
    _, fine_logits = model(x)
    score = fine_logits[0, target_class]
    model.zero_grad()
    score.backward()
    if x.grad is None:
        # Defensive fallback — shouldn't happen, but if it does, return zeros
        # rather than crashing the whole visualization.
        return np.zeros(x.shape[-2:], dtype=np.float32)
    sal = x.grad.detach().abs().max(dim=1)[0].squeeze().cpu().numpy()
    if sal.max() > 0:
        sal = (sal - sal.min()) / (sal.max() - sal.min() + 1e-8)
    return sal


# ── Feature maps (x-ray style) ─────────────────────────────────────────────
def feature_maps(model: torch.nn.Module, x: torch.Tensor,
                 n_maps: int = 8) -> np.ndarray:
    """Average activations from the last conv layer and return top-N channels."""
    model.eval()
    last = _last_conv_module(model)
    activations = {}
    h = last.register_forward_hook(
        lambda _m, _i, o: activations.setdefault("a", o.detach())
    )
    with torch.no_grad():
        _ = model(x)
    h.remove()
    fmap = activations["a"].squeeze(0).cpu().numpy()  # (C, H, W)
    energies = fmap.mean(axis=(1, 2))
    idx = np.argsort(-energies)[:n_maps]
    return fmap[idx]


# ── Visual ─────────────────────────────────────────────────────────────────
def visualize(
    model:             torch.nn.Module,
    image_path:        Union[str, Path],
    fine_class_names:  List[str],
    save_dir:          Union[str, Path],
    tag:               str = "sample",
) -> str:
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / f"{tag}_explain.png"

    x, pil_img = _load_image_tensor(image_path)
    x = x.to(cfg.DEVICE)

    # Auto-predict target class from the fine head
    model = model.to(cfg.DEVICE).eval()
    with torch.no_grad():
        _, fine_logits = model(x)
        target_class = int(fine_logits.argmax(dim=1).item())
    class_name = (fine_class_names[target_class]
                  if 0 <= target_class < len(fine_class_names)
                  else f"idx={target_class}")

    gc  = GradCAM(model)
    cam = gc(x, target_class)
    gc.remove()

    # Saliency and feature_maps each need a FRESH tensor — the GradCAM call
    # above consumed the autograd graph attached to `x`.
    x_sal, _   = _load_image_tensor(image_path)
    x_sal      = x_sal.to(cfg.DEVICE)
    sal        = saliency_map(model, x_sal, target_class)

    x_feat, _  = _load_image_tensor(image_path)
    x_feat     = x_feat.to(cfg.DEVICE)
    fmaps      = feature_maps(model, x_feat, n_maps=4)

    img_np = _unnormalize(x.squeeze(0))

    fig, axes = plt.subplots(2, 4, figsize=(16, 8))
    fig.suptitle(f"Prediction: {class_name}", fontsize=12)

    axes[0, 0].imshow(img_np);                 axes[0, 0].set_title("input");     axes[0, 0].axis("off")
    axes[0, 1].imshow(img_np);                 axes[0, 1].imshow(cam, cmap="jet", alpha=0.5)
    axes[0, 1].set_title("grad-cam overlay");  axes[0, 1].axis("off")
    axes[0, 2].imshow(cam, cmap="jet");        axes[0, 2].set_title("grad-cam"); axes[0, 2].axis("off")
    axes[0, 3].imshow(sal, cmap="hot");        axes[0, 3].set_title("saliency"); axes[0, 3].axis("off")

    for i in range(4):
        axes[1, i].imshow(fmaps[i], cmap="gray")
        axes[1, i].set_title(f"feature map {i+1}")
        axes[1, i].axis("off")

    fig.tight_layout()
    fig.savefig(save_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return str(save_path)
