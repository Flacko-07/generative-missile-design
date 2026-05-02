#!/usr/bin/env python3
# generate_all_missiles.py – Tomahawk (subsonic), BrahMos (supersonic), Hypersonic glide vehicle

import numpy as np
from stl import mesh
import math

class Missile:
    def __init__(self, config='tomahawk'):
        """
        config:
          'tomahawk'   – subsonic cruise (M ~0.8), cone-cylinder + 4 fins
          'brahmos'    – supersonic cruise (M ~2.8), slender cone-cylinder + 4 fins
          'hypersonic' – hypersonic glide (M ~6+), cone-cylinder-flare, no fins
        """
        if config == 'tomahawk':
            self.nose_length = 1.5
            self.body_diameter = 0.52
            self.body_length = 4.75
            self.fin_span = 0.8
            self.fin_chord = 0.6
            self.fin_thickness = 0.06
            self.fin_sweep = math.radians(25)
            self.fin_offset = 0.1
            self.has_flare = False
        elif config == 'brahmos':
            self.nose_length = 2.0
            self.body_diameter = 0.34
            self.body_length = 6.0
            self.fin_span = 0.45
            self.fin_chord = 0.5
            self.fin_thickness = 0.04
            self.fin_sweep = math.radians(30)
            self.fin_offset = 0.15
            self.has_flare = False
        elif config == 'hypersonic':
            self.nose_length = 0.3          # blunt cone
            self.body_diameter = 0.25
            self.body_length = 1.2
            self.flare_angle = math.radians(10)   # flare half-angle
            self.flare_length = 0.3
            self.has_flare = True
            # no fins
            self.fin_span = 0.0
            self.fin_chord = 0.0
            self.fin_thickness = 0.0
            self.fin_sweep = 0.0
            self.fin_offset = 0.0
        else:
            raise ValueError("Unknown config. Use 'tomahawk', 'brahmos', or 'hypersonic'.")

        self.radius = self.body_diameter / 2.0
        self.total_length = self.nose_length + self.body_length
        if self.has_flare:
            self.total_length += self.flare_length

        # fin placement (if any)
        if self.fin_span > 0:
            self.fin_start_x = self.total_length - self.fin_offset - self.fin_chord
        else:
            self.fin_start_x = 0.0

    def _naca4_profile(self, max_t, n_points=50):
        """NACA 00xx symmetric thickness distribution (half-thickness)."""
        x = np.linspace(0, 1, n_points)
        t = max_t / 2.0
        # NACA 4-digit thickness formula
        y_t = 5 * t * (0.2969*np.sqrt(x) - 0.1260*x - 0.3516*x**2 + 0.2843*x**3 - 0.1015*x**4)
        return x, y_t

    def _create_fin_surface(self):
        """Generate one fin (upper and lower surface) as a mesh of triangles.
           Fin starts at (0,0) root leading edge, extends in spanwise (y) and chordwise (x)."""
        n_span = 12          # number of spanwise stations
        n_chord = 50         # number of chordwise points
        span_stations = np.linspace(0, self.fin_span, n_span)

        # profile scaled later, get raw thickness shape
        x_prof, y_prof = self._naca4_profile(self.fin_thickness, n_chord)

        vertices = []
        faces = []

        # Compute leading-edge and trailing-edge x at each span station due to sweep
        x_le_root = 0.0
        x_le_tip = self.fin_span * math.tan(self.fin_sweep)
        x_te_root = self.fin_chord
        x_te_tip = self.fin_chord + self.fin_span * math.tan(self.fin_sweep)

        for i, s in enumerate(span_stations):
            # x start and end of this span station's chord
            x_le = x_le_root + (x_le_tip - x_le_root) * s / self.fin_span
            x_te = x_te_root + (x_te_tip - x_te_root) * s / self.fin_span
            chord = x_te - x_le

            for j in range(n_chord):
                xc = x_prof[j]
                x = x_le + xc * chord
                half_thick = y_prof[j] * chord
                # Upper surface (positive z), lower surface (negative z)
                vertices.append([x, s, half_thick])
                vertices.append([x, s, -half_thick])

        verts = np.array(vertices, dtype=np.float32)
        n_vert_per_span = 2 * n_chord  # upper then lower

        # Triangulate between consecutive span stations
        for i in range(n_span - 1):
            off0 = i * n_vert_per_span
            off1 = (i + 1) * n_vert_per_span
            # Upper surface quads -> two triangles
            for j in range(n_chord - 1):
                v0 = off0 + j
                v1 = off1 + j
                v2 = off1 + j + 1
                v3 = off0 + j + 1
                faces.append([v0, v1, v2])
                faces.append([v0, v2, v3])
                # Lower surface (indices offset by n_chord)
                v0_l = off0 + n_chord + j
                v1_l = off1 + n_chord + j
                v2_l = off1 + n_chord + j + 1
                v3_l = off0 + n_chord + j + 1
                faces.append([v0_l, v1_l, v2_l])
                faces.append([v0_l, v2_l, v3_l])

        # Create mesh object
        fin_mesh = mesh.Mesh(np.zeros(len(faces), dtype=mesh.Mesh.dtype))
        for k, face in enumerate(faces):
            for l in range(3):
                fin_mesh.vectors[k][l] = verts[face[l]]
        return fin_mesh

    def _body_surface(self):
        """Generate axi-symmetric body: nose (tangent ogive) + cylinder + optional flare."""
        n_x = 120        # stations along length
        n_theta = 72     # points around circumference

        vertices = []
        faces = []

        # ---- Nose (tangent ogive) ----
        for i in range(n_x):
            x = (i / (n_x - 1)) * self.nose_length
            # Tangent ogive: r(x) = R * sqrt( 1 - ((x - L_n)/L_n)^2 )
            radical = 1.0 - ((x - self.nose_length) / self.nose_length) ** 2
            if radical < 0:
                radical = 0.0
            r = self.radius * math.sqrt(radical)
            for j in range(n_theta):
                theta = 2 * math.pi * j / n_theta
                y = r * math.cos(theta)
                z = r * math.sin(theta)
                vertices.append([x, y, z])

        # ---- Cylinder ----
        for i in range(n_x):
            x = self.nose_length + (i / (n_x - 1)) * self.body_length
            r = self.radius
            for j in range(n_theta):
                theta = 2 * math.pi * j / n_theta
                y = r * math.cos(theta)
                z = r * math.sin(theta)
                vertices.append([x, y, z])

        # ---- Flare (if any) ----
        if self.has_flare:
            for i in range(n_x):
                x = self.nose_length + self.body_length + (i / (n_x - 1)) * self.flare_length
                # radius grows linearly from body radius to body_radius + flare_length * tan(flare_angle)
                r = self.radius + (i / (n_x - 1)) * self.flare_length * math.tan(self.flare_angle)
                for j in range(n_theta):
                    theta = 2 * math.pi * j / n_theta
                    y = r * math.cos(theta)
                    z = r * math.sin(theta)
                    vertices.append([x, y, z])

        verts = np.array(vertices, dtype=np.float32)
        # Total rings: nose rings (n_x) + cylinder rings (n_x) + optional flare rings (n_x)
        n_rings = n_x + n_x + (n_x if self.has_flare else 0)

        # Triangulate between rings
        for i in range(n_rings - 1):
            i0 = i * n_theta
            i1 = (i + 1) * n_theta
            for j in range(n_theta):
                j_next = (j + 1) % n_theta
                v0 = i0 + j
                v1 = i1 + j
                v2 = i1 + j_next
                v3 = i0 + j_next
                faces.append([v0, v1, v2])
                faces.append([v0, v2, v3])

        # Close the nose tip? The first ring (x=0) has r=0 → all vertices are at same point (degenerate).
        # We leave it; snappyHexMesh will handle fine.
        # Close the tail? For cylinder/flare we leave it open; the mesh will be closed by the background mesh
        # and we can add a symmetry plane or base if needed later.

        body_mesh = mesh.Mesh(np.zeros(len(faces), dtype=mesh.Mesh.dtype))
        for k, face in enumerate(faces):
            for l in range(3):
                body_mesh.vectors[k][l] = verts[face[l]]
        return body_mesh

    def generate_stl(self, filename='missile.stl'):
        """Combine body + 4 fins (if any) and save as ASCII STL."""
        body = self._body_surface()
        meshes = [body]

        if self.fin_span > 0:
            fin_template = self._create_fin_surface()
            for angle_deg in [0, 90, 180, 270]:
                angle = math.radians(angle_deg)
                fin = mesh.Mesh(fin_template.data.copy())
                # Rotate around x-axis: y,z
                for i in range(len(fin.vectors)):
                    for j in range(3):
                        y, z = fin.vectors[i][j][1], fin.vectors[i][j][2]
                        fin.vectors[i][j][1] = y * math.cos(angle) - z * math.sin(angle)
                        fin.vectors[i][j][2] = y * math.sin(angle) + z * math.cos(angle)
                # Translate to correct x-position
                fin.x += self.fin_start_x
                meshes.append(fin)

        combined = mesh.Mesh(np.concatenate([m.data for m in meshes]))
        combined.save(filename)
        print(f"STL saved to {filename}")

if __name__ == "__main__":
    # Generate all three
    for config in ['tomahawk', 'brahmos', 'hypersonic']:
        m = Missile(config)
        m.generate_stl(f'{config}.stl')