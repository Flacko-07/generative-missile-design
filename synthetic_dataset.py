#!/usr/bin/env python3
"""
generate_synthetic_dataset.py
=============================
Uses the trained surrogate ensemble and generator to create a high-confidence
synthetic dataset of (geometry, coefficients) pairs.

Only designs where the ensemble uncertainty is LOW are retained.
This dataset can be used to pre-train a stronger conditional GAN.
"""

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.preprocessing import StandardScaler
from scipy.spatial.distance import mahalanobis
import json, os, sys

# ------------------------------------------------------------
# Config
# ------------------------------------------------------------
NOISE_DIM = 50
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Load training data (for scalers and envelope)
df = pd.read_csv("clean_dataset.csv")
design_cols = ['nose_length','body_diameter','body_length',
               'fin_span','fin_chord','fin_thickness','fin_sweep_deg',
               'fin_offset','flare_angle_deg','flare_length']
cond_cols   = ['Cd','Cl','Cm','mach','aoa']

# Scalers (must match those used in active_learning.py)
scaler_X = StandardScaler().fit(df[design_cols])
scaler_C = StandardScaler().fit(df[cond_cols])

# Physical bounds for each design parameter (min, max)
param_bounds = {
    'nose_length':    (0.2, 2.5),
    'body_diameter':  (0.15, 0.6),
    'body_length':    (0.8, 7.0),
    'fin_span':       (0.0, 1.2),
    'fin_chord':      (0.0, 0.8),
    'fin_thickness':  (0.0, 0.08),
    'fin_sweep_deg':  (-45, 45),
    'fin_offset':     (-0.2, 0.5),
    'flare_angle_deg':(0.0, 15),
    'flare_length':   (0.0, 0.5)
}

# ------------------------------------------------------------
# 1. Load trained models
# ------------------------------------------------------------
# Need to define the classes exactly as in active_learning.py
class Surrogate(nn.Module):
    def __init__(self, in_dim=10+2, out_dim=3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, 128), nn.ReLU(),
            nn.Linear(128, 128), nn.ReLU(),
            nn.Linear(128, out_dim)
        )
    def forward(self, design, mach, aoa):
        return self.net(torch.cat([design, mach.unsqueeze(-1), aoa.unsqueeze(-1)], dim=1))

class SurrogateEnsemble:
    def __init__(self, models):
        self.models = models
    def predict(self, design, mach, aoa):
        preds = []
        with torch.no_grad():
            for model in self.models:
                preds.append(model(design, mach, aoa).cpu().numpy())
        preds = np.array(preds)
        return preds.mean(axis=0), preds.std(axis=0)

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

# Load ensemble (saved with torch.save(surrogate_ensemble, ...))
ensemble_data = torch.load("surrogate_ensemble.pth", map_location=DEVICE, weights_only=False)
# The ensemble object was saved with its models attribute
ensemble = SurrogateEnsemble(ensemble_data.models) if hasattr(ensemble_data, 'models') else ensemble_data

# Load single surrogate for possible inverse design (optional)
single_surrogate = Surrogate().to(DEVICE)
single_surrogate.load_state_dict(torch.load("single_surrogate.pth", map_location=DEVICE, weights_only=False))
# Load generator
gen = Generator().to(DEVICE)
gen.load_state_dict(torch.load("gen.pth", map_location=DEVICE, weights_only=False))
gen.eval()

# ------------------------------------------------------------
# 2. Feasibility enforcement (same as active_learning.py)
# ------------------------------------------------------------
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

# ------------------------------------------------------------
# 3. Generate target conditions within training envelope
# ------------------------------------------------------------
# We want to cover the full range of (Cd, Cl, Cm, Mach, AoA) but stay within the convex hull of the training data.
# Use the same filtering as before: Mahalanobis distance <= 95th percentile.

all_conds = df[cond_cols].values
cov = np.cov(all_conds, rowvar=False)
inv_cov = np.linalg.inv(cov)
mean = np.mean(all_conds, axis=0)

cd_min, cd_max = df['Cd'].min(), df['Cd'].max()
cl_min, cl_max = df['Cl'].min(), df['Cl'].max()
cm_min, cm_max = df['Cm'].min(), df['Cm'].max()
mach_vals = np.sort(df['mach'].unique())
aoa_vals  = np.sort(df['aoa'].unique())

# Generate a large grid of targets
targets = []
for cd in np.linspace(cd_min, cd_max, 8):         # coarse grid, will get many points
    for cl in np.linspace(cl_min, cl_max, 8):
        for cm in np.linspace(cm_min, cm_max, 8):
            for mach in mach_vals:
                for aoa in aoa_vals:
                    targets.append([cd, cl, cm, mach, aoa])
targets_arr = np.array(targets)

# Filter using Mahalanobis distance (keep 95% of the training distribution)
filtered_targets = []
for t in targets_arr:
    md = mahalanobis(t, mean, inv_cov)
    if md < np.percentile([mahalanobis(c, mean, inv_cov) for c in all_conds], 95):
        filtered_targets.append(t)
filtered_targets = np.array(filtered_targets)
print(f"Target candidates after envelope filtering: {len(filtered_targets)}")

# ------------------------------------------------------------
# 4. Generate synthetic data, filter by uncertainty
# ------------------------------------------------------------
synthetic_rows = []
uncertainties = []
count = 0
max_samples = 5000  # we'll aim for 5000 high-confidence points

with torch.no_grad():
    for t in filtered_targets:
        if count >= max_samples:
            break
        cond_tensor = torch.tensor(t, dtype=torch.float32).unsqueeze(0).to(DEVICE)
        # Generate a design (multiple times for diversity?)
        noise = torch.randn(1, NOISE_DIM).to(DEVICE)
        design_norm = gen(noise, cond_tensor)
        # Predict with ensemble
        mach_t = torch.tensor([t[3]], dtype=torch.float32).to(DEVICE)
        aoa_t  = torch.tensor([t[4]], dtype=torch.float32).to(DEVICE)
        pred_mean, pred_std = ensemble.predict(design_norm, mach_t, aoa_t)

        # Average std across Cd, Cl, Cm
        avg_uncertainty = pred_std.mean()

        # Only keep designs with low uncertainty (e.g., < 10% of the training coefficient range)
        # You can adjust the threshold.
        if avg_uncertainty > 0.2 * (df['Cd'].max() - df['Cd'].min()):  # roughly 5% of Cd range
            continue

        # Convert design to physical and clamp
        design_phys = scaler_X.inverse_transform(design_norm.cpu().numpy())[0]
        for i, col in enumerate(design_cols):
            low, high = param_bounds[col]
            design_phys[i] = np.clip(design_phys[i], low, high)
        design_phys = enforce_feasibility(design_phys)

        # Check that predicted coefficients are physical
        cd_pred = pred_mean[0,0]
        cl_pred = pred_mean[0,1]
        cm_pred = pred_mean[0,2]
        if cd_pred <= 0 or abs(cl_pred) > 100 or abs(cm_pred) > 100:
            continue

        # Store row
        row = {
            "nose_length": design_phys[0],
            "body_diameter": design_phys[1],
            "body_length": design_phys[2],
            "fin_span": design_phys[3],
            "fin_chord": design_phys[4],
            "fin_thickness": design_phys[5],
            "fin_sweep_deg": design_phys[6],
            "fin_offset": design_phys[7],
            "flare_angle_deg": design_phys[8],
            "flare_length": design_phys[9],
            "Cd": cd_pred,
            "Cl": cl_pred,
            "Cm": cm_pred,
            "mach": t[3],
            "aoa": t[4],
            "uncertainty": avg_uncertainty
        }
        synthetic_rows.append(row)
        count += 1

print(f"Collected {len(synthetic_rows)} high-confidence synthetic points.")

# Save to CSV
syn_df = pd.DataFrame(synthetic_rows)
# Reorder columns to match clean_dataset.csv (plus uncertainty)
cols_order = design_cols + ['Cd','Cl','Cm','mach','aoa','uncertainty']
syn_df = syn_df[cols_order]
syn_df.to_csv("synthetic_dataset.csv", index=False)
print("Synthetic dataset saved to synthetic_dataset.csv")