#!/usr/bin/env python3
"""
Export Generator weights from gen.pth → gen_weights.npz
with keys that match api/design.py: W0, b0, W1, b1, W2, b2.
"""
import numpy as np
import torch
import torch.nn as nn

NOISE_DIM = 50
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

gen = Generator()
gen.load_state_dict(torch.load("gen.pth", map_location="cpu", weights_only=False))
gen.eval()

# Extract only Linear layers – they are at indices 0, 2, 4
linear_layers = [m for m in gen.net if isinstance(m, nn.Linear)]
weights = {}
for i, layer in enumerate(linear_layers):
    weights[f"W{i}"] = layer.weight.detach().cpu().numpy()
    weights[f"b{i}"] = layer.bias.detach().cpu().numpy()

np.savez_compressed("gen_weights.npz", **weights)
print("Exported gen_weights.npz with keys:", list(weights.keys()))