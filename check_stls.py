#!/usr/bin/env python3
"""Validate every printable STL in the repo the way a print service's uploader does.

(`*mock*.stl` is skipped - board_mock.stl is a preview aid, not a part.)

    python3 check_stls.py

Checks each mesh is watertight, consistently wound, a single body, free of
degenerate faces and of positive volume, and prints its bounding box and
material volume so an order can be priced at a glance.
"""
import glob
import sys

import trimesh

MIN_WALL = 1.0   # MJF PA12-HP minimum wall, for reference in the printout


def check(path):
    m = trimesh.load(path)
    e = m.bounds[1] - m.bounds[0]
    degenerate = int((m.area_faces < 1e-9).sum())
    ok = (m.is_watertight and m.is_winding_consistent and m.body_count == 1
          and degenerate == 0 and m.volume > 0)
    return ok, e, m.volume / 1000, m.body_count, degenerate


def main():
    paths = [p for p in sorted(glob.glob('*/*.stl')) if 'mock' not in p]
    if not paths:
        sys.exit('no STLs found - run from the repo root')
    width = max(len(p) for p in paths)
    print(f"{'file':{width}}  {'bounding box (mm)':>26}  {'cm3':>7}  result")
    print('-' * (width + 46))
    failed, total = [], 0.0
    for p in paths:
        ok, e, vol, bodies, degen = check(p)
        total += vol
        note = '' if ok else f"  <- bodies={bodies} degenerate={degen}"
        print(f"{p:{width}}  {e[0]:8.1f} x {e[1]:6.1f} x {e[2]:5.1f}  {vol:7.2f}  "
              f"{'PASS' if ok else 'FAIL'}{note}")
        if not ok:
            failed.append(p)
    print('-' * (width + 46))
    print(f"{len(paths)} files, {total:.1f} cm3 total "
          f"(not all variants are meant to be ordered together)")
    if failed:
        sys.exit(f"FAILED: {', '.join(failed)}")
    print(f"all watertight, single-body, no degenerate faces; "
          f"designed minimum wall >= {MIN_WALL} mm")


if __name__ == '__main__':
    main()
