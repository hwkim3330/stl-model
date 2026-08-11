#!/usr/bin/env python3
"""Fully closed EVB-LAN9692-LM box with matched port cut-outs.

Four printed parts:
  lan9692_box_tray.stl   floor, full-height side walls, standoffs, lid bosses,
                         and the channels the end panels slide into
  lan9692_box_front.stl  MATEnet slot + 4 SFP+ windows
  lan9692_box_rear.stl   RJ45, USB-C, OCuLink, DC jack, power switch, reset
  lan9692_box_lid.stl    vented top, screws down and traps both panels

The end panels are separate parts on purpose. Connector X/Y comes from the
released pick-and-place file and is exact; connector *heights* are not in any
released file, so those come from the part datasheets and standards listed in
PORTS below. If one window turns out wrong, a panel is a ~12 cm3 reprint
instead of the whole box.

Port geometry, all from 02-01022-R1_PNP.txt (designator, footprint, centre):

  7x J12/J11A-F  CON_2304372-9      TE MATEnet header, 19.05 mm pitch
  4x X1A-D       CON_SFP_CAGE_U77-A111X
  1x J33         CON_JACK_RJ45_L829-1J1T-43
  1x J30         CON_USB-2.0_TYPE-C_USB4105_SMD
  1x J21         CON_OCULINK_SMD_RA_AMP_G14A42121B12HR
  1x J23         CON_JACK_PWR_2.5MM_PJ-002BH
  1x SW3         SW_SLIDE_TH_ESW_500SSP1S1M6QEA
  1x SW2         SW_TACT_TH_RA_1825027-5

Requires: trimesh, manifold3d.
"""
import numpy as np
import trimesh
from trimesh.creation import box, cylinder

from lan9692_case import BW, BH, HOLES, PCB_T

# --------------------------------------------------------------------------
# Parameters (mm)
# --------------------------------------------------------------------------
FIT = 1.2                # board edge to side-wall inner face
WALL = 3.0
FLOOR_T = 2.0
STANDOFF_H = 8.0         # under-board space
INNER_H = 26.0           # above the PCB. Not derivable from released data;
                         # see README. The lid depends on it, nothing else.
LID_T = 2.0
PANEL_T = 2.4
PANEL_GAP = 0.5          # board edge to panel inner face
CHANNEL_D = 2.0          # how far the panel slides into each side wall
CHANNEL_SLOP = 0.35      # per side, on the channel width
RABBET = 0.8             # how far the panel seats into the floor. Kept under
                         # FLOOR_T - 1.0 so the floor stays a printable wall.
RAIL_IN = 1.6            # PCB support ledge (bottom paste is clear to 1.6)
BOSS_D = 7.0
SCREW_PILOT = 2.9
SCREW_CLEAR = 3.4
LID_BOSS_D = 9.0         # local outward thickening of the side wall
LID_BOSS_L = 16.0
FOOT_D, FOOT_H = 16.0, 2.5
VENTS = True             # False -> sealed box, port windows only. See README:
                         # the board budgets 12 V @ 4.1 A, so a sealed plastic
                         # box has no way to shed that.
VENT_CELL, VENT_RIB, VENT_MARGIN = 16.0, 4.5, 3.5
RIB_W, RIB_H = 3.0, 5.0

# --------------------------------------------------------------------------
# Derived
# --------------------------------------------------------------------------
Z_FLOOR = FLOOR_T
Z_PCB = Z_FLOOR + STANDOFF_H          # PCB underside
Z_TOP = Z_PCB + PCB_T                 # PCB top face - all port heights ride on this
Z_LID = Z_TOP + INNER_H               # lid underside

WX0, WX1 = -FIT - WALL, BW + FIT + WALL        # side walls, outer faces
PX0, PX1 = -FIT - CHANNEL_D, BW + FIT + CHANNEL_D   # panel width (into channels)
FY1 = -PANEL_GAP                      # front panel inner face
FY0 = FY1 - PANEL_T
RY0 = BH + PANEL_GAP                  # rear panel inner face
RY1 = RY0 + PANEL_T
LID_Y = (FY0, RY1)
Z_PANEL0 = Z_FLOOR - RABBET           # panels seat in a floor rabbet
BOSS_Y = (FY1 + LID_BOSS_L / 2 + 2, RY0 - LID_BOSS_L / 2 - 2)  # clear of the
                                    # panel channels

# Port windows. z is measured from the PCB top face.
#   src: where the size comes from - 'ds' datasheet, 'msa' standard, 'est' estimate
PORTS = dict(
    front=[
        # one continuous slot: 17.75 mm wide bodies on a 19.05 mm pitch leave
        # only 1.3 mm between them, so individual windows are not printable
        dict(name='MATEnet x7', x=(11.684 - 17.75 / 2 - 0.75, 125.984 + 17.75 / 2 + 0.75),
             z=(-0.5, 13.5 + 1.0), src='ds'),
        *[dict(name=f'SFP+ {c}', x=(x - 7.5, x + 7.5), z=(-0.4, 10.4), src='msa')
          for c, x in zip('ABCD', (145.6, 164.6, 183.6, 202.6))],
    ],
    rear=[
        dict(name='RJ45 J33', x=(58.803 - 8.5, 58.803 + 8.5), z=(-0.5, 14.5), src='ds'),
        dict(name='USB-C J30', x=(37.762 - 5.25, 37.762 + 5.25), z=(-0.6, 4.4),
             src='ds', relief=1.4),
        dict(name='OCuLink J21', x=(118.305 - 12.0, 118.305 + 12.0), z=(-0.5, 8.5), src='est'),
        dict(name='switch SW3', x=(188.110 - 7.0, 188.110 + 7.0), z=(-0.5, 7.0), src='est'),
    ],
)
ROUND_PORTS = dict(
    rear=[dict(name='DC jack J23', x=171.283, z=6.5, d=11.0, src='est'),
          dict(name='reset SW2', x=21.844, z=3.5, d=6.0, src='est')],
)


def bx(x0, x1, y0, y1, z0, z1):
    m = box(extents=(x1 - x0, y1 - y0, z1 - z0))
    m.apply_translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    return m


def cyl(d, z0, z1, x, y, axis='z', sections=48):
    m = cylinder(radius=d / 2, height=z1 - z0, sections=sections)
    if axis == 'y':
        m.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
        m.apply_translation((x, (z0 + z1) / 2, y))
    else:
        m.apply_translation((x, y, (z0 + z1) / 2))
    return m


def union(parts):
    return trimesh.boolean.union(parts, engine='manifold')


def difference(a, cutters):
    return trimesh.boolean.difference([a] + cutters, engine='manifold')


def vent_grid(x0, x1, u0, u1, keepouts, thick_lo, thick_hi, plane='xy'):
    """Square vent holes over a rectangle, skipping cells near `keepouts`."""
    cuts = []
    if not VENTS:
        return cuts
    nx = max(int((x1 - x0) // (VENT_CELL + VENT_RIB)), 1)
    nu = max(int((u1 - u0) // (VENT_CELL + VENT_RIB)), 1)
    sx = nx * VENT_CELL + (nx - 1) * VENT_RIB
    su = nu * VENT_CELL + (nu - 1) * VENT_RIB
    ox, ou = (x0 + x1) / 2 - sx / 2, (u0 + u1) / 2 - su / 2
    half = VENT_CELL / 2 * np.sqrt(2)
    for i in range(nx):
        for j in range(nu):
            a0 = ox + i * (VENT_CELL + VENT_RIB)
            b0 = ou + j * (VENT_CELL + VENT_RIB)
            a1, b1 = a0 + VENT_CELL, b0 + VENT_CELL
            if (a0 < x0 + VENT_MARGIN or a1 > x1 - VENT_MARGIN
                    or b0 < u0 + VENT_MARGIN or b1 > u1 - VENT_MARGIN):
                continue
            ca, cb = (a0 + a1) / 2, (b0 + b1) / 2
            if any(np.hypot(ca - ka, cb - kb) < kr + half for ka, kb, kr in keepouts):
                continue
            if plane == 'xy':
                cuts.append(bx(a0, a1, b0, b1, thick_lo, thick_hi))
            else:  # yz, for the side walls: thickness runs along X
                cuts.append(bx(thick_lo, thick_hi, a0, a1, b0, b1))
    return cuts


def build_tray():
    solids = [bx(WX0, WX1, FY0, RY1, 0, Z_FLOOR)]                       # floor
    for x0, x1 in ((WX0, -FIT), (BW + FIT, WX1)):                       # side walls
        solids.append(bx(x0, x1, FY0, RY1, Z_FLOOR, Z_LID))
    solids.append(bx(-FIT, RAIL_IN, 0, BH, Z_FLOOR, Z_PCB))             # PCB ledges
    solids.append(bx(BW - RAIL_IN, BW + FIT, 0, BH, Z_FLOOR, Z_PCB))
    for hx, hy in HOLES:                                                # standoffs
        solids.append(cyl(BOSS_D, Z_FLOOR - 0.1, Z_PCB, hx, hy))
    for x0, x1 in ((WX0 - (LID_BOSS_D - WALL), -FIT), (BW + FIT, WX1 + (LID_BOSS_D - WALL))):
        for by in BOSS_Y:                                               # lid bosses
            solids.append(bx(x0, x1, by - LID_BOSS_L / 2, by + LID_BOSS_L / 2,
                             Z_FLOOR, Z_LID))
    for fx, fy in ((4, 4), (BW - 4, 4), (4, BH - 4), (BW - 4, BH - 4)):
        solids.append(cyl(FOOT_D, -FOOT_H, 0.5, fx, fy))                # feet
    tray = union(solids)

    cuts = []
    # panel channels in the side wall inner faces, open at the top
    for y0, y1 in ((FY0 - 1, FY1 + CHANNEL_SLOP), (RY0 - CHANNEL_SLOP, RY1 + 1)):
        for x0, x1 in ((-FIT - CHANNEL_D, -FIT), (BW + FIT, BW + FIT + CHANNEL_D)):
            cuts.append(bx(x0, x1, y0, y1, Z_PANEL0, Z_LID + 1))
    # shallow floor rabbet so the panels seat instead of standing on the floor
    cuts.append(bx(PX0, PX1, FY0 - 1, FY1 + CHANNEL_SLOP, Z_PANEL0, Z_LID + 1))
    cuts.append(bx(PX0, PX1, RY0 - CHANNEL_SLOP, RY1 + 1, Z_PANEL0, Z_LID + 1))

    keep = [(hx, hy, BOSS_D / 2 + 2.5) for hx, hy in HOLES]
    keep += [(fx, fy, FOOT_D / 2 + 2.0)
             for fx, fy in ((4, 4), (BW - 4, 4), (4, BH - 4), (BW - 4, BH - 4))]
    cuts += vent_grid(WX0, WX1, FY0, RY1, keep, -FOOT_H - 1, Z_FLOOR)
    # vent the side walls too - they are the biggest flat areas in the box
    for x0, x1 in ((WX0 - 1, -FIT + 1), (BW + FIT - 1, WX1 + 1)):
        cuts += vent_grid(0, BH, Z_FLOOR + 4, Z_LID - 4,
                          [(by, z, LID_BOSS_D) for by in BOSS_Y
                           for z in (Z_FLOOR, Z_LID)],
                          x0, x1, plane='yz')
    for hx, hy in HOLES:
        cuts.append(cyl(SCREW_PILOT, Z_PCB - 7.0, Z_PCB + 1, hx, hy, sections=32))
    for x0, x1 in ((WX0 - (LID_BOSS_D - WALL), -FIT), (BW + FIT, WX1 + (LID_BOSS_D - WALL))):
        for by in BOSS_Y:
            cuts.append(cyl(SCREW_PILOT, Z_LID - 9.0, Z_LID + 1, (x0 + x1) / 2, by, sections=32))
    return difference(tray, cuts)


def build_panel(which):
    y0, y1 = (FY0, FY1) if which == 'front' else (RY0, RY1)
    panel = bx(PX0, PX1, y0, y1, Z_PANEL0, Z_LID)
    cuts = []
    for p in PORTS[which]:
        cuts.append(bx(p['x'][0], p['x'][1], y0 - 1, y1 + 1,
                       Z_TOP + p['z'][0], Z_TOP + p['z'][1]))
        if p.get('relief'):                     # thin the panel around a recessed port
            r = p['relief']
            outer = (y0 - 1, y0 + r) if which == 'front' else (y1 - r, y1 + 1)
            cuts.append(bx(p['x'][0] - 3, p['x'][1] + 3, outer[0], outer[1],
                           Z_TOP + p['z'][0] - 2.5, Z_TOP + p['z'][1] + 2.5))
    for p in ROUND_PORTS.get(which, []):
        cuts.append(cyl(p['d'], y0 - 1, y1 + 1, p['x'], Z_TOP + p['z'], axis='y'))
    return difference(panel, cuts)


def build_lid():
    lid = bx(WX0 - (LID_BOSS_D - WALL), WX1 + (LID_BOSS_D - WALL), LID_Y[0], LID_Y[1],
             0, LID_T)
    parts = [lid]
    bands = lid_rib_rows()
    for ry in bands:
        parts.append(bx(WX0, WX1, ry - RIB_W / 2, ry + RIB_W / 2, LID_T - 0.1,
                        LID_T + RIB_H))
    lid = union(parts)
    holes = [((WX0 - (LID_BOSS_D - WALL) + -FIT) / 2, by) for by in BOSS_Y]
    holes += [((BW + FIT + WX1 + (LID_BOSS_D - WALL)) / 2, by) for by in BOSS_Y]
    keep = [(hx, hy, LID_BOSS_D) for hx, hy in holes]
    cuts = vent_grid(WX0, WX1, LID_Y[0], LID_Y[1], keep, -1, LID_T + RIB_H + 1)
    for hx, hy in holes:
        cuts.append(cyl(SCREW_CLEAR, -1, LID_T + 1, hx, hy, sections=32))
    return difference(lid, cuts)


def lid_rib_rows():
    ny = max(int((LID_Y[1] - LID_Y[0]) // (VENT_CELL + VENT_RIB)), 2)
    span = ny * VENT_CELL + (ny - 1) * VENT_RIB
    oy = (LID_Y[0] + LID_Y[1]) / 2 - span / 2
    bands = [oy + i * (VENT_CELL + VENT_RIB) + VENT_CELL + VENT_RIB / 2
             for i in range(ny - 1)]
    return [bands[0], bands[len(bands) // 2], bands[-1]]


def report(name, m):
    e = m.bounds[1] - m.bounds[0]
    print(f"  {name:24s} {e[0]:6.1f} x {e[1]:6.1f} x {e[2]:5.1f} mm  "
          f"{m.volume / 1000:6.2f} cm3  watertight={m.is_watertight}")


if __name__ == '__main__':
    import sys
    if '--solid' in sys.argv:
        VENTS = False
    prefix = 'lan9692_box_' if VENTS else 'lan9692_boxsolid_'
    print(f"{'vented' if VENTS else 'SEALED - port windows only'}\n")
    print("port windows (z from PCB top face):")
    for side in ('front', 'rear'):
        for p in PORTS[side]:
            print(f"  {side:5s} {p['name']:14s} x {p['x'][0]:7.2f}..{p['x'][1]:7.2f}"
                  f"  z {p['z'][0]:5.1f}..{p['z'][1]:5.1f}   [{p['src']}]")
        for p in ROUND_PORTS.get(side, []):
            print(f"  {side:5s} {p['name']:14s} x {p['x']:7.2f} Ø{p['d']:.1f}"
                  f"       z {p['z']:5.1f}         [{p['src']}]")
    print()
    parts = {prefix + 'tray.stl': build_tray(),
             prefix + 'front.stl': build_panel('front'),
             prefix + 'rear.stl': build_panel('rear'),
             prefix + 'lid.stl': build_lid()}
    total = 0
    for n, m in parts.items():
        m.export(n)
        report(n, m)
        total += m.volume
    print(f"  {'total':24s} {'':29s}{total / 1000:6.2f} cm3")
    print(f"\n  outside {WX1 + 2 * (LID_BOSS_D - WALL) - WX0:.1f} x {RY1 - FY0:.1f} "
          f"x {Z_LID + LID_T:.1f} mm")
