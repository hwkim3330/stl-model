#!/usr/bin/env python3
"""Render each enclosure variant with the board in it.

The board is `board_mock.py` - the real PCB outline with a block per part at its
pick-and-place position - so these pictures also show whether the port windows
line up with the connectors.

    python3 assembly_preview.py          # writes every img/*.png below
"""
import numpy as np
import trimesh

import board_mock
import lan9692_box as B
import lan9692_case as C
from render_preview import render

CASE = (0.29, 0.55, 0.72)
PANEL = (0.22, 0.44, 0.62)
PCB = (0.10, 0.42, 0.22)
PART = (0.16, 0.18, 0.21)


def scene(meshes, colors):
    """colors entries are either an RGB tuple or a ready per-face array."""
    fc = np.vstack([c if np.ndim(c) == 2 else np.tile(c, (len(m.faces), 1))
                    for m, c in zip(meshes, colors)])
    return trimesh.util.concatenate(meshes), fc


def board(z_pcb):
    """The mock board with its own per-face colours."""
    return board_mock.build(z_pcb, colors=True)


def load(name, dz=0.0):
    m = trimesh.load(name)
    if dz:
        m.apply_translation((0, 0, dz))
    return m


def main():
    # open tray, board in place, lid above
    tray = load('lan9692_tray.stl')
    lid = load('lan9692_lid.stl', C.Z_LID)
    b, bc = board(C.Z_PCB)
    m, fc = scene([tray, b, lid], [CASE, bc, CASE])
    render(m, 26, -52, face_colors=fc).save('img/assembly.png')

    # closed box, lid off so the board and the port windows are both visible
    for prefix, tag in (('lan9692_box_', 'box'), ('lan9692_boxsolid_', 'boxsolid')):
        parts = [load(prefix + 'tray.stl'), load(prefix + 'front.stl'),
                 load(prefix + 'rear.stl')]
        cols = [CASE, PANEL, PANEL]
        bb, bc = board(B.Z_PCB)
        m, fc = scene(parts + [bb], cols + [bc])
        render(m, 30, -50, face_colors=fc).save(f'img/{tag}_with_board.png')

        m, fc = scene(parts + [bb, load(prefix + 'lid.stl', B.Z_LID)],
                      cols + [bc, CASE])
        render(m, 24, -55, face_colors=fc).save(f'img/{tag}_assembly.png')
        # low front view: connectors sitting in their windows
        render(m, 8, -4, face_colors=fc).save(f'img/{tag}_front_ports.png')
    print('wrote img/assembly.png, img/box_*.png, img/boxsolid_*.png')


if __name__ == '__main__':
    main()
