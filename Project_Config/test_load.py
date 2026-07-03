import torch
print("Loading model...")
try:
    state = torch.load("checkpoints/best_model", map_location="cpu", weights_only=False)
    print("Success, keys:", state.keys())
except Exception as e:
    print("Failed directory load:", e)
try:
    state = torch.load("best_model.pt.zip", map_location="cpu", weights_only=False)
    print("Success loading zip, keys:", state.keys())
except Exception as e:
    print("Failed zip load:", e)
