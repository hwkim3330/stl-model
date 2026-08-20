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
# One column line, at the four corners, all the way up. The earlier design had
# two sets on different Y because an F/F standoff needs a screw at each end and
# one hole cannot take two screws. A plain THREADED STUD does take one hole and
# serve both: it screws into the standoff below and the one above, through the
# plate. M3 x 16 leaves 5.5 mm of thread engaged each side of a 5 mm plate and
# 6.5 mm each side of a 3 mm one. So every plate now has the same four holes.
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
    # TC397 back-left with its connector row 10 mm off the back rim; the
    # T-ETH-Elite back-right, turned 180 so its USB-C faces the back rim too
    # instead of pointing into the middle of the plate. That clears the whole
    # front of the plate for the two injection modules.
    'tc397+eth-elite': [('TC397', 72.0, 120.0, 0),
                        ('T-ETH-Elite', 180.0, 146.0, 180)],
    # two 85 x 75 ESP32-S31 trays, 84 mm apart
    'two-s31': [('module A', 60.0, 132.0, 0), ('module B', 60.0, 48.0, 0)],
}
LAYOUT = 'tc397+eth-elite'

# True  = the boards bolt straight to plate B on its own holes, cut to each
#         board's real pattern. Three plates, no sub-plates, 3 mm lower.
# False = plate B gets deck slots instead and the boards ride on sub-plates D
#         and E, which keeps plate B generic if you swap modules later.
DIRECT_MOUNT = True

# The board hole positions were read off drawings, not off the boards, and that
# is the one error that could scrap plate B. So each board gets a mix: the holes
# whose position is agreed by every source are cut ROUND, and they locate the
# board; the ones carrying doubt are cut as MOUNT_SLOT-long slots in X, which
# absorbs +/-(MOUNT_SLOT - hole)/2 without letting the board float. Four slots
# would tolerate the same error but leave nothing to register against while you
# tighten. Set MOUNT_SLOT = 0 for all-round once the boards are measured.
MOUNT_SLOT = 9.0
# index into each board's hole list: which ones are slotted
TC_SLOTTED = (2, 3)        # (96.99, 59) and (16, 82) - existence not proven
ETH_SLOTTED = (2, 3)       # the top pair - the 58.00 vs 60.25 asymmetry lives here
ZONES = LAYOUTS[LAYOUT]
ZONES_ROT = [(z[0], z[3]) for z in ZONES]      # name -> rotation, for diagrams

# --------------------------------------------------------------------------
# KETI Fault Injection Modules, 260812 - the RJ45 build and the MATEnet build.
# Both come straight out of the KiCad fabrication output, so unlike the two
# boards above nothing here is inferred:
#   outline  Edge_Cuts.gm1
#   holes    PTH.drl, the Ø2.500 tool - the four corner mounting holes
# Their other drilled holes (Ø3.15 / Ø1.7 on the RJ45 board, Ø2.261 on the
# MATEnet one) are the connectors' pegs and shield tabs, NOT mounting points,
# and get no acrylic. Because these are drill-file coordinates the mounts are
# cut plain ROUND - there is no doubt here for a slot to absorb.
#
# Both boards put their two connectors on OPPOSITE SHORT EDGES: traffic in one
# side, out the other. On the MATEnet board the Ø2.261 connector pegs at x=4.085
# and x=65.585 are what give that away.
#
# The two mount patterns are nearly but not quite the same - 63.25 mm apart in x
# on both, but 27.025 mm apart in y on the RJ45 board against 26.000 on the
# MATEnet one. As cut, a zone takes only its own board.
FIM_HOLE_D = 2.9                  # M2.5 free fit, from the Ø2.5 drill
# Both modules are fitted, one across each half of the front. An earlier attempt
# dropped the second one into the 47.6 mm corridor between the TC397 and the fan
# bore, which left 6.8 mm of acrylic each side - legal and mean. Re-solving the
# whole plate instead of squeezing into what was left gives every board at least
# 20 mm to its nearest neighbour.
FIM = {
    'FIM-RJ45': dict(
        board=(69.585, 34.000),
        holes=[(3.085, 3.475), (66.335, 3.475), (3.085, 30.500), (66.335, 30.500)],
        rot=0, at=(55.0, 33.0)),
    'FIM-MATEnet': dict(
        board=(69.585, 32.881),
        holes=[(3.085, 3.500), (66.335, 3.500), (3.085, 29.500), (66.335, 29.500)],
        rot=0, at=(196.0, 30.0)),
}


def orient(board, holes, rot):
    """Turn a board about its own footprint. 0 / 90 CCW / 180 / 270.

    Hole order is preserved, so the slotted-index lists still name the same
    physical holes. Slots are drawn along X, which stays correct for 0 and 180;
    only boards with no slots are ever turned 90 or 270 here.
    """
    w, h = board
    if rot == 0:
        return board, list(holes)
    if rot == 180:
        return board, [(w - hx, h - hy) for hx, hy in holes]
    if rot == 90:
        return (h, w), [(h - hy, hx) for hx, hy in holes]
    if rot == 270:
        return (h, w), [(hy, w - hx) for hx, hy in holes]
    raise ValueError(f"rotation {rot} not supported")


VENT_SLOT = (8.0, 60.0)           # top-plate intake slots (w, l)

# Engraving. Empty: the KETI mark is not approved for use here, so nothing is
# engraved and the ENGRAVE layer is not emitted at all - which also takes the
# second operation, and its charge, off the order. The machinery stays because
# adding a line back is a one-line change: (x, y, height, text), single-stroke
# vector on its own layer so it can never be mistaken for a cut.
ENGRAVE = []

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
        '=': [[(.1,.62),(.9,.62)],[(.1,.38),(.9,.38)]],
        ':': [[(.45,.7),(.55,.7)],[(.45,.25),(.55,.25)]],
        '/': [[(.1,0),(.9,1)]],
        '(': [[(.7,1),(.3,.6),(.3,.4),(.7,0)]],
        ')': [[(.3,1),(.7,.6),(.7,.4),(.3,0)]],
        ',': [[(.5,.15),(.35,-.1)]],
        '+': [[(.5,.15),(.5,.85)],[(.15,.5),(.85,.5)]],
        '#': [[(.3,0),(.4,1)],[(.6,0),(.7,1)],[(.1,.35),(.9,.35)],[(.1,.68),(.9,.68)]],
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


def corner_holes(d, which='lower'):
    pts = lower_columns()          # one column line now; `which` is vestigial
    for x, y in pts:
        d.circle(x, y, M3_FREE / 2)


def deck_points(cx, cy):
    return [(cx + sx * DECK_X / 2, cy + sy * DECK_Y / 2)
            for sx in (-1, 1) for sy in (-1, 1)]


def deck_holes(d, cx, cy):
    # Nothing on the plates calls this now that the sub-plates are gone; it is
    # kept because adapter_lilygo.py takes its pattern from deck_points().
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
    corner_holes(d)                  # 4: one hole per corner, stud through it
    d.circle(FAN_C[0], FAN_C[1], FAN_BORE / 2)
    h = FAN_PITCH / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            d.circle(FAN_C[0] + sx * h, FAN_C[1] + sy * h, FAN_SCREW_D / 2)
    # the boards bolted straight down, on their own patterns...
    for (_, cx, cy), (bw, bh), holes, hd, slotted in board_mounts():
        for i, (hx, hy) in enumerate(holes):
            X, Y = cx - bw / 2 + hx, cy - bh / 2 + hy
            if i in slotted and MOUNT_SLOT > hd:
                d.slot(X, Y, MOUNT_SLOT, hd, horizontal=True)
            else:
                d.circle(X, Y, hd / 2)
    return d


def engrave_segments():
    """The ENGRAVE layer as plain line segments, for the 3D preview."""
    d = Dxf()
    for x, y, h, txt in ENGRAVE:
        d.stroke_text(x, y, h, txt)
    segs = []
    for e in d.e:
        n = [float(v) for k, v in zip(e.split('\n')[::2], e.split('\n')[1::2])
             if k in ('10', '20', '11', '21')]
        if len(n) == 4:
            segs.append(tuple(n))
    return segs


def board_mounts():
    """(zone, board size, holes, hole Ø, slotted indices) for plate B."""
    out = []
    for (name, cx, cy, rot), board, holes, hd, slotted in (
            (ZONES[0], TC_BOARD, TC_HOLES + TC_EXTRA_HOLES, TC_HOLE_D, TC_SLOTTED),
            (ZONES[1], ETH_BOARD, ETH_HOLES, ETH_HOLE_D, ETH_SLOTTED)):
        b, h = orient(board, holes, rot)
        out.append(((name, cx, cy), b, h, hd, slotted))
    for name, f in FIM.items():
        b, h = orient(f['board'], f['holes'], f['rot'])
        out.append(((name, f['at'][0], f['at'][1]), b, h, FIM_HOLE_D, ()))
    return out






def plate_upper():
    """3 mm, the fourth tier. Carries the CAN board, whose holes are not known
    yet - so it ships with the column holes and the vents only.

    Its four column holes sit at exactly plate C's, because the C -> D column is
    an M/F standoff whose 6 mm male stud passes plate C's 3 mm and still has
    3 mm to thread into the F/F standoff below. That is the one place in this
    frame where M/F works: on the 5 mm plates it would leave 1 mm.

    No vents. Plate D is not in the fan's intake path: the fan hangs under plate
    B and draws from the B-C gap, which is open on all four sides, and the C-D
    gap above it is another 50 mm open on all four sides. Slots in the top sheet
    would add nothing, and it is the plate whose real cutting waits on the CAN
    board anyway.
    """
    d = Dxf()
    d.rounded_rect(0, 0, PW, PH, PLATE_R)
    corner_holes(d)
    return d


def plate_top():
    """3 mm. Hand and cable guard, with intake slots over the fan."""
    d = Dxf()
    d.rounded_rect(0, 0, PW, PH, PLATE_R)
    corner_holes(d)
    for i in range(-2, 3):
        d.slot(FAN_C[0] + i * (VENT_SLOT[0] + 6), FAN_C[1],
               VENT_SLOT[1], VENT_SLOT[0], horizontal=False)
    for x, y, h, txt in ENGRAVE:
        d.stroke_text(x, y, h, txt)
    return d


# The small sub-plates are gone. They existed so a module could ride on its own
# carrier instead of bolting to plate B, which stopped being worth two extra
# parts and a deck pattern once every board bolts straight down.
# All four in 5 mm. Three reasons, in order: it makes the stack come out at
# exactly 180 mm, which 3 mm tops cannot (16 mm of plate needs 164 mm of gap and
# standoffs come in 5 mm steps); it makes the order one thickness instead of
# two; and a 5 mm top plate is the one to hang an LCD on.
PLATES = [('plate-a-bottom-5T', plate_bottom, 5),
          ('plate-b-middle-5T', plate_middle, 5),
          ('plate-c-top-5T', plate_top, 5),
          ('plate-d-upper-5T', plate_upper, 5)]


# Nesting: plates of the same thickness laid out on one sheet, so a shop that
# quotes by sheet area does not charge three separate offcuts. (x, y) is the
# lower-left corner of each plate on its sheet.
NESTS = {
    '5T': dict(sheet=(520, 380),
               place=[('plate-a-bottom-5T', 5, 5), ('plate-b-middle-5T', 5, 195),
                      ('plate-c-top-5T', 265, 5), ('plate-d-upper-5T', 265, 195)]),
}


# One sheet with every plate on it, annotated - the layout acrylic shops ask
# for. (name, x, y, label) with the label written under each plate.
COMBINED_SHEET = (580.0, 430.0)
COMBINED = [
    ('plate-a-bottom-5T', 15.0, 235.0, 'PLATE A (BOTTOM)  5T  CLEAR  x1'),
    ('plate-b-middle-5T', 300.0, 235.0, 'PLATE B (MIDDLE)  5T  CLEAR  x1'),
    ('plate-c-top-5T', 15.0, 30.0, 'PLATE C (TOP)  5T  CLEAR  x1'),
    ('plate-d-upper-5T', 300.0, 30.0, 'PLATE D (UPPER)  5T  CLEAR  x1'),
]


def shift_entities(sub, ox, oy):
    out = []
    for e in sub.e:
        def mv(m):
            code, val = m.group(1), float(m.group(2))
            return f"{code}\n{val + (ox if code in ('10', '11') else oy):.4f}"
        out.append(re.sub(r'\b(1[01]|2[01])\n(-?[\d.]+)', mv, e))
    return out


# ---- order drawing ------------------------------------------------------
# Laid out the way the shop's own example sheet is: one framed cell per part,
# part name and quantity at the top left of the cell, material and thickness
# stacked at the top right, overall dimensions on the part. Text is ASCII
# single-stroke so it always renders - the Korean equivalents go in the email.
ORDER_PLATES = ['plate-a-bottom-5T', 'plate-b-middle-5T', 'plate-c-top-5T',
                'plate-d-upper-5T']
ORDER_SPEC = {
    'plate-a-bottom-5T': ('BOTTOM PLATE A', '5T', 1),
    'plate-b-middle-5T': ('MIDDLE PLATE B', '5T', 1),
    'plate-c-top-5T': ('TOP PLATE C', '5T', 1),
    'plate-d-upper-5T': ('UPPER PLATE D', '5T', 1),
}
# cell box: x, y, w, h
ORDER_CELLS = {
    'plate-a-bottom-5T': (10.0, 300.0, 335.0, 250.0),
    'plate-b-middle-5T': (355.0, 300.0, 335.0, 250.0),
    'plate-c-top-5T': (10.0, 30.0, 335.0, 250.0),
    'plate-d-upper-5T': (355.0, 30.0, 335.0, 250.0),
}
ORDER_SHEET = (700.0, 600.0)
ARROW = 2.4
DIM_H = 5.0


def plate_size(name):
    return (PW, PH)          # every plate is the full 250 x 180 now


def dim_h(d, x1, x2, y, label, layer='DIM'):
    d.line(x1, y, x2, y, layer)
    for x, sgn in ((x1, 1), (x2, -1)):
        d.line(x, y, x + sgn * ARROW, y + ARROW * 0.4, layer)
        d.line(x, y, x + sgn * ARROW, y - ARROW * 0.4, layer)
    w = len(label) * DIM_H * 0.76
    d.stroke_text((x1 + x2) / 2 - w / 2, y + 2.0, DIM_H, label, layer)


def dim_v(d, y1, y2, x, label, layer='DIM'):
    d.line(x, y1, x, y2, layer)
    for y, sgn in ((y1, 1), (y2, -1)):
        d.line(x, y, x + ARROW * 0.4, y + sgn * ARROW, layer)
        d.line(x, y, x - ARROW * 0.4, y + sgn * ARROW, layer)
    d.stroke_text(x - 4 - len(label) * DIM_H * 0.76, (y1 + y2) / 2 - DIM_H / 2,
                  DIM_H, label, layer)


def order_cell(d, name, builders):
    cx, cy, cw, ch = ORDER_CELLS[name]
    title, thick, qty = ORDER_SPEC[name]
    w, h = plate_size(name)
    d.line(cx, cy, cx + cw, cy, 'DIM')
    d.line(cx, cy + ch, cx + cw, cy + ch, 'DIM')
    d.line(cx, cy, cx, cy + ch, 'DIM')
    d.line(cx + cw, cy, cx + cw, cy + ch, 'DIM')
    # part name + quantity, top left inside the cell
    d.stroke_text(cx + 8, cy + ch - 16, 7.0, f'{title}   {qty} EA', 'DIM')
    # material stack: top right if the cell is wide enough, else under the title
    lines = ('CLEAR ACRYLIC ' + thick, f'{w:.0f} X {h:.0f} MM', 'CUT ON LAYER CUT')
    widest = max(len(t) for t in lines) * 4.6 * 0.76
    title_w = len(f'{title}   {qty} EA') * 7.0 * 0.76
    right_aligned = cw - 16 - title_w > widest
    for i, line in enumerate(lines):
        tw = len(line) * 4.6 * 0.76
        if right_aligned:
            d.stroke_text(cx + cw - 8 - tw, cy + ch - 14 - i * 9, 4.6, line, 'DIM')
        else:
            d.stroke_text(cx + 8, cy + ch - 27 - i * 8, 4.6, line, 'DIM')
    # the part itself, with room left and below for the dimensions
    ox = cx + (cw - w) / 2 + 6
    oy = cy + 34
    if not right_aligned:          # material text took a band under the title
        oy = cy + 30
    d.e += shift_entities(builders[name](), ox, oy)
    dim_h(d, ox, ox + w, oy - 13, f'{w:.0f}')
    dim_v(d, oy, oy + h, ox - 13, f'{h:.0f}')
    return ox, oy


def combined_order(builders):
    """The sheet that goes to the shop."""
    d = Dxf()
    W, H = ORDER_SHEET
    d.rounded_rect(0, 0, W, H, 0.1, layer='SHEET')
    d.stroke_text(12, H - 22, 9.0, 'LAN9692 ACRYLIC FRAME', 'DIM')
    d.stroke_text(12, H - 36, 5.0,
                  'UNIT MM   MATERIAL CLEAR ACRYLIC PMMA   5 PARTS   1 SET', 'DIM')
    d.stroke_text(12, H - 46, 5.0,
                  'LAYER CUT = CUT   LAYER ENGRAVE = ENGRAVE ONLY   '
                  'LAYER DIM AND SHEET DO NOT CUT', 'DIM')
    for name in ORDER_PLATES:
        order_cell(d, name, builders)
    d.stroke_text(355, 244, 5.0, 'HOLES  O36 FAN BORE   O3.4 FOR M3   '
                                 'O2.9 FOR M2.5', 'DIM')
    d.stroke_text(355, 232, 5.0, 'SLOTS AS DRAWN   TOP PLATE C HAS ENGRAVED '
                                 'TEXT ON LAYER ENGRAVE', 'DIM')
    return d


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
    path = os.path.join(out, 'combined-order.dxf')
    n = combined_order(builders).save(path)
    made.append(path)
    print(f"  {'combined-order.dxf':24s} {ORDER_SHEET[0]:.0f} x {ORDER_SHEET[1]:.0f}"
          f" mm sheet, {len(ORDER_PLATES)} plates dimensioned, {n} entities"
          f"   <- SEND THIS")
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
