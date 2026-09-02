#!/usr/bin/env python3
"""Pull the KETI KA7_UNO REV1 board out of its fabrication DXF, once.

    python3 extract_ka7.py TOP.dxf [BOT.dxf]   # -> ka7_uno_rev1.json

The fabrication set is not in this repo - it is KETI's, it is large, and it is
not needed twice. This reads it and writes a compact JSON that everything else
here uses, so the model builds with no vendor files present.

What comes out is exact where the DXF is exact and stated as a guess where it is
not:

  outline        BOARD_OUTLINE, vertices and bulges   exact - and it is NOT a
                 plain rectangle: there is a 0.75 x 5.6 mm notch in the right
                 edge with two 90 degree rounded corners
  holes          every drilled hole, by diameter      exact
  pads           PART_PADS_* and PART_HOLES_*         exact
  silkscreen     SILKSCREEN_OUTLINES_TOP segments     exact
  labels         the silkscreen TEXT entities         exact - and they turn out
                 to be function names (CAN0, LIN1, ETH0, POWER IN) rather than
                 reference designators, which is more use for reading the board
  components     clustered from the pads              positions exact,
                                                      HEIGHTS GUESSED

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
# A cluster containing a THROUGH-HOLE pad is a through-hole part, which on this
# board means a connector, a terminal block or a header. That one bit sorts them
# far better than size and edge-proximity did: on the first pass only 2 of 206
# clusters came out as connectors, while the silkscreen names CAN0, CAN1, LIN0,
# LIN1, both T1S pairs, POWER IN and two NodeID selectors.
# Only the HOLES layer. PART_PADS_LAYER_TOP is pads, not holes - including it
# made 78 of 206 clusters look through-hole, which is most of the board.
TH_LAYERS = {'PART_HOLES_LAYER_TOP'}
# Through-hole pads get their own, wider clustering gap. A 2.54 mm header pitch
# with 1.5 mm pads leaves 1.04 mm between pins, and terminal-block rows sit
# 5.08 mm apart - so at the SMD gap of 0.9 every pin came out as its own
# "component", 78 of them. 4.5 gathers both a header's pins and a screw
# terminal's two rows into one body, and the next-nearest through-hole part on
# this board is far enough away not to be swept in with them.
TH_GAP = 4.5
MOUNT_D = 3.5


def polylines(path, layer):
    """LWPOLYLINEs on a layer, as [(x, y, bulge), ...] per polyline.

    Bulge is a per-vertex group 42 that applies to the segment leaving that
    vertex, so it has to be read positionally - a flat findall loses which
    vertex owns which bulge, and the board outline has exactly two of them.
    """
    t = [l.strip() for l in open(path, errors='ignore')]
    out, i = [], 0
    while i < len(t) - 1:
        if t[i] == '0' and t[i + 1] == 'LWPOLYLINE':
            j, pairs = i + 2, []
            while j < len(t) - 1 and t[j] != '0':
                pairs.append((t[j], t[j + 1]))
                j += 2
            lay = [v for k, v in pairs if k == '8']
            if lay and lay[0] == layer:
                verts, cur = [], None
                for k, v in pairs:
                    if k == '10':
                        cur = [float(v), 0.0, 0.0]
                        verts.append(cur)
                    elif k == '20' and cur:
                        cur[1] = float(v)
                    elif k == '42' and cur:
                        cur[2] = float(v)
                if verts:
                    out.append([tuple(v) for v in verts])
            i = j
        else:
            i += 1
    return out


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


def boxes(ents, layers, mark=None):
    """Pad bounding boxes. With `mark`, each carries a flag: is it on one of
    those layers - i.e. is it a through-hole pad rather than an SMD one."""
    out = []
    for k, b in ents:
        lay = b.get('8', [''])[0]
        if lay not in layers:
            continue
        if k == 'CIRCLE':
            x, y, r = float(b['10'][0]), float(b['20'][0]), float(b['40'][0])
            bb = (x - r, x + r, y - r, y + r)
        elif k == 'LWPOLYLINE':
            xs = [float(v) for v in b.get('10', [])]
            ys = [float(v) for v in b.get('20', [])]
            if not (xs and ys):
                continue
            bb = (min(xs), max(xs), min(ys), max(ys))
        else:
            continue
        out.append(bb + ((lay in mark,) if mark else ()))
    return out


def cluster(pads, gap):
    """-> (x0, x1, y0, y1, pad count, any pad through-hole) per component."""
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
             min(p[2] for p in g), max(p[3] for p in g), len(g),
             any(len(p) > 4 and p[4] for p in g))
            for g in groups.values()]


def classify(x0, x1, y0, y1, npads, th, bw, bh):
    """Height above the PCB. GUESSED - there is no height data in a Gerber set.

    `th` - does the cluster contain a through-hole pad - does most of the work.
    A through-hole part on this board is a connector, a terminal block or a
    header, and those are the tall things. Size then separates the three.
    """
    w, h, area = x1 - x0, y1 - y0, (x1 - x0) * (y1 - y0)
    if th:
        if area >= 60.0:
            return 11.0, 'connector'          # RJ45-class, terminal blocks
        if max(w, h) > 3 * max(min(w, h), 0.1):
            return 8.5, 'header'              # a pin row
        return 6.0, 'header'
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

    # every drilled hole, and the pads and silkscreen that make it look like a
    # board rather than a slab
    holes = []
    for k, b in e:
        if k != 'CIRCLE':
            continue
        lay = b.get('8', [''])[0]
        if not (lay.startswith('MOUNTING_HOLES') or lay.startswith('PART_HOLES')):
            continue
        holes.append([round(float(b['10'][0]), 3), round(float(b['20'][0]), 3),
                      round(float(b['40'][0]) * 2, 3)])
    holes = [list(h) for h in sorted({tuple(h) for h in holes})]

    pads = [[round(v, 3) for v in bb] for bb in boxes(e, PAD_LAYERS)]
    silk = []
    for pl in polylines(top, 'SILKSCREEN_OUTLINES_TOP'):
        for (x0, y0, _), (x1, y1, _) in zip(pl, pl[1:]):
            if (x1 - x0) ** 2 + (y1 - y0) ** 2 > 0.04:      # skip 0.2 mm stubs
                silk.append([round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3)])

    # two passes, because the two kinds of pad want different gaps
    th_pads = [b for b in boxes(e, PAD_LAYERS, mark=TH_LAYERS) if b[4]]
    smd_pads = [b for b in boxes(e, PAD_LAYERS, mark=TH_LAYERS) if not b[4]]
    clusters = cluster(th_pads, TH_GAP) + cluster(smd_pads, CLUSTER_GAP)

    comps = []
    for x0, x1, y0, y1, n, th in sorted(clusters,
                                        key=lambda c: -(c[1] - c[0]) * (c[3] - c[2])):
        z, kind = classify(x0, x1, y0, y1, n, th, bw, bh)
        comps.append(dict(x=round((x0 + x1) / 2, 3), y=round((y0 + y1) / 2, 3),
                          w=round(x1 - x0, 3), h=round(y1 - y0, 3),
                          pads=n, th=th, z=z, kind=kind))

    data = dict(
        name='KETI KA7_UNO REV1',
        outline=[[round(v, 4) for v in p] for p in
                 polylines(top, 'BOARD_OUTLINE')[0]],
        holes=holes,
        pads=pads,
        silk=silk,
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
    print(f"  outline {len(data['outline'])} vertices, "
          f"{sum(1 for v in data['outline'] if v[2])} of them arcs")
    print(f"  {len(holes)} drilled holes, {len(pads)} pads, "
          f"{len(silk)} silkscreen segments")
    print(f"  {len(comps)} components clustered at {CLUSTER_GAP} mm, "
          f"{len(labels)} silkscreen labels")
    import collections
    print("  by kind:", dict(collections.Counter(c['kind'] for c in comps)))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(*sys.argv[1:3])
