#!/usr/bin/env python3
"""Adapter tray that bolts a LilyGo T-ETH-Elite case to the acrylic plate.

The T-ETH-Elite case is Cicicok's design (CC BY) and has no deck holes in its
floor, and adding them would mean drilling through its internal board supports.
So instead: a shallow tray with the standard 45 mm deck square underneath and a
rim the case drops into. The screw heads sit in counterbores so they cannot lift
the case off the floor.

    python3 adapter_lilygo.py     # -> adapter_lilygo.stl

Requires: trimesh, manifold3d.
"""
import os

import trimesh
from trimesh.creation import box, cylinder

CASE = (72.0, 53.0)          # LilyGo T-ETH-Elite case footprint, measured
FIT = 0.6                    # per side
RIM_W = 3.0
RIM_H = 6.0                  # how far the rim comes up the case side
FLOOR_T = 2.5
DECK_PITCH = 45.0            # same square as everything else in this repo
SCREW_CLEAR = 3.4
CBORE_D, CBORE_H = 6.6, 1.6  # M3 pan head sunk below the floor surface
CORNER_R = 3.0

OW = CASE[0] + 2 * (FIT + RIM_W)
OH = CASE[1] + 2 * (FIT + RIM_W)


def bx(x0, x1, y0, y1, z0, z1):
    m = box(extents=(x1 - x0, y1 - y0, z1 - z0))
    m.apply_translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    return m


def cyl(d, z0, z1, x, y, sections=48):
    m = cylinder(radius=d / 2, height=z1 - z0, sections=sections)
    m.apply_translation((x, y, (z0 + z1) / 2))
    return m


def rounded(x0, x1, y0, y1, z0, z1, r):
    parts = [bx(x0 + r, x1 - r, y0, y1, z0, z1), bx(x0, x1, y0 + r, y1 - r, z0, z1)]
    for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r), (x0 + r, y1 - r), (x1 - r, y1 - r)):
        parts.append(cyl(2 * r, z0, z1, cx, cy))
    return trimesh.boolean.union(parts, engine='manifold')


def deck_points():
    h = DECK_PITCH / 2
    return [(OW / 2 + sx * h, OH / 2 + sy * h)
            for sx in (-1, 1) for sy in (-1, 1)]


def build():
    body = rounded(0, OW, 0, OH, 0, FLOOR_T + RIM_H, CORNER_R)
    cavity = bx(RIM_W, OW - RIM_W, RIM_W, OH - RIM_W, FLOOR_T, FLOOR_T + RIM_H + 1)
    cuts = [cavity]
    for x, y in deck_points():
        cuts.append(cyl(SCREW_CLEAR, -1, FLOOR_T + 1, x, y, sections=32))
        cuts.append(cyl(CBORE_D, FLOOR_T - CBORE_H, FLOOR_T + 0.01, x, y, sections=32))
    # lighten the floor and let air through
    for sx in (-1, 1):
        cuts.append(bx(OW / 2 + sx * 14 - 7, OW / 2 + sx * 14 + 7,
                       OH / 2 - 14, OH / 2 + 14, -1, FLOOR_T + 1))
    return trimesh.boolean.difference([body] + cuts, engine='manifold')


if __name__ == '__main__':
    m = build()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       'adapter_lilygo.stl')
    m.export(out)
    e = m.bounds[1] - m.bounds[0]
    print(f"adapter_lilygo.stl  {e[0]:.1f} x {e[1]:.1f} x {e[2]:.1f} mm  "
          f"{m.volume / 1000:.2f} cm3  watertight={m.is_watertight}")
    print(f"  cavity {CASE[0] + 2 * FIT:.1f} x {CASE[1] + 2 * FIT:.1f} mm "
          f"for a {CASE[0]:.0f} x {CASE[1]:.0f} case, rim {RIM_H:.0f} mm tall")
    print(f"  deck holes on a {DECK_PITCH:.0f} mm square, counterbored "
          f"Ø{CBORE_D} x {CBORE_H} deep so heads sit below the floor")
