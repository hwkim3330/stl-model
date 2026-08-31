#!/usr/bin/env python3
"""Pull the KETI KA7_UNO REV1 board out of its fabrication DXF, once.

    python3 extract_ka7.py TOP.dxf [BOT.dxf]   # -> ka7_uno_rev1.json

The fabrication set is not in this repo - it is KETI's, it is large, and it is
not needed twice. This reads it and writes a compact JSON that everything else
here uses, so the model builds with no vendor files present.

What comes out is exact where the DXF is exact and stated as a guess where it is
not:

  outline        BOARD_OUTLINE layer            exact
  mount holes    MOUNTING_HOLES_LAYER_TOP       exact, the Ø3.5 ones
  labels         the silkscreen TEXT entities   exact - and they turn out to be
                 function names (CAN0, LIN1, ETH0, POWER IN) rather than
                 reference designators, which is more use for reading the board
  components     clustered from the pads        positions exact, HEIGHTS GUESSED

There is no pick-and-place file in the Gerber set, so a component is recovered as
a cluster of pads: every pad and hole on the top side, joined where two of them
come within CLUSTER_GAP. 0.9 mm is the value that keeps an 0402's two pads
together without merging neighbouring parts - 0.5 splits passives into separate
"components", 1.3 starts fusing adjacent ICs.
"""
import json
import os
import sys

CLUSTER_GAP = 0.9
PAD_LAYERS = {'PART_PADS_SMD_TOP', 'PART_PADS_LAYER_TOP', 'PART_HOLES_LAYER_TOP'}
MOUNT_D = 3.5


def parse(path):
    t = [l.strip() for l in open(path, errors='ignore')]
    ents, i = [], 0
    while i < len(t) - 1:
        if t[i] == '0' and t[i + 1] in ('CIRCLE', 'LWPOLYLINE', 'TEXT', 'LINE', 'ARC'):
            kind, b, j = t[i + 1], {}, i + 2
            while j < len(t) - 1 and t[j] != '0':
                b.setdefault(t[j], []).append(t[j + 1])
                j += 2
            ents.append((kind, b))
            i = j
        else:
            i += 1
    return ents


def boxes(ents, layers):
    out = []
    for k, b in ents:
        if b.get('8', [''])[0] not in layers:
            continue
        if k == 'CIRCLE':
            x, y, r = float(b['10'][0]), float(b['20'][0]), float(b['40'][0])
            out.append((x - r, x + r, y - r, y + r))
        elif k == 'LWPOLYLINE':
            xs = [float(v) for v in b.get('10', [])]
            ys = [float(v) for v in b.get('20', [])]
            if xs and ys:
                out.append((min(xs), max(xs), min(ys), max(ys)))
    return out


def cluster(pads, gap):
    parent = list(range(len(pads)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i in range(len(pads)):
        for j in range(i + 1, len(pads)):
            A, B = pads[i], pads[j]
            if (max(A[0] - B[1], B[0] - A[1], 0.0) <= gap
                    and max(A[2] - B[3], B[2] - A[3], 0.0) <= gap):
                a, b = find(i), find(j)
                if a != b:
                    parent[a] = b
    groups = {}
    for i in range(len(pads)):
        groups.setdefault(find(i), []).append(pads[i])
    return [(min(p[0] for p in g), max(p[1] for p in g),
             min(p[2] for p in g), max(p[3] for p in g), len(g))
            for g in groups.values()]


def classify(x0, x1, y0, y1, npads, bw, bh):
    """Height above the PCB. GUESSED - there is no height data in a Gerber set.

    An edge part with real area is a connector and gets 11 mm; everything else is
    scaled off its own footprint, which is what separates an 0402 from a QFN.
    """
    w, h, area = x1 - x0, y1 - y0, (x1 - x0) * (y1 - y0)
    edge = min(x0, y0, bw - x1, bh - y1) < 3.0
    if edge and area > 15.0:
        return 11.0, 'connector'
    if area >= 40.0:
        return 3.0, 'large'
    if npads >= 8:
        return 1.2, 'ic'
    if area < 2.0:
        return 0.6, 'passive'
    return 1.0, 'small'


def main(top, bot=None):
    e = parse(top)
    poly = [(k, b) for k, b in e if b.get('8', [''])[0] == 'BOARD_OUTLINE']
    xs = [float(v) for _, b in poly for v in b.get('10', [])]
    ys = [float(v) for _, b in poly for v in b.get('20', [])]
    bw, bh = max(xs) - min(xs), max(ys) - min(ys)

    mounts = sorted({(round(float(b['10'][0]), 3), round(float(b['20'][0]), 3))
                     for k, b in e if k == 'CIRCLE'
                     and b.get('8', [''])[0].startswith('MOUNTING_HOLES')
                     and abs(float(b['40'][0]) * 2 - MOUNT_D) < 1e-6})

    labels = sorted(((b['1'][0], round(float(b['10'][0]), 2), round(float(b['20'][0]), 2))
                     for k, b in e if k == 'TEXT' and '1' in b),
                    key=lambda t: (-t[2], t[1]))

    comps = []
    for x0, x1, y0, y1, n in sorted(cluster(boxes(e, PAD_LAYERS), CLUSTER_GAP),
                                    key=lambda c: -(c[1] - c[0]) * (c[3] - c[2])):
        z, kind = classify(x0, x1, y0, y1, n, bw, bh)
        comps.append(dict(x=round((x0 + x1) / 2, 3), y=round((y0 + y1) / 2, 3),
                          w=round(x1 - x0, 3), h=round(y1 - y0, 3),
                          pads=n, z=z, kind=kind))

    data = dict(
        name='KETI KA7_UNO REV1',
        source='260827_KA7_UNO_REV1_{GBR,DXF}.zip, fabrication set',
        board=[round(bw, 3), round(bh, 3)],
        mount_holes=[list(m) for m in mounts],
        mount_hole_d=MOUNT_D,
        cluster_gap=CLUSTER_GAP,
        heights='GUESSED from footprint size - no height data exists in a Gerber set',
        labels=[list(l) for l in labels],
        components=comps)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       'ka7_uno_rev1.json')
    json.dump(data, open(out, 'w'), indent=1)
    print(f"wrote {os.path.basename(out)}")
    print(f"  board {bw:.3f} x {bh:.3f} mm, {len(mounts)} Ø{MOUNT_D} mount holes")
    print(f"  {len(comps)} components clustered at {CLUSTER_GAP} mm, "
          f"{len(labels)} silkscreen labels")
    import collections
    print("  by kind:", dict(collections.Counter(c['kind'] for c in comps)))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(*sys.argv[1:3])
