"""KA7_UNO REV1 closed case v2: base + lid, Bambu Lab A1, PLA. Ports and board data from case.py / the fab set.

What changed from case.py (v1):
- no pillars sticking out of the corners: the walls are 6.5 mm thick blocks with soft R4 corners, and the lid screws
  into M3 heat-set inserts in the wall corners (4 x M3 x 8, heads sunk in the lid);
- the floor is open under the whole AC7200 SoM, so its heatsink passes through (up to 8 mm under the FPGA face) and
  breathes from below (stand the case on 4 rubber feet); the case stays 6 mm lower than v1; the lid is slotted over
  the hot half;
- the port openings run up to the top of the base, so the board drops in with its connectors already overhanging the
  edges, and the lid carries tongues that close each opening down to just above its connector;
- printable as drawn: base floor on the bed, lid top face on the bed, no supports, no brim; the lid's bed-side
  counterbores use stepped bridges, nothing prints in mid air.

Board: 4 x M3 x 6 self-tapping into the posts (Ø2.6 pilots).

Run:  uv run --with cadquery --with trimesh --with numpy --with vtk --with matplotlib --with scipy --with networkx \\
        --with manifold3d python ka7-uno-can-board/case_v2.py
"""
import os
import sys

import cadquery as cq
import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import case as K  # noqa: E402  (ports, board, SoM)

BW, BH, PCB = K.BOARD_W, K.BOARD_H, K.PCB_T
CLEAR, WALL, R_OUT = 0.5, 6.5, 4.0
FLOOR, LID_T, LIP, LIP_GAP = 2.5, 2.5, 2.0, 0.2
AIR = 3.0                               # FPGA face to floor (no heatsink)
POST = (7.0, 2.6)
INSERT = (4.0, 5.5)                     # M3 heat-set insert pocket: dia, depth
HOLE_IN = 3.2                           # insert axis, in from both cavity walls
CB = (6.4, 2.0)                         # M3 head pocket in the lid top
TONGUE_GAP = 0.3

CX0, CY0, CX1, CY1 = -CLEAR, -CLEAR, BW + CLEAR, BH + CLEAR
OX0, OY0, OX1, OY1 = CX0 - WALL, CY0 - WALL, CX1 + WALL, CY1 + WALL
Z_BOARD = FLOOR + K.SOM_DROP + AIR
Z_TOP = Z_BOARD + PCB
Z_LID = Z_TOP + max(p[4] for p in K.PORTS) + 2.0
H = Z_LID + LID_T
CORNERS = [(CX0 - HOLE_IN, CY0 - HOLE_IN), (CX1 + HOLE_IN, CY0 - HOLE_IN),
           (CX1 + HOLE_IN, CY1 + HOLE_IN), (CX0 - HOLE_IN, CY1 + HOLE_IN)]


def rrect(x0, y0, x1, y1, z0, z1, r):
    return (cq.Workplane("XY").workplane(offset=z0).center((x0 + x1) / 2, (y0 + y1) / 2)
            .rect(x1 - x0, y1 - y0).extrude(z1 - z0).edges("|Z").fillet(r))


def box(x0, y0, z0, x1, y1, z1):
    return cq.Workplane("XY").workplane(offset=z0).center((x0 + x1) / 2, (y0 + y1) / 2).rect(x1 - x0, y1 - y0).extrude(z1 - z0)


def openings():
    """(side, a, b, h): the merged port windows from case.py"""
    return [(s, a, b, h) for s, a, b, h, _ in K.windows()]


def window(side, a, b, z0, z1, grow=0.0, through=1.0):
    """a port opening through the wall; through=0 stops it flush with both wall faces (the lid's tongues)"""
    a, b, t = a - grow, b + grow, through
    if side == "back":
        return box(a, CY1 - t, z0, b, OY1 + t, z1)
    if side == "left":
        return box(OX0 - t, a, z0, CX0 + t, b, z1)
    return box(CX1 - t, a, z0, OX1 + t, b, z1)


def slots(x0, y0, x1, y1, z0, z1, w=3.0, pitch=6.0):
    n = int((x1 - x0) // pitch)
    xs = (x0 + x1) / 2 + (np.arange(n) - (n - 1) / 2) * pitch
    return (cq.Workplane("XY").workplane(offset=z0).pushPoints([(float(x), (y0 + y1) / 2) for x in xs])
            .slot2D(y1 - y0, w, 90).extrude(z1 - z0))


def base():
    b = rrect(OX0, OY0, OX1, OY1, 0, Z_LID, R_OUT)
    b = b.faces("<Z").edges().chamfer(0.6)
    b = b.faces(">Z").edges().fillet(0.8)
    b = b.cut(box(CX0, CY0, FLOOR, CX1, CY1, Z_LID + 1))
    for x, y in K.MOUNTS:
        p = cq.Workplane("XY").workplane(offset=FLOOR).center(x, y).circle(POST[0] / 2).extrude(Z_BOARD - FLOOR)
        b = b.union(p)
    b = b.cut(cq.Workplane("XY").workplane(offset=FLOOR).pushPoints(K.MOUNTS).circle(POST[1] / 2).extrude(Z_BOARD))
    for s, a, bb, h in openings():                     # open to the top: the board drops in, the lid closes them
        b = b.cut(window(s, a, bb, Z_TOP - 0.4, Z_LID + 1))
    b = b.cut(cq.Workplane("XY").workplane(offset=Z_LID - INSERT[1]).pushPoints(CORNERS).circle(INSERT[0] / 2).extrude(INSERT[1] + 1))
    # the AC7200 SoM hangs under the carrier with a heatsink on its FPGA (where on the SoM isn't in the fab data), so
    # the floor under the whole SoM is open: any heatsink up to FLOOR + AIR + face gap passes through and breathes
    som = K.SOM
    b = b.cut(rrect(som[0] + 1, som[1] + 1, som[2] - 1, som[3] - 1, -1, FLOOR + 1, 3.0))
    return b


def lid():
    l = rrect(OX0, OY0, OX1, OY1, Z_LID, H, R_OUT)
    l = l.faces(">Z").edges().fillet(0.8)
    l = l.union(box(CX0 + LIP_GAP, CY0 + LIP_GAP, Z_LID - LIP, CX1 - LIP_GAP, CY1 - LIP_GAP, Z_LID + 0.01))
    for s, a, bb, h in openings():                     # tongues down to just over each connector
        l = l.union(window(s, a, bb, Z_TOP + h + 0.5, Z_LID + 0.01, grow=-TONGUE_GAP, through=0.0))
    l = l.cut(box(CX0 + LIP_GAP + 2.0, CY0 + LIP_GAP + 2.0, Z_LID - LIP - 1, CX1 - LIP_GAP - 2.0, CY1 - LIP_GAP - 2.0, Z_LID))
    l = l.cut(cq.Workplane("XY").workplane(offset=Z_LID - 1).pushPoints(CORNERS).circle(1.7).extrude(LID_T + 2))
    l = l.cut(cq.Workplane("XY").workplane(offset=H - CB[1]).pushPoints(CORNERS).circle(CB[0] / 2).extrude(CB[1] + 1))
    # the lid prints top face down: stepped bridges over the head pockets
    for n, (sx, sy) in enumerate(((CB[0], 3.4), (3.4, 3.4))):
        l = l.cut(cq.Workplane("XY").workplane(offset=H - CB[1] - 0.2 * (n + 1)).pushPoints(CORNERS).rect(sx, sy).extrude(0.2))
    l = l.cut(slots(12, 8, 58, 66, Z_LID - LIP - 1, H + 1))
    return l


def mesh(wp, name):
    p = os.path.join(HERE, name + ".stl")
    cq.exporters.export(wp, p, tolerance=0.02, angularTolerance=0.1)
    return trimesh.load(p)


def floating(m, flip=False):
    """flat faces pointing down (up, for the lid printed upside down) above the bed: they print in mid air"""
    m = m.copy()
    if flip:
        m.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
    z0 = m.bounds[0][2]
    c, n, a = m.triangles_center, m.face_normals, m.area_faces
    f = (n[:, 2] < -0.98) & (c[:, 2] > z0 + 0.3)
    return a[f].sum(), m


def preview(b, l, path):
    sys.path.insert(0, os.path.expanduser("~/prints/crab-arm"))
    import render_v2 as R
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    board = trimesh.load(os.path.join(HERE, "ka7_uno_rev1.stl"))
    board.apply_translation((0, 0, Z_BOARD))
    lo = l.copy(); lo.apply_translation((0, 0, 30))
    c = ((OX0 + OX1) / 2, (OY0 + OY1) / 2, H / 2)
    white, pcb = (0.90, 0.90, 0.89), (0.13, 0.30, 0.24)
    views = [("closed", R._cam(230, 28, 330, c), [(b, white), (l, white)]),
             ("lid off: the board drops in", R._cam(215, 32, 360, (c[0], c[1], c[2] + 10)), [(b, white), (board, pcb), (lo, white)]),
             ("ports (left side)", R._cam(180, 12, 300, c), [(b, white), (l, white), (board, pcb)])]
    fig, axs = plt.subplots(1, 3, figsize=(16, 5))
    for ax, (title, cam, scene) in zip(axs, views):
        ax.imshow(R.render(scene, cam, size=(900, 700)))
        ax.set_title(title, fontsize=11, color="#555")
        ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(path, dpi=110)


if __name__ == "__main__":
    b, l = mesh(base(), "ka7_case_v2_base"), mesh(lid(), "ka7_case_v2_lid")
    fb, _ = floating(b)
    fl, lflat = floating(l, flip=True)
    lflat.apply_translation(-lflat.bounds[0])
    lflat.export(os.path.join(HERE, "ka7_case_v2_lid.stl"))        # stored as printed: top face down
    print(f"case v2 {OX1 - OX0:.1f} x {OY1 - OY0:.1f} x {H:.1f} mm (v1 {K.CASE_H:.1f} high over pillars)")
    print(f"  board underside {Z_BOARD:.2f}, FPGA face {Z_BOARD - K.SOM_DROP:.2f} over the floor top {FLOOR}")
    print(f"  base watertight={b.is_watertight} bodies={len(b.split())}  floating {fb:.0f} mm2")
    print(f"  lid  watertight={l.is_watertight} bodies={len(l.split())}  floating (printed top down) {fl:.0f} mm2")
    for s, a, bb, h in openings():
        print(f"  opening {s:5s} {a:6.2f}..{bb:6.2f}  connector height {h}")
    preview(b, l, os.path.join(HERE, "ka7_case_v2.png"))
