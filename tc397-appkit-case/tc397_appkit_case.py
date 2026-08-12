#!/usr/bin/env python3
"""AURIX Application Kit TC3X7 (TC397/TC387 TFT kits) tray + vented lid.

Board data read out of Infineon's *Application Kit Manual TC3X7 V2.0*,
figure 7-7 "Dimensioning (mm)", which the manual says is "valid for all
Application Kits". The manual is public:

  https://www.infineon.com/assets/row/public/documents/10/44/infineon-applicationkitmanual-tc3x7-usermanual-en.pdf

The Gerbers are not public - Infineon gates board design files behind product
registration - so the figure was measured instead: the PCB outline in it is a
1476 x 1476 px square at 300 dpi, i.e. 14.76 px/mm against the stated
100 x 100 mm, and every feature below was read off that scale and cross-checked
against the drawing's own dimension chain.

  outline        100 x 100 mm                    (manual, "100mm x 100mm")
  mounting       2 x Ø6 mm pads at (11, 4) and (89, 4), origin bottom-left.
                 The dimension chain carries 11, 89 and 4 explicitly. The two
                 top corners have no mounting hole - only connectors.
  side headers   2x20-ish, both edges, full height:
                   left  x 2.87..5.41, y 2.70..94.95
                   right x 94.5..97.0, y 2.68..93.23
  port edge      y = 100 carries POWER, USB, RJ45, CAN, LIN, SD-card, X204

So: walls on three sides, the y = 100 port edge left open, real M3 standoffs on
the two holes that exist, a shelf carrying the rest, and two lid slots for the
side headers.

    python3 tc397_appkit_case.py

Requires: trimesh, manifold3d.
"""
import numpy as np
import trimesh
from trimesh.creation import box, cylinder

# --------------------------------------------------------------------------
BW, BH = 100.0, 100.0
CORNER_R = 2.0               # assumed
PCB_T = 1.6                  # not stated in the manual

# measured off figure 7-7
HOLES = [(11.0, 4.0), (89.0, 4.0)]
HOLE_PAD = 6.0
HEADERS = [dict(name='left header', x=(2.87, 5.41), y=(2.70, 94.95)),
           dict(name='right header', x=(94.50, 97.00), y=(2.68, 93.23))]
HDR_MARGIN = 1.6             # slot clearance around each header

FIT = 0.8
WALL = 2.6
FLOOR_T = 2.2
STANDOFF_H = 8.0
LEDGE_W = 1.6
INNER_H = 24.0               # above the PCB; the TFT and the headers are the
                             # tall parts and the manual gives no heights
LID_T = 2.2
BOSS_D = 7.0
POST_D, POST_OFF = 9.0, 5.0
SCREW_PILOT, SCREW_CLEAR = 2.9, 3.4
FOOT_D, FOOT_H = 12.0, 2.5
VENT_CELL, VENT_RIB, VENT_MARGIN = 13.0, 4.5, 3.5

DECK_HOLES = dict(pitch=45.0, d=3.4)   # matches DECK in lan9692_box.py

Z_FLOOR = FLOOR_T
Z_PCB = Z_FLOOR + STANDOFF_H
Z_TOP = Z_PCB + PCB_T
POST_H = STANDOFF_H + PCB_T + INNER_H
Z_LID = Z_FLOOR + POST_H

WX0, WX1 = -FIT - WALL, BW + FIT + WALL
PLATE_Y0, PLATE_Y1 = -FIT - WALL, BH + 2.5
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
    r = CORNER_R + grow
    parts = [bx(-grow, BW + grow, CORNER_R - grow, BH - CORNER_R + grow, z0, z1),
             bx(CORNER_R - grow, BW - CORNER_R + grow, -grow, BH + grow, z0, z1)]
    for cx, cy in ((CORNER_R, CORNER_R), (BW - CORNER_R, CORNER_R),
                   (CORNER_R, BH - CORNER_R), (BW - CORNER_R, BH - CORNER_R)):
        parts.append(cyl(2 * r, z0, z1, cx, cy))
    return union(parts)


def shelf(z0, z1):
    """Perimeter ledge, minus the strips the side headers sit over."""
    ring = difference(board_plate(FIT, z0, z1),
                      [board_plate(FIT - LEDGE_W, z0 - 1, z1 + 1)])
    return ring


def deck_points():
    h = DECK_HOLES['pitch'] / 2
    return [(BW / 2 + sx * h, BH / 2 + sy * h)
            for sx in (-1, 1) for sy in (-1, 1)]


def header_slots(z0, z1):
    cuts = []
    for h in HEADERS:
        cuts.append(bx(h['x'][0] - HDR_MARGIN, h['x'][1] + HDR_MARGIN,
                       h['y'][0] - HDR_MARGIN, h['y'][1] + HDR_MARGIN, z0, z1))
    return cuts


def vents(z0, z1, keepouts, avoid=()):
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
            if any(not (x1 < a[0] or x0 > a[1] or y1 < a[2] or y0 > a[3])
                   for a in avoid):
                continue
            cuts.append(bx(x0, x1, y0, y1, z0, z1))
    return cuts


def build_tray():
    solids = [bx(WX0, WX1, PLATE_Y0, PLATE_Y1, 0, Z_FLOOR)]
    for x0, x1 in ((WX0, -FIT), (BW + FIT, WX1)):                 # side walls
        solids.append(bx(x0, x1, PLATE_Y0, PLATE_Y1, Z_FLOOR, Z_FLOOR + POST_H))
    solids.append(bx(WX0, WX1, PLATE_Y0, -FIT, Z_FLOOR, Z_FLOOR + POST_H))  # back
    solids.append(shelf(Z_FLOOR, Z_PCB))
    for hx, hy in HOLES:                                          # real standoffs
        solids.append(cyl(BOSS_D, Z_FLOOR - 0.1, Z_PCB, hx, hy))
    for px, py in POSTS:
        solids.append(cyl(POST_D, Z_FLOOR - 0.1, Z_FLOOR + POST_H, px, py))
    for fx, fy in FEET:
        solids.append(cyl(FOOT_D, -FOOT_H, 0.5, fx, fy))
    tray = union(solids)

    keep = [(px, py, POST_D / 2 + 3.0) for px, py in POSTS]
    keep += [(fx, fy, FOOT_D / 2 + 2.0) for fx, fy in FEET]
    keep += [(hx, hy, BOSS_D / 2 + 2.5) for hx, hy in HOLES]
    keep += [(dx, dy, DECK_HOLES['d'] / 2 + 4.0) for dx, dy in deck_points()]
    cuts = vents(-FOOT_H - 1, Z_FLOOR, keep)
    for hx, hy in HOLES:
        cuts.append(cyl(SCREW_PILOT, Z_PCB - 7.0, Z_PCB + 1, hx, hy, sections=32))
    for px, py in POSTS:
        cuts.append(cyl(SCREW_PILOT, Z_FLOOR + POST_H - 9.0, Z_FLOOR + POST_H + 1,
                        px, py, sections=32))
    for dx, dy in deck_points():
        cuts.append(cyl(DECK_HOLES['d'], -FOOT_H - 1, Z_FLOOR + 1, dx, dy,
                        sections=32))
    return difference(tray, cuts)


def build_lid():
    parts = [bx(WX0, WX1, PLATE_Y0, PLATE_Y1, 0, LID_T)]
    for px, py in POSTS:
        parts.append(bx(px - PAD, px + PAD, py - PAD, py + PAD, 0, LID_T))
    lid = union(parts)
    avoid = [(h['x'][0] - HDR_MARGIN - 2, h['x'][1] + HDR_MARGIN + 2,
              h['y'][0] - HDR_MARGIN - 2, h['y'][1] + HDR_MARGIN + 2)
             for h in HEADERS]
    keep = [(px, py, POST_D / 2 + 3.0) for px, py in POSTS]
    cuts = header_slots(-1, LID_T + 1) + vents(-1, LID_T + 1, keep, avoid)
    for px, py in POSTS:
        cuts.append(cyl(SCREW_CLEAR, -1, LID_T + 1, px, py, sections=32))
    return difference(lid, cuts)


def report(n, m):
    e = m.bounds[1] - m.bounds[0]
    print(f"  {n:26s} {e[0]:6.1f} x {e[1]:6.1f} x {e[2]:5.1f} mm  "
          f"{m.volume / 1000:6.2f} cm3  watertight={m.is_watertight}")


if __name__ == '__main__':
    tray, lid = build_tray(), build_lid()
    tray.export('tc397_appkit_tray.stl')
    lid.export('tc397_appkit_lid.stl')
    report('tc397_appkit_tray.stl', tray)
    report('tc397_appkit_lid.stl', lid)
    print(f"\n  board       {BW:.0f} x {BH:.0f} mm, standoffs at "
          f"{', '.join(f'({x:.0f},{y:.0f})' for x, y in HOLES)}")
    for h in HEADERS:
        print(f"  {h['name']:13s} slot {h['x'][1] - h['x'][0] + 2 * HDR_MARGIN:5.2f} x "
              f"{h['y'][1] - h['y'][0] + 2 * HDR_MARGIN:6.2f} mm")
    print(f"  open edge   y = {BH:.0f} (POWER, USB, RJ45, CAN, LIN, SD)")
    print(f"  assembled   {WX1 - WX0:.1f} x {PLATE_Y1 - PLATE_Y0:.1f} x "
          f"{Z_LID + LID_T:.1f} mm")
