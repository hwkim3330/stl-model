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
import math
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
T_A, T_B, T_C, T_D = 3.0, 3.0, 3.0, 3.0   # plate thicknesses, all one stock
H_BOARD = 10.0                         # board standoff, plate A -> PCB
H_AB = 50.0                            # plate A -> plate B
H_BC = 50.0                            # plate B -> plate C. 40 leaves only
                                       # 2 mm over the 38 mm TC397 case
H_CD = 50.0                            # plate C -> plate D. Pure air, free to
                                       # choose; 50 keeps one standoff length.
# The column is M/F standoffs, male end up. Each one's stud crosses the plate
# above it and threads into the standoff beyond, so a plate needs only one hole
# per corner. 6 mm through a 3 mm plate leaves 3 mm engaged - the reason every
# plate here is 3 mm.
MF_STUD = 6.0
FAN_THICK = 11.0                       # Noctua NF-A4x10 mechanical
                                       # envelope; 12 with the anti-
                                       # vibration pads fitted

# True  = all-acrylic: bare boards on their own sub-plates, nothing printed
# False = the printed TC397 / T-ETH-Elite cases
ACRYLIC_ONLY = True
SUB_T = 3.0                            # sub-plate thickness
ETH_STANDOFF = 8.0                     # M2.5 under the T-ETH-Elite
TC_STANDOFF = 8.0                      # M3 under the TC397, 4 places
ETH_PARTS_H = 15.2                     # over the PCB, from LilyGo's 3D CAD
TC_PARTS_H = 20.0                      # over the PCB - assumed, no source
FIM_STANDOFF = 20.0                    # M2.5 under either injection module
FIM_PARTS_H = 13.5                     # the RJ45 magjacks, the tallest part on it
FIM_MN_PARTS_H = 11.0                  # MATEnet jacks are lower than an RJ45
RPI_STANDOFF = 8.0                     # M2.5 under the Raspberry Pi on plate C
RPI_PARTS_H = 16.0                     # the USB stacks, from RP-008343-DS-1
CAN_STANDOFF = 8.0                     # M3 under the KA7_UNO CAN board
CAN_PARTS_H = 15.0                     # assumed - its connector heights are not
                                       # in the fabrication set
LCD_STANDOFF = 12.0                    # under the display, to clear its back pan
LCD_THICK = 6.0                        # module thickness, RP-008246-DS-1

# 20 mm under the injection modules only - their RJ45 and MATEnet jacks are
# through-hole and want the room underneath. The TC397 and the T-ETH-Elite go
# back to 8 mm, which is what they were bought with.
#
# per-zone heights, by the name in make_plates' zone tuple - a size test used to
# pick these and would have put the rotated 34 mm injection module in the
# T-ETH-Elite's bracket by accident
HEIGHTS = {'TC397': (TC_STANDOFF, TC_PARTS_H),
           'T-ETH-Elite': (ETH_STANDOFF, ETH_PARTS_H),
           'FIM-RJ45': (FIM_STANDOFF, FIM_PARTS_H),
           'FIM-MATEnet': (FIM_STANDOFF, FIM_MN_PARTS_H)}

Z_A = 0.0
Z_PCB = T_A + H_BOARD                  # PCB underside
Z_B = T_A + H_AB                       # plate B underside
Z_C = Z_B + T_B + H_BC                 # plate C underside
Z_D = Z_C + T_C + H_CD                 # plate D underside
TOTAL = Z_D + T_D

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


ENGRAVE_W = 0.9                        # laser kerf-ish stroke width
ENGRAVE_DEPTH = 0.6


def groove(x1, y1, x2, y2, z0, z1, w=None):
    """A rounded-end bar along a segment, for engraved strokes."""
    w = w or ENGRAVE_W
    L = math.hypot(x2 - x1, y2 - y1)
    m = bx(-L / 2, L / 2, -w / 2, w / 2, z0, z1)
    ang = math.atan2(y2 - y1, x2 - x1)
    m.apply_transform(trimesh.transformations.rotation_matrix(ang, [0, 0, 1]))
    m.apply_translation(((x1 + x2) / 2, (y1 + y2) / 2, 0))
    ends = [cyl(w, z0, z1, x1, y1, sections=8), cyl(w, z0, z1, x2, y2, sections=8)]
    return trimesh.boolean.union([m] + ends, engine='manifold')


PLATE_DXF = {'A': 'plate-a-bottom-3T', 'B': 'plate-b-middle-3T',
             'C': 'plate-c-top-3T', 'D': 'plate-d-upper-3T'}


def dxf_features(stem, layer='CUT'):
    """Read a plate's features straight out of the DXF the cutter is sent.

    Returned as ('circle', x, y, d) / ('slot', x, y, length, width, horizontal)
    / ('line', x1, y1, x2, y2) for the ENGRAVE layer.

    This used to re-derive the geometry from the constants a second time, and it
    drifted: plate B went on being modelled with the legacy 45 mm deck slots
    long after the DXF had moved to real board mounts, so the preview showed a
    plate that was never going to be cut. Reading the shipped file is the only
    arrangement in which the two cannot disagree.

    Slot ends are told apart from the outline's rounded corners by arc span -
    a cap is a half circle, a corner is a quarter - and each cap's start angle
    says which end of which axis it is, so pairing is unambiguous even for the
    five vent slots that share a centre line.
    """
    import review
    ents = [(k, b) for k, b in
            review.parse(os.path.join(HERE, 'dxf', stem + '.dxf'))
            if b.get('8') == layer]
    if not ents:
        raise ValueError(f"{stem}: nothing on layer {layer}")
    if layer != 'CUT':
        return [('line', float(b['10']), float(b['20']),
                 float(b['11']), float(b['21'])) for k, b in ents if k == 'LINE']

    out, caps = [], {90: [], 270: [], 0: [], 180: []}
    for k, b in ents:
        if k == 'CIRCLE':
            out.append(('circle', float(b['10']), float(b['20']),
                        float(b['40']) * 2))
        elif k == 'ARC':
            a0, a1 = float(b['50']), float(b['51'])
            if abs((a1 - a0) % 360 - 180) > 1e-6:
                continue                       # 90 deg: a rounded plate corner
            key = round(a0 % 360)              # 90 left, 270 right, 180 bottom, 0 top
            if key not in caps:
                raise ValueError(f"{stem}: slot cap at odd angle {a0}")
            caps[key].append((float(b['10']), float(b['20']),
                              float(b['40']) * 2))

    # 90 pairs with 270 across X, 180 with 0 across Y; the shared coordinate
    # must match exactly and the far cap must lie on the far side.
    for lo, hi, horizontal in ((90, 270, True), (180, 0, False)):
        same, along = (1, 0) if horizontal else (0, 1)
        for cap in caps[lo]:
            mate = [p for p in caps[hi] if abs(p[same] - cap[same]) < 1e-6
                    and abs(p[2] - cap[2]) < 1e-6 and p[along] > cap[along]]
            if not mate:
                raise ValueError(f"{stem}: unpaired slot cap at "
                                 f"({cap[0]:.3f}, {cap[1]:.3f})")
            m = min(mate, key=lambda p: p[along])
            caps[hi].remove(m)
            out.append(('slot', (cap[0] + m[0]) / 2, (cap[1] + m[1]) / 2,
                        m[along] - cap[along] + cap[2], cap[2], horizontal))
        caps[lo] = []
    left = [p for v in caps.values() for p in v]
    if left:
        raise ValueError(f"{stem}: {len(left)} slot caps left unpaired")
    return out


def plate(kind, z0, thick):
    """3D version of a plate, cut from its own DXF - see dxf_features."""
    r = P.PLATE_R
    body = trimesh.boolean.union(
        [bx(r, P.PW - r, 0, P.PH, z0, z0 + thick),
         bx(0, P.PW, r, P.PH - r, z0, z0 + thick)] +
        [cyl(2 * r, z0, z0 + thick, x, y, sections=32)
         for x in (r, P.PW - r) for y in (r, P.PH - r)], engine='manifold')
    z1, z2 = z0 - 1, z0 + thick + 1
    cuts = []
    for f in dxf_features(PLATE_DXF[kind]):
        if f[0] == 'circle':
            cuts.append(cyl(f[3], z1, z2, f[1], f[2],
                            sections=64 if f[3] > 20 else 40))
        else:
            cuts.append(slot_solid(f[1], f[2], f[3], f[4], z1, z2,
                                   horizontal=f[5]))
    if P.ENGRAVE:
        # the ENGRAVE layer, as real grooves so the preview shows the lettering.
        # P.ENGRAVE is empty while the KETI mark is unapproved, and then the
        # layer is absent from the DXF entirely - which is not a fault.
        for _, x1, y1, x2, y2 in dxf_features(PLATE_DXF[kind], 'ENGRAVE'):
            cuts.append(groove(x1, y1, x2, y2, z0 + thick - ENGRAVE_DEPTH,
                               z0 + thick + 0.2))
    return trimesh.boolean.difference([body] + cuts, engine='manifold')


def hexs(z0, z1, points, af=5.5):
    """Hex standoff, across-flats `af` - M3 standoffs are 5.5 mm A/F."""
    return [cyl(af / math.cos(math.pi / 6), z0, z1, x, y, sections=6)
            for x, y in points]


def screw(x, y, z_head, length, up=False, d=3.0, head_d=5.5, head_h=2.0):
    """Pan-head M3. z_head is the face the head sits on; `up` = pointing +Z."""
    s = -1 if not up else 1
    shank = cyl(d, min(z_head, z_head + s * length), max(z_head, z_head + s * length),
                x, y, sections=12)
    head = cyl(head_d, min(z_head, z_head - s * head_h),
               max(z_head, z_head - s * head_h), x, y, sections=12)
    return trimesh.util.concatenate([shank, head])


# joint: name, screw length, material it passes through, standoff it enters
JOINTS = []


def corner_points(which='lower'):
    return P.lower_columns()          # one column line; `which` is vestigial


def build(upto='D'):
    """upto='A' gives just plate A, its standoffs and the board - the view that
    shows whether the drilled pattern really lines up."""
    parts, cols = [], []
    JOINTS.clear()          # build() may be called more than once per run

    def add(m, c):
        parts.append(m)
        cols.append(c)

    add(plate('A', Z_A, T_A), ACRYLIC)
    pcb_pts = [(P.BOARD_OFF[0] + x, P.BOARD_OFF[1] + y) for x, y in P.LAN_HOLES]
    for s in hexs(T_A, Z_PCB, pcb_pts):
        add(s, METAL)
    for x, y in pcb_pts:                                  # M3x8 up from below
        add(screw(x, y, Z_A, 8.0, up=True), METAL)
    JOINTS.append(('LAN9692 standoff, from under plate A', 8.0, T_A, 10.0))
    board, bcol = board_mock.build(Z_PCB, colors=True)
    board.apply_translation((P.BOARD_OFF[0], P.BOARD_OFF[1], 0))
    add(board, bcol)
    if upto == 'A':
        return parts, cols
    for s in hexs(T_A, Z_B, corner_points('lower')):
        add(s, METAL)
    for x, y in corner_points('lower'):
        add(screw(x, y, Z_A, 8.0, up=True), METAL)       # into the A->B standoff
    JOINTS.append(('A->B standoff, from under plate A', 8.0, T_A, H_AB))

    add(plate('B', Z_B, T_B), ACRYLIC)
    # The fan sits ON TOP of plate B, like every other board on that plate, and
    # blows down through the bore onto the switch. Same airflow as hanging it
    # underneath, but it stops eating into the A-B gap where the LAN9692's tall
    # parts are, and every fastener on plate B is then reached from above.
    fan = trimesh.boolean.difference(
        [bx(P.FAN_C[0] - 20, P.FAN_C[0] + 20, P.FAN_C[1] - 20, P.FAN_C[1] + 20,
            Z_B + T_B, Z_B + T_B + FAN_THICK),
         cyl(P.FAN_BORE, Z_B + T_B - 1, Z_B + T_B + FAN_THICK + 1, *P.FAN_C,
             sections=64)],
        engine='manifold')
    add(fan, FAN_COL)
    # No screw at plate B: the standoff below sends its male stud up through the
    # single corner hole and into the standoff above.
    for s in hexs(Z_B + T_B, Z_C, corner_points()):
        add(s, METAL)
    for x, y in corner_points():
        add(cyl(3.0, Z_B, Z_B + MF_STUD, x, y, sections=16), METAL)
    JOINTS.append(('M/F stud through plate B', MF_STUD, T_B, H_BC))

    for m, c in modules(Z_B + T_B):
        add(m, c)

    add(plate('C', Z_C, T_C), ACRYLIC)
    for m, c in pi_on_plate_c(Z_C + T_C) + can_on_plate_c(Z_C + T_C):
        add(m, c)
    if upto == 'C':
        for x, y in corner_points():
            add(cyl(3.0, Z_C, Z_C + MF_STUD, x, y, sections=16), METAL)
            add(cyl(5.5, Z_C + T_C, Z_C + T_C + 2.4, x, y, sections=6), METAL)
        JOINTS.append(('M/F stud through plate C, nut on top', MF_STUD, T_C, MF_STUD))
        return parts, cols

    # Fourth tier, same again at plate C.
    for s in hexs(Z_C + T_C, Z_D, corner_points()):
        add(s, METAL)
    for x, y in corner_points():
        add(cyl(3.0, Z_C, Z_C + MF_STUD, x, y, sections=16), METAL)
    JOINTS.append(('M/F stud through plate C', MF_STUD, T_C, H_CD))
    add(plate('D', Z_D, T_D), ACRYLIC)
    # the 7-inch display, screen up, on standoffs that clear its own back pan
    lx = P.LCD_AT[0] - P.LCD_LENS[0] / 2
    ly = P.LCD_AT[1] - P.LCD_LENS[1] / 2
    for hx, hy in P.LCD_HOLES:
        add(cyl(5.5, Z_D + T_D, Z_D + T_D + LCD_STANDOFF, lx + hx, ly + hy), METAL)
    zl = Z_D + T_D + LCD_STANDOFF
    add(bx(lx, lx + P.LCD_LENS[0], ly, ly + P.LCD_LENS[1], zl, zl + LCD_THICK),
        (0.10, 0.10, 0.12))
    # The top standoff's stud comes through plate D and takes a nut - the one
    # fastener in the column that is not a screw or a standoff.
    for x, y in corner_points():
        add(cyl(3.0, Z_D, Z_D + MF_STUD, x, y, sections=16), METAL)
        add(cyl(5.5, Z_D + T_D, Z_D + T_D + 2.4, x, y, sections=6), METAL)
    JOINTS.append(('M/F stud through plate D, nut on top', MF_STUD, T_D, MF_STUD))
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


def sub_stack(cx, cy, plate_wh, board_wh, holes, standoff, parts_h, z_top,
              plate=True):
    """A sub-plate (optional), its standoffs, the bare PCB and a parts block."""
    pw, ph = plate_wh
    bw, bh = board_wh
    ox, oy = cx - pw / 2, cy - ph / 2
    bx0, by0 = ox + (pw - bw) / 2, oy + (ph - bh) / 2
    t = SUB_T if plate else 0.0
    out = [(bx(ox, ox + pw, oy, oy + ph, z_top, z_top + SUB_T), ACRYLIC)] if plate else []
    for hx, hy in holes:
        out.append((cyl(5.0, z_top + t, z_top + t + standoff,
                        bx0 + hx, by0 + hy), METAL))
    z = z_top + t + standoff
    out.append((bx(bx0, bx0 + bw, by0, by0 + bh, z, z + 1.6), (0.09, 0.36, 0.20)))
    out.append((bx(bx0 + 4, bx0 + bw - 4, by0 + 4, by0 + bh - 4,
                   z + 1.6, z + 1.6 + parts_h), (0.13, 0.14, 0.16)))
    return out


def modules(z_top):
    """Whatever the current plate-B layout carries, at its real height."""
    out = []
    if ACRYLIC_ONLY and P.DIRECT_MOUNT:
        for (name, cx, cy), (bw, bh), holes, _, _ in P.board_mounts():
            if name not in HEIGHTS:
                raise KeyError(f"no standoff/height for zone {name!r} - add it "
                               "to HEIGHTS rather than guessing from the size")
            standoff, parts_h = HEIGHTS[name]
            out += sub_stack(cx, cy, (bw, bh), (bw, bh), holes,
                             standoff, parts_h, z_top, plate=False)
        return out
    if ACRYLIC_ONLY:
        (_, tx, ty, _tr), (_, lx, ly, _lr) = P.ZONES
        out += sub_stack(tx, ty, P.TC_PLATE, P.TC_BOARD, P.TC_HOLES,
                         TC_STANDOFF, TC_PARTS_H, z_top)
        out += sub_stack(lx, ly, P.ETH_PLATE, P.ETH_BOARD, P.ETH_HOLES,
                         ETH_STANDOFF, ETH_PARTS_H, z_top)
        return out
    if P.LAYOUT == 'tc397+eth-elite':
        (_, tx, ty, _tr), (_, lx, ly, _lr) = P.ZONES
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
        for name, (_, cx, cy, _rot) in zip(('esp32_s31_tray.stl', 'esp32_s31_lid.stl'),
                                           (P.ZONES[1], P.ZONES[1])):
            dz = S.Z_LID if 'lid' in name else 0
            out.append((place(os.path.join(S31, name), cx, cy, z_top + dz), CASE))
    return out


def pi_on_plate_c(z_top):
    """The Raspberry Pi 4B, on its own standoffs on plate C."""
    out = []
    bw, bh = P.RPI_BOARD
    bx0, by0 = P.RPI_AT[0] - bw / 2, P.RPI_AT[1] - bh / 2
    for hx, hy in P.RPI_HOLES:
        out.append((cyl(5.0, z_top, z_top + RPI_STANDOFF,
                        bx0 + hx, by0 + hy), METAL))
    z = z_top + RPI_STANDOFF
    out.append((bx(bx0, bx0 + bw, by0, by0 + bh, z, z + 1.6), (0.09, 0.36, 0.20)))
    out.append((bx(bx0 + 3, bx0 + bw - 3, by0 + 3, by0 + bh - 3,
                   z + 1.6, z + 1.6 + RPI_PARTS_H), (0.13, 0.14, 0.16)))
    return out


def can_on_plate_c(z_top):
    """The KETI KA7_UNO CAN board, beside the Pi on plate C."""
    out = []
    bw, bh = P.CAN_BOARD
    bx0, by0 = P.CAN_AT[0] - bw / 2, P.CAN_AT[1] - bh / 2
    for hx, hy in P.CAN_HOLES:
        out.append((cyl(5.5, z_top, z_top + CAN_STANDOFF,
                        bx0 + hx, by0 + hy), METAL))
    z = z_top + CAN_STANDOFF
    out.append((bx(bx0, bx0 + bw, by0, by0 + bh, z, z + 1.6), (0.09, 0.36, 0.20)))
    out.append((bx(bx0 + 4, bx0 + bw - 4, by0 + 4, by0 + bh - 4,
                   z + 1.6, z + 1.6 + CAN_PARTS_H), (0.13, 0.14, 0.16)))
    return out


def pi_top(z_top):
    return max(float(m.bounds[1][2])
               for m, _ in pi_on_plate_c(z_top) + can_on_plate_c(z_top))


def module_top(z_top):
    return max(float(m.bounds[1][2]) for m, _ in modules(z_top))


def checks():
    print("hole alignment")
    ok = True
    for i, (hx, hy) in enumerate(P.LAN_HOLES, 1):
        px, py = P.BOARD_OFF[0] + hx, P.BOARD_OFF[1] + hy
        inside = 6 < px < P.PW - 6 and 6 < py < P.PH - 6
        near = min(np.hypot(px - cx, py - cy)
                   for cx, cy in corner_points())
        ok &= inside and near > 8
        print(f"  hole {i} board ({hx:7.3f},{hy:7.3f}) -> plate ({px:7.3f},{py:7.3f})"
              f"  on plate={inside}  nearest corner standoff {near:5.1f} mm")
    print(f"\nfan bore centre  ({P.FAN_C[0]:.2f}, {P.FAN_C[1]:.2f})")
    print(f"  U1 on the board ({board_mock.PARTS[0][1]:.2f}, ...) -> "
          f"switch at plate ({P.BOARD_OFF[0] + P.U1[0]:.2f}, "
          f"{P.BOARD_OFF[1] + P.U1[1]:.2f})   offset "
          f"{np.hypot(P.FAN_C[0] - P.BOARD_OFF[0] - P.U1[0], P.FAN_C[1] - P.BOARD_OFF[1] - P.U1[1]):.3f} mm")

    print("\nfastener engagement  (screw length - what it passes through)")
    ok2 = True
    for j in globals().get('FULL_JOINTS', JOINTS):
        name, length, through, depth = j[:4]
        two_ended = len(j) > 4 and j[4]
        # a stud is threaded into a standoff at BOTH ends, so what is left after
        # the plate is shared between them - report per end, not the total
        eng = (length - through) / 2 if two_ended else length - through
        verdict = 'OK' if 3.0 <= eng <= depth else ('too little' if eng < 3.0
                                                    else 'bottoms out')
        ok2 &= verdict == 'OK'
        print(f"  {name:44s} M3 x {length:4.1f} through {through:4.1f} mm"
              f"  -> {eng:4.1f} mm of thread   {verdict}")
    if not ok2:
        ok = False
    print("  (an M/F standoff's 6 mm stud through a 5 mm plate gives 1.0 mm - "
          "this is the check that rules that out)")

    tall = max(board_mock.PARTS, key=lambda p: p[5])
    top = Z_PCB + board_mock.PCB_T + tall[5]
    print(f"\nvertical stack")
    print(f"  plate A            {Z_A:6.1f} .. {Z_A + T_A:6.1f}")
    print(f"  PCB                {Z_PCB:6.1f} .. {Z_PCB + board_mock.PCB_T:6.1f}")
    print(f"  tallest part top   {top:6.1f}   ({tall[0]}, {tall[6]})")
    print(f"  plate B            {Z_B:6.1f} .. {Z_B + T_B:6.1f}"
          f"   clearance to the board below {Z_B - top:5.1f} mm")
    print(f"  fan (on top of B)  {Z_B + T_B:6.1f} .. {Z_B + T_B + FAN_THICK:6.1f}")
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
    print(f"  plate C            {Z_C:6.1f} .. {Z_C + T_C:6.1f}")
    p_top = pi_top(Z_C + T_C)
    print(f"  plate C boards top {p_top:6.1f}   clearance to plate D "
          f"{Z_D - p_top:5.1f} mm")
    if Z_D - p_top < 3:
        ok = False
    print(f"  plate D            {Z_D:6.1f} .. {Z_D + T_D:6.1f}"
          f"   <- total height {TOTAL:.0f} mm")
    if Z_B - top < 3:
        ok = False
        print("  !! raise H_AB - the fan is too close to the board")
    if Z_C - e_top < 3:
        ok = False
        print("  !! raise H_BC - the tallest module hits plate C")
    return ok


def exploded(parts, gap=28.0):
    """Lift each layer apart along Z so the joints are visible."""
    out = []
    for m, c in parts:
        z = float(m.bounds[0][2])
        lift = 0.0
        if z >= Z_C - 1: lift = 3 * gap
        elif z >= Z_B + T_B - 1: lift = 2 * gap
        elif z >= Z_B - FAN_THICK - 1: lift = gap
        n = m.copy()
        n.apply_translation((0, 0, lift))
        out.append((n, c))
    return out


if __name__ == '__main__':
    parts, cols = build()
    FULL_JOINTS = list(JOINTS)      # build('A') later would truncate it
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

    ex = exploded(list(zip(parts, cols)))
    exf = np.vstack([c if np.ndim(c) == 2 else np.tile(c, (len(m.faces), 1))
                     for m, c in ex])
    render(trimesh.util.concatenate([m for m, _ in ex]), 20, -56,
           face_colors=exf).save(os.path.join(HERE, 'img/exploded.png'))

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
