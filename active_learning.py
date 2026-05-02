#!/usr/bin/env python3
"""
active_learning.py (corrected)
- Trains a conditional GAN (WGAN-GP) and a surrogate ensemble.
- Selects target conditions that lie *inside* the training data envelope.
- Identifies where the GAN + surrogate are least accurate / most uncertain.
- Suggests 8 missile designs that are physically plausible.
"""

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from scipy.spatial.distance import mahalanobis
import json, os, sys

# ------------------------------------------------------------
# Config
# ------------------------------------------------------------
NOISE_DIM = 50
BATCH_SIZE = 256
GAN_EPOCHS = 500
SURROGATE_EPOCHS = 300
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Load training data
df = pd.read_csv("combined_dataset.csv")
design_cols = ['nose_length','body_diameter','body_length',
               'fin_span','fin_chord','fin_thickness','fin_sweep_deg',
               'fin_offset','flare_angle_deg','flare_length']
cond_cols   = ['Cd','Cl','Cm','mach','aoa']

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
# Scale the data
# ------------------------------------------------------------
scaler_X = StandardScaler().fit(df[design_cols])
scaler_C = StandardScaler().fit(df[cond_cols])
X = scaler_X.transform(df[design_cols])
C = scaler_C.transform(df[cond_cols])

X_t = torch.tensor(X, dtype=torch.float32).to(DEVICE)
C_t = torch.tensor(C, dtype=torch.float32).to(DEVICE)
dataset = TensorDataset(X_t, C_t)
loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)

# ------------------------------------------------------------
# 1. Surrogate model (Cd,Cl,Cm predictor)
# ------------------------------------------------------------
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

# Ensemble wrapper – MUST be defined before it is used
class SurrogateEnsemble:
    def __init__(self, num_models=5):
        self.models = [Surrogate().to(DEVICE) for _ in range(num_models)]

    def train(self, X, mach, aoa, y, epochs=300):
        for i, model in enumerate(self.models):
            # Bootstrap sample (random with replacement)
            idx = np.random.choice(len(X), size=len(X), replace=True)
            Xb, mb, ab, yb = X[idx], mach[idx], aoa[idx], y[idx]
            ds = TensorDataset(
                torch.tensor(Xb, dtype=torch.float32),
                torch.tensor(mb, dtype=torch.float32),
                torch.tensor(ab, dtype=torch.float32),
                torch.tensor(yb, dtype=torch.float32)
            )
            loader = DataLoader(ds, batch_size=256, shuffle=True)
            opt = optim.Adam(model.parameters(), lr=1e-3)
            mse = nn.MSELoss()
            for epoch in range(epochs):
                for xb, mb, ab, yb in loader:
                    pred = model(xb.to(DEVICE), mb.to(DEVICE), ab.to(DEVICE))
                    loss = mse(pred, yb.to(DEVICE))
                    opt.zero_grad(); loss.backward(); opt.step()
            print(f"  Ensemble model {i+1}/{len(self.models)} trained.")

    def predict(self, design, mach, aoa):
        preds = []
        with torch.no_grad():
            for model in self.models:
                preds.append(model(design, mach, aoa).cpu().numpy())
        preds = np.array(preds)   # (num_models, batch, 3)
        mean = preds.mean(axis=0)
        std  = preds.std(axis=0)
        return mean, std

# ------------------------------------------------------------
# Train surrogate ensemble (for error/uncertainty scoring)
# ------------------------------------------------------------
print("Training surrogate ensemble...")
surrogate_ensemble = SurrogateEnsemble(num_models=5)
surrogate_ensemble.train(X, df['mach'].values, df['aoa'].values,
                         df[['Cd','Cl','Cm']].values, epochs=SURROGATE_EPOCHS)

# ------------------------------------------------------------
# Train a SINGLE surrogate for differentiable inverse design
# ------------------------------------------------------------
print("Training single surrogate for inverse design...")
single_surrogate = Surrogate().to(DEVICE)
opt_surr = optim.Adam(single_surrogate.parameters(), lr=1e-3)
mse = nn.MSELoss()
surr_dataset = TensorDataset(X_t, 
                             torch.tensor(df['mach'].values, dtype=torch.float32).to(DEVICE),
                             torch.tensor(df['aoa'].values, dtype=torch.float32).to(DEVICE),
                             torch.tensor(df[['Cd','Cl','Cm']].values, dtype=torch.float32).to(DEVICE))
surr_loader = DataLoader(surr_dataset, batch_size=256, shuffle=True)

for epoch in range(SURROGATE_EPOCHS):
    for xb, mb, ab, yb in surr_loader:
        pred = single_surrogate(xb, mb, ab)
        loss = mse(pred, yb)
        opt_surr.zero_grad(); loss.backward(); opt_surr.step()
    if epoch % 50 == 0:
        print(f"Single surrogate epoch {epoch} loss {loss.item():.4f}")

# ------------------------------------------------------------
# 2. Conditional GAN (WGAN-GP)
# ------------------------------------------------------------
class Generator(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(NOISE_DIM+5, 256), nn.LeakyReLU(0.2),
            nn.Linear(256, 256), nn.LeakyReLU(0.2),
            nn.Linear(256, len(design_cols))
        )
    def forward(self, noise, cond):
        return self.net(torch.cat([noise, cond], dim=1))

class Discriminator(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(len(design_cols)+5, 256), nn.LeakyReLU(0.2),
            nn.Linear(256, 256), nn.LeakyReLU(0.2),
            nn.Linear(256, 1)
        )
    def forward(self, design, cond):
        return self.net(torch.cat([design, cond], dim=1))

gen = Generator().to(DEVICE)
disc = Discriminator().to(DEVICE)
opt_gen = optim.Adam(gen.parameters(), lr=1e-4, betas=(0.5, 0.9))
opt_disc = optim.Adam(disc.parameters(), lr=1e-4, betas=(0.5, 0.9))

def gradient_penalty(disc, real, fake, cond):
    batch_size = real.size(0)
    eps = torch.rand(batch_size, 1, device=DEVICE).expand_as(real)
    interpolated = eps * real + (1 - eps) * fake
    interpolated.requires_grad_(True)
    d_int = disc(interpolated, cond)
    gradients = torch.autograd.grad(
        outputs=d_int, inputs=interpolated,
        grad_outputs=torch.ones_like(d_int),
        create_graph=True, retain_graph=True
    )[0]
    gradients = gradients.view(batch_size, -1)
    norm = gradients.norm(2, dim=1)
    return ((norm - 1) ** 2).mean()

print("Training GAN...")
for epoch in range(GAN_EPOCHS):
    for real_x, real_c in loader:
        real_x, real_c = real_x.to(DEVICE), real_c.to(DEVICE)
        # Discriminator updates
        for _ in range(5):
            noise = torch.randn(real_x.size(0), NOISE_DIM, device=DEVICE)
            fake_x = gen(noise, real_c)
            d_loss = disc(fake_x.detach(), real_c).mean() - disc(real_x, real_c).mean() \
                     + 10 * gradient_penalty(disc, real_x, fake_x.detach(), real_c)
            opt_disc.zero_grad(); d_loss.backward(); opt_disc.step()
        # Generator update
        noise = torch.randn(real_x.size(0), NOISE_DIM, device=DEVICE)
        fake_x = gen(noise, real_c)
        g_loss = -disc(fake_x, real_c).mean()
        opt_gen.zero_grad(); g_loss.backward(); opt_gen.step()
    if epoch % 50 == 0:
        print(f"GAN epoch {epoch} D {d_loss.item():.4f} G {g_loss.item():.4f}")

# Save models
torch.save(gen.state_dict(), "gen.pth")
torch.save(disc.state_dict(), "disc.pth")
torch.save(surrogate_ensemble, "surrogate_ensemble.pth")   # saves whole ensemble
torch.save(single_surrogate.state_dict(), "single_surrogate.pth")

# ------------------------------------------------------------
# 3. Define the target grid WITHIN training data envelope
# ------------------------------------------------------------
cd_min, cd_max = df['Cd'].min(), df['Cd'].max()
cl_min, cl_max = df['Cl'].min(), df['Cl'].max()
cm_min, cm_max = df['Cm'].min(), df['Cm'].max()
mach_vals = np.sort(df['mach'].unique())
aoa_vals  = np.sort(df['aoa'].unique())

targets = []
for cd in np.linspace(cd_min, cd_max, 4):
    for cl in np.linspace(cl_min, cl_max, 4):
        for cm in np.linspace(cm_min, cm_max, 4):
            for mach in mach_vals:
                for aoa in aoa_vals:
                    targets.append([cd, cl, cm, mach, aoa])

targets_arr = np.array(targets)
all_conds = df[cond_cols].values
cov = np.cov(all_conds, rowvar=False)
inv_cov = np.linalg.inv(cov)
mean = np.mean(all_conds, axis=0)
filtered_targets = []
for t in targets_arr:
    md = mahalanobis(t, mean, inv_cov)
    if md < np.percentile([mahalanobis(c, mean, inv_cov) for c in all_conds], 95):
        filtered_targets.append(t)
filtered_targets = np.array(filtered_targets)
print(f"Targets after filtering: {len(filtered_targets)}")

# ------------------------------------------------------------
# 4. Identify high‑error + high‑uncertainty regions
# ------------------------------------------------------------
gen.eval()
scores = []
with torch.no_grad():
    for t in filtered_targets:
        cond_tensor = torch.tensor(t, dtype=torch.float32).unsqueeze(0).to(DEVICE)
        noise = torch.randn(1, NOISE_DIM).to(DEVICE)
        design_norm = gen(noise, cond_tensor)
        mach_t = torch.tensor([t[3]], dtype=torch.float32).to(DEVICE)
        aoa_t  = torch.tensor([t[4]], dtype=torch.float32).to(DEVICE)
        # Use the ensemble for prediction (returns numpy)
        pred_mean, pred_std = surrogate_ensemble.predict(design_norm, mach_t, aoa_t)
        err = np.abs(pred_mean - t[:3]).mean()
        uncertainty = pred_std.mean()
        score = err + 0.5 * uncertainty          # combined score
        scores.append(score)

# Select the 100 points with largest score
top_idx = np.argsort(scores)[-100:]
high_err_targets = filtered_targets[top_idx]

# Cluster into 8 representative conditions
kmeans = KMeans(n_clusters=8, random_state=42).fit(high_err_targets)
centroids = kmeans.cluster_centers_
print("Centroids (inside training envelope):")
print(centroids)

# ------------------------------------------------------------
# 5. Inverse design with bounds (FEASIBILITY‑AWARE)
# ------------------------------------------------------------
def enforce_feasibility(design):
    """
    Ensure the design vector is physically consistent.
    returns the corrected design (same shape or clipped).
    """
    # Unpack (order MUST match design_cols)
    nose_len, body_diam, body_len, fin_span, fin_chord, fin_thick, sweep_deg, offset, flare_deg, flare_len = design

    # If fin_span > 0, fin_chord and fin_thick must be positive
    if fin_span > 0:
        if fin_chord <= 0:
            fin_chord = 0.05  # minimum chord
        if fin_thick <= 0:
            fin_thick = 0.005  # minimum thickness
    else:
        # No fins at all → force chord/thickness to zero
        fin_chord = 0.0
        fin_thick = 0.0
        sweep_deg = 0.0
        offset = 0.0

    # If flare_angle > 0, flare_length must be positive
    if flare_deg > 0:
        if flare_len <= 0:
            flare_len = 0.01  # minimum flare length
    else:
        flare_len = 0.0

    # Ensure positive basic dimensions
    nose_len = max(nose_len, 0.1)
    body_diam = max(body_diam, 0.05)
    body_len = max(body_len, 0.1)

    return np.array([nose_len, body_diam, body_len, fin_span, fin_chord, fin_thick, sweep_deg, offset, flare_deg, flare_len])

def inverse_design(target, surrogate_model, scaler_X, bounds_dict, design_cols, n_iter=2000):
    target_tensor = torch.tensor(target, dtype=torch.float32).to(DEVICE)
    design = torch.nn.Parameter(torch.randn(1, len(design_cols)).to(DEVICE) * 0.5)
    optimiser = optim.Adam([design], lr=1e-2)
    for _ in range(n_iter):
        mach_t = target_tensor[3].unsqueeze(0)
        aoa_t  = target_tensor[4].unsqueeze(0)
        pred = surrogate_model(design, mach_t, aoa_t)
        loss = nn.MSELoss()(pred, target_tensor[:3].unsqueeze(0))
        optimiser.zero_grad()
        loss.backward()
        optimiser.step()
    # Convert and clamp to physical bounds
    design_np = design.detach().cpu().numpy()
    design_phys = scaler_X.inverse_transform(design_np)[0]
    for i, col in enumerate(design_cols):
        low, high = bounds_dict[col]
        design_phys[i] = np.clip(design_phys[i], low, high)

    # Enforce physical consistency
    design_phys = enforce_feasibility(design_phys)

    return design_phys

selected_designs = []
for centroid in centroids:
    params = inverse_design(centroid, single_surrogate, scaler_X, param_bounds, design_cols)
    selected_designs.append(params.tolist())

# ------------------------------------------------------------
# 6. Save proposals
# ------------------------------------------------------------
output = {
    "targets": centroids.tolist(),
    "designs": selected_designs
}
with open("next_designs.json", "w") as f:
    json.dump(output, f, indent=2)
print("8 plausible missile designs saved to next_designs.json")