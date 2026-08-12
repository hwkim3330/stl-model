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
    # DIRECT_MOUNT = True: both boards bolt to plate B on its own holes, so
    # there are no sub-plates. Set it False in make_plates.py to get plates D
    # and E back.

    ('hardware', 'Hex standoff F/F', 'M3 x 10 mm', 8, 'PCB standoffs on plate A'),
    ('hardware', 'Hex standoff F/F', 'M3 x 45 mm', 8,
     '4 for A->B, 4 for B->C. F/F, not M/F - a 6 mm male stud cannot cross a '
     '5 mm plate and still bite'),
    ('hardware', 'Screw, pan head', 'M3 x 6 mm', 8, 'LAN9692 down onto its standoffs'),
    ('hardware', 'Screw, pan head', 'M3 x 10 mm', 8,
     '4 up through plate A and 4 down through plate B, into the A->B standoffs'),
    ('hardware', 'Screw, pan head', 'M3 x 8 mm', 16,
     '8 up through plate A into the PCB standoffs, 4 up through plate B and '
     '4 down through plate C, into the B->C standoffs'),
    ('hardware', 'Screw, pan head', 'M3 x 10 mm', 4,
     'up through plate B into the TC397 standoffs'),
    ('hardware', 'Screw, self-tapping', 'M3 x 16 mm', 4,
     'fan, through plate B into the fan frame - NOT with a nut, there is no room'),
    ('hardware', 'Nut', 'M3', 8, 'spares - no joint in this build needs one'),
    ('hardware', 'Washer', 'M3 nylon', 20, 'under every head that lands on acrylic'),
    ('hardware', 'Hex standoff F/F', 'M2.5 x 8 mm', 4, 'T-ETH-Elite on plate B'),
    ('hardware', 'Screw, pan head', 'M2.5 x 10 mm', 4,
     'up through plate B into the T-ETH-Elite standoffs'),
    ('hardware', 'Screw, pan head', 'M2.5 x 6 mm', 4, 'T-ETH-Elite down onto them'),
    ('hardware', 'Hex standoff F/F', 'M3 x 8 mm', 4, 'TC397 on plate B'),
    ('hardware', 'Screw, pan head', 'M3 x 6 mm', 4, 'TC397 down onto them'),
    ('hardware', 'Nylon standoff, adhesive base', '8 mm', 2,
     'spares - only needed if the two less certain TC397 holes are not holes'),
    ('hardware', 'Rubber foot', 'self-adhesive, ~10 mm', 4, 'under plate A'),

    ('electrical', 'Fan', '40 x 40 x 10 mm, 12 V DC, 3-pin or bare leads', 1,
     'Noctua NF-A4x10 FLX (32 x 32 mm pitch, 10 mm thick) or Sunon MF40101V. '
     'Cut the INCLUDED extension cable to solder the barrel socket on, not the '
     "fan's own lead"),
    ('electrical', 'DC splitter, 1 female to 2 male', 'barrel 5.5 x 2.5 mm', 1,
     'NOT 5.5 x 2.1 - the board jack is 2.5. Female end takes the adapter'),
    ('electrical', 'DC adapter', '12 V 5 A, barrel 5.5 x 2.5 mm, centre +', 1,
     'board budgets 4.1 A, fan ~0.15 A'),
    ('electrical', 'Barrel SOCKET (female), solder type', '5.5 x 2.5 mm', 1,
     'on the fan lead - the splitter outputs are male, so the fan needs female'),

    # nothing printed in the all-acrylic build. The printed cases in this repo
    # remain valid if you would rather box the small boards up:
    #   tc397_appkit_{tray,lid}.stl, lilygo_*_fit.stl + adapter_lilygo.stl
]

SUPPLIER = {'acrylic': 'laser / acrylic shop',
            'hardware': 'electronics parts supplier',
            'electrical': 'electronics parts supplier'}


def write_csv(path):
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['order from', 'group', 'item', 'spec', 'qty', 'note'])
        for g, item, spec, qty, note in BOM:
            w.writerow([SUPPLIER[g], g, item, spec, qty, note])
    return path


def as_markdown():
    out = []
    for g in ('acrylic', 'hardware', 'electrical'):
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
