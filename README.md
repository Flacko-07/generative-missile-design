# Generative Missile Design

This repository implements a conditional generative model that maps target aerodynamic coefficients and flight condition parameters to physically plausible missile geometries.

## Overview

The core idea is to learn an inverse design mapping from target \( C_d, C_l, C_m \) along with Mach number and angle of attack to a 10-parameter missile shape description. The generator is trained on a combined dataset of simulated or precomputed missile designs and their aerodynamic coefficients.

Key components:
- `generate_final_design.py`: Loads a trained conditional generator and standardization scalers, then produces a feasible missile geometry for a given target condition.
- `active_learning.py`: Routines for active learning or iterative data generation and model refinement.
- `synthetic_dataset.py`: Tools for generating or augmenting datasets of missile designs.
- `parametric_sweep.py`: Scripts to explore parametric spaces of designs and conditions.
- `geometry.py`: Utilities for parameterizing missile geometries.
- `collect_results.py`, `merge_syn_clean.py`: Helpers for dataset preparation and aggregation.

The design vector includes:
- Nose length
- Body diameter
- Body length
- Fin span
- Fin chord
- Fin thickness
- Fin sweep (degrees)
- Fin longitudinal offset
- Flare angle (degrees)
- Flare length

The conditioning vector includes:
- Drag coefficient \( C_d \)
- Lift coefficient \( C_l \)
- Pitching moment coefficient \( C_m \)
- Mach number
- Angle of attack (degrees)

## Inverse design usage

The main entry point for inverse design is `generate_final_design.py`. It expects a trained generator checkpoint (`gen.pth`) and a combined dataset file (`combined_dataset.csv`) in the repository root.

### Command-line

```bash
python3 generate_final_design.py <Cd> <Cl> <Cm> <Mach> <AoA>
```

Example:

```bash
python3 generate_final_design.py 0.1 0.0 0.0 0.8 5.0
```

This prints a JSON dictionary with the 10 geometric parameters corresponding to a feasible missile design for the requested aerodynamic targets.

### Feasibility constraints

The generator output is post-processed to enforce simple physical constraints, including:
- Non-negative or bounded lengths and diameters
- Optional fins and flare (zeroed parameters when not present)
- Clamping of each parameter to predefined min/max bounds

This ensures that even if the raw generator output is slightly out-of-distribution, the final design remains physically reasonable.

## Repository structure

- `active_learning.py` – training and active learning routines for the conditional generator.
- `generate_final_design.py` – inference script for inverse design given target aero coefficients and conditions.
- `synthetic_dataset.py` – generation of synthetic missile datasets.
- `parametric_sweep.py` – exploration of parametric design/condition grids.
- `geometry.py` – geometry parameterization and related utilities.
- `collect_results.py` – scripts for aggregating and post-processing simulation/model outputs.
- `merge_syn_clean.py` – utilities for merging synthetic and cleaned datasets.
- `clean_dataset.csv` – example or base dataset of missile geometries and aerodynamic coefficients.
- `gan_dataset/` – additional data used for GAN training.

## Requirements

The code is written in Python and depends on standard scientific and ML libraries such as:
- `torch`
- `numpy`
- `pandas`
- `scikit-learn`

You can create a minimal environment using:

```bash
pip install torch numpy pandas scikit-learn
```

The file `requirements-gan.txt` can be extended with additional dependencies as needed for training scripts.

## Planned UI and deployment

The project is designed to support a simple web UI for specifying target \( C_d, C_l, C_m \), Mach, and AoA, invoking the inverse design model, and displaying the resulting geometric parameters. A typical deployment stack is:
- Backend API endpoint wrapping `generate_final_design.generate(...)`.
- Frontend (e.g., Next.js/React) hosted on Vercel for interactive usage.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
