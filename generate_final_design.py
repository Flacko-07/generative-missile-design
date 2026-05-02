#!/usr/bin/env python3
"""
Given target [Cd, Cl, Cm, Mach, AoA], outputs a physically valid missile design.
"""

import torch
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
import json, sys, math

# ---------- Model definitions (same as active_learning.py) ----------
import torch.nn as nn

NOISE_DIM = 50
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class Generator(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(NOISE_DIM+5, 256), nn.LeakyReLU(0.2),
            nn.Linear(256, 256), nn.LeakyReLU(0.2),
            nn.Linear(256, 10)
        )
    def forward(self, noise, cond):
        return self.net(torch.cat([noise, cond], dim=1))

# ---------- Load scalers ----------
df = pd.read_csv("combined_dataset.csv")
design_cols = ['nose_length','body_diameter','body_length',
               'fin_span','fin_chord','fin_thickness','fin_sweep_deg',
               'fin_offset','flare_angle_deg','flare_length']
cond_cols   = ['Cd','Cl','Cm','mach','aoa']

scaler_X = StandardScaler().fit(df[design_cols])
scaler_C = StandardScaler().fit(df[cond_cols])

# ---------- Load generator ----------
gen = Generator().to(DEVICE)
gen.load_state_dict(torch.load("gen.pth", map_location=DEVICE, weights_only=False))
gen.eval()

# ---------- Feasibility enforcement ----------
def enforce_feasibility(design):
    nose_len, body_diam, body_len, fin_span, fin_chord, fin_thick, sweep_deg, offset, flare_deg, flare_len = design
    if fin_span > 0:
        if fin_chord <= 0:
            fin_chord = 0.05
        if fin_thick <= 0:
            fin_thick = 0.005
    else:
        fin_chord = 0.0
        fin_thick = 0.0
        sweep_deg = 0.0
        offset = 0.0
    if flare_deg > 0:
        if flare_len <= 0:
            flare_len = 0.01
    else:
        flare_len = 0.0
    nose_len = max(nose_len, 0.1)
    body_diam = max(body_diam, 0.05)
    body_len = max(body_len, 0.1)
    return np.array([nose_len, body_diam, body_len, fin_span, fin_chord, fin_thick, sweep_deg, offset, flare_deg, flare_len])

# ---------- Generate design ----------
def generate(target_cd, target_cl, target_cm, target_mach, target_aoa):
    target = np.array([target_cd, target_cl, target_cm, target_mach, target_aoa])
    cond_norm = scaler_C.transform([target])
    noise = torch.randn(1, NOISE_DIM).to(DEVICE)
    with torch.no_grad():
        design_norm = gen(noise, torch.tensor(cond_norm, dtype=torch.float32).to(DEVICE))
    design_phys = scaler_X.inverse_transform(design_norm.cpu().numpy())[0]
    # Clamp to bounds (optional but safe)
    param_bounds = {
        'nose_length': (0.2, 2.5), 'body_diameter': (0.15, 0.6), 'body_length': (0.8, 7.0),
        'fin_span': (0.0, 1.2), 'fin_chord': (0.0, 0.8), 'fin_thickness': (0.0, 0.08),
        'fin_sweep_deg': (-45, 45), 'fin_offset': (-0.2, 0.5), 'flare_angle_deg': (0.0, 15), 'flare_length': (0.0, 0.5)
    }
    for i, col in enumerate(design_cols):
        low, high = param_bounds[col]
        design_phys[i] = np.clip(design_phys[i], low, high)
    design_phys = enforce_feasibility(design_phys)
    design_dict = dict(zip(design_cols, design_phys.tolist()))
    return design_dict

if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("Usage: python3 generate_final_design.py <Cd> <Cl> <Cm> <Mach> <AoA>")
        sys.exit(1)
    cd, cl, cm, mach, aoa = map(float, sys.argv[1:])
    result = generate(cd, cl, cm, mach, aoa)
    print(json.dumps(result, indent=2))