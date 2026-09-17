#!/usr/bin/env python3
"""Acrylic alternative to the printed case: two plates and standoffs.

    python3 acrylic_case.py    # -> dxf/*.dxf + a 2-up order sheet + web check

The printed case wraps the board, so its four screws have to live outside the
board and land on an 80.4 x 100.4 pattern that plate C does not have. Plates
do not wrap anything: they bolt through the board's OWN four holes, which are
already plate C's 63 x 83 pattern. So the acrylic version drops onto the frame
with no change to any cut file, and the same two plates work on a desk.

Sizes come from ka7_uno_rev1.json and the Gerber, same as case.py.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'acrylic-frame'))
from make_plates import Dxf                                    # noqa: E402

BOARD_W, BOARD_H = 70.0, 90.0
PCB_T = 1.6
MOUNTS = [(3.5, 3.5), (66.5, 3.5), (66.5, 86.5), (3.5, 86.5)]  # board-local
M3_FREE = 3.4

BORDER = 4.0                      # acrylic beyond the board on every side
PW, PH = BOARD_W + 2 * BORDER, BOARD_H + 2 * BORDER
PLATE_R = 5.0
T = 3.0                           # same 3 mm sheet as the frame

# the AC7200 hangs under the carrier: 45 x 55 at board x 14.08..59.08,
# y 1.48..56.48, reaching 7.22 mm down with the FPGA facing the bottom plate
SOM = (14.08, 1.48, 59.08, 56.48)
SOM_DROP = 3.0 + 1.6 + 2.62
WINDOW_INSET = 4.0                # the bottom plate's window, inside the SoM

LOWER = 10.0                      # standoff under the board
UPPER = 20.0                      # standoff over it, clearing the 13.5 mm RJ45
PORT_H = 13.5

VENT_W, VENT_GAP = 4.0, 5.0
VENT_BOX = (14.0, 20.0, 64.0, 78.0)      # plate-local, clear of the mount holes
VENT_RIB = 6.0                    # mid rib, so the slots do not run the full span


def B(x, y):
    """Board-local to plate-local."""
    return x + BORDER, y + BORDER


def mount_holes(d):
    for hx, hy in MOUNTS:
        px, py = B(hx, hy)
        d.circle(px, py, M3_FREE / 2)


def vents(d):
    x0, y0, x1, y1 = VENT_BOX
    pitch = VENT_W + VENT_GAP
    n = int((x1 - x0 + VENT_GAP) // pitch)
    span = n * pitch - VENT_GAP
    sx = (x0 + x1) / 2 - span / 2 + VENT_W / 2
    half = (y1 - y0 - VENT_RIB) / 2
    out = []
    for i in range(n):
        cx = sx + i * pitch
        for cy in (y0 + half / 2, y1 - half / 2):
            d.slot(cx, cy, half, VENT_W, horizontal=False)
            out.append((cx, cy, VENT_W, half))
    return out


def window():
    """The bottom plate's opening, under the FPGA."""
    x0, y0 = B(SOM[0] + WINDOW_INSET, SOM[1] + WINDOW_INSET)
    x1, y1 = B(SOM[2] - WINDOW_INSET, SOM[3] - WINDOW_INSET)
    return x0, y0, x1, y1


def plate_bottom():
    d = Dxf()
    d.rounded_rect(0, 0, PW, PH, PLATE_R)
    mount_holes(d)
    d.rounded_rect(*window(), 3.0)
    return d


def plate_top():
    d = Dxf()
    d.rounded_rect(0, 0, PW, PH, PLATE_R)
    mount_holes(d)
    vents(d)
    return d


PLATES = [('ka7-plate-bottom-3T', plate_bottom),
          ('ka7-plate-top-3T', plate_top)]


def webs():
    """Smallest bridge of acrylic anywhere on either plate."""
    rows = []
    wx0, wy0, wx1, wy1 = window()
    rows.append(('bottom: window to plate edge',
                 min(wx0, wy0, PW - wx1, PH - wy1)))
    rows.append(('bottom: window to nearest mount hole',
                 min(max(wx0 - px, px - wx1, wy0 - py, py - wy1) - M3_FREE / 2
                     for px, py in (B(*m) for m in MOUNTS))))
    rows.append(('either: mount hole to plate edge',
                 min(min(px, py, PW - px, PH - py) for px, py in
                     (B(*m) for m in MOUNTS)) - M3_FREE / 2))
    x0, y0, x1, y1 = VENT_BOX
    rows.append(('top: vent web', min(VENT_GAP, VENT_RIB)))
    rows.append(('top: vent field to plate edge',
                 min(x0, y0, PW - x1, PH - y1)))
    rows.append(('top: vent field to nearest mount hole',
                 min(max(x0 - px, px - x1, y0 - py, py - y1) - M3_FREE / 2
                     for px, py in (B(*m) for m in MOUNTS))))
    return rows


def report():
    print(f"KA7-UNO acrylic case   2 plates, {PW:.0f} x {PH:.0f} x {T:.0f} mm, "
          f"{BORDER:.0f} mm of acrylic beyond the board on every side")
    print(f"  mount holes  Ø{M3_FREE}  at the board's own "
          f"{MOUNTS[1][0] - MOUNTS[0][0]:.0f} x {MOUNTS[2][1] - MOUNTS[0][1]:.0f} "
          f"pitch - the same pattern plate C already has")
    wx0, wy0, wx1, wy1 = window()
    print(f"  bottom window {wx1 - wx0:.1f} x {wy1 - wy0:.1f} under the FPGA")
    n = int((VENT_BOX[2] - VENT_BOX[0] + VENT_GAP) // (VENT_W + VENT_GAP))
    print(f"  top vents     {2 * n} slots {VENT_W:.0f} mm wide, two banks with a "
          f"{VENT_RIB:.0f} mm rib")

    print("\n  standalone stack")
    z = 0.0
    for name, h in (('bottom plate', T), ('M3 x 10 M/F standoff', LOWER),
                    ('carrier', PCB_T), ('M3 x 20 M/F standoff', UPPER),
                    ('top plate', T)):
        print(f"    {name:24s} {z:6.2f} .. {z + h:6.2f}")
        z += h
    print(f"    {'':24s} total {z:.1f} mm, nut on the stud through the top plate")
    print(f"    FPGA face to the bottom plate  {LOWER - SOM_DROP:.2f} mm")
    print(f"    RJ45 to the top plate          {UPPER - PORT_H:.2f} mm")

    print("\n  on plate C, drop the bottom plate - plate C is already it")
    z = LOWER + PCB_T + UPPER + T
    print(f"    standoff {LOWER:.0f} + carrier {PCB_T} + standoff {UPPER:.0f} + "
          f"plate {T:.0f} = {z:.1f} mm over plate C, against 47.0 mm of headroom")

    print("\n  webs")
    ok = True
    for label, mm in webs():
        good = mm >= 3.0
        ok &= good
        print(f"    {'ok  ' if good else 'THIN'} {label:38s} {mm:6.2f} mm")
    return ok


def preview(path):
    """Flat picture of both plates, drawn from the DXF entities themselves."""
    import math
    from PIL import Image, ImageDraw
    sc, M = 5, 26
    W = int((2 * PW + 10) * sc) + 2 * M
    H = int((PH + 14) * sc) + 2 * M
    im = Image.new('RGB', (W, H), (245, 246, 248))
    dr = ImageDraw.Draw(im)
    T_ = lambda x, y: (M + x * sc, H - M - y * sc)
    for i, (name, build) in enumerate(PLATES):
        ox = i * (PW + 10.0)
        dr.rectangle([T_(ox, PH), T_(ox + PW, 0)], fill=(214, 227, 234))
        for ent in build().e:
            ln = ent.split('\n')
            g = {ln[j]: ln[j + 1] for j in range(0, len(ln) - 1, 2)}
            col = (30, 40, 48)
            if ln[1] == 'LINE':
                dr.line([T_(float(g['10']) + ox, float(g['20'])),
                         T_(float(g['11']) + ox, float(g['21']))], fill=col, width=2)
            elif ln[1] == 'CIRCLE':
                cx, cy, r = float(g['10']) + ox, float(g['20']), float(g['40'])
                dr.ellipse([T_(cx - r, cy + r), T_(cx + r, cy - r)],
                           outline=col, fill=(245, 246, 248), width=2)
            elif ln[1] == 'ARC':
                cx, cy, r = float(g['10']) + ox, float(g['20']), float(g['40'])
                a0, a1 = float(g['50']), float(g['51'])
                pts = [T_(cx + r * math.cos(math.radians(a)),
                          cy + r * math.sin(math.radians(a)))
                       for a in [a0 + (a1 - a0) * k / 24 for k in range(25)]]
                dr.line(pts, fill=col, width=2)
        dr.text((M + ox * sc, H - M + 6), name, fill=(60, 70, 80))
    im.save(path)
    return im.size


if __name__ == '__main__':
    if not report():
        raise SystemExit('acrylic_case.py: a web came out under 3 mm')
    out = os.path.join(HERE, 'dxf')
    os.makedirs(out, exist_ok=True)
    print()
    for name, build in PLATES:
        d = build()
        p = os.path.join(out, name + '.dxf')
        print(f"  {name}.dxf   {d.save(p)} entities")

    sheet = Dxf()
    for i, (name, build) in enumerate(PLATES):
        ox = i * (PW + 10.0)
        for ent in build().e:
            ln = ent.split('\n')
            for j in range(1, len(ln)):
                if ln[j - 1] in ('10', '11'):
                    ln[j] = f"{float(ln[j]) + ox:.4f}"
            sheet.e.append('\n'.join(ln))
        sheet.stroke_text(ox + 4, PH + 5, 5.0, name.upper().replace('-', ' '),
                          layer='DIM')
    p = os.path.join(out, 'ka7-acrylic-order.dxf')
    print(f"  ka7-acrylic-order.dxf   {sheet.save(p)} entities  "
          f"(both plates, send this one)")
    q = os.path.join(HERE, 'ka7_acrylic_plates.png')
    print(f"  ka7_acrylic_plates.png  {preview(q)[0]} x {preview(q)[1]}")
