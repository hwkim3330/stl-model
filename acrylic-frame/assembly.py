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
H_BC = 45.0                            # plate B -> plate C. 40 leaves only
                                       # 2 mm over the 38 mm TC397 case
FAN_THICK = 10.0

# True  = all-acrylic: bare boards on their own sub-plates, nothing printed
# False = the printed TC397 / T-ETH-Elite cases
ACRYLIC_ONLY = True
SUB_T = 3.0                            # sub-plate thickness
ETH_STANDOFF = 6.0                     # M2.5 under the T-ETH-Elite
TC_STANDOFF = 8.0                      # M3 under the TC397, 4 places
ETH_PARTS_H = 15.2                     # over the PCB, from LilyGo's 3D CAD
TC_PARTS_H = 20.0                      # over the PCB - assumed, no source

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

    for m, c in modules(Z_B + T_B):
        add(m, c)

    add(plate('C', Z_C, T_C), ACRYLIC)
    return parts, cols


TC = os.path.join(HERE, '..', 'tc397-appkit-case')
LG = os.path.join(HERE, '..', 'lilygo-t-eth-elite-case')
ADAPTER_FLOOR = 2.5          # adapter_lilygo.py FLOOR_T
LG_LID_DROP = 19.898         # the T-ETH-Elite lid's lip sinks into the base


def place(path, cx, cy, z):
    """Centre a part's own footprint on (cx, cy) and sit its base at z.

    The STLs are saved wherever they were built - the T-ETH-Elite lid, for
    instance, lives at x -76..-4 because it is laid out beside its base for
    printing - so normalise off each mesh's own bounds instead of assuming the
    file origin means anything.
    """
    m = trimesh.load(path)
    lo, hi = m.bounds
    m.apply_translation((cx - (lo[0] + hi[0]) / 2,
                         cy - (lo[1] + hi[1]) / 2,
                         z - lo[2]))
    return m


def sub_stack(cx, cy, plate_wh, board_wh, holes, standoff, parts_h, z_top):
    """A sub-plate, its standoffs, the bare PCB and a block for its parts."""
    pw, ph = plate_wh
    bw, bh = board_wh
    ox, oy = cx - pw / 2, cy - ph / 2
    bx0, by0 = ox + (pw - bw) / 2, oy + (ph - bh) / 2
    out = [(bx(ox, ox + pw, oy, oy + ph, z_top, z_top + SUB_T), ACRYLIC)]
    for hx, hy in holes:
        out.append((cyl(5.0, z_top + SUB_T, z_top + SUB_T + standoff,
                        bx0 + hx, by0 + hy), METAL))
    z = z_top + SUB_T + standoff
    out.append((bx(bx0, bx0 + bw, by0, by0 + bh, z, z + 1.6), (0.09, 0.36, 0.20)))
    out.append((bx(bx0 + 4, bx0 + bw - 4, by0 + 4, by0 + bh - 4,
                   z + 1.6, z + 1.6 + parts_h), (0.13, 0.14, 0.16)))
    return out


def modules(z_top):
    """Whatever the current plate-B layout carries, at its real height."""
    out = []
    if ACRYLIC_ONLY:
        (_, tx, ty), (_, lx, ly) = P.ZONES
        out += sub_stack(tx, ty, P.TC_PLATE, P.TC_BOARD, P.TC_HOLES,
                         TC_STANDOFF, TC_PARTS_H, z_top)
        out += sub_stack(lx, ly, P.ETH_PLATE, P.ETH_BOARD, P.ETH_HOLES,
                         ETH_STANDOFF, ETH_PARTS_H, z_top)
        return out
    if P.LAYOUT == 'tc397+eth-elite':
        (_, tx, ty), (_, lx, ly) = P.ZONES
        sys.path.insert(0, TC)
        import tc397_appkit_case as T
        out.append((place(os.path.join(TC, 'tc397_appkit_tray.stl'), tx, ty,
                          z_top), CASE))
        out.append((place(os.path.join(TC, 'tc397_appkit_lid.stl'), tx, ty,
                          z_top + T.Z_LID), CASE))
        ad = trimesh.load(os.path.join(HERE, 'adapter_lilygo.stl'))
        aw, ah = (ad.bounds[1] - ad.bounds[0])[:2]
        ad.apply_translation((lx - aw / 2, ly - ah / 2, z_top))
        out.append((ad, CASE))
        zc = z_top + ADAPTER_FLOOR
        out.append((place(os.path.join(LG, 'lilygo_t-eth_elite_case_bottom_fit.stl'),
                          lx, ly, zc), CASE))
        out.append((place(os.path.join(LG, 'lilygo_t-eth_elite_case_top_fit.stl'),
                          lx, ly, zc + LG_LID_DROP), CASE))
    else:
        import esp32_s31_case as S
        for name, (_, cx, cy) in zip(('esp32_s31_tray.stl', 'esp32_s31_lid.stl'),
                                     (P.ZONES[1], P.ZONES[1])):
            dz = S.Z_LID if 'lid' in name else 0
            out.append((place(os.path.join(S31, name), cx, cy, z_top + dz), CASE))
    return out


def module_top(z_top):
    return max(float(m.bounds[1][2]) for m, _ in modules(z_top))


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
    print(f"\nmodules on plate B (layout '{P.LAYOUT}'"
          f"{', all-acrylic' if ACRYLIC_ONLY else ', printed cases'})")
    boxes = []
    for m, _ in modules(Z_B + T_B):
        lo, hi = m.bounds[0], m.bounds[1]
        on = lo[0] > 0 and hi[0] < P.PW and lo[1] > 0 and hi[1] < P.PH
        fan_xy = (abs((lo[0] + hi[0]) / 2 - P.FAN_C[0]) < 20 + (hi[0] - lo[0]) / 2
                  and abs((lo[1] + hi[1]) / 2 - P.FAN_C[1]) < 20 + (hi[1] - lo[1]) / 2)
        boxes.append((lo, hi))
        ok_ = on and not fan_xy
        print(f"  x {lo[0]:6.1f}..{hi[0]:6.1f}  y {lo[1]:6.1f}..{hi[1]:6.1f}  "
              f"on plate={str(on):5s} clear of fan={str(not fan_xy):5s}"
              f"{'' if ok_ else '   <-- PROBLEM'}")
        ok &= ok_
    e_top = module_top(Z_B + T_B)
    print(f"  tallest module top {e_top:6.1f}   clearance to plate C "
          f"{Z_C - e_top:5.1f} mm   (layout '{P.LAYOUT}')")
    print(f"  plate C            {Z_C:6.1f} .. {TOTAL:6.1f}")
    if Z_B - FAN_THICK - top < 3:
        ok = False
        print("  !! raise H_AB - the fan is too close to the board")
    if Z_C - e_top < 3:
        ok = False
        print("  !! raise H_BC - the tallest module hits plate C")
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
