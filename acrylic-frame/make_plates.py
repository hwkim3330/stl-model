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
import os
import re
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
CORNER_INSET = 8.0                # lower standoff column, in from each corner
# The plate-to-plate joints use plain F/F standoffs with a screw at each end,
# because an M/F standoff's 6 mm male stud cannot pass a 5 mm plate and still
# bite. That means each plate must not share a hole between the column below it
# and the column above it, so the two columns sit at different Y.
UPPER_Y = (40.0, 140.0)           # B -> C column, on the same X lines
M3_FREE = 3.4                     # M3 clearance in acrylic
FAN_BORE = 36.0                   # 40 mm fan. Ø38 would match the impeller but
                                  # leaves only 1.93 mm of acrylic to the M3
                                  # screw holes at 22.63 mm radius; Ø36 gives
                                  # 2.93 mm. See review.py.
FAN_PITCH = 32.0                  # 40 mm fan standard, matches NF-A4x10
FAN_SCREW_D = 3.4                 # M3 free fit. If you want to use the screws
                                  # in the fan's own box instead, those need
                                  # ~Ø4.5 - then drop FAN_BORE to 35.0 or the
                                  # web to the bore falls to 2.38 mm.
SLOT_W, SLOT_L = 3.4, 16.0        # adjustment slots for the module trays
DECK_X, DECK_Y = 35.0, 45.0       # optional sub-plate mounting, on plate B as
                                  # well as on plates D and E. Chosen to clear
                                  # both boards' mount slots by >4.8 mm, which a
                                  # 45 mm square could not do.
DECK_PITCH = 45.0                 # legacy, only used by the printed trays
# Where module trays bolt onto plate B. Both layouts use the same 45 mm deck
# square, so any tray in this repo fits either. Checked in assembly.py.
LAYOUTS = {
    # Positions put each board's PORT edge near a plate edge so cables leave
    # the frame instead of crossing it: the TC397's connector row ends up 14 mm
    # from the back edge, the T-ETH-Elite's USB-C 10 mm from the front and its
    # RJ45 17 mm from the right. Both clear the fan and the corner columns.
    'tc397+eth-elite': [('TC397', 70.0, 116.0),
                        ('T-ETH-Elite', 201.1, 34.6)],
    # two 85 x 75 ESP32-S31 trays, 84 mm apart
    'two-s31': [('module A', 60.0, 132.0), ('module B', 60.0, 48.0)],
}
LAYOUT = 'tc397+eth-elite'

# True  = the boards bolt straight to plate B on its own holes, cut to each
#         board's real pattern. Three plates, no sub-plates, 3 mm lower.
# False = plate B gets deck slots instead and the boards ride on sub-plates D
#         and E, which keeps plate B generic if you swap modules later.
DIRECT_MOUNT = True

# The board hole positions were read off drawings, not off the boards. That is
# the one error that would scrap plate B, so the mount features are cut as short
# SLOTS rather than round holes: MOUNT_SLOT mm long absorbs a misread of up to
# +/-(MOUNT_SLOT - hole)/2 in X. Set it equal to the hole diameter for plain
# round holes once the boards have been measured.
MOUNT_SLOT = 9.0
ZONES = LAYOUTS[LAYOUT]
VENT_SLOT = (8.0, 60.0)           # top-plate intake slots (w, l)

# Engraving on the top plate. Single-stroke vector text on its own layer, so the
# shop runs it at engrave power and it is never mistaken for a cut. A real KETI
# logo would need the logo as vector (AI/SVG/DXF) - drop it in on this layer.
ENGRAVE = [(20.0, 150.0, 14.0, 'KETI'),
           (20.0, 132.0, 7.0, 'LAN9692 TSN BENCH')]

# Optional 4th plate: the LilyGo T-ETH-Elite bolted straight down instead of
# living in its printed case. Its four mounting holes genuinely are NOT a
# rectangle - the bottom pair is 58.0 mm apart and the top pair 60.25 - and two
# independent LilyGo files agree on that to 0.04 mm, so it is the real design
# and not a CAD slip:
#   3D CAD  shell/3D/T-ETH-ELite.7z   -> 58.00 / 60.25
#   2D DXF  shell/T-ETH-ELite.dxf     -> 58.04 / 60.24
# Positions below are from the PCB's bottom-left corner, top view.
ETH_BOARD = (66.191, 49.192)
ETH_HOLES = [(3.33, 4.63), (61.33, 4.63), (2.98, 46.23), (63.23, 46.20)]
ETH_HOLE_D = 2.9                  # M2.5 free fit
ETH_PLATE = (76.0, 60.0)

# 5th plate: the TC397 Application Kit bolted down instead of living in its
# printed tray. Four isolated round pads in figure 7-7 of the Application Kit
# Manual TC3X7 V2.0 have BOTH coordinates in the drawing's dimension chains
#   x: 3.01 11 16 28.41 46.19 74.676 89 96.99 100
#   y: 2.7  4  51 59    64.262 82    96.72 100
# and the drawing exists "for development of extension boards", so what it
# dimensions is what an extension board has to match. Confidence differs:
#   (11, 4) and (89, 4)      Ø6.0 pads, unambiguous, on the front edge
#   (96.99, 59), (16, 82)    Ø4.0 pads, dimensioned and isolated - very likely
#                            mounting holes, but not proven
# Cut all four. If the last two turn out to be something else you simply leave
# those screws out and fall back on adhesive props; an unused hole costs
# nothing, whereas two screws on one edge leaves the port edge cantilevered.
TC_BOARD = (100.0, 100.0)
TC_HOLES = [(11.0, 4.0), (89.0, 4.0), (96.99, 59.0), (16.0, 82.0)]
# Anything you find on the real board that the drawing does not dimension goes
# here, measured from the PCB's bottom-left corner. Extra holes in acrylic are
# free; an unused one costs nothing.
TC_EXTRA_HOLES = []
TC_HOLE_D = 3.4
TC_PLATE = (110.0, 110.0)

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

    def text(self, x, y, height, string, layer='TEXT'):
        self.e.append(f"0\nTEXT\n8\n{layer}\n10\n{x:.4f}\n20\n{y:.4f}\n30\n0.0\n"
                      f"40\n{height:.4f}\n1\n{string}\n")

    # single-stroke glyphs on a 0..1 x 0..1 box, as polyline point lists
    GLYPHS = {
        'A': [[(0,0),(.5,1),(1,0)],[(.22,.4),(.78,.4)]],
        'E': [[(1,1),(0,1),(0,0),(1,0)],[(0,.5),(.75,.5)]],
        'I': [[(.5,0),(.5,1)],[(.15,1),(.85,1)],[(.15,0),(.85,0)]],
        'K': [[(0,0),(0,1)],[(.9,1),(0,.45)],[(.15,.55),(.95,0)]],
        'L': [[(0,1),(0,0),(.9,0)]],
        'N': [[(0,0),(0,1),(1,0),(1,1)]],
        'T': [[(0,1),(1,1)],[(.5,1),(.5,0)]],
        'S': [[(1,.85),(.5,1),(0,.85),(0,.6),(1,.4),(1,.15),(.5,0),(0,.15)]],
        'B': [[(0,0),(0,1),(.7,1),(1,.85),(1,.65),(.7,.5),(0,.5)],
              [(.7,.5),(1,.35),(1,.15),(.7,0),(0,0)]],
        'C': [[(1,.85),(.5,1),(0,.75),(0,.25),(.5,0),(1,.15)]],
        'D': [[(0,0),(0,1),(.6,1),(1,.7),(1,.3),(.6,0),(0,0)]],
        'H': [[(0,0),(0,1)],[(1,0),(1,1)],[(0,.5),(1,.5)]],
        'M': [[(0,0),(0,1),(.5,.45),(1,1),(1,0)]],
        'O': [[(.5,1),(0,.75),(0,.25),(.5,0),(1,.25),(1,.75),(.5,1)]],
        'P': [[(0,0),(0,1),(.7,1),(1,.8),(1,.6),(.7,.45),(0,.45)]],
        'R': [[(0,0),(0,1),(.7,1),(1,.8),(1,.6),(.7,.45),(0,.45)],
              [(.5,.45),(1,0)]],
        'U': [[(0,1),(0,.2),(.5,0),(1,.2),(1,1)]],
        'V': [[(0,1),(.5,0),(1,1)]],
        'W': [[(0,1),(.2,0),(.5,.6),(.8,0),(1,1)]],
        'X': [[(0,0),(1,1)],[(0,1),(1,0)]],
        'Y': [[(0,1),(.5,.5),(1,1)],[(.5,.5),(.5,0)]],
        'F': [[(1,1),(0,1),(0,0)],[(0,.5),(.75,.5)]],
        'G': [[(1,.85),(.5,1),(0,.75),(0,.25),(.5,0),(1,.2),(1,.45),(.55,.45)]],
        '0': [[(.5,1),(0,.75),(0,.25),(.5,0),(1,.25),(1,.75),(.5,1)]],
        '1': [[(.2,.8),(.5,1),(.5,0)],[(.15,0),(.85,0)]],
        '3': [[(0,.9),(.5,1),(1,.85),(1,.6),(.5,.5),(1,.4),(1,.15),(.5,0),(0,.1)]],
        '4': [[(.75,0),(.75,1),(0,.3),(1,.3)]],
        '5': [[(1,1),(0,1),(0,.55),(.6,.6),(1,.4),(1,.15),(.5,0),(0,.1)]],
        '7': [[(0,1),(1,1),(.35,0)]],
        '8': [[(.5,.5),(0,.65),(0,.85),(.5,1),(1,.85),(1,.65),(.5,.5),
               (0,.35),(0,.15),(.5,0),(1,.15),(1,.35),(.5,.5)]],
        '-': [[(.1,.5),(.9,.5)]],
        '.': [[(.4,0),(.6,0)]],
        '2': [[(0,.85),(.5,1),(1,.85),(1,.6),(0,0),(1,0)]],
        '6': [[(1,.9),(.5,1),(0,.75),(0,.15),(.5,0),(1,.15),(1,.35),(.5,.5),(0,.35)]],
        '9': [[(0,.1),(.5,0),(1,.25),(1,.85),(.5,1),(0,.85),(0,.65),(.5,.5),(1,.65)]],
        ' ': [],
    }

    def stroke_text(self, x, y, height, string, layer='ENGRAVE', gap=0.22):
        """Single-stroke vector text - engraves cleanly, no font needed."""
        w = height * 0.62
        cx = x
        missing = sorted(set(string.upper()) - set(self.GLYPHS))
        if missing:
            raise ValueError(f"stroke_text: no glyph for {missing} in {string!r} - "
                             f"add it to Dxf.GLYPHS rather than losing letters")
        for ch in string.upper():
            for poly in self.GLYPHS[ch]:
                for (ax, ay), (bx_, by) in zip(poly, poly[1:]):
                    self.line(cx + ax * w, y + ay * height,
                              cx + bx_ * w, y + by * height, layer)
            cx += w * (1 + gap)
        return cx - x - w * gap

    def save(self, path):
        head = ("0\nSECTION\n2\nHEADER\n9\n$INSUNITS\n70\n4\n"
                "9\n$MEASUREMENT\n70\n1\n0\nENDSEC\n"
                "0\nSECTION\n2\nENTITIES\n")
        with open(path, 'w') as f:
            f.write(head + ''.join(self.e) + "0\nENDSEC\n0\nEOF\n")
        return len(self.e)


def lower_columns():
    return [(x, y) for x in (CORNER_INSET, PW - CORNER_INSET)
            for y in (CORNER_INSET, PH - CORNER_INSET)]


def upper_columns():
    return [(x, y) for x in (CORNER_INSET, PW - CORNER_INSET) for y in UPPER_Y]


def corner_holes(d, which='both'):
    pts = (lower_columns() if which == 'lower' else
           upper_columns() if which == 'upper' else
           lower_columns() + upper_columns())
    for x, y in pts:
        d.circle(x, y, M3_FREE / 2)


def deck_points(cx, cy):
    return [(cx + sx * DECK_X / 2, cy + sy * DECK_Y / 2)
            for sx in (-1, 1) for sy in (-1, 1)]


def deck_holes(d, cx, cy):
    for x, y in deck_points(cx, cy):
        d.circle(x, y, M3_FREE / 2)


def plate_bottom():
    """5 mm. Carries the LAN9692 on M3 standoffs."""
    d = Dxf()
    d.rounded_rect(0, 0, PW, PH, PLATE_R)
    corner_holes(d, 'lower')
    for hx, hy in LAN_HOLES:
        d.circle(BOARD_OFF[0] + hx, BOARD_OFF[1] + hy, M3_FREE / 2)
    return d


def plate_middle():
    """5 mm. Fan hangs underneath blowing down onto the switch; trays on top."""
    d = Dxf()
    d.rounded_rect(0, 0, PW, PH, PLATE_R)
    corner_holes(d, 'both')          # 8: the column below and the one above
    d.circle(FAN_C[0], FAN_C[1], FAN_BORE / 2)
    h = FAN_PITCH / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            d.circle(FAN_C[0] + sx * h, FAN_C[1] + sy * h, FAN_SCREW_D / 2)
    # the boards bolted straight down, on their own patterns...
    for (_, cx, cy), (bw, bh), holes, hd in board_mounts():
        for hx, hy in holes:
            d.slot(cx - bw / 2 + hx, cy - bh / 2 + hy,
                   max(MOUNT_SLOT, hd), hd, horizontal=True)
    # ...and a deck pattern so a sub-plate can be used instead, without
    # re-cutting. 35 x 45 rather than a 45 mm square: that is what clears both
    # boards' mount slots.
    for _, cx, cy in ZONES:
        deck_holes(d, cx, cy)
    return d


def board_mounts():
    """(zone, board size, hole list, hole Ø) for whatever plate B carries."""
    return [(ZONES[0], TC_BOARD, TC_HOLES + TC_EXTRA_HOLES, TC_HOLE_D),
            (ZONES[1], ETH_BOARD, ETH_HOLES, ETH_HOLE_D)]


def plate_eth_elite():
    """3 mm. Carries a bare T-ETH-Elite on M2.5 standoffs, bolts to plate B."""
    d = Dxf()
    w, h = ETH_PLATE
    d.rounded_rect(0, 0, w, h, 4.0)
    ox, oy = (w - ETH_BOARD[0]) / 2, (h - ETH_BOARD[1]) / 2
    for hx, hy in ETH_HOLES:
        d.circle(ox + hx, oy + hy, ETH_HOLE_D / 2)
    deck_holes(d, w / 2, h / 2)
    return d


def plate_tc397():
    """3 mm. Carries a bare TC397 Application Kit, bolts to plate B."""
    d = Dxf()
    w, h = TC_PLATE
    d.rounded_rect(0, 0, w, h, 4.0)
    ox, oy = (w - TC_BOARD[0]) / 2, (h - TC_BOARD[1]) / 2
    for hx, hy in TC_HOLES + TC_EXTRA_HOLES:
        d.circle(ox + hx, oy + hy, TC_HOLE_D / 2)
    deck_holes(d, w / 2, h / 2)
    return d


def plate_top():
    """3 mm. Hand and cable guard, with intake slots over the fan."""
    d = Dxf()
    d.rounded_rect(0, 0, PW, PH, PLATE_R)
    corner_holes(d, 'upper')
    for i in range(-2, 3):
        d.slot(FAN_C[0] + i * (VENT_SLOT[0] + 6), FAN_C[1],
               VENT_SLOT[1], VENT_SLOT[0], horizontal=False)
    for x, y, h, txt in ENGRAVE:
        d.stroke_text(x, y, h, txt)
    return d


PLATES = [('plate-a-bottom-5T', plate_bottom, 5),
          ('plate-b-middle-5T', plate_middle, 5),
          ('plate-c-top-3T', plate_top, 3),
          ('plate-d-eth-elite-3T', plate_eth_elite, 3),
          ('plate-e-tc397-3T', plate_tc397, 3)]


# Nesting: plates of the same thickness laid out on one sheet, so a shop that
# quotes by sheet area does not charge three separate offcuts. (x, y) is the
# lower-left corner of each plate on its sheet.
NESTS = {
    '5T': dict(sheet=(260, 380),
               place=[('plate-a-bottom-5T', 5, 5), ('plate-b-middle-5T', 5, 195)]),
    '3T': dict(sheet=(260, 190), place=[('plate-c-top-3T', 5, 5)]),
}


# One sheet with every plate on it, annotated - the layout acrylic shops ask
# for. (name, x, y, label) with the label written under each plate.
COMBINED_SHEET = (580.0, 430.0)
COMBINED = [
    ('plate-a-bottom-5T', 15.0, 235.0, 'PLATE A (BOTTOM)  5T  CLEAR  x1'),
    ('plate-b-middle-5T', 300.0, 235.0, 'PLATE B (MIDDLE)  5T  CLEAR  x1'),
    ('plate-c-top-3T', 15.0, 30.0, 'PLATE C (TOP)  3T  CLEAR  x1'),
    ('plate-e-tc397-3T', 300.0, 30.0, 'PLATE E  3T  CLEAR  x1'),
    ('plate-d-eth-elite-3T', 430.0, 30.0, 'PLATE D  3T  CLEAR  x1'),
]


def shift_entities(sub, ox, oy):
    out = []
    for e in sub.e:
        def mv(m):
            code, val = m.group(1), float(m.group(2))
            return f"{code}\n{val + (ox if code in ('10', '11') else oy):.4f}"
        out.append(re.sub(r'\b(1[01]|2[01])\n(-?[\d.]+)', mv, e))
    return out


def combined(builders):
    """All five plates on one annotated sheet."""
    d = Dxf()
    W, H = COMBINED_SHEET
    d.rounded_rect(0, 0, W, H, 0.1, layer='SHEET')
    # title block in the empty area between plate B and plate E
    d.text(300, 205, 8.0, 'LAN9692 ACRYLIC FRAME - 5 PLATES')
    d.text(300, 190, 5.0, 'ALL DIMENSIONS mm.  MATERIAL: CLEAR ACRYLIC (PMMA)')
    d.text(300, 178, 5.0, 'CUT LAYER = CUT.  TEXT AND SHEET OUTLINE DO NOT CUT.')
    d.text(300, 166, 5.0, '5T x 2 SHEETS (A, B)   3T x 3 SHEETS (C, D, E)')
    d.text(300, 154, 5.0, 'HOLES: O3.4 / O2.9 / O36 FAN BORE.  SLOTS AS DRAWN.')
    for name, ox, oy, label in COMBINED:
        sub = builders[name]()
        d.e += shift_entities(sub, ox, oy)
        d.text(ox, oy - 11, 6.0, label)
    return d


def nest(tag, spec, builders):
    """One DXF per thickness with every plate of that thickness on it."""
    d = Dxf()
    w, h = spec['sheet']
    d.rounded_rect(0, 0, w, h, 0.1, layer='SHEET')     # reference outline only
    for name, ox, oy in spec['place']:
        sub = builders[name]()
        for e in sub.e:
            def shift(m):
                code, val = m.group(1), float(m.group(2))
                off = ox if code in ('10', '11') else oy
                return f"{code}\n{val + off:.4f}"
            d.e.append(re.sub(r'\b(1[01]|2[01])\n(-?[\d.]+)', shift, e))
    return d


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
    builders = {n: fn for n, fn, _ in PLATES}
    path = os.path.join(out, 'combined-all-plates.dxf')
    n = combined(builders).save(path)
    made.append(path)
    print(f"  {'combined-all-plates.dxf':24s} {COMBINED_SHEET[0]:.0f} x "
          f"{COMBINED_SHEET[1]:.0f} mm sheet, 5 plates annotated, {n} entities")
    for tag, spec in NESTS.items():
        path = os.path.join(out, f'nested-{tag}.dxf')
        n = nest(tag, spec, builders).save(path)
        made.append(path)
        print(f"  {'nested-' + tag + '.dxf':24s} {spec['sheet'][0]} x "
              f"{spec['sheet'][1]} mm sheet, {len(spec['place'])} plates, {n} entities")
    import bom
    root = os.path.dirname(out)
    bom.write_csv(os.path.join(root, 'BOM.csv'))
    zpath = os.path.join(root, 'acrylic-frame-dxf.zip')
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in made:
            z.write(p, os.path.join('acrylic-frame', os.path.basename(p)))
        for extra in ('CUTTING.md', 'BOM.csv'):
            z.write(os.path.join(root, extra), 'acrylic-frame/' + extra)
    print(f"\n  {os.path.basename(zpath)}  ({os.path.getsize(zpath)} bytes)")
    print(f"  board centred at offset ({BOARD_OFF[0]:.2f}, {BOARD_OFF[1]:.2f})")
    print(f"  fan centre ({FAN_C[0]:.2f}, {FAN_C[1]:.2f}) = U1 + offset")


if __name__ == '__main__':
    main()
