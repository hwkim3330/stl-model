#!/usr/bin/env python3
"""Check the generated DXFs the way the acrylic will fail, not the way I drew it.

    python3 review.py

Rasterises each plate's actual DXF output and measures, per plate:

  * the web left between every pair of cut features
  * the web between each cut and the plate edge
  * that every cut lies inside the outline

Thin webs are what snap in 3 mm acrylic, and they are invisible in a render.
Thresholds below are deliberately conservative for cast acrylic.
"""
import glob
import math
import os
import re
import sys

import numpy as np
from scipy import ndimage

PX = 8.0           # pixels per mm
WARN = 3.0         # mm - a web this thin in 3 mm acrylic is fragile
FAIL = 1.5         # mm - will not survive handling


def parse(path):
    t = open(path).read().split('\n')
    ents, i = [], 0
    while i < len(t) - 1:
        if t[i] == '0' and t[i + 1] in ('LINE', 'CIRCLE', 'ARC'):
            kind, b, j = t[i + 1], {}, i + 2
            while j < len(t) - 1 and t[j] != '0':
                b[t[j]] = t[j + 1]
                j = j + 2
            ents.append((kind, b))
            i = j
        else:
            i += 1
    return ents


def raster(ents, layer=None):
    """Fill every closed shape; returns (mask, origin, shape)."""
    xs, ys = [], []
    for k, b in ents:
        if layer and b.get('8') != layer:
            continue
        for a, c in (('10', '20'), ('11', '21')):
            if a in b:
                xs.append(float(b[a]))
                ys.append(float(b[c]))
        if k in ('CIRCLE', 'ARC'):
            r = float(b['40'])
            xs += [float(b['10']) - r, float(b['10']) + r]
            ys += [float(b['20']) - r, float(b['20']) + r]
    x0, y0 = min(xs) - 2, min(ys) - 2
    W = int((max(xs) + 2 - x0) * PX) + 1
    H = int((max(ys) + 2 - y0) * PX) + 1
    return x0, y0, W, H


def draw(ents, x0, y0, W, H, layer='CUT'):
    """Return a boolean image of the drawn strokes."""
    img = np.zeros((H, W), bool)
    yy, xx = np.mgrid[0:H, 0:W]
    px = x0 + xx / PX
    py = y0 + yy / PX
    for k, b in ents:
        if b.get('8') != layer:
            continue
        if k == 'CIRCLE':
            cx, cy, r = float(b['10']), float(b['20']), float(b['40'])
            img |= (np.hypot(px - cx, py - cy) - r) ** 2 < (1.5 / PX) ** 2
        elif k == 'ARC':
            cx, cy, r = float(b['10']), float(b['20']), float(b['40'])
            a0, a1 = math.radians(float(b['50'])), math.radians(float(b['51']))
            ang = np.arctan2(py - cy, px - cx) % (2 * math.pi)
            lo, hi = a0 % (2 * math.pi), a1 % (2 * math.pi)
            inarc = (ang >= lo) & (ang <= hi) if lo <= hi else (ang >= lo) | (ang <= hi)
            img |= inarc & (np.abs(np.hypot(px - cx, py - cy) - r) < 1.5 / PX)
        else:
            ax, ay = float(b['10']), float(b['20'])
            bx_, by = float(b['11']), float(b['21'])
            dx, dy = bx_ - ax, by - ay
            L2 = dx * dx + dy * dy
            if L2 < 1e-12:
                continue
            t = np.clip(((px - ax) * dx + (py - ay) * dy) / L2, 0, 1)
            img |= np.hypot(px - (ax + t * dx), py - (ay + t * dy)) < 1.5 / PX
    return img


def review(path):
    ents = parse(path)
    x0, y0, W, H = raster(ents)
    strokes = draw(ents, x0, y0, W, H)
    # Everything that is not a drawn line splits into: the region touching the
    # image border (outside the plate), the material, and one region per cut.
    lab, n = ndimage.label(~strokes)
    if n < 2:
        return path, [], 0.0, 0
    border = set(lab[0].tolist()) | set(lab[-1].tolist())
    border |= set(lab[:, 0].tolist()) | set(lab[:, -1].tolist())
    border.discard(0)
    sizes = {i: int((lab == i).sum()) for i in range(1, n + 1)}
    material_id = max((i for i in sizes if i not in border), key=sizes.get)
    outside = np.isin(lab, list(border))
    cut_ids = [i for i in sizes if i not in border and i != material_id]

    regions = [outside] + [lab == i for i in cut_ids]
    names = ['plate edge'] + [f'cut {k}' for k in range(1, len(cut_ids) + 1)]
    cn = len(cut_ids)
    worst, issues = 1e9, []
    for i in range(len(regions)):
        di = ndimage.distance_transform_edt(~regions[i]) / PX
        for j in range(i + 1, len(regions)):
            g = float(di[regions[j]].min())
            worst = min(worst, g)
            if g < WARN:
                issues.append((g, names[i], names[j]))
    return path, sorted(issues), worst, cn


def hole_census():
    """Count the holes the DXFs actually contain, per plate."""
    import make_plates as M
    mounts = sum(len(h) for _, _, h, _ in M.board_mounts()) if M.DIRECT_MOUNT else 8
    c = {
        'plate-a-bottom-5T': len(M.lower_columns()) + len(M.LAN_HOLES),
        'plate-b-middle-5T': (len(M.lower_columns()) + len(M.upper_columns())
                              + 1 + 4 + mounts),        # fan bore, fan screws
        'plate-c-top-3T': len(M.upper_columns()) + 5,   # + intake slots
    }
    if not M.DIRECT_MOUNT:
        c['plate-d-eth-elite-3T'] = len(M.ETH_HOLES) + 4
        c['plate-e-tc397-3T'] = len(M.TC_HOLES + M.TC_EXTRA_HOLES) + 4
    return c


def fastener_audit():
    """Every hole that takes a screw, against what the BOM orders."""
    import make_plates as M
    import bom
    need = {
        'A->B standoff column': 2 * len(M.lower_columns()),
        'B->C standoff column': 2 * len(M.upper_columns()),
        'LAN9692 to plate A': 2 * len(M.LAN_HOLES),
        'fan to plate B': 4,
    }
    if M.DIRECT_MOUNT:
        for (name, _, _), _, holes, _ in M.board_mounts():
            need[f'{name} to plate B'] = 2 * len(holes)
    else:
        need['plate D + E to plate B'] = 8
        need['T-ETH-Elite to plate D'] = 2 * len(M.ETH_HOLES)
        need['TC397 to plate E'] = 2 * len(M.TC_HOLES + M.TC_EXTRA_HOLES)
    ordered = sum(q for g, item, spec, q, note in bom.BOM
                  if g == 'hardware' and item.startswith('Screw'))
    print(f"\nfasteners: {sum(need.values())} screw positions in the design, "
          f"{ordered} screws in the BOM"
          f"   {'OK' if ordered >= sum(need.values()) else 'SHORT'}")
    for k, v in need.items():
        print(f"    {v:3d}  {k}")


if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    files = sorted(glob.glob(os.path.join(here, 'dxf', 'plate-*.dxf')))
    bad = False
    print(f"web check at {PX:.0f} px/mm   warn < {WARN} mm   fail < {FAIL} mm\n")
    for f in files:
        path, issues, worst, cn = review(f)
        tag = 'OK' if not issues else ('FAIL' if worst < FAIL else 'WARN')
        print(f"  {os.path.basename(path):26s} {cn:2d} cuts   thinnest web "
              f"{worst:6.2f} mm   {tag}")
        for g, a, b in issues[:6]:
            print(f"      {g:5.2f} mm between {a} and {b}")
        bad |= worst < FAIL
        expect = hole_census().get(os.path.basename(path)[:-4])
        if expect is not None and expect != cn:
            print(f"      hole count {cn} in the DXF, {expect} expected  <-- MISMATCH")
            bad = True
    fastener_audit()
    sys.exit(1 if bad else 0)
