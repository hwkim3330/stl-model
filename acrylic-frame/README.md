# LAN9692 acrylic frame

Three laser-cut plates instead of a printed box. Order file:
**[`acrylic-frame-dxf.zip`](acrylic-frame-dxf.zip)** — see [CUTTING.md](CUTTING.md)
for the material/thickness/quantity table and the hardware list.

![assembly](img/assembly.png)
![joints](img/joint_detail.png)
![exploded](img/exploded.png)

`assembly.py` builds the whole stack in 3D from the same constants the DXFs come
from, so the plates here and the plates the cutter gets cannot drift apart. It
is a picture, not a printable part — `assembly.stl`, 250 × 180 × 103 mm.
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

**Nothing here is 3D printed.** Three laser-cut plates and hardware.

| Plate | Material | Size | Carries |
|---|---|---|---|
| A — bottom | 5 mm clear acrylic | 250 × 180 mm | LAN9692 on 8 × M3 standoffs |
| B — middle | 5 mm clear acrylic | 250 × 180 mm | 40 mm fan underneath; both small boards on top |
| C — top | 3 mm clear | 250 × 180 mm | guard, intake slots over the fan |

Both small boards bolt **straight to plate B**, which is cut with each board's
own mounting pattern — the TC397's four holes and the T-ETH-Elite's four
asymmetric ones. No sub-plates.

Stack ≈ 5 + 45 + 5 + 45 + 3 = **103 mm** tall.

### Plate B layout

`LAYOUT` at the top of `make_plates.py` picks what plate B carries. Both options
use the same 45 mm deck square, so any tray in this repo fits either:

| `LAYOUT` | Zones | Fits? |
|---|---|---|
| **`tc397+eth-elite`** (default) | TC397 case at (74, 90), T-ETH-Elite at (178, 36) | yes — 8.5 mm between the cases, 11.3 mm under the fan |
| `two-s31` | two 85 × 75 trays at (60, 132) and (60, 48) | yes — 9 mm apart |

The **ESP32-S31 CoreBoard case (85 × 75) will not fit beside the TC397** — the
strip left between the TC397 case and the fan bore is 39.1 mm. The LilyGo
T-ETH-Elite case is 72 × 53, which does fit, in the space under the fan.

The T-ETH-Elite case is a third-party design with no deck holes, so print
**`adapter_lilygo.stl`** (79 × 60 × 8.5 mm, 14.5 cm³): it bolts to the plate on
the 45 mm square through counterbored holes and the case drops into its rim.

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
118 cm³ for the open tray, 163 cm³ vented, 237 cm³ fully sealed. Flat plates
turn most of that volume into three sheets and a bag of standoffs, keep the
board visible, and make the *one* number nobody has published — how much
clearance the five DC-DC daughter modules need — a standoff swap instead of a
reprint.

Keep printing the parts that are actually 3D: the ESP32-S31 and TC397 trays,
and any adapter bracket. Plate B's slots use the **same 45 mm square** as the
`DECK` pattern on the printed LAN9692 lid, so those trays bolt to either.

## What is on the plates

Everything positioned from the released manufacturing data, not measured off a
photo:

* **Plate A** — the eight LAN9692 mounting holes, tool T23 in the drill file
  (Ø3.048 mm), opened to Ø3.4 for M3. The board is centred, so the offset from
  the plate origin is (18.32, 15.07).
* **Plate B** — the fan bore is centred on **U1, the switch die itself**, at
  pick-and-place coordinate (167.31, 78.69) → plate (185.63, 93.76). The fan
  hangs underneath and blows down onto it. Ø38 bore, 32 mm M3 pitch, for a
  standard 40 mm fan.
* **Plate B** — two mounting zones of four 3.4 × 16 mm slots on a 45 mm square,
  at **(60, 48)** for the ESP32-S31 and **(60, 132)** for the FIM or a spare.
  Slots, not holes, so a tray shifts ±6 mm. 84 mm apart, which clears two
  85 × 75 mm trays by 9 mm and keeps both away from the fan.
* **Plate C** — five 8 × 60 mm intake slots over the fan.

## How the sub-plates attach to plate B

Four M3 through the **45 mm deck square**, which every plate and tray in this
repo shares:

```
        board on M2.5 / M3 standoffs
   ┌──────────────────────────────┐
   │   plate D or E   3 mm        │   Ø3.4 holes on the 45 mm square
   ╞══════════════════════════════╡ ← M3 x 12 pan head, from above
   │   plate B        5 mm        │   3.4 x 16 mm SLOTS on the same square
   └──────────────────────────────┘ ← M3 nut underneath
```

The sub-plate has plain holes, plate B has **slots** running in X, so the
module shifts ±6.3 mm without a new plate. Checked: the hole and slot centres
coincide to **0.000 mm**, and the nut hangs into 19.5 mm of clear space above
the LAN9692's tallest part, so nothing fouls.

## Fan power

**One 12 V adapter, split before the board — nothing is tapped on the PCB.**

```
12 V 5 A adapter ──> Y splitter ─┬─> LAN9692 J23   (5.5 x 2.5 mm, centre +)
                                 └─> 40 mm 12 V fan
```

The board's jack is 5.5 / **2.5** mm (PJ-002BH, centre positive) and most cheap
splitters are 5.5 / 2.1, which contacts badly — get the 2.5 mm one. The board
budgets 4.1 A worst case and the fan draws ~0.15 A, so 5 A covers both. Never
feed it 24 V: the input TVS is an SMBJ13D with a 13 V standoff.

## Regenerating

```bash
python3 make_plates.py     # -> dxf/*.dxf + acrylic-frame-dxf.zip
python3 assembly.py        # -> assembly.stl, img/*.png, fit checks
python3 review.py          # web-thickness check on the generated DXFs
```

`review.py` checks the generated DXFs three ways: the acrylic left between
every pair of cut features and between each cut and the plate edge, the hole
count per plate against what the design should contain, and every screw
position in the build against the quantities in the BOM. It caught the fan bore
leaving 1.93 mm to its screw holes, and four screws missing from the BOM.

Plate size, corner radius, fan size, slot pattern and zone positions are all
constants at the top of the script. `PW, PH = 260, 190` if you want more room
for cable ties and a switch.
