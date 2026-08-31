#!/usr/bin/env python3
"""Regenerate every picture in img/ from the current design, in one go.

    python3 render_all.py

Images were being produced ad hoc, which lets them drift from the geometry they
are supposed to show. Everything here reads the same constants and the same
generated DXFs the cutter gets, so a stale picture cannot survive a rerun.
"""
import os
import sys

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..', 'lan9692-evb-case')]

import assembly as A                     # noqa: E402
import make_plates as M                  # noqa: E402
from render_preview import render, rot, W, H   # noqa: E402

IMG = os.path.join(HERE, 'img')
LAYER_COL = {'CUT': (255, 170, 60), 'DIM': (215, 215, 215),
             'ENGRAVE': (255, 80, 80), 'SHEET': (70, 70, 70)}


# --------------------------------------------------------------------------
# DXF previews
def dxf_entities(path):
    t = open(path).read().split('\n')
    out, i = [], 0
    while i < len(t) - 1:
        if t[i] == '0' and t[i + 1] in ('LINE', 'CIRCLE', 'ARC'):
            kind, b, j = t[i + 1], {}, i + 2
            while j < len(t) - 1 and t[j] != '0':
                b[t[j]] = t[j + 1]
                j += 2
            out.append((kind, b))
            i = j
        else:
            i += 1
    return out


def draw_dxf(paths, out, scale=2.0, pad=12, dark=True, size=None, cols=1):
    tiles = []
    for path in paths:
        ents = dxf_entities(path)
        xs = [float(b[k]) for _, b in ents for k in ('10', '11') if k in b]
        ys = [float(b[k]) for _, b in ents for k in ('20', '21') if k in b]
        for kind, b in ents:
            if kind in ('CIRCLE', 'ARC'):
                r = float(b['40'])
                xs += [float(b['10']) - r, float(b['10']) + r]
                ys += [float(b['20']) - r, float(b['20']) + r]
        x0, y0 = min(xs), min(ys)
        w = size[0] if size else max(xs) - x0
        h = size[1] if size else max(ys) - y0
        W, H = int(w * scale) + 2 * pad, int(h * scale) + 2 * pad
        bg = (12, 12, 12) if dark else (255, 255, 255)
        im = Image.new('RGB', (W, H), bg)
        d = ImageDraw.Draw(im)

        def P(x, y):
            return (pad + (x - x0) * scale, H - pad - (y - y0) * scale)

        for kind, b in ents:
            c = LAYER_COL.get(b.get('8'), (120, 120, 120))
            if not dark and c == (215, 215, 215):
                c = (40, 40, 40)
            if not dark and c == (255, 170, 60):
                c = (20, 60, 110)
            if kind == 'LINE':
                d.line([P(float(b['10']), float(b['20'])),
                        P(float(b['11']), float(b['21']))], fill=c, width=2)
            elif kind == 'CIRCLE':
                cx, cy, r = float(b['10']), float(b['20']), float(b['40'])
                d.ellipse([P(cx - r, cy + r), P(cx + r, cy - r)], outline=c, width=2)
            else:
                cx, cy, r = float(b['10']), float(b['20']), float(b['40'])
                a0, a1 = float(b['50']), float(b['51'])
                d.arc([P(cx - r, cy + r), P(cx + r, cy - r)], -a1, -a0, fill=c, width=2)
        tiles.append(im)
    if len(tiles) == 1:
        tiles[0].save(out)
    else:
        rows = (len(tiles) + cols - 1) // cols
        cw = max(t.width for t in tiles)
        chh = max(t.height for t in tiles)
        sheet = Image.new('RGB', (cw * cols, chh * rows), (255, 255, 255))
        for i, t in enumerate(tiles):
            sheet.paste(t, ((i % cols) * cw, (i // cols) * chh))
        sheet.save(out)
    print('  ' + os.path.relpath(out, HERE))


# --------------------------------------------------------------------------
def scene(parts, cols):
    fc = np.vstack([c if np.ndim(c) == 2 else np.tile(c, (len(m.faces), 1))
                    for m, c in zip(parts, cols)])
    return trimesh.util.concatenate(parts), fc


def three_d():
    parts, cols = A.build()
    m, fc = scene(parts, cols)
    m.export(os.path.join(HERE, 'assembly.stl'))
    for name, elev, azim in (('assembly', 22, -54), ('joint_detail', 14, -62),
                             ('assembly_front', 6, -2), ('assembly_top', 89, 0)):
        render(m, elev, azim, face_colors=fc).save(os.path.join(IMG, name + '.png'))
        print(f"  img/{name}.png")
    labelled(22, -54, os.path.join(IMG, 'assembly_labelled.png'))
    labelled(20, -56, os.path.join(IMG, 'exploded_labelled.png'), explode=True)
    ex = A.exploded(list(zip(parts, cols)))
    m, fc = scene([p for p, _ in ex], [c for _, c in ex])
    render(m, 20, -56, face_colors=fc).save(os.path.join(IMG, 'exploded.png'))
    print("  img/exploded.png")
    ap, ac = A.build(upto='A')
    m, fc = scene(ap, ac)
    render(m, 89, 0, face_colors=fc).save(os.path.join(IMG, 'plate_a_board.png'))
    m, fc = scene(ap[:-1], ac[:-1])
    render(m, 89, 0, face_colors=fc).save(os.path.join(IMG, 'plate_a_holes.png'))
    print("  img/plate_a_board.png  img/plate_a_holes.png")
    e = trimesh.load(os.path.join(HERE, 'assembly.stl'))
    print(f"  assembly.stl  {len(e.faces)} faces  "
          f"{'x'.join(f'{v:.0f}' for v in e.bounds[1] - e.bounds[0])} mm")


FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


def visible_ids(mesh, gid, elev, azim):
    """Which group owns each pixel, by the same z-buffer render() uses.

    A label anchored at a 3D point lands wherever that point projects even when
    something else is in front of it - which is how "plate B" ended up pointing
    at plate C's surface. Anchoring instead at the centroid of a part's own
    VISIBLE pixels cannot do that: if a part is hidden it has no pixels and gets
    no label.
    """
    R = rot(elev, azim)
    v = mesh.vertices @ R.T
    lo, hi = v.min(0), v.max(0)
    span = max(hi[0] - lo[0], hi[2] - lo[2]) * 1.08
    sc = min(W, H) / span
    px = (v[:, 0] - (lo[0] + hi[0]) / 2) * sc + W / 2
    py = H / 2 - (v[:, 2] - (lo[2] + hi[2]) / 2) * sc
    depth = v[:, 1]

    ids = np.full((H, W), -1, np.int32)
    zbuf = np.full((H, W), np.inf)
    order = np.argsort(-mesh.triangles_center @ R.T @ np.array([0, 1, 0]))
    for f in order:
        i0, i1, i2 = mesh.faces[f]
        xs = np.array([px[i0], px[i1], px[i2]])
        ys = np.array([py[i0], py[i1], py[i2]])
        zs = np.array([depth[i0], depth[i1], depth[i2]])
        x0, x1 = int(max(np.floor(xs.min()), 0)), int(min(np.ceil(xs.max()) + 1, W))
        y0, y1 = int(max(np.floor(ys.min()), 0)), int(min(np.ceil(ys.max()) + 1, H))
        if x0 >= x1 or y0 >= y1:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        d = ((ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2]))
        if abs(d) < 1e-9:
            continue
        w0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / d
        w1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / d
        w2 = 1 - w0 - w1
        ins = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not ins.any():
            continue
        z = w0 * zs[0] + w1 * zs[1] + w2 * zs[2]
        sl = (slice(y0, y1), slice(x0, x1))
        win = ins & (z < zbuf[sl])
        zb = zbuf[sl]; zb[win] = z[win]; zbuf[sl] = zb
        ib = ids[sl]; ib[win] = gid[f]; ids[sl] = ib
    return ids


def project(mesh, elev, azim, pts):
    """Same camera render() uses, so a 3D point lands on the right pixel."""
    R = rot(elev, azim)
    v = mesh.vertices @ R.T
    lo, hi = v.min(0), v.max(0)
    span = max(hi[0] - lo[0], hi[2] - lo[2]) * 1.08
    s = min(W, H) / span
    p = np.asarray(pts, float) @ R.T
    return np.stack([(p[:, 0] - (lo[0] + hi[0]) / 2) * s + W / 2,
                     H / 2 - (p[:, 2] - (lo[2] + hi[2]) / 2) * s], 1)


def labelled(elev, azim, out, explode=False):
    """Render, then hang a name off each part's own visible pixels.

    The names come from build() itself - assembly.NAMES, one per part - so
    nothing here reconstructs build()'s ordering, which is the mistake that put
    "plate B" over plate C's surface.
    """
    parts, cols = A.build()
    names = list(A.NAMES)
    if explode:
        ex = A.exploded(list(zip(parts, cols)))
        parts = [p for p, _ in ex]
        cols = [c for _, c in ex]
    order = []
    for n in names:
        if n and n not in order:
            order.append(n)
    gid = np.concatenate([np.full(len(p.faces),
                                  order.index(n) if n in order else -1, np.int32)
                          for p, n in zip(parts, names)])
    groups = [(n, None) for n in order]
    mesh, fc = scene(parts, cols)
    im = render(mesh, elev, azim, face_colors=fc).convert('RGB')
    ids = visible_ids(mesh, gid, elev, azim)

    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype(FONT, 21)
    except OSError:
        f = ImageFont.load_default()

    anchors = []
    for g, (name, _) in enumerate(groups):
        ys, xs = np.nonzero(ids == g)
        if len(xs) < 60:                      # hidden, or a sliver - no label
            continue
        anchors.append([name, float(np.median(xs)), float(np.median(ys)), len(xs)])

    cols_ = {0: [], 1: []}
    for a in anchors:
        cols_[0 if a[1] < W / 2 else 1].append(a)
    for side, rows in cols_.items():
        rows.sort(key=lambda r: r[2])
        step = (H - 110) / max(len(rows), 1)
        for i, r in enumerate(rows):
            ly = 55 + step * (i + 0.5)
            lx = 16 if side == 0 else W - 16
            anch = 'la' if side == 0 else 'ra'
            d.line([(r[1], r[2]), (lx + (150 if side == 0 else -150), ly),
                    (lx + (10 if side == 0 else -10), ly)],
                   fill=(120, 128, 140), width=2)
            d.ellipse([r[1] - 4, r[2] - 4, r[1] + 4, r[2] + 4], fill=(230, 90, 70))
            box = d.textbbox((lx, ly - 12), r[0], font=f, anchor=anch)
            d.rectangle([box[0] - 6, box[1] - 3, box[2] + 6, box[3] + 3],
                        fill=(255, 255, 255), outline=(200, 205, 212))
            d.text((lx, ly - 12), r[0], font=f, fill=(30, 34, 40), anchor=anch)
    im.save(out)
    print(f"  {os.path.relpath(out, HERE)}  ({len(anchors)} of {len(groups)} "
          f"parts visible enough to label)")


def hole_check():
    S, PAD, GAP = 6.0, 46, 30
    boards = [('TC397 APPLICATION KIT', M.TC_BOARD,
               M.TC_HOLES + M.TC_EXTRA_HOLES, M.TC_HOLE_D, M.TC_SLOTTED),
              ('LILYGO T-ETH-ELITE', M.ETH_BOARD, M.ETH_HOLES,
               M.ETH_HOLE_D, M.ETH_SLOTTED)]
    Wt = sum(int(b[1][0] * S) for b in boards) + PAD * 3 + GAP
    Ht = max(int(b[1][1] * S) for b in boards) + PAD * 2 + 30
    im = Image.new('RGB', (Wt, Ht), 'white')
    d = ImageDraw.Draw(im)
    d.text((PAD - 20, 12), "CHECK AGAINST THE REAL BOARDS - from the bottom-left "
                           "PCB corner, mm.  ring = round hole, bar = slot",
           fill=(180, 40, 30))
    x0 = PAD
    for name, (bw, bh), holes, hd, slotted in boards:
        def P(x, y):
            return (x0 + x * S, Ht - PAD - y * S)
        a, b = P(0, bh), P(bw, 0)
        d.rectangle([a[0], a[1], b[0], b[1]], outline=(40, 140, 70), width=3)
        d.text((a[0], a[1] - 18), f"{name}   {bw:.3f} x {bh:.3f}", fill=(20, 110, 50))
        for i, (hx, hy) in enumerate(holes):
            p = P(hx, hy)
            r = hd / 2 * S + 3
            if i in slotted:
                half = (M.MOUNT_SLOT - hd) / 2 * S
                d.rounded_rectangle([p[0] - half - r, p[1] - r, p[0] + half + r,
                                     p[1] + r], radius=r, outline=(200, 40, 30),
                                    width=3)
            else:
                d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r],
                          outline=(200, 40, 30), width=3)
            d.text((p[0] + r + 4, p[1] - 7), f"{hx:.2f}, {hy:.2f}", fill=(160, 20, 10))
        x0 += int(bw * S) + GAP + PAD // 2
    im.save(os.path.join(IMG, 'hole_check.png'))
    print("  img/hole_check.png")


def plate_b_layout():
    S, PAD = 4.2, 26
    W = int(M.PW * S) + 2 * PAD
    H = int(M.PH * S) + 2 * PAD + 18
    im = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(im)

    def P(x, y):
        return (PAD + x * S, H - PAD - y * S)
    d.rounded_rectangle([P(0, M.PH)[0], P(0, M.PH)[1], P(M.PW, 0)[0], P(M.PW, 0)[1]],
                        radius=M.PLATE_R * S, outline=(20, 60, 110), width=3)
    lo = M.BOARD_OFF
    d.rectangle([P(lo[0], lo[1] + M.BH), P(lo[0] + M.BW, lo[1])],
                outline=(205, 205, 205), width=2)
    d.text(P(lo[0] + 4, lo[1] + 3), "LAN9692 below", fill=(160, 160, 160))
    for (name, cx, cy), (bw, bh), holes, hd, slotted in M.board_mounts():
        ox, oy = cx - bw / 2, cy - bh / 2
        d.rectangle([P(ox, oy + bh), P(ox + bw, oy)], outline=(40, 140, 70), width=3)
        d.text(P(ox + 3, oy + bh - 6), name, fill=(20, 110, 50))
        for i, (hx, hy) in enumerate(holes):
            p = P(ox + hx, oy + hy)
            r = 2.4
            if i in slotted:
                half = M.MOUNT_SLOT / 2 * S
                d.rounded_rectangle([p[0] - half, p[1] - r, p[0] + half, p[1] + r],
                                    radius=r, fill=(230, 90, 70))
            else:
                d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=(230, 90, 70))
        if 'TC397' in name:
            d.line([P(ox + 4, oy + 100), P(ox + bw - 4, oy + 100)],
                   fill=(230, 140, 40), width=5)
            d.text(P(ox + bw * 0.3, oy + 103), "ports", fill=(200, 110, 20))
        elif name in M.FIM:
            # both connectors sit on the board's two SHORT edges, so which pair
            # of footprint edges that is depends on how the board was turned
            kind = 'RJ45' if 'RJ45' in name else 'MATEnet'
            if M.FIM[name]['rot'] == 90:
                for yy, lab in ((oy + bh, f"{kind} out"), (oy, f"{kind} in")):
                    d.line([P(ox + 4, yy), P(ox + bw - 4, yy)],
                           fill=(230, 140, 40), width=5)
                    d.text(P(ox + 1, yy + (2 if lab.endswith('out') else -7)),
                           lab, fill=(200, 110, 20))
            else:
                for xx, lab in ((ox, f"{kind} out"), (ox + bw, f"{kind} in")):
                    d.line([P(xx, oy + 4), P(xx, oy + bh - 4)],
                           fill=(230, 140, 40), width=5)
                    d.text(P(xx - (26 if lab.endswith('out') else -2),
                             oy + bh * 0.5), lab, fill=(200, 110, 20))
        else:
            # T-ETH-Elite: USB-C on one long edge, RJ45 on one short edge. Which
            # pair depends on how the zone turned it.
            flip = dict(M.ZONES_ROT).get(name, 0) == 180
            uy = (oy + bh) if flip else oy
            rx = ox if flip else (ox + bw)
            d.line([P(ox + 4, uy), P(ox + bw - 4, uy)], fill=(230, 140, 40), width=5)
            d.line([P(rx, oy + 4), P(rx, oy + bh - 4)], fill=(230, 140, 40), width=5)
            d.text(P(ox + 8, uy + (3 if flip else -8)), "USB-C", fill=(200, 110, 20))
            d.text(P(rx + (-30 if flip else 2), oy + bh * 0.4), "RJ45",
                   fill=(200, 110, 20))
    r = M.FAN_BORE / 2
    d.ellipse([P(M.FAN_C[0] - r, M.FAN_C[1] + r), P(M.FAN_C[0] + r, M.FAN_C[1] - r)],
              outline=(120, 60, 160), width=3)
    d.text(P(M.FAN_C[0] - 6, M.FAN_C[1] - r - 7), "fan", fill=(120, 60, 160))
    for x, y in M.lower_columns():
        p = P(x, y)
        d.ellipse([p[0] - 3, p[1] - 3, p[0] + 3, p[1] + 3], fill=(110, 110, 110))
    d.text((PAD, 6), "plate B from above - green = boards, red = their mounts "
                     "(bar = slot), orange = port edges", fill=(60, 60, 60))
    im.save(os.path.join(IMG, 'plateB_layout.png'))
    print("  img/plateB_layout.png")


if __name__ == '__main__':
    os.makedirs(IMG, exist_ok=True)
    dxf = os.path.join(HERE, 'dxf')
    print("DXF previews")
    draw_dxf([os.path.join(dxf, 'combined-order.dxf')],
             os.path.join(IMG, 'order_drawing.png'), scale=2.0)
    draw_dxf([os.path.join(dxf, n + '.dxf') for n in M.ORDER_PLATES],
             os.path.join(IMG, 'plates.png'), scale=3.0, dark=False, cols=2)
    draw_dxf([os.path.join(dxf, 'nested-3T.dxf')],
             os.path.join(IMG, 'nested.png'), scale=3.0, dark=False)
    print("diagrams")
    hole_check()
    plate_b_layout()
    print("3D")
    three_d()
