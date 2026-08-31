# LAN9692 acrylic frame

Four laser-cut plates, all 250 × 180 × 3 mm, instead of a printed box. Order file:
**[`acrylic-frame-dxf.zip`](acrylic-frame-dxf.zip)** — see [CUTTING.md](CUTTING.md)
for the material/thickness/quantity table and the hardware list.

![assembly](img/assembly_labelled.png)
![joints](img/joint_detail.png)
![exploded](img/exploded.png)

`assembly.py` builds the whole stack in 3D from the same constants the DXFs come
from, so the plates here and the plates the cutter gets cannot drift apart. It
is a picture, not a printable part — `assembly.stl`, 250 × 180 × 167 mm over
the nuts.
`ACRYLIC_ONLY = False` at the top swaps the bare boards back for the printed
cases.

![plate A with the board](img/plate_a_board.png)
![plate A holes](img/plate_a_holes.png)

Plate A with the LAN9692 on it, and the same plate with the board hidden so the
eight standoffs are visible in their holes. It runs its own checks:

```
hole 1 board (  3.556,146.304) -> plate ( 21.876,161.374)  on plate=True  nearest corner standoff  17.5 mm
...
fan bore centre  (185.63, 93.76)
  switch at plate (185.63, 93.76)   offset 0.000 mm

vertical stack
  plate A               0.0 ..    5.0
  PCB                  15.0 ..   16.5
  tallest part top     30.5   (DC-DC U3, ADM00987, assumed)
  fan                  40.0 ..   50.0   clearance to board   9.5 mm
  plate B              50.0 ..   55.0
  tallest module top   84.6   clearance to plate C  15.4 mm
  plate C             100.0 ..  103.0

fastener engagement  (screw length - what it passes through)
  LAN9692 standoff, from under plate A   M3 x  8.0 through 5.0 mm -> 3.0 mm   OK
  A->B standoff, from under plate A      M3 x 10.0 through 5.0 mm -> 5.0 mm   OK
  A->B standoff, from above plate B      M3 x 10.0 through 5.0 mm -> 5.0 mm   OK
  B->C standoff, from under plate B      M3 x  8.0 through 5.0 mm -> 3.0 mm   OK
  B->C standoff, from above plate C      M3 x  8.0 through 3.0 mm -> 5.0 mm   OK
```

The two clearances are the ones worth watching. Both are computed against the
**assumed** 14 mm DC-DC module height — measure a module and rerun; if it comes
out taller, `H_AB` at the top of `assembly.py` is the standoff to lengthen, and
nothing else in the design changes.

![plates](img/plates.png)

**Nothing here is 3D printed.** Four laser-cut plates and hardware.

| Plate | Material | Size | Carries |
|---|---|---|---|
| A — bottom | 3 mm clear acrylic | 250 × 180 mm | LAN9692 on 8 × M3 standoffs |
| B — middle | 3 mm clear acrylic | 250 × 180 mm | 40 mm fan and four boards, all on top |
| C — top | 3 mm clear | 250 × 180 mm | Raspberry Pi 4B and the KA7_UNO CAN board |
| D — upper | 3 mm clear | 250 × 180 mm | Raspberry Pi 7-inch Touch Display, centred |

All four boards bolt **straight to plate B**, cut with each board's own pattern:
the TC397's four holes, the T-ETH-Elite's four asymmetric ones, and four each for
the RJ45 and MATEnet fault injection modules. No sub-plates.

![plate B layout](img/plateB_layout.png)

Every mount is a **plain round hole**. Two of four per board used to be 9 mm slots,
buying ±2.8 mm against a misread of the drawing-derived TC397 and T-ETH-Elite
coordinates — but a board has since been offered up to a cut plate and sat
centred, so the slots are gone. `MOUNT_SLOT = 9.0` puts them back.

Positions are chosen so each board's **port edge lands next to a plate edge**,
not in the middle of the plate: the TC397's connector row ends 14 mm from the
back edge, the T-ETH-Elite's USB-C 10 mm from the front and its RJ45 17 mm from
the right. Cables leave the frame instead of crossing it. Both boards clear the
fan and the standoff columns by ≥ 7.8 mm, and there is 48 mm between them.

Stack = 3 + 50 + 3 + 50 + 3 + 50 + 3 = **162 mm**.

### What sits where

| Plate | Carries |
|---|---|
| A | LAN9692 EVB on 8 × M3 standoffs |
| B | 40 mm fan on top over the bore; TC397, T-ETH-Elite, and the RJ45 and MATEnet fault injection modules |
| C | Raspberry Pi 4B, and the KETI KA7_UNO CAN board |
| D | plain guard |

Plate B was solved as a whole rather than filled in board by board, so every board
has at least 20 mm to its nearest neighbour. The T-ETH-Elite is turned 180° to put
its USB-C at the back rim, which is what frees the whole front of the plate for
the two injection modules — one per half, 71.4 mm apart so two facing RJ45 plugs
both have room.

## You cannot order acrylic from an STL

Laser cutting is a 2D process: the machine needs closed **vector paths** in a
plane plus a stated sheet thickness. An STL is a triangle mesh of a solid with
no paths in it at all — a shop would have to slice it and re-trace the outline
by hand, and most will just refuse. That is why this folder ships **DXF**, not
STL.

Rough guide to what each process eats:

| Process | Wants | Thickness comes from |
|---|---|---|
| Laser cut acrylic | **DXF / AI / SVG / DWG** (2D) | you state it when ordering |
| CNC router / mill | DXF for 2.5D, **STEP** for 3D | the model or the order |
| 3D printing | **STL / STEP / 3MF** | the model itself |

## Why plates and not the printed box

The printed enclosures in this repo are sound — every dimension comes from the
Gerber and pick-and-place files — but a 213 × 150 mm board makes them big:
119 cm³ for the open tray, 170 cm³ vented, 235 cm³ fully sealed. Flat plates
turn most of that volume into three sheets and a bag of standoffs, keep the
board visible, and make the *one* number nobody has published — how much
clearance the five DC-DC daughter modules need — a standoff swap instead of a
reprint.

Nothing here is printed. The printed cases elsewhere in the repo still work if
you would rather box the small boards up.

## What is on the plates

Everything positioned from the released manufacturing data, not measured off a
photo:

* **Plate A** — the eight LAN9692 mounting holes, tool T23 in the drill file
  (Ø3.048 mm), opened to Ø3.4 for M3. The board is centred, so the offset from
  the plate origin is (18.32, 15.07).
* **Plate B** — the fan bore is centred on **U1, the switch die itself**, at
  pick-and-place coordinate (167.31, 78.69) → plate (185.63, 93.76). The fan
  hangs underneath and blows down onto it. Ø36 bore, 32 mm M3 pitch, for a
  standard 40 mm fan.
* **Plate B** — each board's own mount pattern, round: the TC397, the
  T-ETH-Elite and both fault injection modules.
* **Plate C** — the Raspberry Pi 4B at 58 × 49, and the KA7_UNO CAN board at
  63 × 83.
* **Plate D** — four column holes and nothing else.

## Fan power

**One 12 V adapter, split before the board — nothing is tapped on the PCB.**

```
GST60A12-P1M ──> Y splitter ─┬─> LAN9692 J23    (5.5 x 2.5, centre +)
  12 V 5 A                   └─> 10-02879 socket ──> Noctua NF-A4x10
```

The board's jack is 5.5 / **2.5** mm (PJ-002BH, centre positive) and most cheap
splitters are 5.5 / 2.1, which contacts badly — get the 2.5 mm one. On the Mean
Well supply the suffix is what decides it: **P1M is 2.5 mm, P1J is 2.1**. The
board budgets 4.1 A worst case and the fan draws 0.05 A (0.6 W at 12 V), so 5 A
covers both. Never feed it 24 V: the input TVS is an SMBJ13D with a 13 V
standoff.

Soldering the fan onto the socket, including which lead is the centre pin and
why the fan is bench-tested before it goes near the board, is in
[CUTTING.md](CUTTING.md#wiring-the-fan-to-the-socket).

## Regenerating

```bash
python3 make_plates.py     # -> dxf/*.dxf + acrylic-frame-dxf.zip
python3 assembly.py        # -> assembly.stl, img/*.png, fit checks
python3 review.py          # web, geometry and fastener audits on the DXFs
python3 render_all.py      # every img/*.png and assembly.stl, from one place
```

`review.py` checks the generated DXFs three ways: the acrylic left between
every pair of cut features and between each cut and the plate edge, the hole
count per plate against what the design should contain, and every screw
position in the build against the quantities in the BOM. It caught the fan bore
leaving 1.93 mm to its screw holes, and four screws missing from the BOM.

Plate size, corner radius, fan size, slot pattern and zone positions are all
constants at the top of the script. `PW, PH = 260, 190` if you want more room
for cable ties and a switch.
