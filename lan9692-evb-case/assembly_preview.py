#!/usr/bin/env python3
"""Render tray + PCB + lid together so the fit can be eyeballed.

The PCB slab is drawn for the preview only - it is not part of any STL.
    python3 assembly_preview.py [out.png]
"""
import sys
import sys

import numpy as np
import trimesh

import lan9692_case as C
from render_preview import render


def main(out='assembly.png', elev=26.0, azim=-52.0, with_lid=True):
    parts, colors = [], []
    tray = trimesh.load('lan9692_tray.stl')
    parts.append(tray)
    colors.append((0.29, 0.55, 0.72))

    pcb = trimesh.creation.box(extents=(C.BW, C.BH, C.PCB_T))
    pcb.apply_translation((C.BW / 2, C.BH / 2, C.Z_PCB + C.PCB_T / 2))
    parts.append(pcb)
    colors.append((0.10, 0.42, 0.22))

    if with_lid:
        lid = trimesh.load('lan9692_lid.stl')
        lid.apply_translation((0, 0, C.Z_LID))
        parts.append(lid)
        colors.append((0.29, 0.55, 0.72))

    face_colors = np.vstack([np.tile(c, (len(p.faces), 1))
                             for p, c in zip(parts, colors)])
    render(trimesh.util.concatenate(parts), elev, azim,
           face_colors=face_colors).save(out)
    print('wrote', out)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'assembly.png')
