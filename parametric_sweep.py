#!/usr/bin/env python3
"""
parametric_sweep.py  –  known‑good builder for the generative missile dataset.
"""

import os, sys, math, random, subprocess, csv, argparse, itertools, shutil, re, struct
from pathlib import Path
import numpy as np
from geometry import Missile

# ── Simulation control ──────────────────────────────────────────────────────────
END_TIME                   = 30
DELTA_T_INIT               = 1e-6
MAX_CO                     = 0.1        # safe CFL for any geometry
FIELD_WRITE_INTERVAL       = 500
FORCE_COEFF_START_TIME     = 0
FORCE_COEFF_WRITE_INTERVAL = 1

# ═══════════════════════════════════════════════════════════════════════════════
# I/O helpers
# ═══════════════════════════════════════════════════════════════════════════════

def write_foam_header(f, class_name, object_name):
    f.write(f"""\
/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  13                                    |
|   \\\\  /    A nd           | Web:      www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       {class_name};
    object      {object_name};
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

""")

def _write_dict(f, d, indent=0):
    prefix = "    " * indent
    for key, value in d.items():
        if isinstance(value, dict):
            f.write(f"{prefix}{key}\n{prefix}{{\n")
            _write_dict(f, value, indent + 1)
            f.write(f"{prefix}}}\n")
        elif isinstance(value, list):
            f.write(f"{prefix}{key} ({' '.join(map(str, value))});\n")
        else:
            f.write(f"{prefix}{key} {value};\n")

def write_foam_dict(filepath, d):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    object_name = os.path.basename(filepath)
    with open(filepath, "w") as f:
        write_foam_header(f, "dictionary", object_name)
        _write_dict(f, d)
    return filepath

def write_foam_field(case_dir, field_name, class_name, dimensions,
                     internal_field, boundary_field):
    filepath = os.path.join(case_dir, "0", field_name)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        write_foam_header(f, class_name, field_name)
        f.write(f"dimensions      {dimensions};\n")
        f.write(f"internalField   {internal_field};\n\n")
        f.write("boundaryField\n{\n")
        for patch, bc in boundary_field.items():
            f.write(f"    {patch}\n    {{\n")
            for k, v in bc.items():
                f.write(f"        {k} {v};\n")
            f.write("    }\n")
        f.write("}\n")
        f.write("// ************************************************************************* //\n")

# ═══════════════════════════════════════════════════════════════════════════════
# STL helper – ensure ASCII solid name matches the patch name snappy expects
# ═══════════════════════════════════════════════════════════════════════════════

def _is_binary_stl(path: Path) -> bool:
    """True when the file is almost certainly a binary STL.

    The naive check ``header.startswith(b"solid")`` is unreliable: many
    exporters (FreeCAD, GMSH, OpenCASCADE …) write a 80-byte ASCII header that
    begins with the word "solid" even for binary files.  A far more reliable
    heuristic is the file-size identity:

        binary STL size = 80 (header) + 4 (uint32 triangle count) + N * 50

    If the actual size matches this formula the file is binary; if it doesn't,
    it is ASCII.  We allow ±4 bytes of slack for the occasional byte-aligned
    exporter.
    """
    file_size = path.stat().st_size
    if file_size < 84:
        # Too small to be a valid binary STL; treat as ASCII.
        return False
    with path.open("rb") as fh:
        fh.read(80)          # skip 80-byte header
        n_raw = fh.read(4)   # triangle count (little-endian uint32)
    if len(n_raw) < 4:
        return False
    n_tri = int.from_bytes(n_raw, "little")
    expected_size = 84 + n_tri * 50
    return abs(file_size - expected_size) <= 4


def get_stl_bounds(stl_path):
    """Return (xmin, xmax) of all vertices in the STL, or None on failure.

    This is the key fix for the zero-sized-patch problem: the blockMesh domain
    and locationInMesh must be computed from the *actual* nose position in the
    STL, not from the assumption that the nose is always at x = 0.

    Works for both ASCII and binary STL without any OpenFOAM dependency.
    """
    path = Path(stl_path)
    if not path.is_file():
        return None
    try:
        if _is_binary_stl(path):
            with path.open("rb") as fh:
                fh.read(80)
                n_tri = int.from_bytes(fh.read(4), "little")
                data = fh.read(n_tri * 50)

            xvals = []
            for i in range(n_tri):
                tri = data[i * 50: i * 50 + 50]
                if len(tri) < 50:
                    break
                # layout per triangle: 12 B normal | 12 B v0 | 12 B v1 | 12 B v2 | 2 B attr
                for v in range(3):
                    x = struct.unpack_from("<f", tri, 12 + v * 12)[0]
                    xvals.append(x)
        else:
            text = path.read_text(encoding="utf-8", errors="replace")
            # "vertex  x  y  z"
            matches = re.findall(
                r"vertex\s+([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)"
                r"\s+([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)"
                r"\s+([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)",
                text,
            )
            if not matches:
                return None
            xvals = [float(m[0]) for m in matches]

        if not xvals:
            return None
        return float(min(xvals)), float(max(xvals))
    except Exception:
        return None
def copy_stl_for_case(src_stl: str, dst_stl: str, patch_name: str = "missile_wall") -> None:
    """
    Copy STL into the case constant/triSurface directory.
    If the STL is ASCII we force the solid/endsolid name to *patch_name* so
    snappyHexMesh creates a patch with exactly that name.  Binary STLs are
    copied unchanged (snappyHexMesh names the patch from the geometry-dict key,
    which is already set to missile_wall in snappyHexMeshDict).
    """
    src = Path(src_stl)
    dst = Path(dst_stl)
    dst.parent.mkdir(parents=True, exist_ok=True)

    if _is_binary_stl(src):
        shutil.copy(str(src), str(dst))
        return

    # ASCII STL — rewrite solid/endsolid name so snappyHexMesh sees patch_name.
    try:
        text = src.read_text(encoding="utf-8", errors="replace")
    except Exception:
        # Fallback: just copy as-is and let OpenFOAM complain with a clear log.
        shutil.copy(str(src), str(dst))
        return

    # Replace the first "solid ..." line and the matching "endsolid ..." line.
    text = re.sub(r"^solid(?:\s+\S+)?", f"solid {patch_name}",
                  text, count=1, flags=re.MULTILINE)
    text = re.sub(r"endsolid(?:\s+\S+)?", f"endsolid {patch_name}",
                  text, count=1, flags=re.MULTILINE)
    dst.write_text(text, encoding="utf-8")

    """
    Copy STL into the case constant/triSurface directory.
    If the STL is ASCII we force the solid/endsolid name to *patch_name* so
    snappyHexMesh creates a patch with exactly that name.  Binary STLs are
    copied unchanged (snappyHexMesh names the patch from the geometry-dict key,
    which is already set to missile_wall in snappyHexMeshDict).

    Note: the old check ``header.lstrip().startswith(b"solid")`` was incorrect —
    binary STLs very often have "solid" in their 80-byte header.  We now use a
    size-based heuristic (_is_binary_stl) which is orders of magnitude more
    reliable.
    """
    src = Path(src_stl)
    dst = Path(dst_stl)
    dst.parent.mkdir(parents=True, exist_ok=True)

    if _is_binary_stl(src):
        shutil.copy(str(src), str(dst))
        return

    # ASCII STL — rewrite solid/endsolid name so snappyHexMesh sees patch_name.
    try:
        text = src.read_text(encoding="utf-8", errors="replace")
    except Exception:
        # Fallback: just copy as-is and let OpenFOAM complain with a clear log.
        shutil.copy(str(src), str(dst))
        return

    text = re.sub(r"^solid(?:\s+\S+)?", f"solid {patch_name}",
                  text, count=1, flags=re.MULTILINE)
    text = re.sub(r"endsolid(?:\s+\S+)?", f"endsolid {patch_name}",
                  text, count=1, flags=re.MULTILINE)
    dst.write_text(text, encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════════
# Missile helper – initialise from a plain parameter dict
# ═══════════════════════════════════════════════════════════════════════════════

def init_missile_from_params(params):
    """Bypass Missile.__init__ (which may expect a config string) and set
    attributes directly from the parameter dictionary."""
    m = Missile.__new__(Missile)
    for k, v in params.items():
        setattr(m, k, v)
    m.radius = m.body_diameter / 2.0
    m.total_length = m.nose_length + m.body_length
    if getattr(m, "has_flare", False):
        m.total_length += getattr(m, "flare_length", 0.0)
    if getattr(m, "fin_span", 0.0) > 0:
        m.fin_start_x = m.total_length - m.fin_offset - m.fin_chord
    else:
        m.fin_start_x = 0.0
    return m


# ═══════════════════════════════════════════════════════════════════════════════
# Mesh: blockMeshDict + snappyHexMeshDict
# ═══════════════════════════════════════════════════════════════════════════════

def write_mesh_system(case_dir, length, x_nose=0.0):
    """Write blockMeshDict and snappyHexMeshDict.

    *x_nose* is the x-coordinate of the missile nose tip as read from the STL
    bounding box.  Previously this was hard-wired to 0, which caused
    snappyHexMesh to produce a zero-sized missile_wall patch whenever the NEXT
    STL files were not positioned at the origin.
    """
    L = length
    x0 = x_nose                 # actual nose position in STL coords
    box_xmin = x0 - L           # one L upstream of the nose
    box_xmax = x0 + 3 * L       # three L downstream of the base
    box_ymax =  2 * L
    box_zmax =  2 * L
    # Point guaranteed to be in the fluid (half an L upstream, on axis)
    loc_x    = x0 - 0.5 * L

    system_dir = os.path.join(case_dir, "system")
    os.makedirs(system_dir, exist_ok=True)

    # ── blockMeshDict ──────────────────────────────────────────────────────────
    block_mesh = f"""\
/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  13                                    |
|   \\\\  /    A nd           | Web:      www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      blockMeshDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

scale   1;

vertices
(
    ({box_xmin} {-box_ymax} {-box_zmax})
    ({box_xmax} {-box_ymax} {-box_zmax})
    ({box_xmax}  {box_ymax} {-box_zmax})
    ({box_xmin}  {box_ymax} {-box_zmax})
    ({box_xmin} {-box_ymax}  {box_zmax})
    ({box_xmax} {-box_ymax}  {box_zmax})
    ({box_xmax}  {box_ymax}  {box_zmax})
    ({box_xmin}  {box_ymax}  {box_zmax})
);

blocks
(
    hex (0 1 2 3 4 5 6 7) (120 60 60) simpleGrading (1 1 1)
);

edges
(
);

boundary
(
    inlet
    {{
        type patch;
        faces
        (
            (0 4 7 3)
        );
    }}
    outlet
    {{
        type patch;
        faces
        (
            (1 5 6 2)
        );
    }}
    top
    {{
        type patch;
        faces
        (
            (3 7 6 2)
        );
    }}
    bottom
    {{
        type patch;
        faces
        (
            (0 4 5 1)
        );
    }}
    frontAndBack
    {{
        type symmetry;
        faces
        (
            (0 3 2 1)
            (4 5 6 7)
        );
    }}
);

mergePatchPairs
(
);

// ************************************************************************* //
"""

    with open(os.path.join(system_dir, "blockMeshDict"), "w") as f:
        f.write(block_mesh)

    # ── snappyHexMeshDict ──────────────────────────────────────────────────────
    snappy = f"""\
/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  13                                    |
|   \\\\  /    A nd           | Web:      www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      snappyHexMeshDict;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

castellatedMesh true;
snap            true;
addLayers       true;

geometry
{{
    missile_wall
    {{
        type triSurfaceMesh;
        file "missile.stl";
        name  missile_wall;
    }}
}};

castellatedMeshControls
{{
    maxLocalCells          100000;
    maxGlobalCells        2000000;
    minRefinementCells         10;
    maxLoadUnbalance         0.10;
    nCellsBetweenLevels           3;
    allowFreeStandingZoneFaces true;

    features
    (
    );

    refinementSurfaces
    {{
        missile_wall
        {{
            level (4 4);
        }}
    }}

    resolveFeatureAngle 30;

    refinementRegions
    {{
    }}

    locationInMesh ({loc_x:.6f} 0 0);
}}

snapControls
{{
    nSmoothPatch  3;
    tolerance     2.0;
    nSolveIter   30;
    nRelaxIter    5;
}}

addLayersControls
{{
    relativeSizes true;
    layers
    {{
        missile_wall
        {{
            nSurfaceLayers 3;
        }}
    }}
    expansionRatio         1.2;
    finalLayerThickness    0.3;
    minThickness           0.1;
    nGrow                    0;
    featureAngle            45;
    minMedialAxisAngle   130;
    nRelaxIter               5;
    nSmoothSurfaceNormals    1;
    nSmoothNormals           3;
    nSmoothThickness        10;
    maxFaceThicknessRatio  0.5;
    maxThicknessToMedialRatio 0.3;
    minMedianAxisAngleCos  0.65;
    nBufferCellsNoExtrude    0;
    nLayerIter              50;
}}

meshQualityControls
{{
    maxNonOrtho             60;
    maxBoundarySkewness     20;
    maxInternalSkewness      4;
    maxConcave              80;
    minVol                 1e-13;
    minTetQuality          1e-30;
    minArea                  -1;
    minTwist               0.02;
    minDeterminant         0.001;
    minFaceWeight          0.02;
    minVolRatio            0.01;
    minTriangleTwist         -1;
    nSmoothScale             4;
    errorReduction          0.75;
}}

mergeTolerance 1e-6;

// ************************************************************************* //
"""

    with open(os.path.join(system_dir, "snappyHexMeshDict"), "w") as f:
        f.write(snappy)


# ═══════════════════════════════════════════════════════════════════════════════
# fluidSolution
# ═══════════════════════════════════════════════════════════════════════════════

def write_fluid_solution(case_dir, mach, length, aoa_deg):
    aoa       = math.radians(aoa_deg)
    Vmag      = mach * 340.0
    Ux        = Vmag * math.cos(aoa)
    Uz        = Vmag * math.sin(aoa)
    k_inf     = 1.5 * (0.01 * Vmag) ** 2
    omega_inf = 10.0 * Vmag / length

    content = f"""\
/*--------------------------------*- C++ -*----------------------------------*\\
| =========                 |                                                 |
| \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\\\    /   O peration     | Version:  13                                    |
|   \\\\  /    A nd           | Web:      www.openfoam.com                      |
|    \\\\/     M anipulation  |                                                 |
\\*---------------------------------------------------------------------------*/
FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      fluidSolution;
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

solvers
{{
    fluid
    {{
        solver           shockFluid;
        model            RAS;
        RASModel         kOmegaSST;
        energy           on;
        pRef             101325;
        pRefCell         0;
        nOuterCorrectors 1;
        consistent       yes;
    }}
}}

freestreamCoeffs
{{
    UInf      ({Ux:.6f} 0 {Uz:.6f});
    pInf      101325;
    TInf      288.15;
    rhoInf    1.225;
    kInf      {k_inf:.6f};
    omegaInf  {omega_inf:.6f};
}}
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
"""
    os.makedirs(os.path.join(case_dir, "system"), exist_ok=True)
    with open(os.path.join(case_dir, "system", "fluidSolution"), "w") as f:
        f.write(content)


# ═══════════════════════════════════════════════════════════════════════════════
# Main case builder
# ═══════════════════════════════════════════════════════════════════════════════

def build_case(case_name, stl_file, mach, aoa_deg, length, diameter):
    case_dir = f"cases/{case_name}"
    os.makedirs(f"{case_dir}/system",             exist_ok=True)
    os.makedirs(f"{case_dir}/constant/triSurface", exist_ok=True)
    os.makedirs(f"{case_dir}/0",                  exist_ok=True)

    # Copy STL, forcing ASCII solid name to missile_wall so snappyHexMesh
    # creates a patch with exactly that name.
    dst_stl = f"{case_dir}/constant/triSurface/missile.stl"
    copy_stl_for_case(stl_file, dst_stl)

    # Read the actual nose position from the copied STL so blockMesh and
    # locationInMesh are always aligned with the geometry, regardless of how
    # the STL was generated (original sweep vs NEXT/Bayesian designs).
    stl_bounds = get_stl_bounds(dst_stl)
    if stl_bounds is not None:
        x_nose = stl_bounds[0]
        if abs(x_nose) > 0.01:
            print(f"  [INFO] STL nose x={x_nose:.4f} (not at origin) — "
                  f"adjusting blockMesh and locationInMesh accordingly.")
    else:
        x_nose = 0.0
        print("  [WARN] Could not read STL bounds; assuming nose at x=0.")

    aoa   = math.radians(aoa_deg)
    Vmag  = mach * 340.0
    Ux    = Vmag * math.cos(aoa)
    Uz    = Vmag * math.sin(aoa)
    kInf  = 1.5  * (0.01 * Vmag) ** 2
    omInf = 10.0 * Vmag / length
    T_inf = 288.15
    p_inf = 101325.0
    rho_inf = 1.225

    write_mesh_system(case_dir, length, x_nose=x_nose)
    write_fluid_solution(case_dir, mach, length, aoa_deg)

    Aref = math.pi * (diameter / 2) ** 2
    write_foam_dict(f"{case_dir}/system/controlDict", {
        "application":          "foamRun",
        "startFrom":            "startTime",
        "startTime":            0,
        "stopAt":               "endTime",
        "endTime":              END_TIME,
        "deltaT":               DELTA_T_INIT,
        "adjustTimeStep":       "yes",
        "maxCo":                MAX_CO,
        "maxDeltaT":            1e-3,
        "writeControl":         "timeStep",
        "writeInterval":        FIELD_WRITE_INTERVAL,
        "purgeWrite":           0,
        "writeFormat":          "ascii",
        "writePrecision":       10,
        "runTimeModifiable":    "yes",
        "functions": {
            "forceCoeffs1": {
                "type":          "forceCoeffs",
                "libs":          ['"libforces.so"'],
                "patches":       ["missile_wall"],
                "rhoInf":        rho_inf,
                "CofR":          [0, 0, 0],
                "liftDir":       [0, 0, 1],
                "dragDir":       [1, 0, 0],
                "pitchAxis":     [0, 1, 0],
                "magUInf":       Vmag,
                "lRef":          length,
                "Aref":          Aref,
                "writeControl":  "timeStep",
                "writeInterval": FORCE_COEFF_WRITE_INTERVAL,
                "timeStart":     FORCE_COEFF_START_TIME,
            }
        },
    })

    write_foam_dict(f"{case_dir}/system/fvSchemes", {
        "ddtSchemes":   {"default": "localEuler"},
        "gradSchemes":  {"default": "Gauss linear"},
        "divSchemes": {
            "default":          "none",
            "div(tauMC)":       "Gauss linear",
            "div(phi,rho)":     "Gauss vanLeer",
            "div(phi,p)":       "Gauss vanLeer",
            "div(phi,U)":       "Gauss vanLeerV",
            "div(phi,T)":       "Gauss vanLeer",
            "div(phi,K)":       "Gauss vanLeer",
            "div(phi,k)":       "Gauss upwind",
            "div(phi,omega)":   "Gauss upwind",
            "div(phid,p)":      "Gauss vanLeer",
        },
        "laplacianSchemes":     {"default": "Gauss linear corrected"},
        "interpolationSchemes": {"default": "linear"},
        "snGradSchemes":        {"default": "corrected"},
        "wallDist":             {"method":  "meshWave"},
    })

    p_solver = {
        "solver":                  "GAMG",
        "tolerance":               1e-7,
        "relTol":                  0.05,
        "smoother":                "GaussSeidel",
        "nPreSweeps":              0,
        "nPostSweeps":             2,
        "cacheAgglomeration":      "true",
        "nCellsInCoarsestLevel":   20,
        "agglomerator":            "faceAreaPair",
        "mergeLevels":             1,
    }
    smooth_solver = {
        "solver":    "smoothSolver",
        "smoother":  "symGaussSeidel",
        "tolerance": 1e-8,
        "relTol":    0.1,
    }

    write_foam_dict(f"{case_dir}/system/fvSolution", {
        "solvers": {
            "rho":      {"solver": "diagonal"},
            "rhoFinal": {"solver": "diagonal"},
            "p":        p_solver,
            "pFinal":   p_solver,
            "U":        smooth_solver,
            "UFinal":   smooth_solver,
            "e":        smooth_solver,
            "eFinal":   smooth_solver,
            "h":        smooth_solver,
            "hFinal":   smooth_solver,
            "k":        smooth_solver,
            "kFinal":   smooth_solver,
            "omega":    smooth_solver,
            "omegaFinal": smooth_solver,
        },
        "PIMPLE": {
            "nOuterCorrectors":         1,
            "nCorrectors":              1,
            "nNonOrthogonalCorrectors": 2,
            "transonic":                "yes",
            "nEnergySweeps":            1,
            "pRefCell":                 0,
            "pRefValue":                0,
            "residualControl": {
                "p":     1e-4,
                "U":     1e-4,
                "e":     1e-4,
                "k":     1e-4,
                "omega": 1e-4,
            },
        },
        "relaxationFactors": {
            "equations": {
                "k":     0.7,
                "omega": 0.7,
            },
        },
    })

    write_foam_dict(f"{case_dir}/system/fvConstraints", {
        "limitTemperature1": {
            "type":     "limitTemperature",
            "cellZone": "all",
            "min":      50,
            "max":      8000,
        },
        "limitVelocity1": {
            "type":     "limitMag",
            "cellZone": "all",
            "field":    "U",
            "max":      3500,
        },
        "boundK1": {
            "type":  "bound",
            "field": "k",
            "min":   1e-10,
            "max":   1e6,
        },
        "boundOmega1": {
            "type":  "bound",
            "field": "omega",
            "min":   1e-10,
            "max":   1e10,
        },
        "boundNut1": {
            "type":  "bound",
            "field": "nut",
            "min":   0,
            "max":   0.1,
        },
    })

    write_foam_dict(f"{case_dir}/constant/thermophysicalProperties", {
        "thermoType": {
            "type":            "hePsiThermo",
            "mixture":         "pureMixture",
            "transport":       "const",
            "thermo":          "hConst",
            "equationOfState": "perfectGas",
            "specie":          "specie",
            "energy":          "sensibleInternalEnergy",
        },
        "mixture": {
            "specie":         {"nMoles": 1, "molWeight": 28.96},
            "thermodynamics": {"Cp": 1004.5, "Hf": 0},
            "transport":      {"mu": 1.8e-5, "Pr": 0.71},
        },
    })

    write_foam_dict(f"{case_dir}/constant/turbulenceProperties", {
        "simulationType": "RAS",
        "RAS": {
            "RASModel":   "kOmegaSST",
            "turbulence": "on",
            "printCoeffs": "on",
        },
    })

    # 0/ fields
    freeU = {"type": "freestream", "freestreamValue": f"uniform ({Ux:.6f} 0 {Uz:.6f})"}
    freeP = {"type": "freestream", "freestreamValue": f"uniform {p_inf}"}
    freeT = {"type": "freestream", "freestreamValue": f"uniform {T_inf}"}
    freeK = {"type": "freestream", "freestreamValue": f"uniform {kInf:.6f}"}
    freeO = {"type": "freestream", "freestreamValue": f"uniform {omInf:.6f}"}

    write_foam_field(case_dir, "U", "volVectorField", "[0 1 -1 0 0 0 0]",
        f"uniform ({Ux:.6f} 0 {Uz:.6f})",
        {"inlet": freeU, "outlet": freeU, "top": freeU, "bottom": freeU,
         "frontAndBack": {"type": "symmetry"}, "missile_wall": {"type": "fixedValue", "value": "uniform (0 0 0)"}})
    write_foam_field(case_dir, "p", "volScalarField", "[1 -1 -2 0 0 0 0]", f"uniform {p_inf}",
        {"inlet": freeP, "outlet": freeP, "top": freeP, "bottom": freeP,
         "frontAndBack": {"type": "symmetry"}, "missile_wall": {"type": "zeroGradient"}})
    write_foam_field(case_dir, "T", "volScalarField", "[0 0 0 1 0 0 0]", f"uniform {T_inf}",
        {"inlet": freeT, "outlet": freeT, "top": freeT, "bottom": freeT,
         "frontAndBack": {"type": "symmetry"}, "missile_wall": {"type": "zeroGradient"}})
    write_foam_field(case_dir, "rho", "volScalarField", "[1 -3 0 0 0 0 0]", f"uniform {rho_inf}",
        {"inlet": {"type": "freestream", "freestreamValue": f"uniform {rho_inf}"},
         "outlet": {"type": "freestream", "freestreamValue": f"uniform {rho_inf}"},
         "top": {"type": "freestream", "freestreamValue": f"uniform {rho_inf}"},
         "bottom": {"type": "freestream", "freestreamValue": f"uniform {rho_inf}"},
         "frontAndBack": {"type": "symmetry"}, "missile_wall": {"type": "zeroGradient"}})
    write_foam_field(case_dir, "k", "volScalarField", "[0 2 -2 0 0 0 0]", f"uniform {kInf:.6f}",
        {"inlet": freeK, "outlet": freeK, "top": freeK, "bottom": freeK,
         "frontAndBack": {"type": "symmetry"}, "missile_wall": {"type": "kqRWallFunction", "value": f"uniform {kInf:.6f}"}})
    write_foam_field(case_dir, "omega", "volScalarField", "[0 0 -1 0 0 0 0]", f"uniform {omInf:.6f}",
        {"inlet": freeO, "outlet": freeO, "top": freeO, "bottom": freeO,
         "frontAndBack": {"type": "symmetry"}, "missile_wall": {"type": "fixedValue", "value": "uniform 1e6"}})
    write_foam_field(case_dir, "nut", "volScalarField", "[0 2 -1 0 0 0 0]", "uniform 1e-6",
        {"inlet": {"type": "calculated", "value": "uniform 1e-6"}, "outlet": {"type": "calculated", "value": "uniform 1e-6"},
         "top": {"type": "calculated", "value": "uniform 1e-6"}, "bottom": {"type": "calculated", "value": "uniform 1e-6"},
         "frontAndBack": {"type": "symmetry"}, "missile_wall": {"type": "nutkWallFunction", "value": "uniform 0"}})
    write_foam_field(case_dir, "alphat", "volScalarField", "[1 -1 -1 0 0 0 0]", "uniform 0",
        {"inlet": {"type": "calculated", "value": "uniform 0"}, "outlet": {"type": "calculated", "value": "uniform 0"},
         "top": {"type": "calculated", "value": "uniform 0"}, "bottom": {"type": "calculated", "value": "uniform 0"},
         "frontAndBack": {"type": "symmetry"},
         "missile_wall": {"type": "compressible::alphatWallFunction", "Prt": "0.85", "value": "uniform 0"}})

    print(f"[OK] Case '{case_name}'  M={mach}  AoA={aoa_deg}°  "
          f"Vmag={Vmag:.1f} m/s  built in {case_dir}/")


# ═══════════════════════════════════════════════════════════════════════════════
# Parameter Sampler, process_case, main
# ═══════════════════════════════════════════════════════════════════════════════

def random_design(config_type='random'):
    """
    Return a dict of parameters for one random missile.
    If config_type is 'random', it uniformly picks among the three families;
    otherwise you can force one family ('tomahawk','brahmos','hypersonic').
    """
    if config_type == 'random':
        family = random.choice(['tomahawk','brahmos','hypersonic'])
    else:
        family = config_type

    if family == 'tomahawk':
        # Subsonic cruise
        nose_length   = random.uniform(1.0, 2.0)
        body_diameter = random.uniform(0.4, 0.6)
        body_length   = random.uniform(3.5, 5.5)
        fin_span      = random.uniform(0.5, 1.0)
        fin_chord     = random.uniform(0.4, 0.8)
        fin_thickness = random.uniform(0.04, 0.08)
        fin_sweep     = random.uniform(15, 35)
        fin_offset    = random.uniform(0.05, 0.2)
        has_flare     = False
    elif family == 'brahmos':
        # Supersonic
        nose_length   = random.uniform(1.5, 2.5)
        body_diameter = random.uniform(0.28, 0.40)
        body_length   = random.uniform(5.0, 7.0)
        fin_span      = random.uniform(0.3, 0.6)
        fin_chord     = random.uniform(0.3, 0.6)
        fin_thickness = random.uniform(0.03, 0.05)
        fin_sweep     = random.uniform(20, 40)
        fin_offset    = random.uniform(0.1, 0.25)
        has_flare     = False
    else:  # hypersonic
        nose_length   = random.uniform(0.2, 0.5)
        body_diameter = random.uniform(0.15, 0.35)
        body_length   = random.uniform(0.8, 1.8)
        flare_angle   = random.uniform(5, 15)          # degrees
        flare_length  = random.uniform(0.2, 0.5)
        # no fins
        fin_span = fin_chord = fin_thickness = fin_sweep = fin_offset = 0.0
        has_flare = True

    params = {
        "nose_length": nose_length,
        "body_diameter": body_diameter,
        "body_length": body_length,
        "fin_span": fin_span,
        "fin_chord": fin_chord,
        "fin_thickness": fin_thickness,
        "fin_sweep": math.radians(fin_sweep) if fin_span > 0 else 0.0,
        "fin_offset": fin_offset,
        "has_flare": has_flare,
    }
    if has_flare:
        params["flare_angle"] = math.radians(flare_angle)
        params["flare_length"] = flare_length
    else:
        params["flare_angle"] = 0.0
        params["flare_length"] = 0.0
    return params, family


# -------------------------  Run One Case  -------------------------
def process_case(design_id, params, family, mach, aoa, do_run):
    """Build case, optionally run, return dict of results."""
    case_name = f"{design_id}_M{mach}_A{aoa}"
    case_dir = os.path.join("cases", case_name)

    m = init_missile_from_params(params)

    # Generate STL (once per design)
    stl_file = os.path.join("stl_variants", f"{design_id}.stl")
    os.makedirs(os.path.dirname(stl_file), exist_ok=True)
    if not os.path.exists(stl_file):
        m.generate_stl(stl_file)

    # Build OpenFOAM case
    build_case(case_name, stl_file, mach, aoa, m.total_length, m.body_diameter)

    if not do_run:
        return None

    original_dir = os.getcwd()
    try:
        os.chdir(case_dir)
        for cmd in (["blockMesh"], ["snappyHexMesh", "-overwrite"],
                    ["foamRun", "-solver", "shockFluid"]):
            subprocess.run(cmd, check=True)
        Path("DONE").touch()
    finally:
        os.chdir(original_dir)

    # Extract coefficients
    coeff_file = os.path.join(case_dir, "postProcessing", "forceCoeffs1", "0", "forceCoeffs.dat")
    coeffs = {}
    if os.path.isfile(coeff_file):
        with open(coeff_file) as f:
            lines = f.readlines()
        for line in reversed(lines):
            if line.startswith("#") or not line.strip():
                continue
            cols = line.split()
            if len(cols) < 5:
                continue
            try:
                coeffs = {"Cd": float(cols[2]), "Cl": float(cols[3]), "Cm": float(cols[1])}
                break
            except (ValueError, IndexError):
                continue
    return coeffs


# -------------------------  Main  -------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=100, help="Number of random designs")
    parser.add_argument("--run", action="store_true", help="Actually solve the cases")
    parser.add_argument("--np", type=int, default=1)
    args = parser.parse_args()

    os.makedirs("stl_variants", exist_ok=True)
    os.makedirs("cases", exist_ok=True)

    mach_range = [0.8, 1.5, 2.5, 4.0, 6.0]
    aoa_range  = [0, 2, 4, 6, 8]

    fieldnames = ["design_id", "family"] + \
                 ["nose_length","body_diameter","body_length",
                  "fin_span","fin_chord","fin_thickness","fin_sweep_deg",
                  "fin_offset","flare_angle_deg","flare_length",
                  "mach","aoa","Cd","Cl","Cm"]
    results_csv = "generative_dataset.csv"

    with open(results_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

    for i in range(args.samples):
        params, family = random_design('random')
        design_id = f"DES_{i:04d}"

        m = init_missile_from_params(params)
        stl_file = os.path.join("stl_variants", f"{design_id}.stl")
        if not os.path.exists(stl_file):
            m.generate_stl(stl_file)

        for mach, aoa in itertools.product(mach_range, aoa_range):
            try:
                coeffs = process_case(design_id, params, family, mach, aoa, args.run)
            except Exception as exc:
                print(f"[ERROR] {design_id} M{mach} A{aoa}: {exc}")
                coeffs = None

            row = {
                "design_id": design_id,
                "family": family,
                "nose_length": params["nose_length"],
                "body_diameter": params["body_diameter"],
                "body_length": params["body_length"],
                "fin_span": params["fin_span"],
                "fin_chord": params["fin_chord"],
                "fin_thickness": params["fin_thickness"],
                "fin_sweep_deg": math.degrees(params["fin_sweep"]) if params["fin_span"] > 0 else 0.0,
                "fin_offset": params["fin_offset"],
                "flare_angle_deg": math.degrees(params.get("flare_angle", 0.0)),
                "flare_length": params.get("flare_length", 0.0),
                "mach": mach,
                "aoa": aoa
            }
            if coeffs:
                row.update(coeffs)
            with open(results_csv, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writerow(row)
            if args.run and coeffs:
                print(f"Done {design_id} M{mach} A{aoa}")

    print(f"Dataset saved to {results_csv}")


if __name__ == "__main__":
    main()