#!/usr/bin/env python3
"""
Export the conditional Generator weights from gen.pth into a pure NumPy .npz archive.
The Vercel API uses these weights directly – no torch needed.
"""
import numpy as np
import torch
import torch.nn as nn

NOISE_DIM = 50        # must match the Generator definition
COND_DIM = 5
OUT_DIM = 10

class Generator(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(NOISE_DIM + COND_DIM, 256),
            nn.LeakyReLU(0.2),
            nn.Linear(256, 256),
            nn.LeakyReLU(0.2),
            nn.Linear(256, OUT_DIM)
        )
    def forward(self, noise, cond):
        return self.net(torch.cat([noise, cond], dim=1))

# Load the trained model
device = torch.device("cpu")
gen = Generator()
gen.load_state_dict(torch.load("gen.pth", map_location=device, weights_only=False))
gen.eval()

# Extract weights & biases for each Linear layer
weights = {}
for idx, module in enumerate(gen.net):
    if isinstance(module, nn.Linear):
        w = module.weight.detach().cpu().numpy()
        b = module.bias.detach().cpu().numpy()
        weights[f"layer_{idx}_weight"] = w
        weights[f"layer_{idx}_bias"] = b

# Save to a lightweight archive
np.savez_compressed("gen_weights.npz", **weights)
print(f"Exported gen_weights.npz successfully.")
print(f"File size: {np.round(np.savez_compressed('gen_weights.npz', **{}).__sizeof__() / 1024, 2)} KB")  # quick size check