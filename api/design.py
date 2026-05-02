import torch
import json
import numpy as np
from http.server import BaseHTTPRequestHandler
from generate_final_design import generate

class handler(BaseHTTPRequestHandler):
    def _set_headers(self, status_code=200, content_type="application/json"):
        self.send_response(status_code)
        self.send_header("Content-type", content_type)
        self.end_headers()

    def do_GET(self):
        try:
            # Parse query params
            from urllib.parse import urlparse, parse_qs
            query = urlparse(self.path).query
            params = parse_qs(query)

            def get_float(name):
                if name not in params:
                    raise ValueError(f"Missing required parameter: {name}")
                return float(params[name][0])

            cd = get_float("cd")
            cl = get_float("cl")
            cm = get_float("cm")
            mach = get_float("mach")
            aoa = get_float("aoa")

            design = generate(cd, cl, cm, mach, aoa)

            self._set_headers(200)
            self.wfile.write(json.dumps({
                "inputs": {
                    "Cd": cd,
                    "Cl": cl,
                    "Cm": cm,
                    "Mach": mach,
                    "AoA": aoa
                },
                "design": design
            }).encode("utf-8"))
        except Exception as e:
            self._set_headers(400)
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length > 0 else b"{}"
            data = json.loads(body.decode("utf-8"))

            def get_float(name):
                if name not in data:
                    raise ValueError(f"Missing required field: {name}")
                return float(data[name])

            cd = get_float("cd")
            cl = get_float("cl")
            cm = get_float("cm")
            mach = get_float("mach")
            aoa = get_float("aoa")

            design = generate(cd, cl, cm, mach, aoa)

            self._set_headers(200)
            self.wfile.write(json.dumps({
                "inputs": {
                    "Cd": cd,
                    "Cl": cl,
                    "Cm": cm,
                    "Mach": mach,
                    "AoA": aoa
                },
                "design": design
            }).encode("utf-8"))
        except Exception as e:
            self._set_headers(400)
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
