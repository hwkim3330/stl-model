#!/usr/bin/env python3
"""Bill of materials for the LAN9692 acrylic frame, one complete set.

    python3 bom.py        # -> BOM.csv, and prints it as a table

Quantities come from the fastener stack, not from guessing: every F/F standoff
takes a screw at each end, so a joint is two screws, and review.py counts the
screw positions in the geometry against the totals here.

Part numbers marked (checked) were read off the manufacturer or distributor
page while writing this. The rest are as supplied and have NOT been confirmed -
check the description before ordering, particularly that a standoff is
Female/Female and a barrel is 2.5 mm and not 2.1.
"""
import csv
import os

# group, item, spec, qty, part, supplier, note
BOM = [
    ('acrylic', 'Plate A - bottom', 'clear acrylic 3 mm, 250 x 180', 1,
     'plate-a-bottom-3T.dxf', 'laser shop', 'carries the LAN9692'),
    ('acrylic', 'Plate B - middle', 'clear acrylic 3 mm, 250 x 180', 1,
     'plate-b-middle-3T.dxf', 'laser shop', 'fan under, modules on top'),
    ('acrylic', 'Plate C - top', 'clear acrylic 3 mm, 250 x 180', 1,
     'plate-c-top-3T.dxf', 'laser shop', 'guard, intake slots over the fan'),
    ('acrylic', 'Plate D - upper', 'clear acrylic 3 mm, 250 x 180', 1,
     'plate-d-upper-3T.dxf', 'laser shop',
     'fourth tier, for the CAN board. Column holes and vents only - the CAN '
     "board's own hole pattern is not known yet"),

    ('hardware', 'Hex standoff F/F', 'M3 x 10 mm, stainless', 8,
     'RS 224-0443 (checked: F/F)', 'RS Korea',
     'LAN9692 on plate A. The board drill is Ø3.048, so an M3 screw is a very '
     'tight fit through it - try one by hand first, and use M2.5 here if it '
     'binds; the Ø3.4 acrylic hole takes either'),
    ('hardware', 'Hex standoff M/F', 'M3 x 50 mm, male stud 6 mm', 12,
     '디바이스마트 PCB서포트 금속 F-50mm (already bought, 10 of them)', 'RS Korea',
     'The whole column: 4 per gap, three gaps, all fitted male end UP. Each '
     "one's stud crosses the plate above it and threads 3 mm into the standoff "
     'beyond, so every plate needs only ONE hole per corner. This is why the '
     'plates are 3 mm - through 5 mm the same stud would leave 1 mm. 10 came in '
     'the parts order, so 2 more are needed'),
    ('hardware', 'Nut', 'M3', 4, 'RS 521-917 or plain', 'RS Korea',
     'on the four studs that come through plate D, the top of the stack'),
    ('hardware', 'Hex standoff F/F', 'M3 x 20 mm, brass', 4,
     'Wurth 970080324 (8 mm) - want the 20 mm length in the same range', 'RS Korea',
     'TC397 on plate B. 20 mm under every board on that plate, not 8: one stock '
     'length for all four, and it leaves room under a board for connector tails '
     'and for a cable to turn. Checked - the tallest module then tops out at '
     '101.6 mm with 8.4 mm still clear under plate C'),
    ('hardware', 'Hex standoff F/F', 'M2.5 x 20 mm, brass', 12,
     'Wurth 970080144 (8 mm) - want the 20 mm length in the same range', 'RS Korea',
     '4 for the T-ETH-Elite and 4 for each injection module - all three have '
     'Ø2.5 mounting holes, so all three are M2.5'),

    ('hardware', 'Screw, pan head', 'M3 x 6 mm', 12, 'RS 190-428', 'RS Korea',
     'LAN9692 down onto its 8 standoffs, TC397 down onto its 4'),
    ('hardware', 'Screw, pan head', 'M3 x 8 mm', 16, 'RS 797-6193', 'RS Korea',
     '8 up through plate A into the LAN9692 standoffs, 4 up through plate A '
     'into the first column standoff, 4 up through plate B into the TC397 '
     'standoffs. At 3 mm of plate an M3 x 8 engages 5 mm everywhere, so the '
     'M3 x 10 line is gone'),

    ('hardware', 'Screw, pan head', 'M3 x 25 mm', 4, 'RS 914-1490', 'RS Korea',
     'fan: right through plate B and the fan, nyloc nut underneath. 5 mm plate '
     '+ 10 mm fan + washer + a 4 mm nyloc needs about 19.5 mm engaged, so an '
     'M3 x 20 has nothing left for the nylon to lock onto. The screws in the '
     "fan's own box are fatter and want Ø4.5 holes"),
    ('hardware', 'Screw, pan head', 'M2.5 x 6 mm', 12, 'RS 528-716', 'RS Korea',
     'T-ETH-Elite and both injection modules, down onto their standoffs'),
    ('hardware', 'Screw, pan head', 'M2.5 x 8 mm', 12, 'RS 797-6190', 'RS Korea',
     'up through plate B into those standoffs'),
    ('hardware', 'Nut, nyloc', 'M3, DIN 985', 12, 'RS 521-917', 'RS Korea',
     '4 for the fan, 8 spare. Nyloc because the fan is the one vibrating part'),
    ('hardware', 'Washer, nylon', 'M3', 40, 'Essentra MFW030A / DK RPC1552-ND',
     'DigiKey Korea',
     'under every screw head that lands on acrylic: 12 under plate A, 24 on '
     'plate B, 4 on plate D. Nothing lands on plate C - a standoff body sits on '
     'it, not a screw head'),
    ('hardware', 'Nylon standoff, adhesive base', '8 mm', 2, '-', 'any',
     'spares - only needed if the two less certain TC397 holes are not holes'),
    ('hardware', 'Rubber foot', 'self-adhesive, ~10 mm', 4, 'RS 136-8964',
     'RS Korea', 'under plate A'),

    ('electrical', 'Fan', '40 x 40 x 10 mm, 12 V, 0.6 W', 1,
     'Noctua NF-A4x10 FLX (checked: 40x40x10, 12 V, 0.6 W)', 'domestic retail',
     '32 x 32 mm screw pitch, matching the holes in plate B. Solder the barrel '
     'socket to the INCLUDED extension cable, not to the fan\'s own lead'),
    ('electrical', 'DC adapter', '12 V 5 A, barrel 5.5 x 2.5 x 11 mm, centre +',
     1, 'Mean Well GST60A12-P1M / DK 1866-GST60A12-P1M-ND (checked: 5.5 x 2.5, '
     'centre +)', 'DigiKey Korea',
     'board budgets 4.1 A, fan 0.05 A. P1M is the 2.5 mm plug; the P1J variant '
     'of the same supply is 2.1 mm and will contact badly in the board jack'),
    ('electrical', 'Barrel socket (female) to bare leads', '5.5 x 2.5 mm, '
     '18 AWG, 305 mm', 1,
     'Tensility 10-02879 / DK 839-10-02879-ND (checked: female, 5.5/2.5, '
     '18 AWG, 6 A, red + black)', 'DigiKey Korea',
     "this is the connector the fan's wires join to. Female, because the "
     'splitter outputs are male. Which lead is the centre pin is NOT in the '
     'datasheet - meter it, do not assume red'),
    ('electrical', 'DC splitter, 1 female in to 2 male out', 'barrel 5.5 x 2.5 mm',
     1, '-', 'domestic retail',
     'NOT 5.5 x 2.1. The adapter plug is male, so the splitter must be '
     'female-in / male-out or you end up male-to-male'),
]

SUPPLIER_NOTE = {
    'laser shop': 'send dxf/combined-order.dxf - see CUTTING.md',
    'RS Korea': 'screws, nuts, standoffs, feet',
    'DigiKey Korea': 'washers, power supply, barrel socket',
    'domestic retail': 'fan and the barrel Y splitter',
    'any': '',
}


def write_csv(path):
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['supplier', 'group', 'item', 'spec', 'qty', 'part number',
                    'note'])
        for g, item, spec, qty, part, sup, note in BOM:
            w.writerow([sup, g, item, spec, qty, part, note])
    return path


def as_markdown():
    out = []
    for g in ('acrylic', 'hardware', 'electrical'):
        out.append(f"\n### {g}\n")
        out.append('| Item | Spec | Qty | Part number | Supplier | Note |')
        out.append('|---|---|---:|---|---|---|')
        for gg, item, spec, qty, part, sup, note in BOM:
            if gg == g:
                out.append(f'| {item} | {spec} | {qty} | {part} | {sup} | {note} |')
    return '\n'.join(out)


if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    p = write_csv(os.path.join(here, 'BOM.csv'))
    print(f"wrote {os.path.basename(p)}  ({len(BOM)} lines)")
    for sup, note in SUPPLIER_NOTE.items():
        n = sum(1 for b in BOM if b[5] == sup)
        if n:
            print(f"  {sup:18s} {n:2d} lines   {note}")
    print(as_markdown())
