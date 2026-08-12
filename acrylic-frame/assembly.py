#!/usr/bin/env python3
"""Build the whole acrylic stack in 3D and check that it actually fits.

Not a printable part - it is the three plates, the standoffs, the LAN9692 with
its real parts, the fan and the ESP32-S31 case, assembled at their true heights
so the hole pattern and the clearances can be looked at and measured.

    python3 assembly.py        # -> assembly.stl, img/assembly*.png, checks

Plate geometry comes from make_plates.py, so the plates here and the DXFs sent
to the cutter cannot drift apart. The board comes from ../lan9692-evb-case/
board_mock.py, which places a block per part at its pick-and-place coordinate.
"""
import os
import sys

import numpy as np
import trimesh
from trimesh.creation import box, cylinder

HERE = os.path.dirname(os.path.abspath(__file__))
L9 = os.path.join(HERE, '..', 'lan9692-evb-case')
S31 = os.path.join(HERE, '..', 'esp32-s31-coreboard-case')
sys.path[:0] = [HERE, L9, S31]

import board_mock                      # noqa: E402
import make_plates as P                # noqa: E402
from render_preview import render      # noqa: E402

# --------------------------------------------------------------------------
# stack heights (mm)
T_A, T_B, T_C = 5.0, 5.0, 3.0          # plate thicknesses
H_BOARD = 10.0                         # board standoff, plate A -> PCB
H_AB = 45.0                            # plate A -> plate B
H_BC = 40.0                            # plate B -> plate C
FAN_THICK = 10.0

Z_A = 0.0
Z_PCB = T_A + H_BOARD                  # PCB underside
Z_B = T_A + H_AB                       # plate B underside
Z_C = Z_B + T_B + H_BC                 # plate C underside
TOTAL = Z_C + T_C

ACRYLIC = (0.62, 0.78, 0.86)
METAL = (0.55, 0.58, 0.62)
FAN_COL = (0.20, 0.21, 0.24)
CASE = (0.55, 0.60, 0.66)


def bx(x0, x1, y0, y1, z0, z1):
    m = box(extents=(x1 - x0, y1 - y0, z1 - z0))
    m.apply_translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    return m


def cyl(d, z0, z1, x, y, sections=40):
    m = cylinder(radius=d / 2, height=z1 - z0, sections=sections)
    m.apply_translation((x, y, (z0 + z1) / 2))
    return m


def slot_solid(cx, cy, length, width, z0, z1, horizontal=True):
    """Same rounded slot the DXF draws, as a solid to subtract."""
    r = width / 2
    half = max(length / 2 - r, 0.0)
    if horizontal:
        core = bx(cx - half, cx + half, cy - r, cy + r, z0, z1)
        ends = [(cx - half, cy), (cx + half, cy)]
    else:
        core = bx(cx - r, cx + r, cy - half, cy + half, z0, z1)
        ends = [(cx, cy - half), (cx, cy + half)]
    return trimesh.boolean.union(
        [core] + [cyl(width, z0, z1, x, y) for x, y in ends], engine='manifold')


def plate(kind, z0, thick):
    """3D version of the DXF plates, from the same constants."""
    body = bx(0, P.PW, 0, P.PH, z0, z0 + thick)
    cuts = [cyl(P.M3_FREE, z0 - 1, z0 + thick + 1, x, y)
            for x in (P.CORNER_INSET, P.PW - P.CORNER_INSET)
            for y in (P.CORNER_INSET, P.PH - P.CORNER_INSET)]
    if kind == 'A':
        cuts += [cyl(P.M3_FREE, z0 - 1, z0 + thick + 1,
                     P.BOARD_OFF[0] + hx, P.BOARD_OFF[1] + hy)
                 for hx, hy in P.LAN_HOLES]
    elif kind == 'B':
        cuts.append(cyl(P.FAN_BORE, z0 - 1, z0 + thick + 1, *P.FAN_C, sections=64))
        h = P.FAN_PITCH / 2
        cuts += [cyl(P.M3_FREE, z0 - 1, z0 + thick + 1,
                     P.FAN_C[0] + sx * h, P.FAN_C[1] + sy * h)
                 for sx in (-1, 1) for sy in (-1, 1)]
        for _, cx, cy in P.ZONES:
            d = P.DECK_PITCH / 2
            cuts += [slot_solid(cx + sx * d, cy + sy * d, P.SLOT_L, P.SLOT_W,
                                z0 - 1, z0 + thick + 1)
                     for sx in (-1, 1) for sy in (-1, 1)]
    else:
        for i in range(-2, 3):
            cuts.append(slot_solid(P.FAN_C[0] + i * (P.VENT_SLOT[0] + 6), P.FAN_C[1],
                                   P.VENT_SLOT[1], P.VENT_SLOT[0],
                                   z0 - 1, z0 + thick + 1, horizontal=False))
    return trimesh.boolean.difference([body] + cuts, engine='manifold')


def standoffs(z0, z1, points, d=6.0):
    return [cyl(d, z0, z1, x, y, sections=24) for x, y in points]


def corner_points():
    return [(x, y) for x in (P.CORNER_INSET, P.PW - P.CORNER_INSET)
            for y in (P.CORNER_INSET, P.PH - P.CORNER_INSET)]


def build(upto='C'):
    """upto='A' gives just plate A, its standoffs and the board - the view that
    shows whether the drilled pattern really lines up."""
    parts, cols = [], []

    def add(m, c):
        parts.append(m)
        cols.append(c)

    add(plate('A', Z_A, T_A), ACRYLIC)
    for s in standoffs(T_A, Z_PCB, [(P.BOARD_OFF[0] + x, P.BOARD_OFF[1] + y)
                                    for x, y in P.LAN_HOLES]):
        add(s, METAL)
    board, bcol = board_mock.build(Z_PCB, colors=True)
    board.apply_translation((P.BOARD_OFF[0], P.BOARD_OFF[1], 0))
    add(board, bcol)
    if upto == 'A':
        return parts, cols
    for s in standoffs(T_A, Z_B, corner_points()):
        add(s, METAL)

    fan = trimesh.boolean.difference(
        [bx(P.FAN_C[0] - 20, P.FAN_C[0] + 20, P.FAN_C[1] - 20, P.FAN_C[1] + 20,
            Z_B - FAN_THICK, Z_B),
         cyl(P.FAN_BORE, Z_B - FAN_THICK - 1, Z_B + 1, *P.FAN_C, sections=64)],
        engine='manifold')
    add(fan, FAN_COL)

    add(plate('B', Z_B, T_B), ACRYLIC)
    for s in standoffs(Z_B + T_B, Z_C, corner_points()):
        add(s, METAL)

    import esp32_s31_case as S
    off = (P.ZONES[1][1] - S.BW / 2, P.ZONES[1][2] - S.BH / 2, Z_B + T_B)
    for name in ('esp32_s31_tray.stl', 'esp32_s31_lid.stl'):
        m = trimesh.load(os.path.join(S31, name))
        m.apply_translation((off[0], off[1], off[2] + (S.Z_LID if 'lid' in name else 0)))
        add(m, CASE)

    add(plate('C', Z_C, T_C), ACRYLIC)
    return parts, cols


def checks():
    print("hole alignment")
    ok = True
    for i, (hx, hy) in enumerate(P.LAN_HOLES, 1):
        px, py = P.BOARD_OFF[0] + hx, P.BOARD_OFF[1] + hy
        inside = 6 < px < P.PW - 6 and 6 < py < P.PH - 6
        near = min(np.hypot(px - cx, py - cy) for cx, cy in corner_points())
        ok &= inside and near > 8
        print(f"  hole {i} board ({hx:7.3f},{hy:7.3f}) -> plate ({px:7.3f},{py:7.3f})"
              f"  on plate={inside}  nearest corner standoff {near:5.1f} mm")
    print(f"\nfan bore centre  ({P.FAN_C[0]:.2f}, {P.FAN_C[1]:.2f})")
    print(f"  U1 on the board ({board_mock.PARTS[0][1]:.2f}, ...) -> "
          f"switch at plate ({P.BOARD_OFF[0] + P.U1[0]:.2f}, "
          f"{P.BOARD_OFF[1] + P.U1[1]:.2f})   offset "
          f"{np.hypot(P.FAN_C[0] - P.BOARD_OFF[0] - P.U1[0], P.FAN_C[1] - P.BOARD_OFF[1] - P.U1[1]):.3f} mm")

    tall = max(board_mock.PARTS, key=lambda p: p[5])
    top = Z_PCB + board_mock.PCB_T + tall[5]
    print(f"\nvertical stack")
    print(f"  plate A            {Z_A:6.1f} .. {Z_A + T_A:6.1f}")
    print(f"  PCB                {Z_PCB:6.1f} .. {Z_PCB + board_mock.PCB_T:6.1f}")
    print(f"  tallest part top   {top:6.1f}   ({tall[0]}, {tall[6]})")
    print(f"  fan                {Z_B - FAN_THICK:6.1f} .. {Z_B:6.1f}"
          f"   clearance to board {Z_B - FAN_THICK - top:5.1f} mm")
    print(f"  plate B            {Z_B:6.1f} .. {Z_B + T_B:6.1f}")
    import esp32_s31_case as S
    e_top = Z_B + T_B + S.Z_LID + S.LID_T
    print(f"  ESP32-S31 case top {e_top:6.1f}   clearance to plate C "
          f"{Z_C - e_top:5.1f} mm")
    print(f"  plate C            {Z_C:6.1f} .. {TOTAL:6.1f}")
    if Z_B - FAN_THICK - top < 3:
        ok = False
        print("  !! raise H_AB - the fan is too close to the board")
    if Z_C - e_top < 3:
        ok = False
        print("  !! raise H_BC - the ESP32 case hits plate C")
    return ok


if __name__ == '__main__':
    parts, cols = build()
    fc = np.vstack([c if np.ndim(c) == 2 else np.tile(c, (len(m.faces), 1))
                    for m, c in zip(parts, cols)])
    scene = trimesh.util.concatenate(parts)
    scene.export(os.path.join(HERE, 'assembly.stl'))
    e = scene.bounds[1] - scene.bounds[0]
    print(f"assembly.stl  {e[0]:.1f} x {e[1]:.1f} x {e[2]:.1f} mm, "
          f"{len(parts)} bodies  (a picture, not a printable part)\n")
    os.makedirs(os.path.join(HERE, 'img'), exist_ok=True)
    render(scene, 22, -54, face_colors=fc).save(os.path.join(HERE, 'img/assembly.png'))
    render(scene, 6, -2, face_colors=fc).save(os.path.join(HERE, 'img/assembly_front.png'))
    render(scene, 89, 0, face_colors=fc).save(os.path.join(HERE, 'img/assembly_top.png'))

    # plate A + board only, straight down: the hole-alignment view
    aparts, acols = build(upto='A')
    afc = np.vstack([c if np.ndim(c) == 2 else np.tile(c, (len(m.faces), 1))
                     for m, c in zip(aparts, acols)])
    render(trimesh.util.concatenate(aparts), 89, 0,
           face_colors=afc).save(os.path.join(HERE, 'img/plate_a_board.png'))
    # and without the board, so the eight standoffs sit visibly in their holes
    render(trimesh.util.concatenate(aparts[:-1]), 89, 0,
           face_colors=np.vstack([np.tile(c, (len(m.faces), 1))
                                  for m, c in zip(aparts[:-1], acols[:-1])])
           ).save(os.path.join(HERE, 'img/plate_a_holes.png'))
    print(checks() and "\nall checks pass" or "\nCHECK FAILED")
