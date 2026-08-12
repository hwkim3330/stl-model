# LAN9692 acrylic frame

Three laser-cut plates instead of a printed box. Order file:
**[`acrylic-frame-dxf.zip`](acrylic-frame-dxf.zip)** — see [CUTTING.md](CUTTING.md)
for the material/thickness/quantity table and the hardware list.

![plates](img/plates.png)

| Plate | Material | Size | Carries |
|---|---|---|---|
| A — bottom | 5 mm clear acrylic | 250 × 180 mm | LAN9692 on 8 × M3 standoffs |
| B — middle | 5 mm clear/smoke | 250 × 180 mm | 40 mm fan underneath, module trays on top |
| C — top | 3 mm clear | 250 × 180 mm | guard, intake slots over the fan |

Stack ≈ 5 + 45 + 5 + 40 + 3 = **98 mm** tall.

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
  at (62, 128) and (62, 52). Slots, not holes, so a tray can shift ±6 mm.
* **Plate C** — five 8 × 60 mm intake slots over the fan.

## Fan power

Run the fan off its own supply, not off the board. The expansion header J4 does
budget 5 V @ 2 A, but on a test rig you do not want fan noise on the switch's
rails. Simplest: a **12 V fan tapped at the jack net** — you are already
bringing 12 V in, and it skips the buck converter a 5 V fan would need.

## Regenerating

```bash
python3 make_plates.py     # -> dxf/*.dxf + acrylic-frame-dxf.zip
```

Plate size, corner radius, fan size, slot pattern and zone positions are all
constants at the top of the script. `PW, PH = 260, 190` if you want more room
for cable ties and a switch.
