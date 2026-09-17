#!/usr/bin/env python3
"""Build every alternative frame variant and render it in 3D.

    python3 render_variants.py     # -> dxf-<variant>/ + img/variant_<v>_iso.png

Only 'v1' owns dxf/ and the order zip. Everything here writes to its own folder
and its own images, so an alternative can be looked at - and spun in the web
viewer - without any chance of being the file that gets sent to a shop.
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..', 'lan9692-evb-case')]

import make_plates as M                  # noqa: E402
import assembly as A                     # noqa: E402
import render_all as R                   # noqa: E402

ALTERNATIVES = [v for v in M.VARIANTS if v != 'v1']


def load(variant):
    """Re-import the design with a different variant selected."""
    os.environ['FRAME_VARIANT'] = variant
    importlib.reload(M)
    importlib.reload(A)
    importlib.reload(R)
    return M, A, R


def build(variant):
    m, a, r = load(variant)
    m.main()
    ok = a.checks()
    out = os.path.join(HERE, 'img', f'variant_{variant.replace("+", "")}_iso.png')
    r.labelled(26, -54, out)
    print(f"  {os.path.relpath(out, HERE)}")
    return ok


if __name__ == '__main__':
    for v in ALTERNATIVES:
        print(f"\n=== {v} ===")
        build(v)
    load('v1')       # leave the modules as the shipped design
    print("\nback to v1")
