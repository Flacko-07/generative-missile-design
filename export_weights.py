#!/usr/bin/env python3
"""
Run this ONCE locally to export gen.pth weights to gen_weights.npz.
The .npz file is used by the Vercel API (numpy-only, no torch needed at runtime).

    python3 export_weights.py

Outputs: gen_weights.npz  (~1-2 MB)
"""
import torch
import torch.nn as nn
import numpy as np

NOISE_DIM = 50

class Generator(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(NOISE_DIM+5, 256), nn.LeakyReLU(0.2),
            nn.Linear(256, 256),         nn.LeakyReLU(0.2),
            nn.Linear(256, 10)
        )
    def forward(self, noise, cond):
        return self.net(torch.cat([noise, cond], dim=1))

gen = Generator()
gen.load_state_dict(torch.load('gen.pth', map_location='cpu', weights_only=False))
gen.eval()

# Extract linear layer weights: net[0], net[2], net[4]
linear_layers = [m for m in gen.net if isinstance(m, nn.Linear)]
np.savez('gen_weights.npz',
    W0=linear_layers[0].weight.detach().numpy(),
    b0=linear_layers[0].bias.detach().numpy(),
    W1=linear_layers[1].weight.detach().numpy(),
    b1=linear_layers[1].bias.detach().numpy(),
    W2=linear_layers[2].weight.detach().numpy(),
    b2=linear_layers[2].bias.detach().numpy(),
)
print('Exported gen_weights.npz successfully.')
import os
size_kb = os.path.getsize('gen_weights.npz') / 1024
print(f'File size: {size_kb:.1f} KB')
