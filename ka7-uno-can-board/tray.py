"""One-piece open tray for the KETI KA7_UNO REV1 CAN board, Bambu Lab A1, PLA.

The AC7200 SoM hangs under the carrier (7.2 mm, plus a stick-on heatsink), and every connector (power, CAN, LIN on
the left edge, T1S and RJ45 on the back) overhangs an edge. So this is a tray, not a box: a floor, a low wall that
stops under the board, and four posts on the board's own mounting holes (fab data, ka7_uno_rev1.json). Nothing
above the board; every connector stays reachable. Same design language as prints/tc4d7/tray.py.

  M3 bolt from below (head in the floor) -> post -> board -> nut on top.   4 x M3 x 25 + nuts + washers.

The floor under the SoM is a field of rounded slots for air. The bolt counterbores are on the bed face, so their
ceilings use stepped bridges (a slot across the counterbore, then a square, then the hole) instead of a floating ring.
Prints flat, no supports, no brim.

Run:  uv run --with cadquery --with trimesh --with numpy --with vtk --with matplotlib --with scipy --with networkx \\
        --with manifold3d python ka7-uno-can-board/tray.py
"""
import os
import sys

import cadquery as cq
import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))

BOARD = (70.0, 90.0, 1.6)
MOUNTS = [(3.5, 3.5), (66.5, 3.5), (66.5, 86.5), (3.5, 86.5)]   # board frame (x right, y back), NPTH 3.5
SOM = (14.08, 1.48, 59.08, 56.48)                                 # x0, y0, x1, y1 under the board
SOM_DROP, HEATSINK, AIR = 7.22, 6.0, 3.0                          # as case.py
GAP = 1.5                   # board edge to wall
WALL = 2.4
FLOOR = 4.0
LIFT = 18.0                 # floor top to board underside (>= SOM_DROP + HEATSINK + AIR = 16.2)
WALL_H = 10.0               # the wall stops well under the board's edge connectors
R_CORNER = 6.0
POST = (9.0, 3.4)           # OD, bore (exact fab holes: plain M3 clearance)
ROOT = 2.0
CBORE = (6.4, 3.2)          # M3 socket head 5.5 x 3
BRIDGE = 0.2                # one layer per bridge step
VENT = (3.6, 7.0)           # slot width, pitch

L, W = BOARD[0] + 2 * (GAP + WALL), BOARD[1] + 2 * (GAP + WALL)


def to_tray(x, y):
    return x - BOARD[0] / 2, y - BOARD[1] / 2


def post(p):
    r, a = POST[0] / 2, ROOT
    prof = (cq.Workplane("XZ").moveTo(0, FLOOR - 0.5).lineTo(r + a, FLOOR - 0.5).lineTo(r + a, FLOOR)
            .radiusArc((r, FLOOR + a), a).lineTo(r, FLOOR + LIFT - 0.8)
            .radiusArc((r - 0.8, FLOOR + LIFT), -0.8).lineTo(0, FLOOR + LIFT).close())
    return prof.revolve(360, (0, 0, 0), (0, 1, 0)).translate((p[0], p[1], 0))


def vents():
    """rounded slots along y under the SoM, centred on it"""
    x0, y0, x1, y1 = SOM
    xs = np.arange(x0 + 4, x1 - 3, VENT[1])
    xs = xs - (xs.mean() - (x0 + x1) / 2)
    cy = (y0 + y1) / 2
    return [to_tray(float(x), cy) for x in xs], (y1 - y0) - 8


def tray():
    pts = [to_tray(*h) for h in MOUNTS]
    t = cq.Workplane("XY").rect(L, W).extrude(FLOOR + WALL_H).edges("|Z").fillet(R_CORNER)
    t = t.cut(cq.Workplane("XY").workplane(offset=FLOOR).rect(L - 2 * WALL, W - 2 * WALL)
              .extrude(WALL_H + 1).edges("|Z").fillet(R_CORNER - WALL))
    t = t.faces(">Z").edges().fillet(WALL / 2 - 0.05)
    t = t.faces("<Z").edges().chamfer(0.6)
    for p in pts:
        t = t.union(post(p))
    t = t.cut(cq.Workplane("XY").pushPoints(pts).circle(POST[1] / 2).extrude(FLOOR + LIFT + 1))
    t = t.cut(cq.Workplane("XY").pushPoints(pts).circle(CBORE[0] / 2).extrude(CBORE[1]))
    for n, (sx, sy) in enumerate(((CBORE[0], POST[1]), (POST[1], POST[1]))):      # stepped bridges
        t = t.cut(cq.Workplane("XY").workplane(offset=CBORE[1] + BRIDGE * n).pushPoints(pts).rect(sx, sy).extrude(BRIDGE))
    vp, vl = vents()
    t = t.cut(cq.Workplane("XY").pushPoints(vp).slot2D(vl, VENT[0], 90).extrude(FLOOR + 1))
    return t


def ceiling_check(m):
    """flat downward faces above the bed (they print in mid air), mm2"""
    z0 = m.bounds[0][2]
    c, n, a = m.triangles_center, m.face_normals, m.area_faces
    return a[(n[:, 2] < -0.98) & (c[:, 2] > z0 + 0.3)].sum()


def preview(m, path):
    sys.path.insert(0, os.path.expanduser("~/prints/crab-arm"))
    import render_v2 as R
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    board = trimesh.load(os.path.join(HERE, "ka7_uno_rev1.stl"))
    board.apply_translation((-BOARD[0] / 2, -BOARD[1] / 2, FLOOR + LIFT))
    white, pcb = (0.92, 0.92, 0.91), (0.13, 0.30, 0.24)
    views = [("tray", R._cam(215, 34, 300, (0, 0, 8)), [(m, white)]),
             ("with the board", R._cam(215, 26, 320, (0, 0, 14)), [(m, white), (board, pcb)]),
             ("underside: vents under the SoM", R._cam(205, -40, 300, (0, 0, 4)), [(m, white)])]
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.6))
    for ax, (title, cam, scene) in zip(axs, views):
        ax.imshow(R.render(scene, cam, size=(900, 680)))
        ax.set_title(title, fontsize=11, color="#555")
        ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(path, dpi=110)


if __name__ == "__main__":
    out = os.path.join(HERE, "ka7_tray.stl")
    cq.exporters.export(tray(), out, tolerance=0.02, angularTolerance=0.1)
    m = trimesh.load(out)
    # the SoM + heatsink must clear the floor; the board must sit only on the posts
    clear = LIFT - (SOM_DROP + HEATSINK)
    print(f"tray {L:.1f} x {W:.1f} x {FLOOR + LIFT:.1f}  watertight={m.is_watertight}  bodies={len(m.split())}  "
          f"{len(vents()[0])} vent slots  heatsink-to-floor {clear:.1f} mm  floating ceiling {ceiling_check(m):.0f} mm2")
    preview(m, os.path.join(HERE, "ka7_tray.png"))
