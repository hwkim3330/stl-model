#!/usr/bin/env python3
"""Bench v2: three acrylic stacks, one LAN9692 at the base of each.

    python3 make_v2.py        # -> dxf/*.dxf, stl/*.stl, img/*.png, and a check table

v1 (../acrylic-frame/) is one stack with everything on top of a single switch.
v2 is the three-switch ring: three identical bases, and every plate above them
cut to one outline and one column pattern, so any upper plate fits any stack.
What a stack carries is decided by which plates you bolt on, not by the cutter.

    plate    count  carries
    A base     3    LAN9692 on 8 standoffs (v1 plate A, unchanged)
    B io       3    9692 fan on top over the bore; FIM-RJ45 v2, FIM-MATEnet,
                    T1 connector gender
    C can      2    KA7-UNO CAN boards, four mount sets (fit up to four)
    C ecu      1    TC397, T-ETH-Elite, ESP32-S31
    D top      3    plain guard

    stack    plates
    FR       A  B-io  C-can  D
    FL       A  B-io  C-can  D
    REAR     A  B-io  C-ecu  D     (the ACU sits here, as on the vehicle)

Board data for the LAN9692, TC397, T-ETH-Elite, ESP32-S31, KA7-UNO and the
MATEnet injection module is imported from ../acrylic-frame/make_plates.py, so
v1 and v2 cannot disagree about a hole. The two new boards are read from their
own KiCad files - see NEW_BOARDS below.
"""
import math
import os
import sys
import zipfile

import numpy as np
import trimesh
from shapely.geometry import Point, box
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [os.path.join(ROOT, 'acrylic-frame'),
                os.path.join(ROOT, 'lan9692-evb-case')]

import make_plates as M                  # noqa: E402
import variants as V                     # noqa: E402

PW, PH, T = M.PW, M.PH, 3.0              # every plate: 250 x 180 x 3 clear

# --------------------------------------------------------------------------
# New boards, from their KiCad PCBs (Edge.Cuts outline, MountingHole footprints).
# Coordinates are from each board's bottom-left corner, top view.
#
# FIM-RJ45 v2 (260910) is NOT the v1 RJ45 module: 45.40 x 41.75 against
# 69.585 x 34.000. Its four MountingHole_2.5mm footprints are not a rectangle -
# the right pair sits 0.2 / 0.4 mm off square - and they are cut where KiCad
# puts them. RJ45 jacks J1/J2 face the left edge; J3/J4 are 1x9 sockets on top.
#
# T1 connector gender: 84.0 x 28.4. Three MountingHole footprints plus the
# Ø2.5 peg of J3 in the fourth corner, the same 0.326 mm skew at both ends.
# J1/J2 (TE 9-2304372-9) and J3 (TE 2305987-1) all face the bottom edge.
NEW_BOARDS = {
    'FIM-RJ45v2': ((45.40, 41.75),
                   [(25.525, 3.60), (41.800, 4.00), (25.525, 38.06), (42.000, 38.46)],
                   2.9),
    'T1-Gender': ((84.00, 28.40),
                  [(3.375, 3.40), (80.826, 3.40), (3.049, 24.90), (80.500, 24.90)],
                  2.9),
}
NEW_PORTS = {'FIM-RJ45v2': {'-x'}, 'T1-Gender': {'-y'}}
for k, v in NEW_BOARDS.items():
    V.BOARDS[k] = v
V.PORTS.update(NEW_PORTS)

# standoff under the PCB, height of the tallest part above it (mm)
HEIGHT = {
    'TC397': (8.0, 20.0), 'T-ETH-Elite': (8.0, 15.2), 'ESP32-S31': (8.0, 14.0),
    'FIM-MATEnet': (20.0, 11.0), 'FIM-RJ45v2': (20.0, 13.5),
    'T1-Gender': (10.0, 12.0),           # connector height assumed
}

# --------------------------------------------------------------------------
# The CAN board. The AC7200 SoM hangs under the carrier (7.22 mm), and the
# 20 mm heatsink under that. Mounted the right way up on 35 mm standoffs the
# heatsink ends 7.8 mm above the plate, in open air, and every terminal stays
# on top where a hand can reach it. Flipping the board would put the screw
# terminals face-down; cutting a window would drop the heatsink into the layer
# below and make that plate's layout depend on this one's.
HEATSINK = 20.0
CAN_STANDOFF = 35.0
SOM = (14.08, 1.48, 59.08, 56.48)        # on the carrier, from ../ka7-uno-can-board
SOM_DROP = M.CAN_SOM_DROP if hasattr(M, 'CAN_SOM_DROP') else 7.22

# --------------------------------------------------------------------------
# Plate layouts: (board, cx, cy, rot)
B_IO = [('T1-Gender', 62.0, 26.0, 0),
        ('FIM-RJ45v2', 35.0, 110.0, 0),
        ('FIM-MATEnet', 120.0, 150.0, 0)]
C_ECU = [('TC397', 60.0, 100.0, 90),
         ('ESP32-S31', 195.0, 140.0, 180),
         ('T-ETH-Elite', 195.0, 45.0, 0)]
C_CAN = [('KA7-UNO',) + t for t in M.CAN_ARRANGE['four-pinwheel']]
CAN_FITTED = 3                           # boards drawn in the preview

# heights: plate underside to plate underside is T + gap
GAP_AB, GAP_BC, GAP_CD = 50.0, 50.0, 60.0
Z_A = 0.0
Z_B = Z_A + T + GAP_AB
Z_C = Z_B + T + GAP_BC
Z_D = Z_C + T + GAP_CD

STACKS = {'FR': 'can', 'FL': 'can', 'REAR': 'ecu'}
COUNT = {'A-base': 3, 'B-io': 3, 'C-can': 2, 'C-ecu': 1, 'D-top': 3}


# --------------------------------------------------------------------------
# 2D: one list of cut features per plate, drawn to DXF and extruded to STL
def columns():
    return M.lower_columns()


def holes_for(spec):
    out = []
    for name, cx, cy, rot in spec:
        board, holes, hd = V.BOARDS[name][:3]
        b, h = M.orient(board, holes, rot)
        for hx, hy in h:
            out.append((cx - b[0] / 2 + hx, cy - b[1] / 2 + hy, hd))
    return out


def plate_features(kind):
    """-> list of (x, y, d) circles; every plate is the same rounded outline."""
    f = [(x, y, M.M3_FREE) for x, y in columns()]
    if kind == 'A-base':
        f += [(M.BOARD_OFF[0] + x, M.BOARD_OFF[1] + y, M.M3_FREE) for x, y in M.LAN_HOLES]
    elif kind == 'B-io':
        f.append((M.FAN_C[0], M.FAN_C[1], M.FAN_BORE))
        h = M.FAN_PITCH / 2
        f += [(M.FAN_C[0] + sx * h, M.FAN_C[1] + sy * h, M.FAN_SCREW_D)
              for sx in (-1, 1) for sy in (-1, 1)]
        f += holes_for(B_IO)
    elif kind == 'C-can':
        f += holes_for(C_CAN)
    elif kind == 'C-ecu':
        f += holes_for(C_ECU)
    return f


def write_dxf(kind, path):
    d = M.Dxf()
    d.rounded_rect(0, 0, PW, PH, M.PLATE_R)
    for x, y, dia in plate_features(kind):
        d.circle(x, y, dia / 2)
    return d.save(path)


def plate_poly(kind):
    outline = box(0, 0, PW, PH)
    r = M.PLATE_R
    outline = outline.buffer(-r, join_style=2).buffer(r, resolution=16)
    cuts = unary_union([Point(x, y).buffer(d / 2, resolution=24)
                        for x, y, d in plate_features(kind)])
    return outline.difference(cuts)


# --------------------------------------------------------------------------
# checks - the v1 layout checker, run on every v2 plate
def run_checks():
    ok_all = True
    print('\nplate checks  (mm, want)')
    for title, spec, fan in (('B-io', B_IO, True), ('C-ecu', C_ECU, False),
                             ('C-can', C_CAN, False)):
        ps, rows, ports, ok = V.check(spec, fan=fan)
        ok_all &= ok
        print(f'  {title}: {"OK" if ok else "FAIL"}')
        for label, mm, want in rows:
            flag = '' if mm >= want else '   <-- FAIL'
            if mm < want or 'web' in label or 'fan' in label:
                print(f'    {label:55s} {mm:7.2f}  >= {want}{flag}')
        for label, far, who in ports:
            print(f'    {label:55s} {far:7.2f}  ' + (f'blocked by {who}' if who else 'to rim'))
    # vertical
    print('\nvertical  (per stack)')
    rows = []
    tall_b = max(HEIGHT[n][0] + 1.6 + HEIGHT[n][1] for n, *_ in B_IO)
    rows.append(('B-io tallest board top -> plate C', GAP_BC - tall_b, 5.0))
    rows.append(('B-io fan top -> plate C', GAP_BC - 11.0, 5.0))
    tall_e = max(HEIGHT[n][0] + 1.6 + HEIGHT[n][1] for n, *_ in C_ECU)
    rows.append(('C-ecu tallest board top -> plate D', GAP_CD - tall_e, 5.0))
    rows.append(('KA7 heatsink bottom -> plate C', CAN_STANDOFF - SOM_DROP - HEATSINK, 5.0))
    rows.append(('KA7 carrier parts top -> plate D',
                 GAP_CD - CAN_STANDOFF - 1.6 - M_CAN_PARTS, 5.0))
    rows.append(('LAN9692 tallest part -> plate B (v1 figure)',
                 Z_B - (T + 10.0 + 1.6 + 14.0), 5.0))
    for label, mm, want in rows:
        ok = mm >= want
        ok_all &= ok
        print(f'  {label:55s} {mm:7.2f}  >= {want}' + ('' if ok else '   <-- FAIL'))
    return ok_all


M_CAN_PARTS = 12.65                      # top of ka7_uno_rev1.stl over the PCB face

# --------------------------------------------------------------------------
# 3D preview
ACRYL = (0.62, 0.78, 0.86, 0.55)
COL = {'plate': (158, 199, 219), 'pcb': (38, 110, 60), 'part': (70, 70, 78),
       'metal': (170, 175, 182), 'fan': (50, 52, 60), 'som': (30, 80, 140),
       'sink': (200, 205, 212), 'lan': (30, 90, 50)}


def tag(m, c):
    m.visual.face_colors = np.tile(np.array(list(COL[c]) + [255], np.uint8), (len(m.faces), 1))
    return m


def slab(x0, y0, x1, y1, z0, z1):
    m = trimesh.creation.box(extents=(x1 - x0, y1 - y0, z1 - z0))
    m.apply_translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    return m


def post(x, y, z0, z1, d=5.5):
    m = trimesh.creation.cylinder(radius=d / 2, height=z1 - z0, sections=6)
    m.apply_translation((x, y, (z0 + z1) / 2))
    return tag(m, 'metal')


def plate3d(kind, z):
    m = trimesh.creation.extrude_polygon(plate_poly(kind), T)
    m.apply_translation((0, 0, z))
    return tag(m, 'plate')


def board3d(name, cx, cy, rot, z_top, detail=False):
    """A board on its standoffs on the plate whose top face is z_top."""
    board, holes, _ = V.BOARDS[name][:3]
    b, h = M.orient(board, holes, rot)
    x0, y0 = cx - b[0] / 2, cy - b[1] / 2
    parts = []
    if name == 'KA7-UNO':
        so = CAN_STANDOFF
        zp = z_top + so
        ka7 = trimesh.load(os.path.join(ROOT, 'ka7-uno-can-board', 'ka7_uno_rev1.stl'))
        if not detail:
            ka7 = slab(0, 0, 70, 90, 0, 1.6)
            ka7 = tag(ka7, 'pcb')
            parts.append(ka7)
            for bx0, by0, bx1, by1 in ((0, 20, 12, 60), (25, 78, 64, 90)):
                parts.append(tag(slab(bx0, by0, bx1, by1, 1.6, 1.6 + 12.0), 'part'))
        else:
            parts.append(tag(ka7, 'pcb'))
        sx0, sy0, sx1, sy1 = SOM
        parts.append(tag(slab(sx0, sy0, sx1, sy1, -SOM_DROP, -3.0), 'som'))
        cxs, cys = (sx0 + sx1) / 2, (sy0 + sy1) / 2
        parts.append(tag(slab(cxs - 20, cys - 20, cxs + 20, cys + 20,
                              -SOM_DROP - HEATSINK, -SOM_DROP), 'sink'))
        m = trimesh.util.concatenate(parts)
        # board-local -> plate: rotate about the board's own footprint like orient()
        w, hgt = board
        R = {0: np.eye(3), 90: np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]]),
             180: np.array([[-1, 0, 0], [0, -1, 0], [0, 0, 1]]),
             270: np.array([[0, 1, 0], [-1, 0, 0], [0, 0, 1]])}[rot]
        Tm = np.eye(4)
        Tm[:3, :3] = R
        m.apply_transform(Tm)
        lo = m.bounds[0]
        # keep the PCB footprint, not the heatsink, on the board rectangle
        pcb_lo = (R @ np.array([[0, 0, 0], [w, hgt, 0]]).T).T.min(0)
        m.apply_translation((x0 - pcb_lo[0], y0 - pcb_lo[1], zp))
        out = [m]
    else:
        so, ph = HEIGHT[name]
        zp = z_top + so
        out = [tag(slab(x0, y0, x0 + b[0], y0 + b[1], zp, zp + 1.6), 'pcb'),
               tag(slab(x0 + 3, y0 + 3, x0 + b[0] - 3, y0 + b[1] - 3,
                        zp + 1.6, zp + 1.6 + ph), 'part')]
    for hx, hy in h:
        out.append(post(x0 + hx, y0 + hy, z_top, zp, d=5.0))
    return out


def stack3d(role, detail=False):
    parts = [plate3d('A-base', Z_A)]
    lan = trimesh.load(os.path.join(ROOT, 'lan9692-evb-case', 'board_mock.stl'))
    lan.apply_translation((M.BOARD_OFF[0], M.BOARD_OFF[1], T + 10.0))
    parts.append(tag(lan, 'lan'))
    for x, y in M.LAN_HOLES:
        parts.append(post(M.BOARD_OFF[0] + x, M.BOARD_OFF[1] + y, T, T + 10.0))
    parts.append(plate3d('B-io', Z_B))
    parts.append(tag(slab(M.FAN_C[0] - 20, M.FAN_C[1] - 20, M.FAN_C[0] + 20,
                          M.FAN_C[1] + 20, Z_B + T, Z_B + T + 11.0), 'fan'))
    for spec in B_IO:
        parts += board3d(*spec, Z_B + T)
    kind = 'C-can' if role == 'can' else 'C-ecu'
    parts.append(plate3d(kind, Z_C))
    spec = C_CAN[:CAN_FITTED] if role == 'can' else C_ECU
    for s in spec:
        parts += board3d(*s, Z_C + T, detail=detail)
    parts.append(plate3d('D-top', Z_D))
    for x, y in columns():
        for z0, z1 in ((Z_A + T, Z_B), (Z_B + T, Z_C), (Z_C + T, Z_D)):
            parts.append(post(x, y, z0, z1, d=6.0))
    return trimesh.util.concatenate(parts)


def render_png(mesh, path, elev=24, azim=-52):
    from render_preview import render
    img = render(mesh, elev=elev, azim=azim,
                 face_colors=mesh.visual.face_colors[:, :3] / 255.0)
    img.save(path)


# --------------------------------------------------------------------------
def main():
    for sub in ('dxf', 'stl', 'img'):
        os.makedirs(os.path.join(HERE, sub), exist_ok=True)
    ok = run_checks()

    print('\nDXF')
    made = []
    for kind, n in COUNT.items():
        p = os.path.join(HERE, 'dxf', f'{kind}.dxf')
        ents = write_dxf(kind, p)
        made.append(p)
        print(f'  {kind + ".dxf":14s} x{n}  {PW:.0f} x {PH:.0f} x {T:.0f} mm clear, {ents} entities')
    stamp = (2026, 1, 1, 0, 0, 0)
    with zipfile.ZipFile(os.path.join(HERE, 'bench-v2-dxf.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
        for p in made:
            info = zipfile.ZipInfo('bench-v2/' + os.path.basename(p), date_time=stamp)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, open(p, 'rb').read())

    print('\nSTL')
    for kind in COUNT:
        m = trimesh.creation.extrude_polygon(plate_poly(kind), T)
        p = os.path.join(HERE, 'stl', f'plate_{kind}.stl')
        m.export(p)
        print(f'  {os.path.basename(p):22s} watertight={m.is_watertight}')
    stacks = {}
    for name, role in STACKS.items():
        m = stack3d(role)
        stacks[name] = m
        p = os.path.join(HERE, 'stl', f'stack_{name}.stl')
        m.export(p)
        print(f'  {os.path.basename(p):22s} {m.extents.round(1).tolist()} mm')
    # the three on a bench, side by side with 60 mm between them
    row = []
    for i, name in enumerate(('FL', 'FR', 'REAR')):
        m = stacks[name].copy()
        m.apply_translation((i * (PW + 60.0), 0, 0))
        row.append(m)
    bench = trimesh.util.concatenate(row)
    bench.export(os.path.join(HERE, 'stl', 'bench_v2.stl'))
    print(f'  bench_v2.stl           {bench.extents.round(1).tolist()} mm')

    if '--no-png' not in sys.argv:
        print('\nPNG')
        for name, role in (('FR', 'can'), ('REAR', 'ecu')):
            p = os.path.join(HERE, 'img', f'stack_{name}.png')
            render_png(stack3d(role), p)
            print(f'  {os.path.relpath(p, HERE)}')
        for title, spec, fan in (('B-io', B_IO, True), ('C-can', C_CAN[:CAN_FITTED], False),
                                 ('C-ecu', C_ECU, False)):
            p = os.path.join(HERE, 'img', f'plate_{title}.png')
            V.draw(p, f'{title} (top view)', spec, fan=fan)
            print(f'  {os.path.relpath(p, HERE)}')
    print('\n' + ('ALL CHECKS OK' if ok else 'SOME CHECKS FAILED'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
