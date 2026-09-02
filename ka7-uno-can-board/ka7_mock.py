#!/usr/bin/env python3
"""The KA7_UNO REV1 board as a solid, from ka7_uno_rev1.json. No DXF needed.

    python3 ka7_mock.py        # -> ka7_uno_rev1.stl + four coloured renders

Everything geometric here is the board's own fabrication data:

  outline       the BOARD_OUTLINE polyline, arcs included - it is not a plain
                rectangle, there is a 0.75 x 5.6 mm notch in the right edge with
                two 90 degree rounded corners
  holes         all 88 drilled holes, cut through the slab at their real Ø
  pads          928 of them, laid on the copper faces
  silkscreen    1436 segments, on the top face
  components    206, positions exact

The only guessed number is component HEIGHT, because no PCB format carries it -
see extract_ka7.py for how each one is inferred and from what.
"""
import json
import math
import os

import numpy as np
import trimesh
from shapely import geometry
from trimesh.creation import extrude_polygon

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, 'ka7_uno_rev1.json')))

PCB_T = 1.6
PAD_T = 0.05          # copper proud of the solder mask
SILK_T = 0.02
SILK_W = 0.16

# A board reads as a board because of its colours, not its outline.
SOLDERMASK = (0.055, 0.30, 0.16)
COPPER = (0.83, 0.68, 0.32)
SILK = (0.94, 0.95, 0.94)
# Connectors and headers get their own hues rather than another near-black,
# because on the first pass they were the same colour as the ICs and the same
# height as the passives, and disappeared into the board.
BODY = {'connector': (0.16, 0.20, 0.30),      # terminal blocks, the T1S bank
        'header': (0.42, 0.40, 0.20),         # pin rows and jumper blocks
        'large': (0.14, 0.15, 0.17),
        'ic': (0.07, 0.07, 0.08),
        'small': (0.24, 0.25, 0.28),
        'passive': (0.34, 0.31, 0.28)}

BOARD = tuple(DATA['board'])
MOUNT_HOLES = [tuple(m) for m in DATA['mount_holes']]
LABELS = [tuple(l) for l in DATA['labels']]


def outline_polygon(arc_seg=8):
    """The board outline as a shapely polygon, bulges expanded into arcs.

    A DXF bulge is tan(theta/4) for the arc leaving that vertex, signed by
    direction. Two of this board's ten vertices carry one.
    """
    v = DATA['outline']
    pts = []
    for i, (x, y, b) in enumerate(v):
        pts.append((x, y))
        if not b:
            continue
        x2, y2, _ = v[(i + 1) % len(v)]
        theta = 4 * math.atan(b)
        chord = math.hypot(x2 - x, y2 - y)
        r = chord / (2 * math.sin(theta / 2))
        # centre is off the chord midpoint by the sagitta complement
        mx, my = (x + x2) / 2, (y + y2) / 2
        d = math.sqrt(max(r * r - (chord / 2) ** 2, 0.0))
        ux, uy = -(y2 - y) / chord, (x2 - x) / chord
        cx, cy = mx - ux * d * np.sign(b), my - uy * d * np.sign(b)
        a0 = math.atan2(y - cy, x - cx)
        for k in range(1, arc_seg):
            a = a0 + theta * k / arc_seg
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return geometry.Polygon(pts)


def bx(x0, x1, y0, y1, z0, z1):
    m = trimesh.creation.box(extents=(x1 - x0, y1 - y0, z1 - z0))
    m.apply_translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    return m


def slab():
    """The PCB itself: real outline, every drilled hole cut through it."""
    poly = outline_polygon()
    for hx, hy, hd in DATA['holes']:
        poly = poly.difference(geometry.Point(hx, hy).buffer(hd / 2, quad_segs=6))
    m = extrude_polygon(poly, PCB_T)
    return m


def bar(x0, y0, x1, y1, w, z0, z1):
    """A thin flat bar along a segment - one silkscreen stroke."""
    L = math.hypot(x1 - x0, y1 - y0)
    m = bx(-L / 2, L / 2, -w / 2, w / 2, z0, z1)
    m.apply_transform(trimesh.transformations.rotation_matrix(
        math.atan2(y1 - y0, x1 - x0), [0, 0, 1]))
    m.apply_translation(((x0 + x1) / 2, (y0 + y1) / 2, 0))
    return m


def build(z0=0.0, colors=False, detail=True):
    """PCB at z0, everything else on top. Origin is the board's own corner.

    detail=False gives just the slab and the component bodies, which is what the
    acrylic frame's preview wants - there a board ten times the fidelity of its
    neighbours looks like a mistake.
    """
    parts, cols = [], []

    board = slab()
    board.apply_translation((0, 0, z0))
    parts.append(board)
    cols.append(SOLDERMASK)

    if detail:
        # 73 of the silkscreen segments are fab-drawing annotation sitting off
        # the board - reference text in the margin. Copper and silk only exist
        # on the board, so clip to the real outline, notch included.
        poly = outline_polygon()
        pads = [bx(x0, x1, y0, y1, z0 + PCB_T, z0 + PCB_T + PAD_T)
                for x0, x1, y0, y1 in DATA['pads']
                if poly.contains(geometry.Point((x0 + x1) / 2, (y0 + y1) / 2))]
        if pads:
            parts.append(trimesh.util.concatenate(pads))
            cols.append(COPPER)
        # BOTH endpoints, not the midpoint: the fab drawing's leader lines run
        # from a component out to its reference text in the margin, and plenty of
        # those have a midpoint still over the board.
        silk = [bar(x0, y0, x1, y1, SILK_W,
                    z0 + PCB_T + PAD_T, z0 + PCB_T + PAD_T + SILK_T)
                for x0, y0, x1, y1 in DATA['silk']
                if poly.contains(geometry.Point(x0, y0))
                and poly.contains(geometry.Point(x1, y1))]
        if silk:
            parts.append(trimesh.util.concatenate(silk))
            cols.append(SILK)

    top = z0 + PCB_T + PAD_T
    for kind in BODY:
        group = [bx(c['x'] - c['w'] / 2, c['x'] + c['w'] / 2,
                    c['y'] - c['h'] / 2, c['y'] + c['h'] / 2, top, top + c['z'])
                 for c in DATA['components'] if c['kind'] == kind]
        if group:
            parts.append(trimesh.util.concatenate(group))
            cols.append(BODY[kind])

    if not colors:
        return trimesh.util.concatenate(parts)
    return parts, cols


def top(z0=0.0):
    return z0 + PCB_T + PAD_T + max(c['z'] for c in DATA['components'])


if __name__ == '__main__':
    import sys
    sys.path.insert(0, os.path.join(HERE, '..', 'lan9692-evb-case'))
    from render_preview import render

    m = build()
    out = os.path.join(HERE, 'ka7_uno_rev1.stl')
    m.export(out)
    e = m.bounds[1] - m.bounds[0]
    print(f"{os.path.basename(out)}  {e[0]:.1f} x {e[1]:.1f} x {e[2]:.1f} mm  "
          f"{len(m.faces):,} faces")
    print(f"  outline {len(DATA['outline'])} vertices "
          f"({sum(1 for v in DATA['outline'] if v[2])} arcs), "
          f"{len(DATA['holes'])} holes cut through")
    print(f"  {len(DATA['pads'])} pads, {len(DATA['silk'])} silkscreen segments, "
          f"{len(DATA['components'])} components")
    print(f"  tallest part {top():.1f} mm over the plate it sits on")

    parts, cols = build(colors=True)
    fc = np.vstack([np.tile(c, (len(p.faces), 1)) for p, c in zip(parts, cols)])
    mesh = trimesh.util.concatenate(parts)
    for name, elev, azim in (('iso', 34, -40), ('top', 89, 0),
                             ('front', 8, 0), ('detail', 22, -70)):
        f = os.path.join(HERE, f'ka7_uno_rev1_{name}.png')
        render(mesh, elev, azim, face_colors=fc).save(f)
        print(f"  {os.path.basename(f)}")
