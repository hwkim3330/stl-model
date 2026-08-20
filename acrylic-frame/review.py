#!/usr/bin/env python3
"""Check the generated DXFs the way the acrylic will fail, not the way I drew it.

    python3 review.py

Rasterises each plate's actual DXF output and measures, per plate:

  * the web left between every pair of cut features
  * the web between each cut and the plate edge
  * every intended cut matched in the DXF by position AND size, with no strays
  * every screw position in the build against the quantities in the BOM

The geometry match is the important one. An earlier version counted cuts per
plate instead, and passed a plate that had eight leftover deck slots where eight
board mounts were intended - the counts agreed, the coordinates did not.

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


def expected_features():
    """Every cut the design intends, as (plate, kind, x, y, size).

    kind 'circle' -> Ø size;  'slot'/'slotv' -> length `size` along X / along Y,
    width `w`.
    """
    import make_plates as M
    exp = {n: [] for n, _, _ in M.PLATES}
    A, B, C = 'plate-a-bottom-5T', 'plate-b-middle-5T', 'plate-c-top-3T'
    D = 'plate-d-upper-3T'
    for x, y in M.lower_columns():
        exp[A].append(('circle', x, y, M.M3_FREE, 0))
        exp[B].append(('circle', x, y, M.M3_FREE, 0))
    # plate C's four upper-column holes serve twice: the F/F standoff below it
    # and the M/F standoff above it, whose stud passes the 3 mm plate. So plate
    # D repeats the same four positions and no new holes appear in C.
    for x, y in M.upper_columns():
        exp[B].append(('circle', x, y, M.M3_FREE, 0))
        exp[C].append(('circle', x, y, M.M3_FREE, 0))
        exp[D].append(('circle', x, y, M.M3_FREE, 0))
    for hx, hy in M.LAN_HOLES:
        exp[A].append(('circle', M.BOARD_OFF[0] + hx, M.BOARD_OFF[1] + hy,
                       M.M3_FREE, 0))
    exp[B].append(('circle', M.FAN_C[0], M.FAN_C[1], M.FAN_BORE, 0))
    h = M.FAN_PITCH / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            exp[B].append(('circle', M.FAN_C[0] + sx * h, M.FAN_C[1] + sy * h,
                           M.FAN_SCREW_D, 0))
    for (_, cx, cy), (bw, bh), holes, hd, slotted in M.board_mounts():
        for i, (hx, hy) in enumerate(holes):
            X, Y = cx - bw / 2 + hx, cy - bh / 2 + hy
            if i in slotted and M.MOUNT_SLOT > hd:
                exp[B].append(('slot', X, Y, M.MOUNT_SLOT, hd))
            else:
                exp[B].append(('circle', X, Y, hd, 0))
    for plate in (C, D):
        for i in range(-2, 3):
            exp[plate].append(('slotv', M.FAN_C[0] + i * (M.VENT_SLOT[0] + 6),
                               M.FAN_C[1], M.VENT_SLOT[1], M.VENT_SLOT[0]))
    return exp


def geometry_audit(tol=0.02):
    """Match every intended cut against the DXF actually written."""
    import glob
    exp = expected_features()
    print("\ngeometry: every intended cut, matched in the DXF that was written")
    bad = False
    for name, want in exp.items():
        f = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dxf', name + '.dxf')
        if not os.path.exists(f):
            print(f"  {name:26s} FILE MISSING")
            bad = True
            continue
        # only the CUT layer is geometry the shop cuts; ENGRAVE/TEXT is artwork
        ents = [(k, b) for k, b in parse(f) if b.get('8') == 'CUT']
        circles = [(float(b['10']), float(b['20']), float(b['40']) * 2)
                   for k, b in ents if k == 'CIRCLE']
        arcs = [(float(b['10']), float(b['20']), float(b['40']) * 2)
                for k, b in ents if k == 'ARC']
        miss = []
        used = 0
        for kind, x, y, size, w in want:
            if kind == 'circle':
                hit = any(abs(cx - x) < tol and abs(cy - y) < tol
                          and abs(cd - size) < tol for cx, cy, cd in circles)
                used += 1
            else:
                half = (size - w) / 2
                dx, dy = (half, 0) if kind == 'slot' else (0, half)
                hit = all(any(abs(ax - (x + s * dx)) < tol
                              and abs(ay - (y + s * dy)) < tol
                              and abs(ad - w) < tol for ax, ay, ad in arcs)
                          for s in (1, -1))
                used += 1
            if not hit:
                miss.append((kind, round(x, 3), round(y, 3), size))
        # the outline contributes 4 arcs; anything else unaccounted for is a stray
        stray = len(circles) - sum(1 for k, *_ in want if k == 'circle')
        tag = 'OK' if not miss and stray == 0 else 'FAIL'
        if tag == 'FAIL':
            bad = True
        print(f"  {name:26s} {len(want):3d} intended, {len(miss)} missing, "
              f"{stray:+d} stray circles   {tag}")
        for m in miss[:4]:
            print(f"        missing {m}")
    return not bad


def zip_audit():
    """The order zip against the files it was built from.

    The zip carries CUTTING.md and the DXFs, so editing either without
    rerunning make_plates.py ships the shop a stale copy - which is exactly
    what happened to CUTTING.md once. Compare contents, not timestamps.
    """
    import hashlib
    import zipfile
    here = os.path.dirname(os.path.abspath(__file__))
    zp = os.path.join(here, 'acrylic-frame-dxf.zip')
    print("\norder zip: every member against the file on disk")
    if not os.path.exists(zp):
        print("  acrylic-frame-dxf.zip MISSING")
        return False
    bad = []
    with zipfile.ZipFile(zp) as z:
        for member in z.namelist():
            # the zip flattens dxf/ into its top level, so try both
            rel = os.path.relpath(member, 'acrylic-frame')
            for cand in (os.path.join(here, rel), os.path.join(here, 'dxf', rel)):
                if os.path.exists(cand):
                    local = cand
                    break
            else:
                bad.append((member, 'no such file on disk'))
                continue
            a = hashlib.md5(z.read(member)).hexdigest()
            b = hashlib.md5(open(local, 'rb').read()).hexdigest()
            if a != b:
                bad.append((member, 'differs from disk'))
        n = len(z.namelist())
    for m, why in bad:
        print(f"        {m}: {why}")
    print(f"  {n} members, {len(bad)} stale   {'OK' if not bad else 'FAIL'}")
    return not bad


def model_audit(tol=0.01):
    """The 3D preview's cuts against the DXFs, feature by feature.

    assembly.py used to build the plates from the constants a second time, so a
    change to the DXF did not have to reach the mesh - plate B was previewed
    with the legacy 45 mm deck slots while its DXF carried real board mounts.
    It now reads the shipped DXF, and this proves it kept doing so.
    """
    import assembly as A
    import make_plates as M
    print("\n3D preview: every cut in the mesh, against the DXF it was cut from")
    exp = expected_features()
    bad = False
    for kind, stem in A.PLATE_DXF.items():
        got = A.dxf_features(stem)
        want = exp[stem]
        miss = []
        for f in want:
            if f[0] == 'circle':
                hit = any(g[0] == 'circle' and abs(g[1] - f[1]) < tol
                          and abs(g[2] - f[2]) < tol and abs(g[3] - f[3]) < tol
                          for g in got)
            else:
                hit = any(g[0] == 'slot' and abs(g[1] - f[1]) < tol
                          and abs(g[2] - f[2]) < tol and abs(g[3] - f[3]) < tol
                          and abs(g[4] - f[4]) < tol
                          and g[5] == (f[0] == 'slot') for g in got)
            if not hit:
                miss.append(f)
        stray = len(got) - len(want)
        tag = 'OK' if not miss and stray == 0 else 'FAIL'
        bad |= tag == 'FAIL'
        print(f"  plate {kind}  {len(got):2d} cuts in the mesh, "
              f"{len(miss)} missing, {stray:+d} stray   {tag}")
        for m in miss[:4]:
            print(f"        missing {m}")
    if M.ENGRAVE:
        n = len(A.dxf_features(A.PLATE_DXF['C'], 'ENGRAVE'))
        print(f"  plate C engraving: {n} strokes read from the ENGRAVE layer"
              f"   {'OK' if n else 'MISSING'}")
        bad |= not n
    else:
        print("  engraving: none specified, and no ENGRAVE layer emitted   OK")
    return not bad


def fastener_audit():
    """Every hole that takes a screw, against what the BOM orders."""
    import make_plates as M
    import bom
    need = {
        'A->B standoff column': 2 * len(M.lower_columns()),
        # the upper column is two joints sharing plate C's holes: a screw up
        # into the B->C standoff, then the C->D M/F stud through the plate and a
        # screw down through plate D. Two screws per position either way.
        'B->C + C->D column': 2 * len(M.upper_columns()),
        'LAN9692 to plate A': 2 * len(M.LAN_HOLES),
        'fan to plate B': 4,
    }
    if M.DIRECT_MOUNT:
        for (name, _, _), _, holes, _, _ in M.board_mounts():
            need[f'{name} to plate B'] = 2 * len(holes)
    else:
        need['plate D + E to plate B'] = 8
        need['T-ETH-Elite to plate D'] = 2 * len(M.ETH_HOLES)
        need['TC397 to plate E'] = 2 * len(M.TC_HOLES + M.TC_EXTRA_HOLES)
    ordered = sum(b[3] for b in bom.BOM
                  if b[0] == 'hardware' and b[1].startswith('Screw'))
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
    if not geometry_audit():
        bad = True
    if not model_audit():
        bad = True
    if not zip_audit():
        bad = True
    fastener_audit()
    sys.exit(1 if bad else 0)
