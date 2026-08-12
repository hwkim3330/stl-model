#!/usr/bin/env python3
"""Render the LAN9692 box with another case bolted to its lid deck.

    python3 stack_preview.py        # -> img/stack_s31.png, img/stack_tc397.png

The deck is four M3 bosses on a 45 mm square on the LAN9692 box lid; the
ESP32-S31 and TC397 trays carry matching Ø3.4 holes through their floors, on
the same square, so either bolts on in either orientation. Their own feet are
shorter than the 4 mm bosses, so nothing fouls the lid.
"""
import os
import sys

import numpy as np
import trimesh

ROOT = os.path.dirname(os.path.abspath(__file__))
L9 = os.path.join(ROOT, 'lan9692-evb-case')
S31 = os.path.join(ROOT, 'esp32-s31-coreboard-case')
TC = os.path.join(ROOT, 'tc397-triboard-case')
sys.path[:0] = [L9, S31, TC]

import lan9692_box as B                              # noqa: E402
from render_preview import render                    # noqa: E402

CASE = (0.29, 0.55, 0.72)
PANEL = (0.22, 0.44, 0.62)
UPPER = (0.55, 0.60, 0.66)
PCB = (0.09, 0.36, 0.20)


def load(d, name, offset=(0, 0, 0), rot=0.0):
    m = trimesh.load(os.path.join(d, name))
    if rot:
        m.apply_transform(trimesh.transformations.rotation_matrix(
            np.radians(rot), [0, 0, 1], m.centroid))
    m.apply_translation(offset)
    return m


def deck_origin():
    """World point the stacked case's board centre lands on, and its base z."""
    cx, cy = B.DECK['x'], B.DECK['y']
    z = B.Z_LID + B.LID_T + B.DECK['boss_h']
    return cx, cy, z


def base_box(with_board=True):
    import board_mock
    parts = [load(L9, 'lan9692_box_tray.stl'), load(L9, 'lan9692_box_front.stl'),
             load(L9, 'lan9692_box_rear.stl'),
             load(L9, 'lan9692_box_lid.stl', (0, 0, B.Z_LID))]
    cols = [CASE, PANEL, PANEL, CASE]
    if with_board:
        m, fc = board_mock.build(B.Z_PCB, colors=True)
        parts.append(m)
        cols.append(fc)
    return parts, cols


def scene(meshes, colors, out, elev=24, azim=-55):
    fc = np.vstack([c if np.ndim(c) == 2 else np.tile(c, (len(m.faces), 1))
                    for m, c in zip(meshes, colors)])
    render(trimesh.util.concatenate(meshes), elev, azim,
           face_colors=fc).save(os.path.join(ROOT, out))
    print('wrote', out)


def main():
    os.makedirs(os.path.join(ROOT, 'img'), exist_ok=True)
    dx, dy, dz = deck_origin()

    import esp32_s31_case as S
    parts, cols = base_box()
    off = (dx - S.BW / 2, dy - S.BH / 2, dz)
    parts += [load(S31, 'esp32_s31_tray.stl', off),
              load(S31, 'esp32_s31_lid.stl',
                   (off[0], off[1], off[2] + S.Z_LID))]
    cols += [UPPER, UPPER]
    scene(parts, cols, 'img/stack_s31.png')

    import tc397_case as T
    parts, cols = base_box()
    # 90 deg so the 165 mm case lies across the 233.8 mm lid instead of
    # overhanging its 155.7 mm depth
    tray = load(TC, 'tc397_tray.stl', rot=90)
    lid = load(TC, 'tc397_lid.stl', rot=90)
    lid.apply_translation((0, 0, T.Z_LID))
    for m in (tray, lid):
        c = (T.BW / 2, T.BH / 2)
        m.apply_translation((dx - c[1], dy - c[0], dz))
    parts += [tray, lid]
    cols += [UPPER, UPPER]
    scene(parts, cols, 'img/stack_tc397.png', elev=22, azim=-58)


if __name__ == '__main__':
    main()
