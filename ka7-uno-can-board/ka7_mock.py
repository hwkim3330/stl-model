#!/usr/bin/env python3
"""The KA7_UNO REV1 board as a solid, from ka7_uno_rev1.json. No DXF needed.

    python3 ka7_mock.py        # -> ka7_uno_rev1.stl, and prints what it built

A block per component, at the position the fabrication DXF puts it and at a
height guessed from its footprint - see extract_ka7.py for how the guess is made
and why it has to be one. Used by ../acrylic-frame/assembly.py so the frame's
preview shows the real board rather than a featureless slab.
"""
import json
import os

import trimesh
from trimesh.creation import box, cylinder

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, 'ka7_uno_rev1.json')))

PCB_T = 1.6
PCB = (0.09, 0.36, 0.20)
COL = {'connector': (0.13, 0.14, 0.16), 'large': (0.16, 0.17, 0.20),
       'ic': (0.11, 0.11, 0.13), 'small': (0.22, 0.23, 0.26),
       'passive': (0.30, 0.31, 0.34)}

BOARD = tuple(DATA['board'])
MOUNT_HOLES = [tuple(m) for m in DATA['mount_holes']]
LABELS = [tuple(l) for l in DATA['labels']]


def bx(x0, x1, y0, y1, z0, z1):
    m = box(extents=(x1 - x0, y1 - y0, z1 - z0))
    m.apply_translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    return m


def build(z0=0.0, colors=False):
    """PCB at z0, components on top. Origin is the board's own corner."""
    parts, cols = [], []
    slab = bx(0, BOARD[0], 0, BOARD[1], z0, z0 + PCB_T)
    holes = [cylinder(radius=DATA['mount_hole_d'] / 2, height=PCB_T + 2,
                      sections=24) for _ in MOUNT_HOLES]
    for h, (x, y) in zip(holes, MOUNT_HOLES):
        h.apply_translation((x, y, z0 + PCB_T / 2))
    parts.append(trimesh.boolean.difference([slab] + holes, engine='manifold'))
    cols.append(PCB)
    for c in DATA['components']:
        parts.append(bx(c['x'] - c['w'] / 2, c['x'] + c['w'] / 2,
                        c['y'] - c['h'] / 2, c['y'] + c['h'] / 2,
                        z0 + PCB_T, z0 + PCB_T + c['z']))
        cols.append(COL[c['kind']])
    if not colors:
        return trimesh.util.concatenate(parts)
    return parts, cols


def top(z0=0.0):
    return z0 + PCB_T + max(c['z'] for c in DATA['components'])


if __name__ == '__main__':
    m = build()
    out = os.path.join(HERE, 'ka7_uno_rev1.stl')
    m.export(out)
    e = m.bounds[1] - m.bounds[0]
    print(f"{os.path.basename(out)}  {e[0]:.1f} x {e[1]:.1f} x {e[2]:.1f} mm  "
          f"{len(m.faces)} faces")
    print(f"  {len(DATA['components'])} components, tallest {top():.1f} mm "
          f"over the plate it sits on")
    import collections
    for k, n in collections.Counter(c['kind'] for c in DATA['components']).most_common():
        z = max(c['z'] for c in DATA['components'] if c['kind'] == k)
        print(f"    {k:10s} {n:3d}   up to {z:4.1f} mm")
    print(f"  {len(LABELS)} silkscreen labels, e.g. "
          f"{', '.join(l[0] for l in LABELS[:6])}")
