# trainer.py
# ═══════════════════════════════════════════════════════════════════════════
# Training loop with:
#   - per-step tqdm bar       :  "Ep 41/50 TRAIN: 22%|███       | 1028/4699 [05:45<20:22, 3.00it/s, acc=0.969, loss=0.136]"
#   - one-line epoch summary :  "Epoch 040 | Train acc 0.967 | Val acc 0.849 | cat_acc=0.987 cat_f1=0.985 fine_acc=0.849 fine_f1=0.781 | lr=3.96e-05 | 1729s | ✓ BEST SAVED!"
#   - dual-head joint loss with FocalLoss (fine) + label-smoothed CE (category)
#   - MixUp, AMP, warmup-cosine LR, gradient clipping
#   - per-epoch checkpoint, best checkpoint, optional Drive mirror
#   - early stopping on best fine-grained validation F1
# ═══════════════════════════════════════════════════════════════════════════

import os
import math
import time
import json
import shutil
from typing import Dict, Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import AdamW
from tqdm import tqdm   # plain text tqdm — NOT tqdm.auto/notebook (which renders a colored HTML widget in Colab)

import config as cfg
from metrics import MetricTracker


# ───────────────────────────────────────────────────────────────────────────
# Loss functions
# ───────────────────────────────────────────────────────────────────────────
class FocalLoss(nn.Module):
    """Multi-class focal loss with optional class weights."""

    def __init__(self, gamma: float = 2.0,
                 weight: Optional[torch.Tensor] = None,
                 label_smoothing: float = 0.0):
        super().__init__()
        self.gamma = gamma
        self.weight = weight
        self.label_smoothing = label_smoothing

    def forward(self, logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        ce = F.cross_entropy(
            logits, target,
            weight=self.weight,
            reduction="none",
            label_smoothing=self.label_smoothing,
        )
        pt = torch.exp(-ce)
        return ((1.0 - pt) ** self.gamma * ce).mean()


class SoftFocalLoss(nn.Module):
    """Focal loss for SOFT targets (used when MixUp is active).

    Soft targets break standard CE label_smoothing, so MixUp paths route here.
    """

    def __init__(self, gamma: float = 2.0,
                 weight: Optional[torch.Tensor] = None):
        super().__init__()
        self.gamma  = gamma
        self.weight = weight

    def forward(self, logits: torch.Tensor, soft_target: torch.Tensor) -> torch.Tensor:
        log_p = F.log_softmax(logits, dim=-1)
        p     = log_p.exp()
        ce    = -(soft_target * log_p).sum(dim=-1)               # [B]
        pt    = (soft_target * p).sum(dim=-1).clamp(min=1e-8)    # [B]
        loss  = (1.0 - pt) ** self.gamma * ce
        if self.weight is not None:
            # weight per ground-truth class — we approximate via expected weight.
            expected_w = (soft_target * self.weight.unsqueeze(0)).sum(dim=-1)
            loss = loss * expected_w
        return loss.mean()


# ───────────────────────────────────────────────────────────────────────────
# MixUp helpers
# ───────────────────────────────────────────────────────────────────────────
def mixup_data(x: torch.Tensor, cat_y: torch.Tensor, fine_y: torch.Tensor,
               num_categories: int, num_fine: int, alpha: float):
    lam = np.random.beta(alpha, alpha) if alpha > 0 else 1.0
    lam = float(max(lam, 1.0 - lam))            # keep dominant identity
    idx = torch.randperm(x.size(0), device=x.device)

    mixed_x = lam * x + (1.0 - lam) * x[idx]

    cat_a  = F.one_hot(cat_y,  num_classes=num_categories).float()
    fine_a = F.one_hot(fine_y, num_classes=num_fine).float()
    cat_soft  = lam * cat_a  + (1.0 - lam) * cat_a[idx]
    fine_soft = lam * fine_a + (1.0 - lam) * fine_a[idx]
    return mixed_x, cat_soft, fine_soft, lam


# ───────────────────────────────────────────────────────────────────────────
# Warmup-cosine LR
# ───────────────────────────────────────────────────────────────────────────
class WarmupCosineLR:
    def __init__(self, optimizer, warmup_epochs: int, total_epochs: int,
                 base_lr: float, min_lr: float, steps_per_epoch: int):
        self.optimizer       = optimizer
        self.warmup_steps    = max(1, warmup_epochs * steps_per_epoch)
        self.total_steps     = max(self.warmup_steps + 1,
                                   total_epochs * steps_per_epoch)
        self.base_lr         = base_lr
        self.min_lr          = min_lr
        self.step_num        = 0

    def step(self) -> float:
        self.step_num += 1
        if self.step_num <= self.warmup_steps:
            lr = self.base_lr * self.step_num / self.warmup_steps
        else:
            progress = (self.step_num - self.warmup_steps) / max(
                1, self.total_steps - self.warmup_steps)
            progress = min(1.0, progress)
            cos = 0.5 * (1.0 + math.cos(math.pi * progress))
            lr = self.min_lr + (self.base_lr - self.min_lr) * cos
        for pg in self.optimizer.param_groups:
            pg["lr"] = lr
        return lr

    def get_lr(self) -> float:
        return self.optimizer.param_groups[0]["lr"]


# ───────────────────────────────────────────────────────────────────────────
# Trainer
# ───────────────────────────────────────────────────────────────────────────
class Trainer:
    def __init__(self, model, train_loader, val_loader, meta: Dict):
        self.model        = model
        self.train_loader = train_loader
        self.val_loader   = val_loader
        self.meta         = meta
        self.num_fine     = meta["num_fine"]
        self.fine_class_names = meta["fine_class_names"]

        # ── Optimizer with separate LR for backbone vs heads ──
        backbone_params = list(self.model.backbone.parameters())
        head_params     = (list(self.model.category_head.parameters())
                           + list(self.model.fine_head.parameters()))
        self.optimizer = AdamW(
            [
                {"params": backbone_params, "lr": cfg.BASE_LR * 0.5},
                {"params": head_params,     "lr": cfg.BASE_LR},
            ],
            weight_decay=cfg.WEIGHT_DECAY,
        )

        steps_per_epoch = max(1, len(train_loader))
        self.scheduler = WarmupCosineLR(
            self.optimizer,
            warmup_epochs=cfg.WARMUP_EPOCHS,
            total_epochs=cfg.EPOCHS,
            base_lr=cfg.BASE_LR,
            min_lr=cfg.MIN_LR,
            steps_per_epoch=steps_per_epoch,
        )

        # ── Losses ──
        cat_w  = meta["cat_class_weights"].to(cfg.DEVICE)
        fine_w = meta["fine_class_weights"].to(cfg.DEVICE)

        self.cat_ce = nn.CrossEntropyLoss(
            weight=cat_w, label_smoothing=cfg.LABEL_SMOOTHING)
        if cfg.USE_FOCAL_LOSS:
            self.fine_ce = FocalLoss(
                gamma=cfg.FOCAL_GAMMA, weight=fine_w,
                label_smoothing=cfg.LABEL_SMOOTHING)
        else:
            self.fine_ce = nn.CrossEntropyLoss(
                weight=fine_w, label_smoothing=cfg.LABEL_SMOOTHING)

        self.cat_soft  = SoftFocalLoss(gamma=1.0, weight=cat_w)
        self.fine_soft = SoftFocalLoss(gamma=cfg.FOCAL_GAMMA, weight=fine_w)

        self.scaler = torch.amp.GradScaler("cuda", enabled=cfg.USE_AMP
                                           and cfg.DEVICE.type == "cuda")

        # ── State ──
        self.best_val_f1   = -1.0
        self.best_epoch    = -1
        self.epochs_no_imp = 0
        self.history = []

        os.makedirs(cfg.CHECKPOINT_DIR, exist_ok=True)

    # ─────────────────────────────────────────────────────────────────────
    # Training step
    # ─────────────────────────────────────────────────────────────────────
    def _train_one_epoch(self, epoch: int) -> Dict[str, float]:
        self.model.train()
        tracker = MetricTracker(cfg.NUM_CATEGORIES, self.num_fine)

        running_loss = 0.0
        running_n    = 0
        running_correct = 0  # hard-target correct (for live "acc=" display)
        hard_n          = 0

        bar_desc = f"Ep {epoch+1}/{cfg.EPOCHS} TRAIN"
        pbar = tqdm(
            self.train_loader,
            desc=bar_desc,
            leave=False,
            dynamic_ncols=True,
            mininterval=0.3,
        )

        for imgs, cat_y, fine_y in pbar:
            imgs   = imgs.to(cfg.DEVICE,   non_blocking=True)
            cat_y  = cat_y.to(cfg.DEVICE,  non_blocking=True)
            fine_y = fine_y.to(cfg.DEVICE, non_blocking=True)

            use_mixup = (cfg.USE_MIXUP and np.random.rand() < cfg.MIXUP_PROB)

            self.optimizer.zero_grad(set_to_none=True)
            with torch.amp.autocast("cuda", enabled=cfg.USE_AMP
                                    and cfg.DEVICE.type == "cuda"):
                if use_mixup:
                    mx, cat_soft, fine_soft, _lam = mixup_data(
                        imgs, cat_y, fine_y,
                        cfg.NUM_CATEGORIES, self.num_fine, cfg.MIXUP_ALPHA)
                    cat_logits, fine_logits = self.model(mx)
                    loss_cat  = self.cat_soft(cat_logits, cat_soft)
                    loss_fine = self.fine_soft(fine_logits, fine_soft)
                else:
                    cat_logits, fine_logits = self.model(imgs)
                    loss_cat  = self.cat_ce(cat_logits, cat_y)
                    loss_fine = self.fine_ce(fine_logits, fine_y)

                loss = (cfg.CATEGORY_LOSS_WEIGHT * loss_cat
                        + cfg.FINE_LOSS_WEIGHT * loss_fine)

            self.scaler.scale(loss).backward()
            self.scaler.unscale_(self.optimizer)
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), cfg.GRAD_CLIP)
            self.scaler.step(self.optimizer)
            self.scaler.update()
            self.scheduler.step()

            # ── Stats — track against TRUE hard labels for the live bar ──
            bs = imgs.size(0)
            running_loss += loss.item() * bs
            running_n    += bs

            with torch.no_grad():
                fine_pred = fine_logits.argmax(dim=1)
                running_correct += (fine_pred == fine_y).sum().item()
                hard_n          += bs
                # tracker uses argmax preds vs hard labels — fine for both modes
                tracker.update(cat_logits, fine_logits, cat_y, fine_y)

            avg_loss = running_loss / max(1, running_n)
            live_acc = running_correct / max(1, hard_n)
            pbar.set_postfix_str(f"acc={live_acc:.3f}, loss={avg_loss:.3f}")

        pbar.close()
        m = tracker.compute()
        m["loss"] = running_loss / max(1, running_n)
        return m

    # ─────────────────────────────────────────────────────────────────────
    # Validation
    # ─────────────────────────────────────────────────────────────────────
    @torch.no_grad()
    def _validate(self, epoch: int) -> Dict[str, float]:
        self.model.eval()
        tracker = MetricTracker(cfg.NUM_CATEGORIES, self.num_fine)
        running_loss = 0.0
        running_n    = 0

        bar_desc = f"Ep {epoch+1}/{cfg.EPOCHS} VAL  "
        pbar = tqdm(self.val_loader, desc=bar_desc,
                    leave=False, dynamic_ncols=True, mininterval=0.3)

        for imgs, cat_y, fine_y in pbar:
            imgs   = imgs.to(cfg.DEVICE,   non_blocking=True)
            cat_y  = cat_y.to(cfg.DEVICE,  non_blocking=True)
            fine_y = fine_y.to(cfg.DEVICE, non_blocking=True)

            with torch.amp.autocast("cuda", enabled=cfg.USE_AMP
                                    and cfg.DEVICE.type == "cuda"):
                cat_logits, fine_logits = self.model(imgs)
                loss = (cfg.CATEGORY_LOSS_WEIGHT * self.cat_ce(cat_logits, cat_y)
                        + cfg.FINE_LOSS_WEIGHT  * self.fine_ce(fine_logits, fine_y))

            tracker.update(cat_logits, fine_logits, cat_y, fine_y)
            bs = imgs.size(0)
            running_loss += loss.item() * bs
            running_n    += bs

        pbar.close()
        m = tracker.compute()
        m["loss"] = running_loss / max(1, running_n)
        return m

    # ─────────────────────────────────────────────────────────────────────
    # Checkpointing
    # ─────────────────────────────────────────────────────────────────────
    def _build_state(self, epoch: int, val_metrics: Dict[str, float]) -> Dict:
        return {
            "epoch":             epoch,
            "model_state":       self.model.state_dict(),
            "optimizer_state":   self.optimizer.state_dict(),
            "scaler_state":      self.scaler.state_dict(),
            "fine_class_names":  self.fine_class_names,
            "num_fine":          self.num_fine,
            "categories":        cfg.CATEGORIES,
            "img_size":          cfg.IMG_SIZE,
            "backbone":          cfg.BACKBONE,
            "val_metrics":       val_metrics,
            "history":           self.history,
        }

    def _save_per_epoch(self, state: Dict, epoch: int) -> None:
        if not os.path.isdir(cfg.DRIVE_PROJECT_DIR):
            return  # Drive not mounted — silent skip
        os.makedirs(cfg.DRIVE_PER_EPOCH_DIR, exist_ok=True)
        path = os.path.join(cfg.DRIVE_PER_EPOCH_DIR,
                            f"model_epoch{epoch+1:02d}.pt")
        try:
            torch.save(state, path)
        except Exception as e:
            print(f"  [warn] per-epoch save failed: {e}")

    def _save_best(self, state: Dict) -> None:
        local_path = os.path.join(cfg.CHECKPOINT_DIR, "best_model.pt")
        torch.save(state, local_path)

        # Also dump the fine class names alongside for convenience.
        with open(os.path.join(cfg.CHECKPOINT_DIR, "fine_class_names.json"),
                  "w") as f:
            json.dump(self.fine_class_names, f, indent=2)

        if os.path.isdir(cfg.DRIVE_PROJECT_DIR):
            try:
                shutil.copy2(local_path, cfg.DRIVE_BEST_MODEL)
            except Exception as e:
                print(f"  [warn] Drive mirror failed: {e}")

    # ─────────────────────────────────────────────────────────────────────
    # Public entry point
    # ─────────────────────────────────────────────────────────────────────
    def fit(self) -> Dict:
        print("\n" + "═" * 70)
        print(" STARTING TRAINING")
        print("═" * 70)
        print(f" Train batches: {len(self.train_loader)}  |"
              f" Val batches: {len(self.val_loader)}")
        print(f" Total epochs: {cfg.EPOCHS}  |"
              f" Early-stop patience: {cfg.EARLY_STOP_PATIENCE}\n")

        for epoch in range(cfg.EPOCHS):
            t0 = time.time()
            train_m = self._train_one_epoch(epoch)
            val_m   = self._validate(epoch)
            secs    = int(time.time() - t0)

            # Track best on fine-grained validation F1.
            improved = val_m["fine_f1"] > self.best_val_f1
            if improved:
                self.best_val_f1   = val_m["fine_f1"]
                self.best_epoch    = epoch
                self.epochs_no_imp = 0
                state = self._build_state(epoch, val_m)
                self._save_best(state)
                self._save_per_epoch(state, epoch)
                status = "✓ BEST SAVED!"
            else:
                self.epochs_no_imp += 1
                # Still save per-epoch (matches the checkpointing spec).
                state = self._build_state(epoch, val_m)
                self._save_per_epoch(state, epoch)
                status = f"no improvement {self.epochs_no_imp}/{cfg.EARLY_STOP_PATIENCE}"

            lr_now = self.scheduler.get_lr()
            line = (
                f"Epoch {epoch+1:03d} | "
                f"Train acc {train_m['fine_acc']:.3f} | "
                f"Val acc {val_m['fine_acc']:.3f} | "
                f"cat_acc={val_m['cat_acc']:.3f} cat_f1={val_m['cat_f1']:.3f} "
                f"fine_acc={val_m['fine_acc']:.3f} fine_f1={val_m['fine_f1']:.3f} | "
                f"lr={lr_now:.2e} | {secs}s | {status}"
            )
            print(line)

            self.history.append({
                "epoch":     epoch + 1,
                "train":     train_m,
                "val":       val_m,
                "lr":        lr_now,
                "duration":  secs,
                "improved":  improved,
            })

            if self.epochs_no_imp >= cfg.EARLY_STOP_PATIENCE:
                print(f"\n⏹  Early stopping at epoch {epoch+1} "
                      f"(best epoch {self.best_epoch+1}, "
                      f"best fine F1 {self.best_val_f1:.4f})")
                break

        # Persist training history.
        with open(os.path.join(cfg.LOG_DIR, "training_history.json"), "w") as f:
            json.dump(self.history, f, indent=2)

        print("\n" + "═" * 70)
        print(f" TRAINING COMPLETE — best epoch {self.best_epoch+1}, "
              f"fine F1 = {self.best_val_f1:.4f}")
        print("═" * 70)

        return {
            "best_epoch":   self.best_epoch + 1,
            "best_fine_f1": self.best_val_f1,
            "history":      self.history,
        }
