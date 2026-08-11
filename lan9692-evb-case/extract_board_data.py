#!/usr/bin/env python3
"""Pull the mechanical facts for the tray straight out of Microchip's Gerber set.

The archive itself is Microchip's and is not redistributed here. Fetch it from
the EV09P11A page (Gerbers, 30 Apr 2026) and unzip it next to this script:

  https://www.microchip.com/content/dam/mchp/documents/NCS/ProductDocuments/BoardDesignFiles/04-12092-R1-gerber.zip

    python3 extract_board_data.py [dir-with-gerbers]

Prints the board outline, the 3.048 mm mounting holes and a bottom-side
clearance report for the standoffs and the PCB support rails.
"""
import glob
import os
import re
import sys

import numpy as np

MOUNT_TOOL_DIA = 3.048   # 0.120 in, tool T23 in this board's drill report
BOSS_D = 7.0             # standoff outer diameter used by lan9692_case.py
RAIL_CANDIDATES = (1.6, 3.0)


def gerber_points(path, window=None):
    """Every draw/move/flash coordinate in a Gerber file, in mm."""
    t = open(path, errors='replace').read().replace('\r', '')
    fs = re.search(r'%FSLA?X(\d)(\d)Y(\d)(\d)\*%', t)
    if not fs:
        return np.empty((0, 2))
    scale = 10 ** int(fs.group(2))
    inches = bool(re.search(r'%MOIN\*%', t))
    out, x, y = [], 0.0, 0.0
    for m in re.finditer(r'(?:X(-?\d+))?(?:Y(-?\d+))?D0?[123]\*', t):
        if m.group(1) is not None:
            x = int(m.group(1)) / scale
        if m.group(2) is not None:
            y = int(m.group(2)) / scale
        out.append((x, y))
    p = np.array(out, dtype=float)
    if inches:
        p *= 25.4
    if window is not None and len(p):
        x0, x1, y0, y1 = window
        p = p[(p[:, 0] >= x0) & (p[:, 0] <= x1) & (p[:, 1] >= y0) & (p[:, 1] <= y1)]
    return p


def excellon_holes(path):
    """{tool_diameter_mm: [(x, y), ...]} from a metric Excellon file."""
    t = open(path, errors='replace').read().replace('\r', '')
    dec = 3
    fmt = re.search(r'FILE_FORMAT=(\d):(\d)', t)
    if fmt:
        dec = int(fmt.group(2))
    dia = {int(m.group(1)): float(m.group(2))
           for m in re.finditer(r'^T(\d+)F\d+S\d+C([\d.]+)', t, re.M)}
    body = t.split('%\n', 1)[-1]
    holes, cur = {}, None
    for line in body.split('\n'):
        line = line.strip()
        m = re.fullmatch(r'T(\d+)', line)
        if m:
            cur = dia.get(int(m.group(1)))
            holes.setdefault(cur, [])
            continue
        m = re.fullmatch(r'X(-?\d+)Y(-?\d+)', line)
        if m and cur is not None:
            holes[cur].append((int(m.group(1)) / 10 ** dec,
                               int(m.group(2)) / 10 ** dec))
    return holes


def fit_outline(p, holes, min_hits=2):
    """Tightest rectangle of straight outline lines that encloses every hole."""
    def lines(coord):
        v, n = np.unique(np.round(coord, 3), return_counts=True)
        return v[n >= min_hits]
    xs, ys = lines(p[:, 0]), lines(p[:, 1])
    hx0, hx1 = holes[:, 0].min(), holes[:, 0].max()
    hy0, hy1 = holes[:, 1].min(), holes[:, 1].max()
    return (xs[xs <= hx0].max(), xs[xs >= hx1].min(),
            ys[ys <= hy0].max(), ys[ys >= hy1].min())


def main(d='.'):
    board = glob.glob(os.path.join(d, '*.GM2'))
    drill = glob.glob(os.path.join(d, '*RoundHoles.TXT'))
    paste = glob.glob(os.path.join(d, '*.GBP'))
    if not (board and drill):
        sys.exit(f"no *.GM2 / *RoundHoles.TXT in {d!r} - unzip the Gerber set there")

    holes = excellon_holes(drill[0])
    mount = sorted(holes.get(MOUNT_TOOL_DIA, []), key=lambda h: (-h[1], h[0]))
    allh = np.array([h for v in holes.values() for h in v])

    # --- board outline. The BOARD layer also carries the fab drawing frame and
    # its title block, so taking the layer extent is wrong. Every drilled hole
    # must lie inside the board, so take the tightest rectangle made of actual
    # outline lines that still encloses the whole drill pattern.
    p = gerber_points(board[0])
    x0, x1, y0, y1 = fit_outline(p, allh)
    BW, BH = x1 - x0, y1 - y0
    print(f"board outline      {BW:.3f} x {BH:.3f} mm   "
          f"(corners {x0:.3f},{y0:.3f} .. {x1:.3f},{y1:.3f})")
    print(f"                   = {BW / 25.4:.3f} x {BH / 25.4:.3f} in")
    if abs(x0) > 1e-6 or abs(y0) > 1e-6:
        allh = allh - [x0, y0]
        mount = [(x - x0, y - y0) for x, y in mount]
    print(f"\nmounting holes     {len(mount)} x Ø{MOUNT_TOOL_DIA} mm")
    print("HOLES = [")
    for x, y in mount:
        print(f"    ({x:.3f}, {y:.3f}),")
    print("]")
    if mount:
        ins = [min(x, BW - x) for x, _ in mount] + [min(y, BH - y) for _, y in mount]
        print(f"  corner inset {min(ins):.3f} mm = {min(ins) / 25.4:.3f} in")

    if not paste:
        return
    # --- bottom-side clearance. Paste apertures are where bottom-side parts
    # actually sit; the assembly layers also contain text and hole symbols and
    # are useless as a keepout source.
    bp = gerber_points(paste[0], window=(x0 - 1, x1 + 1, y0 - 1, y1 + 1)) - [x0, y0]
    print(f"\nbottom-side pads   {len(bp)} apertures inside the outline")
    print(f"  nearest to left edge  {bp[:, 0].min():.2f} mm")
    print(f"  nearest to right edge {BW - bp[:, 0].max():.2f} mm")
    worst = min(np.hypot(bp[:, 0] - hx, bp[:, 1] - hy).min() for hx, hy in mount)
    print(f"  nearest to any mounting hole centre {worst:.2f} mm "
          f"(Ø{BOSS_D} boss needs {BOSS_D / 2:.1f}) -> "
          f"{'OK' if worst > BOSS_D / 2 else 'COLLISION'}")
    for w in RAIL_CANDIDATES:
        n = ((bp[:, 0] < w) | (bp[:, 0] > BW - w)).sum()
        print(f"  RAIL_IN = {w}: {n} pad(s) under the rail -> "
              f"{'OK' if n == 0 else 'too wide'}")


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '.')
