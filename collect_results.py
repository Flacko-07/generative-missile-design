#!/usr/bin/env python3
"""
collect_results.py
Reads generative_dataset.csv, scans cases for DONE markers,
extracts force coefficients, filters outliers, and writes a clean CSV.
"""

import pandas as pd
import numpy as np
import os, sys

# ---------- Configuration ----------
CSV_FILE = "generative_dataset.csv"
OUTPUT_FILE = "clean_dataset.csv"
CASES_DIR = "cases"

# Coefficients bounds – adjust if needed
MAX_CD = 50.0
MAX_CL = 100.0
MAX_CM = 100.0

# ---------- Main ----------
def extract_coeffs(case_dir, case_name):
    """Return (Cd, Cl, Cm) or (None,None,None) if not found/invalid."""
    coeff_file = os.path.join(case_dir, "postProcessing", "forceCoeffs1", "0", "forceCoeffs.dat")
    if not os.path.isfile(coeff_file):
        return None, None, None

    with open(coeff_file) as f:
        lines = f.readlines()
    # last data line
    for line in reversed(lines):
        if line.startswith("#") or not line.strip():
            continue
        cols = line.split()
        if len(cols) < 5:
            continue
        try:
            cm = float(cols[1]) if cols[1] != '-' else None
            cd = float(cols[2])
            cl = float(cols[3])
            return cd, cl, cm
        except (ValueError, IndexError):
            continue
    return None, None, None

def is_physical(cd, cl, cm):
    """Basic sanity check."""
    if cd is None or cl is None:
        return False
    if cd <= 0 or cd > MAX_CD:
        return False
    if abs(cl) > MAX_CL:
        return False
    if cm is not None and abs(cm) > MAX_CM:
        return False
    return True

# Load original CSV
df = pd.read_csv(CSV_FILE)
print(f"Total rows: {len(df)}")

# Scan each row
new_cd = []
new_cl = []
new_cm = []
converged = []
for idx, row in df.iterrows():
    case_name = f"{row['design_id']}_M{row['mach']}_A{row['aoa']}"
    case_dir = os.path.join(CASES_DIR, case_name)
    done_file = os.path.join(case_dir, "DONE")
    if os.path.isfile(done_file):
        cd, cl, cm = extract_coeffs(case_dir, case_name)
        if is_physical(cd, cl, cm):
            new_cd.append(cd)
            new_cl.append(cl)
            new_cm.append(cm)
            converged.append(True)
        else:
            # DONE but bad values → probably diverged
            new_cd.append(None)
            new_cl.append(None)
            new_cm.append(None)
            converged.append(False)
    else:
        # Not finished
        new_cd.append(None)
        new_cl.append(None)
        new_cm.append(None)
        converged.append(False)

df['Cd'] = new_cd
df['Cl'] = new_cl
df['Cm'] = new_cm
df['converged'] = converged

# Write clean version
clean_df = df[df['converged'] == True].copy()
clean_df.drop(columns=['converged'], inplace=True)
clean_df.to_csv(OUTPUT_FILE, index=False)
print(f"Clean dataset saved: {len(clean_df)} rows (removed {len(df)-len(clean_df)} failed/incomplete cases).")