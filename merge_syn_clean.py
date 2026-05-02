import pandas as pd

# Define the columns we actually use for training (from active_learning.py)
design_cols = ['nose_length','body_diameter','body_length',
               'fin_span','fin_chord','fin_thickness','fin_sweep_deg',
               'fin_offset','flare_angle_deg','flare_length']
cond_cols   = ['Cd','Cl','Cm','mach','aoa']

real = pd.read_csv("clean_dataset.csv")
syn  = pd.read_csv("synthetic_dataset.csv")

# Keep only the numeric training features in both datasets
real = real[design_cols + cond_cols]
syn  = syn[design_cols + cond_cols]   # this automatically drops 'uncertainty'

# Concatenate
combined = pd.concat([real, syn], ignore_index=True)
combined.to_csv("combined_dataset.csv", index=False)
print(f"Combined dataset: {len(combined)} rows")