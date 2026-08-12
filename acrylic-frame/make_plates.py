#!/usr/bin/env python3
"""Laser-cut DXFs for a 3-plate acrylic frame carrying the LAN9692 EVB.

Why acrylic and not one big printed box: the LAN9692 board is 213.36 x 149.86 mm,
so a printed enclosure runs 118-237 cm3 depending on style. The same job as flat
plates is three sheets and a bag of standoffs, the board stays visible, and the
one number still unverified in the printed design - how much clearance the DC-DC
daughter modules need above the board - stops mattering, because you change a
standoff instead of reprinting a box.

    python3 make_plates.py        # -> dxf/*.dxf and acrylic-frame-dxf.zip

Every hole for the LAN9692 comes from its Excellon drill file (tool T23, 8 x
Ø3.048 mm) and the fan sits over U1, the switch die, at the pick-and-place
coordinate (167.31, 78.69). See ../lan9692-evb-case/README.md.

Output is R12 DXF in millimetres, polyline-free: outlines are LINE + ARC,
holes are CIRCLE, slots are two LINEs plus two ARCs. Any laser shop reads it.
"""
import math
import os
import zipfile

# --------------------------------------------------------------------------
# Board data (from the Gerber set - see ../lan9692-evb-case/extract_board_data.py)
BW, BH = 213.360, 149.860
LAN_HOLES = [(3.556, 146.304), (101.600, 146.304), (209.804, 146.304),
             (205.187, 129.330), (205.187, 71.330), (208.788, 51.816),
             (133.350, 51.562), (3.556, 24.892)]
U1 = (167.31, 78.69)              # LAN9692 BGA-356 centre, from the PnP file

# Plate
PW, PH = 250.0, 180.0             # plate outline
PLATE_R = 6.0                     # corner radius
CORNER_INSET = 8.0                # spacer holes in from each corner
M3_FREE = 3.4                     # M3 clearance in acrylic
FAN_BORE = 38.0                   # 40 mm fan
FAN_PITCH = 32.0
SLOT_W, SLOT_L = 3.4, 16.0        # adjustment slots for the module trays
DECK_PITCH = 45.0                 # same square the printed trays already use
# Where module trays bolt onto plate B. Both layouts use the same 45 mm deck
# square, so any tray in this repo fits either. Checked in assembly.py.
LAYOUTS = {
    # TC397 Application Kit case (119 x 119) next to a LilyGo T-ETH-Elite on
    # its adapter (78 x 59): 8.5 mm between them, 11.3 mm from the fan.
    'tc397+eth-elite': [('TC397 case', 74.0, 90.0),
                        ('T-ETH-Elite adapter', 178.0, 36.0)],
    # two 85 x 75 ESP32-S31 trays, 84 mm apart
    'two-s31': [('module A', 60.0, 132.0), ('module B', 60.0, 48.0)],
}
LAYOUT = 'tc397+eth-elite'
ZONES = LAYOUTS[LAYOUT]
VENT_SLOT = (8.0, 60.0)           # top-plate intake slots (w, l)

BOARD_OFF = ((PW - BW) / 2, (PH - BH) / 2)     # board centred on the plate
FAN_C = (BOARD_OFF[0] + U1[0], BOARD_OFF[1] + U1[1])


# --------------------------------------------------------------------------
# minimal R12 DXF writer
class Dxf:
    def __init__(self):
        self.e = []

    def line(self, x1, y1, x2, y2, layer='CUT'):
        self.e.append(f"0\nLINE\n8\n{layer}\n10\n{x1:.4f}\n20\n{y1:.4f}\n30\n0.0\n"
                      f"11\n{x2:.4f}\n21\n{y2:.4f}\n31\n0.0\n")

    def circle(self, cx, cy, r, layer='CUT'):
        self.e.append(f"0\nCIRCLE\n8\n{layer}\n10\n{cx:.4f}\n20\n{cy:.4f}\n30\n0.0\n"
                      f"40\n{r:.4f}\n")

    def arc(self, cx, cy, r, a0, a1, layer='CUT'):
        self.e.append(f"0\nARC\n8\n{layer}\n10\n{cx:.4f}\n20\n{cy:.4f}\n30\n0.0\n"
                      f"40\n{r:.4f}\n50\n{a0:.4f}\n51\n{a1:.4f}\n")

    def slot(self, cx, cy, length, width, horizontal=True, layer='CUT'):
        """Rounded slot: two straights and two half-circle ends."""
        r = width / 2
        half = max(length / 2 - r, 0.0)
        if horizontal:
            self.line(cx - half, cy + r, cx + half, cy + r, layer)
            self.line(cx - half, cy - r, cx + half, cy - r, layer)
            self.arc(cx + half, cy, r, -90, 90, layer)
            self.arc(cx - half, cy, r, 90, 270, layer)
        else:
            self.line(cx + r, cy - half, cx + r, cy + half, layer)
            self.line(cx - r, cy - half, cx - r, cy + half, layer)
            self.arc(cx, cy + half, r, 0, 180, layer)
            self.arc(cx, cy - half, r, 180, 360, layer)

    def rounded_rect(self, x0, y0, x1, y1, r, layer='CUT'):
        self.line(x0 + r, y0, x1 - r, y0, layer)
        self.line(x0 + r, y1, x1 - r, y1, layer)
        self.line(x0, y0 + r, x0, y1 - r, layer)
        self.line(x1, y0 + r, x1, y1 - r, layer)
        self.arc(x1 - r, y1 - r, r, 0, 90, layer)
        self.arc(x0 + r, y1 - r, r, 90, 180, layer)
        self.arc(x0 + r, y0 + r, r, 180, 270, layer)
        self.arc(x1 - r, y0 + r, r, 270, 360, layer)

    def save(self, path):
        head = ("0\nSECTION\n2\nHEADER\n9\n$INSUNITS\n70\n4\n"
                "9\n$MEASUREMENT\n70\n1\n0\nENDSEC\n"
                "0\nSECTION\n2\nENTITIES\n")
        with open(path, 'w') as f:
            f.write(head + ''.join(self.e) + "0\nENDSEC\n0\nEOF\n")
        return len(self.e)


def corner_holes(d):
    for x in (CORNER_INSET, PW - CORNER_INSET):
        for y in (CORNER_INSET, PH - CORNER_INSET):
            d.circle(x, y, M3_FREE / 2)


def deck_slots(d, cx, cy):
    h = DECK_PITCH / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            d.slot(cx + sx * h, cy + sy * h, SLOT_L, SLOT_W, horizontal=True)


def plate_bottom():
    """5 mm. Carries the LAN9692 on M3 standoffs."""
    d = Dxf()
    d.rounded_rect(0, 0, PW, PH, PLATE_R)
    corner_holes(d)
    for hx, hy in LAN_HOLES:
        d.circle(BOARD_OFF[0] + hx, BOARD_OFF[1] + hy, M3_FREE / 2)
    return d


def plate_middle():
    """5 mm. Fan hangs underneath blowing down onto the switch; trays on top."""
    d = Dxf()
    d.rounded_rect(0, 0, PW, PH, PLATE_R)
    corner_holes(d)
    d.circle(FAN_C[0], FAN_C[1], FAN_BORE / 2)
    h = FAN_PITCH / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            d.circle(FAN_C[0] + sx * h, FAN_C[1] + sy * h, M3_FREE / 2)
    for _, cx, cy in ZONES:
        deck_slots(d, cx, cy)
    return d


def plate_top():
    """3 mm. Hand and cable guard, with intake slots over the fan."""
    d = Dxf()
    d.rounded_rect(0, 0, PW, PH, PLATE_R)
    corner_holes(d)
    for i in range(-2, 3):
        d.slot(FAN_C[0] + i * (VENT_SLOT[0] + 6), FAN_C[1],
               VENT_SLOT[1], VENT_SLOT[0], horizontal=False)
    return d


PLATES = [('plate-a-bottom-5T', plate_bottom, 5),
          ('plate-b-middle-5T', plate_middle, 5),
          ('plate-c-top-3T', plate_top, 3)]


def main():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dxf')
    os.makedirs(out, exist_ok=True)
    made = []
    for name, fn, thick in PLATES:
        path = os.path.join(out, name + '.dxf')
        n = fn().save(path)
        made.append(path)
        print(f"  {name + '.dxf':24s} {PW:.0f} x {PH:.0f} mm, {thick} mm acrylic, "
              f"{n} entities")
    zpath = os.path.join(os.path.dirname(out), 'acrylic-frame-dxf.zip')
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in made:
            z.write(p, os.path.join('acrylic-frame', os.path.basename(p)))
        z.write(os.path.join(os.path.dirname(out), 'CUTTING.md'),
                'acrylic-frame/CUTTING.md')
    print(f"\n  {os.path.basename(zpath)}  ({os.path.getsize(zpath)} bytes)")
    print(f"  board centred at offset ({BOARD_OFF[0]:.2f}, {BOARD_OFF[1]:.2f})")
    print(f"  fan centre ({FAN_C[0]:.2f}, {FAN_C[1]:.2f}) = U1 + offset")


if __name__ == '__main__':
    main()
