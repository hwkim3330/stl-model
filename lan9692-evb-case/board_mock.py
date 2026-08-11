#!/usr/bin/env python3
"""Representative EVB-LAN9692-LM model, for previews and for checking the
closed box's port windows against real connector positions.

This is NOT the board. It is the PCB outline plus a block per significant part,
every one placed at the X/Y from the released pick-and-place file. Only the
heights are external: connector datasheets, the SFP MSA, or - for the five
DC-DC daughter modules - an assumption, which is exactly the number `INNER_H`
in the case scripts is waiting on.

    python3 board_mock.py            # -> board_mock.stl + window check
"""
import numpy as np
import trimesh
from trimesh.creation import box, cylinder

from lan9692_case import BW, BH, PCB_T

MODULE_H = 14.0   # <-- the one guess. 3x ADM00987 + 2x PM-LV2 are PCB daughter
                  # modules on Samtec TMM 2 mm headers; no released document
                  # gives their stack height. Everything else below is sourced.

# name, x, y, width(X), depth(Y), height above PCB, source
# THRU holds the parts where only a feature passes through the panel, not the
# body: (protruding feature size across, axis height above the PCB). Both of
# these axis heights are estimates - nothing published gives them.
THRU = {'DC jack J23': (5.5, 6.5),     # 5.5 mm barrel of a 5.5/2.5 plug
        'reset SW2': (3.5, 3.5)}       # tact switch plunger
PARTS = [
    # front edge -------------------------------------------------------------
    *[(f'MATEnet {n}', x, 10.541, 17.75, 21.1, 13.5, 'TE 9-2304372-9')
      for n, x in zip('1234567', (11.684, 30.734, 49.784, 68.834, 87.884,
                                  106.934, 125.984))],
    *[(f'SFP cage {c}', x, 23.4, 14.5, 46.0, 9.8, 'SFP MSA')
      for c, x in zip('ABCD', (145.6, 164.6, 183.6, 202.6))],
    # rear edge --------------------------------------------------------------
    ('RJ45 J33', 58.803, 138.936, 15.88, 21.0, 13.5, '8P8C w/ magnetics'),
    ('USB-C J30', 37.762, 144.866, 9.0, 7.5, 3.2, 'USB-C receptacle'),
    ('OCuLink J21', 118.305, 143.621, 22.0, 8.0, 7.0, 'estimate'),
    ('DC jack J23', 171.283, 140.707, 9.0, 14.5, 11.0, 'PJ-002BH'),
    ('switch SW3', 188.110, 139.767, 12.0, 6.0, 6.0, 'estimate'),
    ('reset SW2', 21.844, 144.018, 6.0, 4.0, 4.0, 'estimate'),
    # tall interior ----------------------------------------------------------
    ('DC-DC U3', 151.568, 127.580, 25.0, 25.0, MODULE_H, 'ADM00987, assumed'),
    ('DC-DC U14', 160.110, 107.770, 25.0, 25.0, MODULE_H, 'ADM00987, assumed'),
    ('DC-DC U10', 174.880, 102.450, 25.0, 25.0, MODULE_H, 'ADM00987, assumed'),
    ('DC-DC U20', 95.440, 116.340, 20.0, 20.0, MODULE_H, 'PM-LV2, assumed'),
    ('DC-DC U17', 27.930, 88.430, 20.0, 20.0, MODULE_H, 'PM-LV2, assumed'),
    ('cap C324', 191.158, 127.071, 10.3, 10.3, 10.2, 'alu F case'),
    ('header J4', 205.190, 100.330, 5.08, 50.8, 5.84, '2x20, 5.84MH'),
    ('header J19', 5.840, 57.850, 5.08, 2.54, 5.84, '1x2, 5.84MH'),
    # flat, for looks --------------------------------------------------------
    ('LAN9692 U4', 189.640, 78.250, 14.0, 18.0, 2.0, 'FBGA-100'),
    *[(f'PHY {d}', x, 36.85, 7.0, 7.0, 0.9, 'QFN-48')
      for d, x in zip('01234567', (10.44, 29.38, 48.43, 67.48, 86.53, 105.58,
                                   124.63))],
]


def bx(x0, x1, y0, y1, z0, z1):
    m = box(extents=(x1 - x0, y1 - y0, z1 - z0))
    m.apply_translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    return m


PCB_COLOR = (0.09, 0.36, 0.20)
PART_COLOR = (0.13, 0.14, 0.16)


def build(z_pcb=0.0, colors=False):
    """PCB top face ends up at z_pcb + PCB_T.

    With colors=True also returns a per-face colour array so previews can tell
    the board apart from the enclosure.
    """
    top = z_pcb + PCB_T
    meshes = [bx(0, BW, 0, BH, z_pcb, top)]
    tint = [PCB_COLOR]
    for name, x, y, w, d, h, _ in PARTS:
        x0, x1 = x - w / 2, x + w / 2
        y0, y1 = y - d / 2, y + d / 2
        # edge connectors are clipped to the board outline for the preview
        meshes.append(bx(max(x0, -1), min(x1, BW + 1), max(y0, -1), min(y1, BH + 1),
                         top, top + h))
        tint.append(PART_COLOR)
    m = trimesh.util.concatenate(meshes)
    if not colors:
        return m
    fc = np.vstack([np.tile(c, (len(q.faces), 1)) for q, c in zip(meshes, tint)])
    return m, fc


def check_windows():
    """Every port window in lan9692_box.py must clear its connector."""
    import lan9692_box as B
    windows = {}
    for side in ('front', 'rear'):
        for p in B.PORTS[side]:
            windows[p['name']] = (p['x'], p['z'])
        for p in B.ROUND_PORTS.get(side, []):
            windows[p['name']] = ((p['x'] - p['d'] / 2, p['x'] + p['d'] / 2),
                                  (p['z'] - p['d'] / 2, p['z'] + p['d'] / 2))
    pairs = [('MATEnet x7', [p for p in PARTS if p[0].startswith('MATEnet')]),
             *[(f'SFP+ {c}', [p for p in PARTS if p[0] == f'SFP cage {c}']) for c in 'ABCD'],
             ('RJ45 J33', [p for p in PARTS if p[0] == 'RJ45 J33']),
             ('USB-C J30', [p for p in PARTS if p[0] == 'USB-C J30']),
             ('OCuLink J21', [p for p in PARTS if p[0] == 'OCuLink J21']),
             ('switch SW3', [p for p in PARTS if p[0] == 'switch SW3']),
             ('DC jack J23', [p for p in PARTS if p[0] == 'DC jack J23']),
             ('reset SW2', [p for p in PARTS if p[0] == 'reset SW2'])]
    print(f"{'window':14s} {'part span':>22s} {'window span':>22s}   "
          f"{'x margin':>9s} {'z margin':>9s}")
    worst = []
    for wname, ps in pairs:
        (wx0, wx1), (wz0, wz1) = windows[wname]
        if wname in THRU:
            size, axis = THRU[wname]
            cx0, cx1 = ps[0][1] - size / 2, ps[0][1] + size / 2
            cz0, ch = axis - size / 2, axis + size / 2
        else:
            cx0 = min(p[1] - p[3] / 2 for p in ps)
            cx1 = max(p[1] + p[3] / 2 for p in ps)
            cz0, ch = 0.0, max(p[5] for p in ps)
        mx = min(cx0 - wx0, wx1 - cx1)
        mz = min(cz0 - wz0, wz1 - ch)
        worst.append((mx, mz, wname))
        print(f"{wname:14s} {cx0:8.2f}..{cx1:8.2f} x{ch:5.1f}h "
              f"{wx0:8.2f}..{wx1:8.2f} x{wz1:5.1f} "
              f"{mx:9.2f} {mz:9.2f}  {'ok' if mx > 0 and mz > 0 else 'CLASH'}")
    bad = [w for mx, mz, w in worst if mx <= 0 or mz <= 0]
    print(f"\ntightest x margin {min(w[0] for w in worst):.2f} mm, "
          f"tightest z margin {min(w[1] for w in worst):.2f} mm")
    tallest = max(PARTS, key=lambda p: p[5])
    print(f"tallest part: {tallest[0]} at {tallest[5]:.1f} mm above the PCB ({tallest[6]})")
    known = [p for p in PARTS if 'assumed' not in p[6]]
    print(f"tallest with a source: {max(known, key=lambda p: p[5])[0]} at "
          f"{max(p[5] for p in known):.1f} mm")
    return not bad


if __name__ == '__main__':
    m = build()
    m.export('board_mock.stl')
    e = m.bounds[1] - m.bounds[0]
    print(f"board mock {e[0]:.2f} x {e[1]:.2f} x {e[2]:.2f} mm "
          f"({len(PARTS)} parts)\n")
    ok = check_windows()
    print("\nall windows clear" if ok else "\nWINDOW CLASH - fix PORTS")
