#!/usr/bin/env python3
"""
EVB-LAN9692-LM (EV09P11A) enclosure generator.

Two printable parts:
  lan9692_tray.stl  - base tray: perforated floor, side walls with PCB support
                      rails, 8 screw standoffs, 4 corner posts, feet
  lan9692_lid.stl   - vented top plate that screws onto the corner posts

Board data source: EVB-LAN9692-LM Hardware User's Guide DS50003848B
  - A.1 Dimension: "The board dimensions are 214 x 150 mm"
  - A.2 PCB Layers: 4 layers
Mounting hole positions were measured off Figure A-1 (board outline) by
rasterising page 52 at 600 dpi, fitting the PCB edge rectangle and scaling it
to the stated 214 x 150 mm. All 8 pads measure 5.74 mm +/- 0.01 mm, so they
are the same feature (M3 mounting holes). Expected accuracy ~ +/-0.3 mm,
hence the generous pilot/clearance holes.

Both long edges of the board carry connectors (7x MATEnet + 4x SFP+ on the
front edge, RJ45 / USB-C / 12 V jack / SMA / OCuLink on the rear edge), so the
tray is deliberately open at both Y ends: no connector cut-outs to get wrong,
and much less material to pay for.

Requires: trimesh, manifold3d, numpy
    pip3 install --break-system-packages trimesh manifold3d
"""

import numpy as np
import trimesh
from trimesh.creation import box, cylinder

# --------------------------------------------------------------------------
# Parameters (mm)
# --------------------------------------------------------------------------
BW, BH = 214.0, 150.0        # PCB outline, per DS50003848B A.1
PCB_T = 1.535                # PCB thickness, per DS50003848B

FIT = 0.4                    # clearance between PCB edge and wall
WALL = 3.0                   # side wall thickness
FLOOR_T = 2.0                # floor plate thickness
STANDOFF_H = 8.0             # gap under the PCB
WALL_H = 14.0                # side wall height above the floor
RAIL_IN = 1.6                # how far the PCB support ledge reaches inboard
INNER_H = 26.0               # clearance above the PCB. Per the Figure 4-1/4-2
                             # board photos the tallest parts are the vertical
                             # expansion header, the red DC/DC modules and the
                             # SMA jacks - all comfortably under 20 mm.
LID_T = 2.0
FOOT_D, FOOT_H = 16.0, 2.5

POST_D = 10.0                # corner posts carrying the lid
POST_OFF = 5.0               # post centre, outboard of the board corner
SCREW_PILOT = 2.9            # M3 thread-forming pilot in plastic
SCREW_CLEAR = 3.4            # M3 clearance in the lid
BOSS_D = 7.0                 # PCB standoff outer diameter

VENT_CELL = 16.0             # lightening / vent grid
VENT_RIB = 4.5
VENT_MARGIN = 3.5            # keep-out from part outline
RIB_W, RIB_H = 3.0, 5.0      # lid stiffening ribs

MAKE_LID = True

# Mounting holes, origin = PCB bottom-left corner (X right, Y up).
# Measured from Figure A-1; see module docstring.
HOLES = [
    (3.68, 146.45),
    (102.01, 146.45),
    (210.53, 146.46),
    (205.88, 129.44),
    (205.88, 71.38),
    (209.50, 51.83),
    (133.87, 51.53),
    (3.68, 24.82),
]

# --------------------------------------------------------------------------
# Derived geometry
# --------------------------------------------------------------------------
Z_FLOOR = FLOOR_T                    # top face of the floor
Z_PCB = Z_FLOOR + STANDOFF_H         # bottom face of the PCB
POST_H = STANDOFF_H + PCB_T + INNER_H
Z_LID = Z_FLOOR + POST_H             # underside of the lid

WX0, WX1 = -FIT - WALL, BW + FIT + WALL      # outer face of the side walls
PLATE_Y0, PLATE_Y1 = -3.0, BH + 3.0
POSTS = [(-POST_OFF, -POST_OFF), (BW + POST_OFF, -POST_OFF),
         (-POST_OFF, BH + POST_OFF), (BW + POST_OFF, BH + POST_OFF)]
PAD = POST_D / 2 + 1.5               # corner pad half-size under each post


def bx(x0, x1, y0, y1, z0, z1):
    """Axis-aligned box from two corners."""
    m = box(extents=(x1 - x0, y1 - y0, z1 - z0))
    m.apply_translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    return m


def cyl(d, z0, z1, x, y, sections=64):
    m = cylinder(radius=d / 2, height=z1 - z0, sections=sections)
    m.apply_translation((x, y, (z0 + z1) / 2))
    return m


def union(parts):
    return trimesh.boolean.union(parts, engine='manifold')


def difference(a, cutters):
    return trimesh.boolean.difference([a] + cutters, engine='manifold')


def plate_solid(z0, z1):
    """Footprint shared by the floor and the lid: main plate + 4 corner pads."""
    parts = [bx(WX0, WX1, PLATE_Y0, PLATE_Y1, z0, z1)]
    for px, py in POSTS:
        parts.append(bx(px - PAD, px + PAD, py - PAD, py + PAD, z0, z1))
    return union(parts)


def vent_cutters(z0, z1, keepouts):
    """Grid of square holes, skipping cells that clash with anything solid.

    keepouts: list of (x, y, r) circles the grid must avoid.
    """
    cuts = []
    nx = int((WX1 - WX0) // (VENT_CELL + VENT_RIB))
    ny = int((PLATE_Y1 - PLATE_Y0) // (VENT_CELL + VENT_RIB))
    span_x = nx * VENT_CELL + (nx - 1) * VENT_RIB
    span_y = ny * VENT_CELL + (ny - 1) * VENT_RIB
    ox = (WX0 + WX1) / 2 - span_x / 2
    oy = (PLATE_Y0 + PLATE_Y1) / 2 - span_y / 2
    for i in range(nx):
        for j in range(ny):
            x0 = ox + i * (VENT_CELL + VENT_RIB)
            y0 = oy + j * (VENT_CELL + VENT_RIB)
            x1, y1 = x0 + VENT_CELL, y0 + VENT_CELL
            if (x0 < WX0 + VENT_MARGIN or x1 > WX1 - VENT_MARGIN
                    or y0 < PLATE_Y0 + VENT_MARGIN or y1 > PLATE_Y1 - VENT_MARGIN):
                continue
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            half = VENT_CELL / 2 * np.sqrt(2)
            if any(np.hypot(cx - kx, cy - ky) < kr + half for kx, ky, kr in keepouts):
                continue
            cuts.append(bx(x0, x1, y0, y1, z0 - 1, z1 + 1))
    return cuts


def build_tray():
    solids = [plate_solid(0.0, Z_FLOOR)]

    # side walls (X sides only - both Y ends stay open for the connectors)
    solids.append(bx(WX0, -FIT, PLATE_Y0, PLATE_Y1, Z_FLOOR, Z_FLOOR + WALL_H))
    solids.append(bx(BW + FIT, WX1, PLATE_Y0, PLATE_Y1, Z_FLOOR, Z_FLOOR + WALL_H))

    # PCB support rails: the wall base thickened inboard up to standoff height
    solids.append(bx(-FIT, RAIL_IN, 0, BH, Z_FLOOR, Z_PCB))
    solids.append(bx(BW - RAIL_IN, BW + FIT, 0, BH, Z_FLOOR, Z_PCB))

    # screw standoffs under the 8 PCB mounting holes
    for hx, hy in HOLES:
        solids.append(cyl(BOSS_D, Z_FLOOR - 0.1, Z_PCB, hx, hy))

    # corner posts for the lid
    for px, py in POSTS:
        solids.append(cyl(POST_D, Z_FLOOR - 0.1, Z_FLOOR + POST_H, px, py))

    # feet
    for fx, fy in [(4, 4), (BW - 4, 4), (4, BH - 4), (BW - 4, BH - 4)]:
        solids.append(cyl(FOOT_D, -FOOT_H, 0.5, fx, fy))

    tray = union(solids)

    keepouts = [(hx, hy, BOSS_D / 2 + 2.5) for hx, hy in HOLES]
    keepouts += [(px, py, POST_D / 2 + 3.0) for px, py in POSTS]
    keepouts += [(fx, fy, FOOT_D / 2 + 2.0)
                 for fx, fy in [(4, 4), (BW - 4, 4), (4, BH - 4), (BW - 4, BH - 4)]]
    cuts = vent_cutters(-FOOT_H - 1, Z_FLOOR, keepouts)

    # pilot holes: PCB standoffs and lid posts
    for hx, hy in HOLES:
        cuts.append(cyl(SCREW_PILOT, Z_PCB - 7.0, Z_PCB + 1, hx, hy, sections=32))
    for px, py in POSTS:
        cuts.append(cyl(SCREW_PILOT, Z_FLOOR + POST_H - 9.0,
                        Z_FLOOR + POST_H + 1, px, py, sections=32))

    return difference(tray, cuts)


def build_lid():
    parts = [plate_solid(0.0, LID_T)]
    # stiffening ribs on top, sitting on solid bands of the vent grid so they
    # are supported over their whole length
    for ry in lid_rib_rows():
        parts.append(bx(WX0 + 2, WX1 - 2, ry - RIB_W / 2, ry + RIB_W / 2,
                        LID_T - 0.1, LID_T + RIB_H))
    lid = union(parts)

    keepouts = [(px, py, POST_D / 2 + 3.0) for px, py in POSTS]
    cuts = vent_cutters(-1, LID_T + RIB_H + 1, keepouts)
    for px, py in POSTS:
        cuts.append(cyl(SCREW_CLEAR, -1, LID_T + 1, px, py, sections=32))
    return difference(lid, cuts)


def lid_rib_rows():
    """Y centres of the solid bands between vent rows, at both ends and middle."""
    ny = int((PLATE_Y1 - PLATE_Y0) // (VENT_CELL + VENT_RIB))
    span_y = ny * VENT_CELL + (ny - 1) * VENT_RIB
    oy = (PLATE_Y0 + PLATE_Y1) / 2 - span_y / 2
    bands = [oy + i * (VENT_CELL + VENT_RIB) + VENT_CELL + VENT_RIB / 2
             for i in range(ny - 1)]
    return [bands[0], bands[len(bands) // 2], bands[-1]]


def report(name, mesh):
    ext = mesh.bounds[1] - mesh.bounds[0]
    print(f"{name:22s} {ext[0]:6.1f} x {ext[1]:6.1f} x {ext[2]:5.1f} mm   "
          f"{mesh.volume / 1000:6.1f} cm3   watertight={mesh.is_watertight}")


if __name__ == '__main__':
    import os
    out = os.path.dirname(os.path.abspath(__file__))

    tray = build_tray()
    tray.export(os.path.join(out, 'lan9692_tray.stl'))
    report('lan9692_tray.stl', tray)

    if MAKE_LID:
        lid = build_lid()
        lid.export(os.path.join(out, 'lan9692_lid.stl'))
        report('lan9692_lid.stl', lid)
        print(f"{'total':22s} {'':29s}"
              f"{(tray.volume + lid.volume) / 1000:6.1f} cm3")

    print(f"\nassembled height: {Z_LID + LID_T:.1f} mm "
          f"(floor {FLOOR_T} + standoff {STANDOFF_H} + PCB {PCB_T} "
          f"+ clearance {INNER_H} + lid {LID_T})")
