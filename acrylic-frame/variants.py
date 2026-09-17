#!/usr/bin/env python3
"""Layout study: candidate arrangements for plate B and plate C.

    python3 variants.py      # -> img/variant_*.png + a clearance table

Nothing here cuts anything. make_plates.py still generates the frame as it
stands; this file exists so a layout can be argued about with numbers before
one of them becomes the cut file. Each candidate is checked for overlap, for
the acrylic left between boards, to the rim, to the corner columns and to the
fan bore, and for whether every board's PORT edges end up facing a rim.
"""
import os
import math

import make_plates as P

HERE = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------
# ESP32-S31-Function-CoreBoard-1, from Espressif's dimension PDF - the same
# numbers ../esp32-s31-coreboard-case/ is built on.
# ports: y=0 two USB-C, x=65 RJ45 + USB-A host, x=0 speaker header.
# Only the y=55 edge (the 2x20 header) is free of connectors.
S31_PORTS = {'-y', '+x', '-x'}

# which edges each board puts its connectors on, at rotation 0
PORTS = {
    'TC397': {'+y'},
    'T-ETH-Elite': {'-y', '-x'},
    'ESP32-S31': S31_PORTS,
    'FIM-RJ45': {'-x', '+x'},
    'FIM-MATEnet': {'-x', '+x'},
    'KA7-UNO': {'-x', '+y'},
}
BOARDS = {k: v[:3] for k, v in P.BOARD_TABLE.items()}
BOARDS['KA7-UNO'] = (P.CAN_BOARD, P.CAN_HOLES, P.CAN_HOLE_D)
ROT_PORT = {
    0: {e: e for e in ('-x', '+x', '-y', '+y')},
    90: {'-x': '-y', '+y': '-x', '+x': '+y', '-y': '+x'},
    180: {'-x': '+x', '+x': '-x', '-y': '+y', '+y': '-y'},
    270: {'-x': '+y', '+y': '+x', '+x': '-y', '-y': '-x'},
}

# --------------------------------------------------------------------------
# Plate B candidates. (name, cx, cy, rot)
# The candidates themselves live in make_plates.LAYOUTS / CAN_ARRANGE, so this
# study and the generator can never disagree about where a board goes.
PLATE_B = {
    'B1 as cut': P.LAYOUTS['tc397+eth-elite'],
    'B2 TC397 turned, S31, modules across the back': P.LAYOUTS['tc397-turned+s31'],
    'B3 TC397 ports left, S31 back-right': P.LAYOUTS['tc397-left+s31'],
}
PLATE_C = {
    'C1 as cut, two boards': [('KA7-UNO',) + t for t in P.CAN_ARRANGE['two']],
    'C2 four boards, pinwheel':
        [('KA7-UNO',) + t for t in P.CAN_ARRANGE['four-pinwheel']],
}


def placed(spec):
    """-> (name, x0, y0, x1, y1, holes, hole_d, port edges after rotation)"""
    out = []
    for name, cx, cy, rot in spec:
        board, holes, hd = BOARDS[name]
        b, h = P.orient(board, holes, rot)
        x0, y0 = cx - b[0] / 2, cy - b[1] / 2
        out.append((name, x0, y0, x0 + b[0], y0 + b[1],
                    [(x0 + hx, y0 + hy) for hx, hy in h], hd,
                    {ROT_PORT[rot][e] for e in PORTS[name]}, rot))
    return out


def rect_gap(a, b):
    """Gap between two axis-aligned rectangles; negative means they overlap."""
    dx = max(b[0] - a[2], a[0] - b[2])
    dy = max(b[1] - a[3], a[1] - b[3])
    if dx >= 0 and dy >= 0:
        return math.hypot(dx, dy)
    return max(dx, dy)


def point_gap(rect, px, py, r):
    dx = max(rect[0] - px, px - rect[2], 0.0)
    dy = max(rect[1] - py, py - rect[3], 0.0)
    if dx == 0 and dy == 0:
        return -r
    return math.hypot(dx, dy) - r


RIM = {'-x': lambda r: r[0], '+x': lambda r: P.PW - r[2],
       '-y': lambda r: r[1], '+y': lambda r: P.PH - r[3]}


MIN_GAP = 5.0        # board to board. Nothing is cut between them, so this is
                     # handling room, not acrylic strength - the web that has to
                     # hold is between mount HOLES, checked separately.
MIN_WEB = 3.0        # acrylic between any two cut features


def blocked(a, edge, others):
    """How far a port edge sees before another board is in the way.

    A port edge that reaches the rim with nothing in front of it is the point of
    the whole layout: the cable leaves the frame instead of crossing it.
    """
    x0, y0, x1, y1 = a[1:5]
    far = RIM[edge]((x0, y0, x1, y1))
    who = None
    for b in others:
        bx0, by0, bx1, by1 = b[1:5]
        if edge in ('-x', '+x'):
            if by1 <= y0 or by0 >= y1:
                continue
            d = x0 - bx1 if edge == '-x' else bx0 - x1
        else:
            if bx1 <= x0 or bx0 >= x1:
                continue
            d = y0 - by1 if edge == '-y' else by0 - y1
        if 0 <= d < far:
            far, who = d, b[0]
    return far, who


def check(spec, fan=False):
    ps = placed(spec)
    rows, ok = [], True

    def need(label, mm, want):
        nonlocal ok
        ok &= mm >= want
        rows.append((label, mm, want))

    for i, a in enumerate(ps):
        for b in ps[i + 1:]:
            need(f'{a[0]} to {b[0]}', rect_gap(a[1:5], b[1:5]), MIN_GAP)
    holes = [(hx, hy, hd, a[0]) for a in ps for hx, hy in a[5] for hd in (a[6],)]
    worst, pair = 1e9, ''
    for i, h in enumerate(holes):
        for g in holes[i + 1:]:
            w = math.hypot(h[0] - g[0], h[1] - g[1]) - h[2] / 2 - g[2] / 2
            if w < worst:
                worst, pair = w, f'{h[3]} / {g[3]}'
        for cx, cy in P.lower_columns():
            w = math.hypot(h[0] - cx, h[1] - cy) - h[2] / 2 - P.M3_FREE / 2
            if w < worst:
                worst, pair = w, f'{h[3]} / column'
    need(f'thinnest web between mount holes  ({pair})', worst, MIN_WEB)
    for a in ps:
        need(f'{a[0]} to the nearest rim',
             min(a[1], a[2], P.PW - a[3], P.PH - a[4]), MIN_WEB)
        need(f'{a[0]} to a corner column',
             min(point_gap(a[1:5], cx, cy, P.M3_FREE / 2)
                 for cx, cy in P.lower_columns()), MIN_WEB)
        if fan:
            need(f'{a[0]} to the fan',
                 min([point_gap(a[1:5], *P.FAN_C, P.FAN_BORE / 2)] +
                     [point_gap(a[1:5], P.FAN_C[0] + sx, P.FAN_C[1] + sy,
                                P.FAN_SCREW_D / 2)
                      for sx in (-P.FAN_PITCH / 2, P.FAN_PITCH / 2)
                      for sy in (-P.FAN_PITCH / 2, P.FAN_PITCH / 2)]), MIN_WEB)
    ports = []
    for a in ps:
        for e in sorted(a[7]):
            far, who = blocked(a, e, [b for b in ps if b is not a])
            ports.append((f'{a[0]} port edge {e}', far, who))
    return ps, rows, ports, ok


def draw(path, title, spec, fan=False):
    from PIL import Image, ImageDraw
    sc, M = 3.4, 30
    W, H = int(P.PW * sc) + 2 * M, int(P.PH * sc) + 2 * M + 22
    im = Image.new('RGB', (W, H), (245, 246, 248))
    dr = ImageDraw.Draw(im)
    T = lambda x, y: (M + x * sc, H - M - y * sc)
    dr.rectangle([T(0, P.PH), T(P.PW, 0)], fill=(216, 229, 236),
                 outline=(60, 80, 95), width=2)
    for cx, cy in P.lower_columns():
        dr.ellipse([T(cx - 3, cy + 3), T(cx + 3, cy - 3)],
                   fill=(245, 246, 248), outline=(60, 80, 95), width=2)
    if fan:
        r = P.FAN_BORE / 2
        dr.ellipse([T(P.FAN_C[0] - r, P.FAN_C[1] + r),
                    T(P.FAN_C[0] + r, P.FAN_C[1] - r)],
                   fill=(245, 246, 248), outline=(60, 80, 95), width=2)
        for sx in (-P.FAN_PITCH / 2, P.FAN_PITCH / 2):
            for sy in (-P.FAN_PITCH / 2, P.FAN_PITCH / 2):
                cx, cy = P.FAN_C[0] + sx, P.FAN_C[1] + sy
                dr.ellipse([T(cx - 1.7, cy + 1.7), T(cx + 1.7, cy - 1.7)],
                           fill=(245, 246, 248), outline=(60, 80, 95))
    for name, x0, y0, x1, y1, holes, hd, ports, rot in placed(spec):
        dr.rectangle([T(x0, y1), T(x1, y0)], fill=(196, 212, 222),
                     outline=(35, 50, 62), width=2)
        for e in ports:                      # port edges in orange
            seg = {'-x': ((x0, y0), (x0, y1)), '+x': ((x1, y0), (x1, y1)),
                   '-y': ((x0, y0), (x1, y0)), '+y': ((x0, y1), (x1, y1))}[e]
            dr.line([T(*seg[0]), T(*seg[1])], fill=(214, 110, 32), width=6)
        for hx, hy in holes:
            r = hd / 2
            dr.ellipse([T(hx - r, hy + r), T(hx + r, hy - r)],
                       fill=(245, 246, 248), outline=(35, 50, 62))
        dr.text(T(x0 + 2, y1 - 6), f'{name}  {rot}°', fill=(20, 30, 40))
    dr.text((M, 8), title, fill=(20, 30, 40))
    dr.text((M, H - 16), 'orange = port edge', fill=(140, 90, 40))
    im.save(path)


def main():
    os.makedirs(os.path.join(HERE, 'img'), exist_ok=True)
    allok = True
    for group, table, fan in (('B', PLATE_B, True), ('C', PLATE_C, False)):
        for i, (title, spec) in enumerate(table.items(), 1):
            ps, rows, ports, ok = check(spec, fan)
            blockedn = sum(1 for _, _, who in ports if who)
            allok &= ok
            tag = title.split()[0].lower()
            draw(os.path.join(HERE, 'img', f'variant_{tag}.png'),
                 f'plate {group} - {title}', spec, fan)
            print(f"\nplate {group}  {title}   "
                  f"{'OK' if ok else 'PROBLEM'}, "
                  f"{len(ports) - blockedn}/{len(ports)} port edges reach a rim")
            for label, mm, want in rows:
                flag = '    ' if mm >= want else ' !! '
                print(f"   {flag}{label:46s} {mm:7.2f} mm  (want {want:.0f})")
            for label, far, who in ports:
                tail = (f'{far:6.1f} mm, then {who}' if who
                        else f'{far:6.1f} mm, clear to the rim')
                print(f"        {label:46s} {tail}")
    print('\nall candidates clear' if allok else '\nsomething overlaps')
    return 0 if allok else 1


if __name__ == '__main__':
    raise SystemExit(main())
