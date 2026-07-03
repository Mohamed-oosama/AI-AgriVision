# datasets.py
# ═══════════════════════════════════════════════════════════════════════════
# Unified dual-label dataset: every sample carries (image, category_label,
# fine_label). Single scan per category root — no triple counting.
# ═══════════════════════════════════════════════════════════════════════════

import os
import random
from collections import Counter, defaultdict
from typing import Dict, List, Tuple

import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from torchvision import transforms
from PIL import Image, UnidentifiedImageError

import config as cfg


# ───────────────────────────────────────────────────────────────────────────
# Transforms
# ───────────────────────────────────────────────────────────────────────────
def build_transforms(train: bool) -> transforms.Compose:
    if train:
        return transforms.Compose([
            transforms.Resize((cfg.IMG_SIZE + 32, cfg.IMG_SIZE + 32)),
            transforms.RandomResizedCrop(
                cfg.IMG_SIZE,
                scale=(0.75, 1.0),
                ratio=(0.85, 1.15),
            ),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomVerticalFlip(p=0.2),
            transforms.RandomRotation(20),
            transforms.ColorJitter(brightness=0.25, contrast=0.25,
                                   saturation=0.20, hue=0.05),
            transforms.RandomAffine(degrees=0, translate=(0.05, 0.05)),
            transforms.ToTensor(),
            transforms.Normalize(cfg.NORM_MEAN, cfg.NORM_STD),
            transforms.RandomErasing(p=0.20, scale=(0.02, 0.15)),
        ])
    return transforms.Compose([
        transforms.Resize((cfg.IMG_SIZE, cfg.IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(cfg.NORM_MEAN, cfg.NORM_STD),
    ])


# ───────────────────────────────────────────────────────────────────────────
# Sample collection (scan each root EXACTLY once)
# ───────────────────────────────────────────────────────────────────────────
IMG_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp")


def _collect_category(root: str, category_name: str) -> Tuple[List[Tuple[str, str]], List[str]]:
    """Walk a category root once. Returns (samples, sorted_class_names).

    samples[i] = (path, fine_class_name)  — fine_class_name is prefixed with
    the category, e.g. 'disease::tomato___blight'.
    """
    if not os.path.isdir(root):
        raise FileNotFoundError(f"Category root not found: {root}")

    class_names = sorted(
        d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))
    )

    samples = []
    for cls in class_names:
        cls_dir = os.path.join(root, cls)
        prefixed = f"{category_name}::{cls}"
        for fname in os.listdir(cls_dir):
            if fname.lower().endswith(IMG_EXTS):
                samples.append((os.path.join(cls_dir, fname), prefixed))
    return samples, [f"{category_name}::{c}" for c in class_names]


def build_global_index() -> Tuple[List[Tuple[str, int, int]], List[str]]:
    """Single source of truth for ALL samples and labels.

    Returns:
        all_samples : list of (path, category_idx, fine_idx)
        fine_class_names : ordered list — index = fine_idx, value = 'cat::class'
    """
    fine_class_names: List[str] = []
    per_cat_samples: Dict[str, List[Tuple[str, str]]] = {}

    # First pass: collect samples + class lists per category.
    for cat in cfg.CATEGORIES:
        root = cfg.CATEGORY_DIRS[cat]
        samples, classes = _collect_category(root, cat)
        per_cat_samples[cat] = samples
        fine_class_names.extend(classes)

    fine_to_idx = {name: i for i, name in enumerate(fine_class_names)}

    # Second pass: build flat index.
    all_samples: List[Tuple[str, int, int]] = []
    for cat, samples in per_cat_samples.items():
        cat_idx = cfg.CATEGORY_TO_IDX[cat]
        for path, prefixed in samples:
            all_samples.append((path, cat_idx, fine_to_idx[prefixed]))

    return all_samples, fine_class_names


# ───────────────────────────────────────────────────────────────────────────
# Stratified train/val split
# ───────────────────────────────────────────────────────────────────────────
def stratified_split(samples: List[Tuple[str, int, int]],
                     val_ratio: float,
                     seed: int) -> Tuple[List, List]:
    rng = random.Random(seed)
    by_fine: Dict[int, List[Tuple[str, int, int]]] = defaultdict(list)
    for s in samples:
        by_fine[s[2]].append(s)

    train, val = [], []
    for fine_idx, group in by_fine.items():
        rng.shuffle(group)
        n_val = max(1, int(round(len(group) * val_ratio)))
        # Guard: never let validation eat the whole class.
        if n_val >= len(group):
            n_val = max(1, len(group) // 5)
        val.extend(group[:n_val])
        train.extend(group[n_val:])

    rng.shuffle(train)
    rng.shuffle(val)
    return train, val


# ───────────────────────────────────────────────────────────────────────────
# Dataset
# ───────────────────────────────────────────────────────────────────────────
class PlantDualLabelDataset(Dataset):
    """Returns (img_tensor, category_idx, fine_idx)."""

    def __init__(self, samples: List[Tuple[str, int, int]], train: bool):
        self.samples = samples
        self.transform = build_transforms(train)
        self.train = train

    def __len__(self) -> int:
        return len(self.samples)

    def _safe_load(self, path: str) -> Image.Image:
        try:
            with Image.open(path) as img:
                return img.convert("RGB")
        except (UnidentifiedImageError, OSError, SyntaxError):
            # Return a black image as a last-resort fallback rather than crashing.
            return Image.new("RGB", (cfg.IMG_SIZE, cfg.IMG_SIZE), (0, 0, 0))

    def __getitem__(self, idx: int):
        path, cat_idx, fine_idx = self.samples[idx]
        img = self._safe_load(path)
        img = self.transform(img)
        return img, cat_idx, fine_idx


# ───────────────────────────────────────────────────────────────────────────
# Sampler weights & class weights
# ───────────────────────────────────────────────────────────────────────────
def compute_sampler_weights(train_samples: List[Tuple[str, int, int]],
                            num_fine: int) -> torch.DoubleTensor:
    counts = Counter(s[2] for s in train_samples)
    # Inverse-frequency weights, smoothed to avoid extreme values.
    inv = {k: 1.0 / np.sqrt(v) for k, v in counts.items()}
    w = [inv[s[2]] for s in train_samples]
    return torch.DoubleTensor(w)


def compute_class_weights(train_samples: List[Tuple[str, int, int]],
                          num_classes: int,
                          label_index: int) -> torch.Tensor:
    """label_index = 1 (category) or 2 (fine)."""
    counts = np.zeros(num_classes, dtype=np.float64)
    for s in train_samples:
        counts[s[label_index]] += 1
    counts = np.maximum(counts, 1.0)
    weights = counts.sum() / (num_classes * counts)   # balanced weighting
    return torch.tensor(weights, dtype=torch.float32)


# ───────────────────────────────────────────────────────────────────────────
# DataLoader builders
# ───────────────────────────────────────────────────────────────────────────
def build_dataloaders():
    print("→ Scanning datasets ...")
    samples, fine_class_names = build_global_index()
    num_fine = len(fine_class_names)

    print(f"  Total samples : {len(samples):,}")
    print(f"  Fine classes  : {num_fine}")
    print(f"  Categories    : {cfg.NUM_CATEGORIES}")

    # Per-category counts (sanity check).
    cat_counts = Counter(s[1] for s in samples)
    for c in cfg.CATEGORIES:
        n = cat_counts[cfg.CATEGORY_TO_IDX[c]]
        print(f"    {c:<11}: {n:>7,} images")

    train_s, val_s = stratified_split(samples, cfg.VAL_SPLIT, cfg.SEED)
    print(f"  Train samples : {len(train_s):,}")
    print(f"  Val samples   : {len(val_s):,}")

    train_ds = PlantDualLabelDataset(train_s, train=True)
    val_ds   = PlantDualLabelDataset(val_s,   train=False)

    sampler = None
    shuffle = True
    if cfg.USE_WEIGHTED_SAMPLER:
        weights = compute_sampler_weights(train_s, num_fine)
        sampler = WeightedRandomSampler(weights, num_samples=len(weights),
                                        replacement=True)
        shuffle = False  # mutually exclusive with sampler

    train_loader = DataLoader(
        train_ds,
        batch_size=cfg.BATCH_SIZE,
        sampler=sampler,
        shuffle=shuffle,
        num_workers=cfg.NUM_WORKERS,
        pin_memory=cfg.PIN_MEMORY,
        persistent_workers=cfg.PERSISTENT_WORKERS and cfg.NUM_WORKERS > 0,
        drop_last=True,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=cfg.BATCH_SIZE,
        shuffle=False,
        num_workers=cfg.NUM_WORKERS,
        pin_memory=cfg.PIN_MEMORY,
        persistent_workers=cfg.PERSISTENT_WORKERS and cfg.NUM_WORKERS > 0,
    )

    cat_class_weights  = compute_class_weights(train_s, cfg.NUM_CATEGORIES, 1)
    fine_class_weights = compute_class_weights(train_s, num_fine,           2)

    meta = {
        "fine_class_names":   fine_class_names,
        "num_fine":           num_fine,
        "cat_class_weights":  cat_class_weights,
        "fine_class_weights": fine_class_weights,
        "train_size":         len(train_s),
        "val_size":           len(val_s),
    }
    return train_loader, val_loader, meta
