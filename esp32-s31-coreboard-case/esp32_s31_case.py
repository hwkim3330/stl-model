#!/usr/bin/env python3
"""ESP32-S31-Function-CoreBoard-1 tray + vented lid.

Outline data is exact, port data is not - see README. The two long edges are
left open so no port position has to be guessed; the only derived feature is
the lid slot for the 40-pin header.

Board data from Espressif's published drawings. The **PDF** carries more than
the DXF does - it dimensions the mounting holes and labels every port, which an
earlier version of this file wrongly reported as unpublished:

  https://dl.espressif.com/schematics/esp32-s31-function-coreboard-1-dimensions.pdf
  https://dl.espressif.com/schematics/esp32-s31-function-coreboard-1-dimensions.dxf

  outline        65.000 x 55.000 mm, corner radius 3.500 mm
                 (the DXF's straight edges run 3.5..61.5 and 3.5..51.5)
  mounting       4 holes on a dimensioned 58.00 x 48.00 rectangle, Ø5.1 pads.
                 Measured off the PDF at 600 dpi: the X and Y scales derived
                 from the two callouts agree to 0.01%, and the holes sit
                 3.25-3.41 mm in from the board edges - i.e. centred on the
                 R3.5 corner arcs, (3.5, 3.5) to (61.5, 51.5).
  header grid    pin 1 at (8.370, 53.270), 2.540 mm pitch, second row at
                 y = 50.730 -> a 2x20 header lying along the y = 55 edge
  ports          y = 0   USB-UART and USB-DBG (two USB-C)
                 x = 65  1GbE RJ45 and USB-HS (USB-A)
                 x = 0   SPK speaker header
                 y = 55  nothing but the 2x20 header

Three of the four edges carry connectors, so only the y = 55 edge gets a wall.

Requires: trimesh, manifold3d.
"""
import numpy as np
import trimesh
from trimesh.creation import box, cylinder

# --------------------------------------------------------------------------
BW, BH = 65.0, 55.0          # outline, from the dimension drawing
CORNER_R = 3.5
PCB_T = 1.6                  # not published; 1.6 is the Espressif norm

HOLES = [(3.5, 3.5), (61.5, 3.5), (3.5, 51.5), (61.5, 51.5)]
BOSS_D = 6.5                 # standoff outer diameter under each hole

FIT = 0.6                    # board edge to wall
WALL = 2.4
FLOOR_T = 2.0
STANDOFF_H = 6.0             # under-board space
WALL_H = 12.0                # back wall, above the floor
INNER_H = 20.0               # above the PCB
LID_T = 2.0
POST_D, POST_OFF = 8.0, 4.5
SCREW_PILOT, SCREW_CLEAR = 2.9, 3.4
FOOT_D, FOOT_H = 10.0, 2.0
VENT_CELL, VENT_RIB, VENT_MARGIN = 11.0, 4.0, 3.0

# Bolts this tray onto the LAN9692 box lid: same square as DECK in
# lan9692_box.py. M3 clearance through the floor, screw heads sit under the
# board in the 6 mm of standoff space. None = plain floor.
DECK_HOLES = dict(pitch=45.0, d=3.4)

# 2x20 header along the y = 55 edge, derived from the dimensioned pin grid
HDR_PIN1 = (8.370, 53.270)
HDR_PITCH = 2.54
HDR_COLS, HDR_ROWS = 20, 2
HDR_MARGIN = 1.6             # slot clearance around the header body

Z_FLOOR = FLOOR_T
Z_PCB = Z_FLOOR + STANDOFF_H
Z_TOP = Z_PCB + PCB_T
POST_H = STANDOFF_H + PCB_T + INNER_H
Z_LID = Z_FLOOR + POST_H

WX0, WX1 = -FIT - WALL, BW + FIT + WALL
PLATE_Y0, PLATE_Y1 = -2.0, BH + 2.0
POSTS = [(-POST_OFF, -POST_OFF), (BW + POST_OFF, -POST_OFF),
         (-POST_OFF, BH + POST_OFF), (BW + POST_OFF, BH + POST_OFF)]
PAD = POST_D / 2 + 1.5


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


def rounded_ring(r_in, z0, z1, grow):
    """Perimeter shelf that follows the board's rounded outline."""
    outer = rounded_plate(grow, z0, z1)
    inner = rounded_plate(grow - r_in, z0 - 1, z1 + 1)
    return difference(outer, [inner])


def rounded_plate(grow, z0, z1):
    """Board outline offset by `grow`, as a rounded rectangle."""
    r = CORNER_R + grow
    body = union([bx(-grow, BW + grow, CORNER_R - grow, BH - CORNER_R + grow, z0, z1),
                  bx(CORNER_R - grow, BW - CORNER_R + grow, -grow, BH + grow, z0, z1)])
    corners = [(CORNER_R, CORNER_R), (BW - CORNER_R, CORNER_R),
               (CORNER_R, BH - CORNER_R), (BW - CORNER_R, BH - CORNER_R)]
    return union([body] + [cyl(2 * r, z0, z1, cx, cy) for cx, cy in corners])


def plate_solid(z0, z1):
    parts = [bx(WX0, WX1, PLATE_Y0, PLATE_Y1, z0, z1)]
    for px, py in POSTS:
        parts.append(bx(px - PAD, px + PAD, py - PAD, py + PAD, z0, z1))
    return union(parts)


def header_slot(z0, z1):
    x0 = HDR_PIN1[0] - HDR_MARGIN
    x1 = HDR_PIN1[0] + (HDR_COLS - 1) * HDR_PITCH + HDR_MARGIN
    y1 = HDR_PIN1[1] + HDR_MARGIN
    y0 = HDR_PIN1[1] - (HDR_ROWS - 1) * HDR_PITCH - HDR_MARGIN
    return bx(x0, x1, y0, y1, z0, z1), (x1 - x0, y1 - y0)


def vents(z0, z1, keepouts, skip=None):
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
            if skip is not None and not (y1 < skip[0] or y0 > skip[1]):
                continue
            cuts.append(bx(x0, x1, y0, y1, z0, z1))
    return cuts


def build_tray():
    solids = [plate_solid(0.0, Z_FLOOR)]
    # one wall, on the only edge that carries no connector
    solids.append(bx(WX0, WX1, BH + FIT, PLATE_Y1, Z_FLOOR, Z_FLOOR + WALL_H))
    # real standoffs: the dimension PDF puts four holes on a 58 x 48 rectangle
    for hx, hy in HOLES:
        solids.append(cyl(BOSS_D, Z_FLOOR - 0.1, Z_PCB, hx, hy))
    for px, py in POSTS:
        solids.append(cyl(POST_D, Z_FLOOR - 0.1, Z_FLOOR + POST_H, px, py))
    for fx, fy in ((5, 5), (BW - 5, 5), (5, BH - 5), (BW - 5, BH - 5)):
        solids.append(cyl(FOOT_D, -FOOT_H, 0.5, fx, fy))
    tray = union(solids)

    keep = [(px, py, POST_D / 2 + 3.0) for px, py in POSTS]
    keep += [(fx, fy, FOOT_D / 2 + 2.0)
             for fx, fy in ((5, 5), (BW - 5, 5), (5, BH - 5), (BW - 5, BH - 5))]
    keep += [(hx, hy, BOSS_D / 2 + 2.5) for hx, hy in HOLES]
    if DECK_HOLES:
        keep += [(dx, dy, DECK_HOLES['d'] / 2 + 4.0) for dx, dy in deck_points()]
    cuts = vents(-FOOT_H - 1, Z_FLOOR, keep)
    for hx, hy in HOLES:
        cuts.append(cyl(SCREW_PILOT, Z_PCB - 5.0, Z_PCB + 1, hx, hy, sections=32))
    for px, py in POSTS:
        cuts.append(cyl(SCREW_PILOT, Z_FLOOR + POST_H - 8.0, Z_FLOOR + POST_H + 1,
                        px, py, sections=32))
    if DECK_HOLES:
        for dx, dy in deck_points():
            cuts.append(cyl(DECK_HOLES['d'], -FOOT_H - 1, Z_FLOOR + 1, dx, dy,
                            sections=32))
    return difference(tray, cuts)


def deck_points():
    h = DECK_HOLES['pitch'] / 2
    return [(BW / 2 + sx * h, BH / 2 + sy * h)
            for sx in (-1, 1) for sy in (-1, 1)]


def build_lid():
    lid = plate_solid(0.0, LID_T)
    slot, size = header_slot(-1, LID_T + 1)
    keep = [(px, py, POST_D / 2 + 3.0) for px, py in POSTS]
    cuts = [slot] + vents(-1, LID_T + 1, keep,
                          skip=(HDR_PIN1[1] - (HDR_ROWS - 1) * HDR_PITCH - HDR_MARGIN - 1,
                                HDR_PIN1[1] + HDR_MARGIN + 1))
    for px, py in POSTS:
        cuts.append(cyl(SCREW_CLEAR, -1, LID_T + 1, px, py, sections=32))
    # the board is screwed to its own standoffs now, so the lid needs no pads
    return difference(lid, cuts), size


def report(n, m):
    e = m.bounds[1] - m.bounds[0]
    print(f"  {n:26s} {e[0]:6.1f} x {e[1]:6.1f} x {e[2]:5.1f} mm  "
          f"{m.volume / 1000:5.2f} cm3  watertight={m.is_watertight}")


if __name__ == '__main__':
    tray = build_tray()
    lid, hdr = build_lid()
    tray.export('esp32_s31_tray.stl')
    lid.export('esp32_s31_lid.stl')
    report('esp32_s31_tray.stl', tray)
    report('esp32_s31_lid.stl', lid)
    print(f"\n  board       {BW} x {BH} mm, corner R{CORNER_R}")
    print(f"  header slot {hdr[0]:.2f} x {hdr[1]:.2f} mm at "
          f"x {HDR_PIN1[0] - HDR_MARGIN:.2f}, y {HDR_PIN1[1] - (HDR_ROWS - 1) * HDR_PITCH - HDR_MARGIN:.2f}")
    print(f"  assembled   {Z_LID + LID_T:.1f} mm tall")
    if DECK_HOLES:
        pts = ', '.join(f"({x:.1f},{y:.1f})" for x, y in deck_points())
        print(f"  deck holes  4 x Ø{DECK_HOLES['d']} on a "
              f"{DECK_HOLES['pitch']:.0f} mm square: {pts}")
