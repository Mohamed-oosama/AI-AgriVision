# model.py
# ═══════════════════════════════════════════════════════════════════════════
# Dual-head EfficientNet-B3:
#   image → backbone → category_head (3) + fine_head (num_fine)
# One tensor per head, joint training.
# ═══════════════════════════════════════════════════════════════════════════

import torch
import torch.nn as nn
import timm

import config as cfg


class DualHeadPlantModel(nn.Module):
    def __init__(self, num_fine: int,
                 num_categories: int = cfg.NUM_CATEGORIES,
                 backbone_name: str = cfg.BACKBONE,
                 pretrained: bool = cfg.PRETRAINED,
                 dropout: float = cfg.DROPOUT):
        super().__init__()

        # num_classes=0 → return pooled features instead of a classifier.
        self.backbone = timm.create_model(
            backbone_name,
            pretrained=pretrained,
            num_classes=0,
            global_pool="avg",
        )
        feat_dim = self.backbone.num_features  # 1536 for EfficientNet-B3

        # Slightly different capacities on the two heads — fine head needs more.
        self.category_head = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(feat_dim, 256),
            nn.GELU(),
            nn.Dropout(dropout * 0.5),
            nn.Linear(256, num_categories),
        )
        self.fine_head = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(feat_dim, 768),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(768, num_fine),
        )

        self._init_heads()

    def _init_heads(self) -> None:
        for module in [self.category_head, self.fine_head]:
            for m in module.modules():
                if isinstance(m, nn.Linear):
                    nn.init.kaiming_normal_(m.weight, nonlinearity="linear")
                    if m.bias is not None:
                        nn.init.zeros_(m.bias)

    def forward_features(self, x: torch.Tensor) -> torch.Tensor:
        return self.backbone(x)

    def forward(self, x: torch.Tensor):
        feats = self.forward_features(x)
        return self.category_head(feats), self.fine_head(feats)


def build_model(num_fine: int) -> DualHeadPlantModel:
    model = DualHeadPlantModel(num_fine=num_fine).to(cfg.DEVICE)
    n_params  = sum(p.numel() for p in model.parameters())
    n_trainab = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  Backbone     : {cfg.BACKBONE}")
    print(f"  Total params : {n_params/1e6:.2f}M  (trainable {n_trainab/1e6:.2f}M)")
    print(f"  Heads        : category={cfg.NUM_CATEGORIES}, fine={num_fine}")
    return model
