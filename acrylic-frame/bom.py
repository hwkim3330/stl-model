#!/usr/bin/env python3
"""Bill of materials for the LAN9692 acrylic frame.

    python3 bom.py        # -> BOM.csv, and prints it as a table

Quantities are derived from the fastener stack, not guessed:

  board  -> plate A   8 x F/F standoff, screwed from under plate A and again
                      from on top of the board
  plate  -> plate     8 x M/F standoff, the upper one's male end passing through
                      the plate into the lower one's female end
  plate C             4 screws from above into the top standoffs
"""
import csv
import os

# group, item, spec, qty, note
BOM = [
    ('acrylic', 'Plate A - bottom', 'clear acrylic 5 mm, 250 x 180, plate-a-bottom-5T.dxf', 1,
     'carries the LAN9692'),
    ('acrylic', 'Plate B - middle', 'clear or smoke acrylic 5 mm, 250 x 180, plate-b-middle-5T.dxf', 1,
     'fan under, modules on top'),
    ('acrylic', 'Plate C - top', 'clear acrylic 3 mm, 250 x 180, plate-c-top-3T.dxf', 1,
     'guard + intake slots'),

    ('hardware', 'Hex standoff F/F', 'M3 x 10 mm', 8, 'PCB standoffs on plate A'),
    ('hardware', 'Hex standoff M/F', 'M3 x 45 mm', 8, '4 for A->B, 4 for B->C'),
    ('hardware', 'Screw, pan head', 'M3 x 6 mm', 8, 'LAN9692 down onto its standoffs'),
    ('hardware', 'Screw, pan head', 'M3 x 8 mm', 12,
     '8 up through plate A into the PCB standoffs, 4 down through plate C'),
    ('hardware', 'Screw, pan head', 'M3 x 12 mm', 8,
     '4 TC397 tray, 4 T-ETH-Elite adapter, through the plate B slots'),
    ('hardware', 'Screw, pan head', 'M3 x 16 mm', 4, 'fan, through plate B'),
    ('hardware', 'Nut', 'M3', 20, '4 under plate A corners, 4 fan, 8 module trays, spares'),
    ('hardware', 'Washer', 'M3 nylon', 20, 'under every head that lands on acrylic'),
    ('hardware', 'Rubber foot', 'self-adhesive, ~10 mm', 4, 'under plate A'),

    ('electrical', 'Fan', '40 x 40 x 10 mm, 12 V DC', 1, 'blows down onto the switch'),
    ('electrical', 'DC splitter, 1 to 2', 'barrel 5.5 x 2.5 mm', 1,
     'NOT 5.5 x 2.1 - the board jack is 2.5'),
    ('electrical', 'DC adapter', '12 V 5 A, barrel 5.5 x 2.5 mm, centre +', 1,
     'board budgets 4.1 A, fan ~0.15 A'),
    ('electrical', 'Barrel plug, solder type', '5.5 x 2.5 mm', 1, 'to wire the fan onto the splitter'),

    ('printed', 'TC397 Application Kit case', 'tc397_appkit_tray.stl + _lid.stl', 1, '82.9 cm3'),
    ('printed', 'LilyGo T-ETH-Elite case', 'lilygo_*_bottom_fit.stl + _top_fit.stl', 1,
     '17.1 cm3, order 2 sets - the buttons come loose'),
    ('printed', 'T-ETH-Elite adapter', 'adapter_lilygo.stl', 1,
     '14.5 cm3, bolts to plate B, case drops in'),
]

SUPPLIER = {'acrylic': 'laser / acrylic shop',
            'hardware': 'electronics parts supplier',
            'electrical': 'electronics parts supplier',
            'printed': '3D print (self or JLC3DP)'}


def write_csv(path):
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['order from', 'group', 'item', 'spec', 'qty', 'note'])
        for g, item, spec, qty, note in BOM:
            w.writerow([SUPPLIER[g], g, item, spec, qty, note])
    return path


def as_markdown():
    out = []
    for g in ('acrylic', 'hardware', 'electrical', 'printed'):
        out.append(f"\n### {g} — {SUPPLIER[g]}\n")
        out.append('| Item | Spec | Qty | Note |')
        out.append('|---|---|---:|---|')
        for gg, item, spec, qty, note in BOM:
            if gg == g:
                out.append(f'| {item} | {spec} | {qty} | {note} |')
    return '\n'.join(out)


if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    p = write_csv(os.path.join(here, 'BOM.csv'))
    print(f"wrote {os.path.basename(p)}  ({len(BOM)} lines)")
    print(as_markdown())
