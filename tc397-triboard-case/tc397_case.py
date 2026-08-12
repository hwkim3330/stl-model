#!/usr/bin/env python3
"""AURIX TC397 TriBoard tray + vented lid, Eurocard 100 x 160 mm.

Same honest split as the other cases in this repo: the outline is the published
form factor, everything else that is not published is left open rather than
guessed.

  outline      100 x 160 mm, Eurocard (DIN 41494) - the form factor Infineon
               gives for the TC3x7 TriBoard
  mounting     not published in anything reachable; Infineon's board pages are
               JS-only and the Mouser/manuals mirrors of the TriBoard manual
               are blocked, so the board sits on a perimeter shelf instead of
               being screwed down
  ports        not published either, so both 160 mm edges stay fully open

If yours is an Application Kit (`..._TFT`) or the gateway kit (`..._24V_GTW`)
rather than a TriBoard, it is not a Eurocard - change BW/BH below and rerun.

    python3 tc397_case.py

Requires: trimesh, manifold3d.
"""
import numpy as np
import trimesh
from trimesh.creation import box, cylinder

# --------------------------------------------------------------------------
BW, BH = 100.0, 160.0        # Eurocard
CORNER_R = 2.0               # assumed; Eurocards are usually lightly rounded
PCB_T = 1.6

FIT = 0.8                    # board edge to wall
WALL = 2.6
FLOOR_T = 2.2
STANDOFF_H = 8.0             # under-board space
LEDGE_W = 2.0                # perimeter shelf the board rests on
WALL_H = 14.0                # short-edge walls, above the floor
INNER_H = 30.0               # above the PCB - a TriBoard carries tall headers
LID_T = 2.2
POST_D, POST_OFF = 9.0, 5.0
SCREW_PILOT, SCREW_CLEAR = 2.9, 3.4
FOOT_D, FOOT_H = 14.0, 2.5
VENT_CELL, VENT_RIB, VENT_MARGIN = 14.0, 4.5, 3.5

# Bolts onto the LAN9692 box lid - same pattern as DECK in lan9692_box.py.
DECK_HOLES = dict(pitch=45.0, d=3.4)

Z_FLOOR = FLOOR_T
Z_PCB = Z_FLOOR + STANDOFF_H
POST_H = STANDOFF_H + PCB_T + INNER_H
Z_LID = Z_FLOOR + POST_H

WX0, WX1 = -FIT - WALL, BW + FIT + WALL
PLATE_Y0, PLATE_Y1 = -2.5, BH + 2.5
POSTS = [(-POST_OFF, -POST_OFF), (BW + POST_OFF, -POST_OFF),
         (-POST_OFF, BH + POST_OFF), (BW + POST_OFF, BH + POST_OFF)]
PAD = POST_D / 2 + 1.5
FEET = ((6, 6), (BW - 6, 6), (6, BH - 6), (BW - 6, BH - 6))


def bx(x0, x1, y0, y1, z0, z1):
    m = box(extents=(x1 - x0, y1 - y0, z1 - z0))
    m.apply_translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    return m


def cyl(d, z0, z1, x, y, sections=48):
    m = cylinder(radius=d / 2, height=z1 - z0, sections=sections)
    m.apply_translation((x, y, (z0 + z1) / 2))
    return m


def union(p):
    return trimesh.boolean.union(p, engine='manifold')


def difference(a, c):
    return trimesh.boolean.difference([a] + c, engine='manifold')


def board_plate(grow, z0, z1):
    """Board outline offset by `grow`, corners rounded."""
    r = CORNER_R + grow
    parts = [bx(-grow, BW + grow, CORNER_R - grow, BH - CORNER_R + grow, z0, z1),
             bx(CORNER_R - grow, BW - CORNER_R + grow, -grow, BH + grow, z0, z1)]
    for cx, cy in ((CORNER_R, CORNER_R), (BW - CORNER_R, CORNER_R),
                   (CORNER_R, BH - CORNER_R), (BW - CORNER_R, BH - CORNER_R)):
        parts.append(cyl(2 * r, z0, z1, cx, cy))
    return union(parts)


def shelf(z0, z1):
    return difference(board_plate(FIT, z0, z1),
                      [board_plate(FIT - LEDGE_W, z0 - 1, z1 + 1)])


def plate_solid(z0, z1):
    parts = [bx(WX0, WX1, PLATE_Y0, PLATE_Y1, z0, z1)]
    for px, py in POSTS:
        parts.append(bx(px - PAD, px + PAD, py - PAD, py + PAD, z0, z1))
    return union(parts)


def deck_points():
    h = DECK_HOLES['pitch'] / 2
    return [(BW / 2 + sx * h, BH / 2 + sy * h)
            for sx in (-1, 1) for sy in (-1, 1)]


def vents(z0, z1, keepouts):
    cuts = []
    nx = int((WX1 - WX0) // (VENT_CELL + VENT_RIB))
    ny = int((PLATE_Y1 - PLATE_Y0) // (VENT_CELL + VENT_RIB))
    sx = nx * VENT_CELL + (nx - 1) * VENT_RIB
    sy = ny * VENT_CELL + (ny - 1) * VENT_RIB
    ox, oy = (WX0 + WX1) / 2 - sx / 2, (PLATE_Y0 + PLATE_Y1) / 2 - sy / 2
    half = VENT_CELL / 2 * np.sqrt(2)
    for i in range(nx):
        for j in range(ny):
            x0 = ox + i * (VENT_CELL + VENT_RIB)
            y0 = oy + j * (VENT_CELL + VENT_RIB)
            x1, y1 = x0 + VENT_CELL, y0 + VENT_CELL
            if (x0 < WX0 + VENT_MARGIN or x1 > WX1 - VENT_MARGIN
                    or y0 < PLATE_Y0 + VENT_MARGIN or y1 > PLATE_Y1 - VENT_MARGIN):
                continue
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            if any(np.hypot(cx - kx, cy - ky) < kr + half for kx, ky, kr in keepouts):
                continue
            cuts.append(bx(x0, x1, y0, y1, z0, z1))
    return cuts


def build_tray():
    solids = [plate_solid(0.0, Z_FLOOR)]
    for x0, x1 in ((WX0, -FIT), (BW + FIT, WX1)):        # 100 mm edges only
        solids.append(bx(x0, x1, PLATE_Y0, PLATE_Y1, Z_FLOOR, Z_FLOOR + WALL_H))
    solids.append(shelf(Z_FLOOR, Z_PCB))
    for px, py in POSTS:
        solids.append(cyl(POST_D, Z_FLOOR - 0.1, Z_FLOOR + POST_H, px, py))
    for fx, fy in FEET:
        solids.append(cyl(FOOT_D, -FOOT_H, 0.5, fx, fy))
    tray = union(solids)

    keep = [(px, py, POST_D / 2 + 3.0) for px, py in POSTS]
    keep += [(fx, fy, FOOT_D / 2 + 2.0) for fx, fy in FEET]
    if DECK_HOLES:
        keep += [(dx, dy, DECK_HOLES['d'] / 2 + 4.0) for dx, dy in deck_points()]
    cuts = vents(-FOOT_H - 1, Z_FLOOR, keep)
    for px, py in POSTS:
        cuts.append(cyl(SCREW_PILOT, Z_FLOOR + POST_H - 9.0, Z_FLOOR + POST_H + 1,
                        px, py, sections=32))
    if DECK_HOLES:
        for dx, dy in deck_points():
            cuts.append(cyl(DECK_HOLES['d'], -FOOT_H - 1, Z_FLOOR + 1, dx, dy,
                            sections=32))
    return difference(tray, cuts)


def build_lid():
    lid = plate_solid(0.0, LID_T)
    pads = [cyl(8.0, -(Z_LID - Z_PCB - PCB_T - 0.3), 0.1, cx, cy)
            for cx, cy in ((CORNER_R + 2, CORNER_R + 2), (BW - CORNER_R - 2, CORNER_R + 2),
                           (CORNER_R + 2, BH - CORNER_R - 2),
                           (BW - CORNER_R - 2, BH - CORNER_R - 2))]
    keep = [(px, py, POST_D / 2 + 3.0) for px, py in POSTS]
    cuts = vents(-1, LID_T + 1, keep)
    for px, py in POSTS:
        cuts.append(cyl(SCREW_CLEAR, -1, LID_T + 1, px, py, sections=32))
    return difference(union([lid] + pads), cuts)


def report(n, m):
    e = m.bounds[1] - m.bounds[0]
    print(f"  {n:22s} {e[0]:6.1f} x {e[1]:6.1f} x {e[2]:5.1f} mm  "
          f"{m.volume / 1000:6.2f} cm3  watertight={m.is_watertight}")


if __name__ == '__main__':
    tray, lid = build_tray(), build_lid()
    tray.export('tc397_tray.stl')
    lid.export('tc397_lid.stl')
    report('tc397_tray.stl', tray)
    report('tc397_lid.stl', lid)
    print(f"\n  board      {BW:.0f} x {BH:.0f} mm Eurocard, corner R{CORNER_R}")
    print(f"  assembled  {WX1 - WX0 + 2 * (PAD - WALL - FIT):.1f} x "
          f"{PLATE_Y1 - PLATE_Y0:.1f} x {Z_LID + LID_T:.1f} mm")
    if DECK_HOLES:
        print(f"  deck holes 4 x Ø{DECK_HOLES['d']} on a {DECK_HOLES['pitch']:.0f} mm "
              f"square, matching lan9692_box.py DECK")
