#!/usr/bin/env python3
"""Retolerance Cicicok's T-ETH-Elite case for a printing service.

The original is an FDM-native design (author printed it on an MK3S+ at 0.2 mm)
and every port opening is drawn at the nominal connector size. Measured off the
STLs:

  RJ45 opening      16.11 x 14.20 mm   (X-min wall)
  USB-C opening      8.99 x  3.11 mm   (X-max wall)
  microSD opening   14.00 x  2.20 mm   (Y-max wall)
  bottom cavity     68.006 x 50.006 mm at the rim
  top insert lip    68.010 x 50.010 mm, wall 0.50 mm

Two problems for an ordered part:

1. The lip is 0.004 mm bigger than the cavity it inserts into, i.e. a nominal
   interference fit before any process tolerance is applied.
2. That lip is only 0.50 mm thick. It is one extrusion width on a 0.4 mm nozzle,
   which is why it works on the author's printer, but it is under the 1.0 mm
   minimum wall MJF asks for.

This script fixes both without touching the fit the author designed: the port
openings grow, the clearance comes out of the bottom's cavity (which has 2.0 mm
of wall to give) rather than off the thin lip, and the lip is thickened inward.

    python3 fit_for_print.py

Writes *_fit.stl next to the originals and prints a before/after check.
Requires: trimesh, manifold3d.
"""
import numpy as np
import trimesh
from trimesh.creation import box

# --- measured geometry of the originals (world coords of each STL) -----------
USBC = dict(axis=0, wall=(53.0, 55.0), y=(10.61, 19.60), z=(7.60, 10.70))
RJ45 = dict(axis=0, wall=(-17.0, -15.0), y=(11.00, 27.10), z=(7.60, 21.80))

USBC_TARGET = (10.0, 4.0)    # a USB-C plug shell is 8.34 x 2.56; leaves ~0.8/0.7
RJ45_TARGET = (16.8, 14.8)   # an 8P8C plug with latch is ~11.7 x 13.5

CAVITY_RELIEF = 0.35         # per side, taken off the bottom's 2.0 mm rim wall
LIP_THICKNESS = 1.0          # grow the top's 0.50 mm lip inward to this


def bx(x0, x1, y0, y1, z0, z1):
    m = box(extents=(x1 - x0, y1 - y0, z1 - z0))
    m.apply_translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    return m


def enlarge_port(spec, target):
    """Cutter that opens a wall aperture out to `target`, keeping its centre."""
    (w0, w1), (a0, a1), (b0, b1) = spec['wall'], spec['y'], spec['z']
    ac, bc = (a0 + a1) / 2, (b0 + b1) / 2
    aw, bw = target
    return bx(w0 - 1, w1 + 1, ac - aw / 2, ac + aw / 2, bc - bw / 2, bc + bw / 2)


def _world_xy(to_3d, coords):
    """Map 2D section coordinates back into the mesh's own XY frame."""
    pts = np.array([[x, y, 0, 1] for x, y in coords]).T
    w = (to_3d @ pts).T[:, :2]
    return w[:, 0].min(), w[:, 1].min(), w[:, 0].max(), w[:, 1].max()


def _slice(mesh, z):
    sec = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    return sec.to_planar() if sec is not None else (None, None)


def cavity_rect(mesh, z):
    """World-XY box of the largest interior ring of the section at `z`."""
    pl, to_3d = _slice(mesh, z)
    best = None
    for poly in pl.polygons_full:
        for ring in poly.interiors:
            r = _world_xy(to_3d, list(ring.coords))
            area = (r[2] - r[0]) * (r[3] - r[1])
            if best is None or area > (best[2] - best[0]) * (best[3] - best[1]):
                best = r
    return best


def outline_rect(mesh, z):
    """World-XY box of the outer outline of the section at `z`."""
    pl, to_3d = _slice(mesh, z)
    pts = [c for poly in pl.polygons_full for c in poly.exterior.coords]
    return _world_xy(to_3d, pts)


def rim_frame(mesh, z_lo, grow):
    """Hollow frame that relieves the cavity wall over z_lo..top by `grow`.

    The cavity is not concentric with the outer shell, so its position is taken
    from the section geometry rather than assumed to be centred.
    """
    hi = mesh.bounds[1]
    x0, y0, x1, y1 = cavity_rect(mesh, (z_lo + hi[2]) / 2)
    outer = bx(x0 - grow, x1 + grow, y0 - grow, y1 + grow, z_lo, hi[2] + 1)
    keep = bx(x0, x1, y0, y1, z_lo - 1, hi[2] + 2)
    return (trimesh.boolean.difference([outer, keep], engine='manifold'),
            (x1 - x0, y1 - y0))


def lip_band(mesh, thickness):
    """Solid ring that thickens the insert lip inward, outer face unchanged."""
    lo, hi = mesh.bounds
    skirt = hi[0] - lo[0]
    z0 = None
    for z in np.arange(hi[2] - 0.1, lo[2], -0.1):
        pl, _ = _slice(mesh, z)
        if pl is None:
            continue
        b = pl.bounds
        if (b[1][0] - b[0][0]) > skirt - 1.0:
            z0 = z + 0.1
            break
    x0, y0, x1, y1 = outline_rect(mesh, (z0 + hi[2]) / 2)
    outer = bx(x0, x1, y0, y1, z0, hi[2])
    void = bx(x0 + thickness, x1 - thickness, y0 + thickness, y1 - thickness,
              z0 - 1, hi[2] + 1)
    return (trimesh.boolean.difference([outer, void], engine='manifold'),
            z0, (x1 - x0, y1 - y0))


def report(tag, mesh):
    e = mesh.bounds[1] - mesh.bounds[0]
    print(f"  {tag:34s} {e[0]:6.2f} x {e[1]:6.2f} x {e[2]:5.2f} mm  "
          f"{mesh.volume / 1000:5.2f} cm3  watertight={mesh.is_watertight}")


def main():
    bot = trimesh.load('lilygo_t-eth_elite_case_bottom.stl')
    top = trimesh.load('lilygo_t-eth_elite_case_top.stl')
    report('bottom, as published', bot)
    report('top, as published', top)

    cutters = [enlarge_port(USBC, USBC_TARGET), enlarge_port(RJ45, RJ45_TARGET)]
    frame, cav = rim_frame(bot, bot.bounds[1][2] - 1.9, CAVITY_RELIEF)
    cutters.append(frame)
    bot_fit = trimesh.boolean.difference([bot] + cutters, engine='manifold')

    band, z0, lip = lip_band(top, LIP_THICKNESS)
    top_fit = trimesh.boolean.union([top, band], engine='manifold')

    print(f"\n  cavity {cav[0]:.3f} x {cav[1]:.3f} -> "
          f"{cav[0] + 2 * CAVITY_RELIEF:.3f} x {cav[1] + 2 * CAVITY_RELIEF:.3f} mm "
          f"(rim wall {2.0 - CAVITY_RELIEF:.2f} mm left)")
    print(f"  lip {lip[0]:.3f} x {lip[1]:.3f} from z={z0:.2f}, "
          f"wall 0.50 -> {LIP_THICKNESS:.2f} mm")
    print(f"  USB-C  8.99 x 3.11 -> {USBC_TARGET[0]:.2f} x {USBC_TARGET[1]:.2f} mm")
    print(f"  RJ45  16.11 x 14.20 -> {RJ45_TARGET[0]:.2f} x {RJ45_TARGET[1]:.2f} mm")
    print()
    bot_fit.export('lilygo_t-eth_elite_case_bottom_fit.stl')
    top_fit.export('lilygo_t-eth_elite_case_top_fit.stl')
    report('bottom_fit.stl', bot_fit)
    report('top_fit.stl', top_fit)


if __name__ == '__main__':
    main()
