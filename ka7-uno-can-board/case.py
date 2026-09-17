#!/usr/bin/env python3
"""3D-printed case for the KETI KA7-UNO Rev1 carrier + ALINX AC7200 SoM.

    python3 case.py      # -> ka7_case_base.stl, ka7_case_lid.stl, PNGs, fit report

Every dimension below is read off the released manufacturing data, not measured
off a photo.  Where a number cannot exist in a Gerber set - component HEIGHTS -
it is marked ASSUMED and collected in PORT_H so one edit fixes it.

Sources
  board outline, mounting holes, drill    ka7_uno_rev1.json (fab DXF)
  connector bodies                        Gerber C-ASSY.gdo (component-side
                                          assembly drawing)
  board-to-board pad strips               Gerber S-PASTE.gdo, SOLDER side
  SoM outline / FPGA height               ALINX AC7200.3.0.stp (STEP)
  board-to-board mated height 3.0 mm      Panasonic AXK580137YG datasheet

The one fact that shapes the whole case: the four 80-pin B2B pad strips are on
the carrier's SOLDER side, so the AC7200 SoM hangs UNDER the carrier, FPGA face
pointing down and fully exposed.  That is where the cooling has to go.
"""
import os
import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- the board
BOARD_W, BOARD_H, PCB_T = 70.0, 90.0, 1.6
MOUNTS = [(3.5, 3.5), (66.5, 3.5), (66.5, 86.5), (3.5, 86.5)]   # NPTH 3.5
MOUNT_D = 3.5

# AC7200 SoM, 45 x 55, centred on the four B2B strips (all four sit 3.70 mm
# in from their nearest SoM edge - that symmetry is what fixes the position).
SOM = (14.08, 1.48, 59.08, 56.48)
SOM_GAP = 3.0      # AXK580137YG / AXK680137YG mated height
SOM_T = 1.6        # SoM PCB
SOM_TALL = 2.62    # FGG484 package above the SoM PCB, from the STEP
SOM_DROP = SOM_GAP + SOM_T + SOM_TALL          # 7.22 mm below the carrier

# Cooling allowance under the FPGA: thermal tape + a stick-on heatsink, then
# air.  HEATSINK = 0 makes the case 6 mm shorter and still clears the SoM.
HEATSINK = 6.0
UNDER_AIR = 3.0

# ------------------------------------------------------- ports, board-local
# span is along the wall; ASSUMED heights are flagged.  'back' = +Y edge,
# 'left' = -X edge, 'right' = +X edge.  Bodies that overhang the board edge
# pass straight through the wall, which is why the openings are full depth.
PORTS = [
    ('ETH0 RJ45',      'back',  47.10, 63.40, 13.5, False),
    ('CN1 T1S0',       'back',  25.70, 33.60, 11.0, True),
    ('CN2 T1S1',       'back',  37.10, 44.80, 11.0, True),
    ('J7 LIN0/LIN1',   'left',  41.00, 59.20, 12.0, True),
    ('J3 CAN0/CAN1',   'left',  21.70, 39.90, 12.0, True),
    ('J1 POWER IN',    'left',  11.50, 20.30, 12.0, True),
    ('right edge',     'right',  8.00, 41.00, 12.0, True),
]
PORT_SIDE_CLEAR = 0.6
MIN_RIB = 2.0      # anything thinner between two openings becomes one opening

# ------------------------------------------------------------- case fabric
CLEAR = 0.5        # board to cavity wall
WALL = 2.5
FLOOR = 2.5
LID_T = 2.5
LIP = 1.5          # lid spigot into the cavity
POST_D = 7.0       # board support post
POST_BORE = 2.6    # M3 self-tapping, or open out to 4.2 for a heat-set insert
EAR_R = 4.0
EAR_HOLE = 3.4

POST = SOM_DROP + HEATSINK + UNDER_AIR         # floor top -> board underside
ABOVE = max(h for _, _, _, _, h, _ in PORTS) + 2.0   # board top -> lid underside

CX0, CY0 = -CLEAR, -CLEAR
CX1, CY1 = BOARD_W + CLEAR, BOARD_H + CLEAR
OX0, OY0 = CX0 - WALL, CY0 - WALL
OX1, OY1 = CX1 + WALL, CY1 + WALL

Z_FLOOR = FLOOR                     # top of the floor
Z_BOARD = Z_FLOOR + POST            # underside of the carrier
Z_TOP = Z_BOARD + PCB_T             # top of the carrier
Z_LID = Z_TOP + ABOVE               # underside of the lid
CASE_H = Z_LID + LID_T

# Four full-height corner pillars, on the diagonal so they miss every port.
# One M3 runs top to bottom through each: lid -> pillar -> plate C standoff
# (or an M3 nut in the counterbore underneath, for desk use).
EP = 2.2
EARS = [(OX0 - EP, OY0 - EP), (OX1 + EP, OY0 - EP),
        (OX1 + EP, OY1 + EP), (OX0 - EP, OY1 + EP)]


def box(x0, y0, z0, x1, y1, z1):
    m = trimesh.creation.box(extents=(x1 - x0, y1 - y0, z1 - z0))
    m.apply_translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    return m


def cyl(x, y, z0, z1, d, seg=48):
    m = trimesh.creation.cylinder(radius=d / 2, height=z1 - z0, sections=seg)
    m.apply_translation((x, y, (z0 + z1) / 2))
    return m


def windows():
    """Ports grouped into the openings actually cut.

    Three of these connectors sit a millimetre apart on the real board, so a
    wall rib between them would be thinner than a printed wall can be.  Any
    rib under MIN_RIB is dropped and the two openings become one.
    """
    out = []
    for side in ('back', 'left', 'right'):
        run = sorted([(a, b, h, n) for n, s, a, b, h, _ in PORTS if s == side])
        cur = None
        for a, b, h, n in run:
            a, b = a - PORT_SIDE_CLEAR, b + PORT_SIDE_CLEAR
            if cur and a - cur[1] < MIN_RIB:
                cur = (cur[0], max(cur[1], b), max(cur[2], h), cur[3] + ' + ' + n)
            else:
                if cur:
                    out.append((side,) + cur)
                cur = (a, b, h, n)
        if cur:
            out.append((side,) + cur)
    return out


def port_cut(side, a, b, h):
    """One opening through a wall, from the board surface up."""
    z0, z1 = Z_TOP - 0.4, Z_TOP + h
    if side == 'back':
        return box(a, CY1 - 1.0, z0, b, OY1 + 4.0, z1)
    if side == 'left':
        return box(OX0 - 4.0, a, z0, CX0 + 1.0, b, z1)
    return box(CX1 - 1.0, a, z0, OX1 + 4.0, b, z1)


def slots(x0, y0, x1, y1, z0, z1, w=3.0, gap=3.0):
    """Vent slots running along Y, centred in the given rectangle."""
    out = []
    pitch = w + gap
    n = int((x1 - x0 - gap) // pitch)
    if n < 1:
        return out
    span = n * pitch - gap
    sx = (x0 + x1) / 2 - span / 2
    for i in range(n):
        a = sx + i * pitch
        out.append(box(a, y0, z0, a + w, y1, z1))
    return out


def base():
    m = box(OX0, OY0, 0, OX1, OY1, Z_LID)
    for ex, ey in EARS:
        m = m.union(cyl(ex, ey, 0, Z_LID, EAR_R * 2))
    cuts = [box(CX0, CY0, Z_FLOOR, CX1, CY1, Z_LID + 1)]        # cavity
    cuts += [cyl(ex, ey, -1, Z_LID + 1, EAR_HOLE) for ex, ey in EARS]
    cuts += [cyl(ex, ey, -1, 2.6, 6.4, seg=6) for ex, ey in EARS]   # M3 nut pocket
    cuts += [port_cut(s, a, b, h) for s, a, b, h, _ in windows()]
    # a shelf for the lid: the lid's lip drops into the cavity, so take the
    # top LIP of the wall back out to the cavity line
    cuts.append(box(CX0 - 0.5, CY0 - 0.5, Z_LID - LIP, CX1 + 0.5, CY1 + 0.5, Z_LID + 1))
    # vents in the floor, right under the SoM / FPGA
    cuts += slots(SOM[0] + 2, SOM[1] + 2, SOM[2] - 2, SOM[3] - 2, -1, FLOOR + 1)
    m = trimesh.boolean.difference([m] + cuts)
    posts = [cyl(x, y, Z_FLOOR, Z_BOARD, POST_D) for x, y in MOUNTS]
    m = trimesh.boolean.union([m] + posts)
    m = trimesh.boolean.difference(
        [m] + [cyl(x, y, Z_FLOOR - 1, Z_BOARD + 1, POST_BORE) for x, y in MOUNTS])
    return m


def lid():
    m = box(OX0, OY0, Z_LID, OX1, OY1, CASE_H)
    m = m.union(box(CX0 - 0.2, CY0 - 0.2, Z_LID - LIP, CX1 + 0.2, CY1 + 0.2, Z_LID))
    for ex, ey in EARS:
        m = m.union(cyl(ex, ey, Z_LID, CASE_H, EAR_R * 2))
    cuts = [cyl(ex, ey, Z_LID - 1, CASE_H + 1, EAR_HOLE) for ex, ey in EARS]
    # clear the lip where a port passes, and vent the lid over the hot half
    cuts += [port_cut(s, a, b, h) for s, a, b, h, _ in windows()]
    cuts += slots(12, 6, 58, 68, Z_LID - LIP - 1, CASE_H + 1)
    m = trimesh.boolean.difference([m] + cuts)
    return m


def contents():
    """Board, SoM and heatsink as plain blocks, for the preview only."""
    parts = [(box(0, 0, Z_BOARD, BOARD_W, BOARD_H, Z_TOP), (0.11, 0.30, 0.16))]
    for name, s, a, b, h, _ in PORTS:
        if s == 'back':
            parts.append((box(a, BOARD_H - 21.5, Z_TOP, b, BOARD_H + 3.9, Z_TOP + h),
                          (0.12, 0.12, 0.13)))
        elif s == 'left':
            parts.append((box(-3.4, a, Z_TOP, 10.9, b, Z_TOP + h), (0.12, 0.12, 0.13)))
    som_z1 = Z_BOARD - SOM_GAP
    parts.append((box(SOM[0], SOM[1], som_z1 - SOM_T, SOM[2], SOM[3], som_z1),
                  (0.10, 0.22, 0.34)))
    hz = som_z1 - SOM_T - SOM_TALL
    # the FPGA's orientation on the SoM is not derivable from this Gerber set,
    # so the heatsink is drawn centred on the SoM - which is also how the
    # cavity is sized, so the case is right either way
    mx, my = (SOM[0] + SOM[2]) / 2, (SOM[1] + SOM[3]) / 2
    parts.append((box(mx - 11.5, my - 11.5, hz, mx + 11.5, my + 11.5, hz + 0.1),
                  (0.15, 0.15, 0.17)))
    if HEATSINK:
        parts.append((box(mx - 12.5, my - 12.5, hz - HEATSINK,
                          mx + 12.5, my + 12.5, hz), (0.62, 0.64, 0.68)))
    return parts


def check(b, l):
    """Assert the openings are actually open and the solids actually solid."""
    ok = True
    rows = []

    def probe(m, pts, want, label):
        nonlocal ok
        got = m.contains(np.array(pts, float))
        good = bool(np.all(got == want))
        ok &= good
        rows.append((label, 'ok' if good else 'FAIL'))

    Z = Z_TOP
    for name, side, a, bb, h, _ in PORTS:
        mid = (a + bb) / 2
        if side == 'back':
            p_, q_ = (mid, CY1 + WALL / 2, Z + h / 2), (mid, CY1 + WALL / 2, Z - 3)
        elif side == 'left':
            p_, q_ = (CX0 - WALL / 2, mid, Z + h / 2), (CX0 - WALL / 2, mid, Z - 3)
        else:
            p_, q_ = (CX1 + WALL / 2, mid, Z + h / 2), (CX1 + WALL / 2, mid, Z - 3)
        probe(b, [p_, q_], [False, True], f'{name} opening / wall under it')

    mx, my = (SOM[0] + SOM[2]) / 2, (SOM[1] + SOM[3]) / 2
    probe(b, [(mx, my, Z_FLOOR + POST / 2)], [False], 'SoM cavity clear')
    row = [(x, my, FLOOR / 2) for x in np.linspace(SOM[0] + 3, SOM[2] - 3, 60)]
    frac = 1 - b.contains(np.array(row, float)).mean()
    ok &= frac > 0.25
    rows.append((f'floor vents under the SoM  {frac * 100:.0f}% open',
                 'ok' if frac > 0.25 else 'FAIL'))
    probe(b, [(MOUNTS[0][0] + 4.5, MOUNTS[0][1], FLOOR / 2)], [True], 'floor solid at a post')
    probe(b, [(MOUNTS[0][0] + 2.2, MOUNTS[0][1], Z_BOARD - 1),
              (MOUNTS[0][0], MOUNTS[0][1], Z_BOARD - 1)], [True, False], 'post body / bore')
    probe(b, [(EARS[0][0] + 3.0, EARS[0][1], CASE_H / 2),
              (EARS[0][0], EARS[0][1], CASE_H / 2)], [True, False], 'pillar body / bore')
    probe(b, [(CX0 - WALL / 2, 70.0, Z_TOP + 5)], [True], 'left wall solid where there is no port')
    probe(l, [(CX0 + 0.1, 45.0, Z_LID - LIP / 2)], [True], 'lid lip present')
    probe(b, [(CX0 - 0.25, 45.0, Z_LID - LIP / 2)], [False], 'rebate cut in the base')
    probe(l, [(35.0, 40.0, CASE_H - 1), (5.0, 40.0, CASE_H - 1)], [False, True], 'lid vents')

    print('\n  fit checks')
    for label, verdict in rows:
        print(f'    {verdict:4s} {label}')
    return ok


def report():
    w = OX1 - OX0 + 2 * (EP + EAR_R)
    d = OY1 - OY0 + 2 * (EP + EAR_R)
    print(f"KA7-UNO case   {w:.1f} x {d:.1f} x {CASE_H:.1f} mm over the pillars, "
          f"pillar holes {w - 2 * EAR_R:.1f} x {d - 2 * EAR_R:.1f} apart")
    print(f"  board {BOARD_W} x {BOARD_H} x {PCB_T}, mounts {MOUNT_D} at "
          f"{MOUNTS[0]} .. {MOUNTS[2]}")
    print(f"  AC7200 SoM 45 x 55 at x {SOM[0]:.2f}..{SOM[2]:.2f}, "
          f"y {SOM[1]:.2f}..{SOM[3]:.2f}, hanging UNDER the carrier")
    print(f"  under the carrier: {SOM_GAP} gap + {SOM_T} SoM PCB + "
          f"{SOM_TALL} FGG484 = {SOM_DROP:.2f} mm to the FPGA face")
    print(f"  floor to board {POST:.2f} mm  -> {HEATSINK:.1f} mm heatsink + "
          f"{UNDER_AIR:.1f} mm air under the FPGA")
    print("\n  vertical stack")
    for n, z in (('outside bottom', 0.0), ('floor top', Z_FLOOR),
                 ('FPGA face', Z_BOARD - SOM_DROP), ('SoM PCB', Z_BOARD - SOM_GAP - SOM_T),
                 ('carrier underside', Z_BOARD), ('carrier top', Z_TOP),
                 ('lid underside', Z_LID), ('lid top', CASE_H)):
        print(f"    {n:20s} {z:7.2f}")
    print("\n  connector bodies, board-local, from the C-ASSY assembly layer")
    for name, s, a, b, h, guess in PORTS:
        print(f"    {name:16s} {s:5s} {a:6.2f}..{b:6.2f}  height {h:5.1f}"
              f"{'   ASSUMED - measure it' if guess else '   (RJ45 magjack)'}")
    print("\n  openings actually cut")
    for s, a, b, h, name in windows():
        print(f"    {s:5s} {a:6.2f}..{b:6.2f}  x {h:5.1f} high   {name}")
    print(f"\n  clearance over the tallest port: {Z_LID - Z_TOP - max(h for *_, h, _ in PORTS):.1f} mm")


if __name__ == '__main__':
    import sys
    sys.path.insert(0, os.path.join(HERE, '..', 'lan9692-evb-case'))
    from render_preview import render

    report()
    b, l = base(), lid()
    for m, n in ((b, 'ka7_case_base'), (l, 'ka7_case_lid')):
        p = os.path.join(HERE, n + '.stl')
        m.export(p)
        e = m.bounds[1] - m.bounds[0]
        print(f"\n{n}.stl  {e[0]:.1f} x {e[1]:.1f} x {e[2]:.1f} mm  "
              f"{len(m.faces):,} faces  watertight={m.is_watertight}")

    if not check(b, l):
        raise SystemExit('case.py: geometry check failed')

    parts = [(b, (0.82, 0.84, 0.88))] + contents()
    fc = np.vstack([np.tile(c, (len(p.faces), 1)) for p, c in parts])
    mesh = trimesh.util.concatenate([p for p, _ in parts])
    for name, elev, azim in (('iso', 26, -46), ('open', 40, 140), ('front', 6, 0)):
        f = os.path.join(HERE, f'ka7_case_{name}.png')
        render(mesh, elev, azim, face_colors=fc).save(f)
        print(f"  {os.path.basename(f)}")

    # cutaway through the middle, so the stack under the carrier is visible
    cut = []
    for i, (m, c) in enumerate(parts):
        # each part's cut face is nudged back a hair so the coplanar caps do
        # not fight for the same depth
        h = m.slice_plane([0, 30.0 + 0.03 * (len(parts) - 1 - i), 0], [0, 1, 0], cap=True)
        if h is not None and len(h.faces):
            cut.append((h, c))
    fcc = np.vstack([np.tile(c, (len(p.faces), 1)) for p, c in cut])
    render(trimesh.util.concatenate([p for p, _ in cut]), 12, 0,
           face_colors=fcc).save(os.path.join(HERE, 'ka7_case_section.png'))
    print("  ka7_case_section.png")

    allp = parts + [(l, (0.72, 0.74, 0.80))]
    fc = np.vstack([np.tile(c, (len(p.faces), 1)) for p, c in allp])
    render(trimesh.util.concatenate([p for p, _ in allp]), 22, -46,
           face_colors=fc).save(os.path.join(HERE, 'ka7_case_closed.png'))
    print("  ka7_case_closed.png")
