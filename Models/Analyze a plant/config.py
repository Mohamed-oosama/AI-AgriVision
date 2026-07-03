# config.py
# ═══════════════════════════════════════════════════════════════════════════
# Centralized configuration for the Plant Diagnosis v2 system.
# All hyperparameters, paths, and switches live here so the rest of the code
# can stay clean and free of magic numbers.
# ═══════════════════════════════════════════════════════════════════════════

import os
import torch

# ───────────────────────────────────────────────────────────────────────────
# Project paths
# ───────────────────────────────────────────────────────────────────────────
PROJECT_ROOT = "/content/plant_diagnosis_v2"
DATA_ROOT    = "/content/plant_data_v2"

DISEASE_DIR    = os.path.join(DATA_ROOT, "disease")
PEST_DIR       = os.path.join(DATA_ROOT, "pest")
DEFICIENCY_DIR = os.path.join(DATA_ROOT, "deficiency")

CHECKPOINT_DIR    = os.path.join(PROJECT_ROOT, "checkpoints")
LOG_DIR           = os.path.join(PROJECT_ROOT, "logs")
EXPORT_DIR        = os.path.join(PROJECT_ROOT, "exports")
INTERPRET_DIR     = os.path.join(PROJECT_ROOT, "interpretability")

# Google Drive mirroring (for safety against Colab session loss)
DRIVE_PROJECT_DIR    = "/content/drive/MyDrive/plant_diagnosis_v2"
DRIVE_BEST_MODEL     = os.path.join(DRIVE_PROJECT_DIR, "best_model.pt")
DRIVE_PER_EPOCH_DIR  = os.path.join(DRIVE_PROJECT_DIR, "Models_for_each_epoch")

# ───────────────────────────────────────────────────────────────────────────
# Category indexing (fixed order — must never change)
# ───────────────────────────────────────────────────────────────────────────
CATEGORIES     = ["disease", "pest", "deficiency"]
CATEGORY_TO_IDX = {c: i for i, c in enumerate(CATEGORIES)}
NUM_CATEGORIES = len(CATEGORIES)

CATEGORY_DIRS = {
    "disease":    DISEASE_DIR,
    "pest":       PEST_DIR,
    "deficiency": DEFICIENCY_DIR,
}

# ───────────────────────────────────────────────────────────────────────────
# Model / training hyperparameters
# ───────────────────────────────────────────────────────────────────────────
BACKBONE       = "efficientnet_b3"   # timm name
PRETRAINED     = True
DROPOUT        = 0.3

IMG_SIZE       = 300                 # EfficientNet-B3 native input
BATCH_SIZE     = 32                  # Tuned for T4; bump to 64 on A100
NUM_WORKERS    = 4
PIN_MEMORY     = True
PERSISTENT_WORKERS = True

EPOCHS                = 50
EARLY_STOP_PATIENCE   = 7
WARMUP_EPOCHS         = 3
BASE_LR               = 3e-4
MIN_LR                = 1e-6
WEIGHT_DECAY          = 1e-4
GRAD_CLIP             = 1.0

LABEL_SMOOTHING       = 0.05
USE_FOCAL_LOSS        = True         # for fine-grained head
FOCAL_GAMMA           = 2.0
CATEGORY_LOSS_WEIGHT  = 0.4
FINE_LOSS_WEIGHT      = 1.0

USE_MIXUP             = True
MIXUP_ALPHA           = 0.2
MIXUP_PROB            = 0.5          # apply on 50% of batches
USE_WEIGHTED_SAMPLER  = True

VAL_SPLIT             = 0.15
SEED                  = 42

USE_AMP               = True         # mixed precision

# ───────────────────────────────────────────────────────────────────────────
# Confidence-gap warning system
# ───────────────────────────────────────────────────────────────────────────
CONFIDENCE_GAP_THRESHOLD = 0.20  # 20%

# Visually confusable pairs (fine-grained, with category prefix)
CONFUSABLE_PAIRS = [
    ("disease::rice___leaf_blast",          "disease::rice___brown_spot"),
    ("disease::corn_(maize)___common_rust_", "disease::corn_(maize)___northern_leaf_blight"),
    ("disease::grape___black_rot",          "disease::grape___esca_(black_measles)"),
]

# ───────────────────────────────────────────────────────────────────────────
# Inference / Top-K
# ───────────────────────────────────────────────────────────────────────────
TOP_K = 3

# ───────────────────────────────────────────────────────────────────────────
# Device
# ───────────────────────────────────────────────────────────────────────────
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ───────────────────────────────────────────────────────────────────────────
# Normalization stats (ImageNet)
# ───────────────────────────────────────────────────────────────────────────
NORM_MEAN = [0.485, 0.456, 0.406]
NORM_STD  = [0.229, 0.224, 0.225]


def ensure_dirs():
    """Create every directory the project writes to."""
    for d in [PROJECT_ROOT, CHECKPOINT_DIR, LOG_DIR, EXPORT_DIR, INTERPRET_DIR]:
        os.makedirs(d, exist_ok=True)


def print_config():
    print("═" * 70)
    print(" PLANT DIAGNOSIS v2 — CONFIG")
    print("═" * 70)
    print(f"  Device          : {DEVICE}")
    print(f"  Backbone        : {BACKBONE} (pretrained={PRETRAINED})")
    print(f"  Image size      : {IMG_SIZE}")
    print(f"  Batch size      : {BATCH_SIZE}")
    print(f"  Epochs          : {EPOCHS}  (early stop patience={EARLY_STOP_PATIENCE})")
    print(f"  Base LR         : {BASE_LR}  (warmup {WARMUP_EPOCHS} ep, min {MIN_LR})")
    print(f"  AMP             : {USE_AMP}")
    print(f"  MixUp           : {USE_MIXUP} (α={MIXUP_ALPHA}, p={MIXUP_PROB})")
    print(f"  Weighted sampler: {USE_WEIGHTED_SAMPLER}")
    print(f"  Categories      : {CATEGORIES}")
    print("═" * 70)
