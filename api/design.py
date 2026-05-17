import json
import numpy as np
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ---------- Numpy-only Generator inference ----------
# Weights are loaded from gen_weights.npz (exported from gen.pth via export_weights.py)
import os

WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), "..", "gen_weights.npz")
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "combined_dataset.csv")

NOISE_DIM = 50

design_cols = ['nose_length','body_diameter','body_length',
               'fin_span','fin_chord','fin_thickness','fin_sweep_deg',
               'fin_offset','flare_angle_deg','flare_length']
cond_cols   = ['Cd','Cl','Cm','mach','aoa']

param_bounds = {
    'nose_length':     (0.2,  2.5),
    'body_diameter':   (0.15, 0.6),
    'body_length':     (0.8,  7.0),
    'fin_span':        (0.0,  1.2),
    'fin_chord':       (0.0,  0.8),
    'fin_thickness':   (0.0,  0.08),
    'fin_sweep_deg':   (-45,  45),
    'fin_offset':      (-0.2, 0.5),
    'flare_angle_deg': (0.0,  15),
    'flare_length':    (0.0,  0.5),
}

def leaky_relu(x, alpha=0.2):
    return np.where(x >= 0, x, alpha * x)

def load_model():
    w = np.load(WEIGHTS_PATH)
    layers = [
        (w['W0'], w['b0']),
        (w['W1'], w['b1']),
        (w['W2'], w['b2']),
    ]
    return layers

def forward(layers, noise, cond):
    x = np.concatenate([noise, cond], axis=1)  # (1, 55)
    x = leaky_relu(x @ layers[0][0].T + layers[0][1])
    x = leaky_relu(x @ layers[1][0].T + layers[1][1])
    x = x @ layers[2][0].T + layers[2][1]
    return x

def load_scalers():
    import csv
    rows = []
    with open(DATA_PATH, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    X = np.array([[float(r[c]) for c in design_cols] for r in rows])
    C = np.array([[float(r[c]) for c in cond_cols]  for r in rows])
    mean_X = X.mean(axis=0); std_X = X.std(axis=0, ddof=0)
    mean_C = C.mean(axis=0); std_C = C.std(axis=0, ddof=0)
    std_X[std_X == 0] = 1.0
    std_C[std_C == 0] = 1.0
    return mean_X, std_X, mean_C, std_C

def enforce_feasibility(d):
    nose_len, body_diam, body_len, fin_span, fin_chord, fin_thick, sweep_deg, offset, flare_deg, flare_len = d
    if fin_span > 0:
        if fin_chord <= 0: fin_chord = 0.05
        if fin_thick <= 0: fin_thick = 0.005
    else:
        fin_chord = fin_thick = sweep_deg = offset = 0.0
    if flare_deg > 0:
        if flare_len <= 0: flare_len = 0.01
    else:
        flare_len = 0.0
    nose_len  = max(nose_len,  0.1)
    body_diam = max(body_diam, 0.05)
    body_len  = max(body_len,  0.1)
    return np.array([nose_len, body_diam, body_len, fin_span, fin_chord, fin_thick, sweep_deg, offset, flare_deg, flare_len])

# Load once at cold start
try:
    _layers = load_model()
    _mean_X, _std_X, _mean_C, _std_C = load_scalers()
    _ready = True
    _error = None
except Exception as e:
    _ready = False
    _error = str(e)

def generate(cd, cl, cm, mach, aoa):
    if not _ready:
        raise RuntimeError(f"Model not loaded: {_error}")
    cond = np.array([[cd, cl, cm, mach, aoa]], dtype=np.float64)
    cond_norm = (cond - _mean_C) / _std_C
    noise = np.random.randn(1, NOISE_DIM)
    design_norm = forward(_layers, noise, cond_norm)
    design_phys = design_norm * _std_X + _mean_X
    for i, col in enumerate(design_cols):
        lo, hi = param_bounds[col]
        design_phys[0, i] = np.clip(design_phys[0, i], lo, hi)
    design_phys = enforce_feasibility(design_phys[0])
    return dict(zip(design_cols, design_phys.tolist()))


class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress Vercel log noise

    def _json(self, status, obj):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def _parse_params(self, params):
        def get(name):
            if name not in params:
                raise ValueError(f'Missing: {name}')
            return float(params[name][0])
        return get('cd'), get('cl'), get('cm'), get('mach'), get('aoa')

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        self.end_headers()

    def do_GET(self):
        try:
            params = parse_qs(urlparse(self.path).query)
            cd, cl, cm, mach, aoa = self._parse_params(params)
            self._json(200, {'inputs': {'Cd':cd,'Cl':cl,'Cm':cm,'Mach':mach,'AoA':aoa}, 'design': generate(cd,cl,cm,mach,aoa)})
        except Exception as e:
            self._json(400, {'error': str(e)})
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            data = json.loads(self.rfile.read(length).decode() if length else '{}')
            params = {k: [str(v)] for k, v in data.items()}
            cd, cl, cm, mach, aoa = self._parse_params(params)
            self._json(200, {'inputs': {'Cd':cd,'Cl':cl,'Cm':cm,'Mach':mach,'AoA':aoa}, 'design': generate(cd,cl,cm,mach,aoa)})
        except Exception as e:
            self._json(400, {'error': str(e)})
