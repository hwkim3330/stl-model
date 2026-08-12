# Cutting order — LAN9692 acrylic frame

Send `acrylic-frame-dxf.zip`. Three plates, all 250 × 180 mm with R6 corners.

| File | Material | Thickness | Qty |
|---|---|---|---|
| `plate-a-bottom-5T.dxf` | clear acrylic (PMMA) | **5 mm** | 1 |
| `plate-b-middle-5T.dxf` | clear or smoke acrylic | **5 mm** | 1 |
| `plate-c-top-3T.dxf` | clear acrylic | **3 mm** | 1 |

* Units are **millimetres** (R12 DXF, `$INSUNITS = 4`).
* Every closed shape is a cut path — outline, holes and slots alike. There is no
  engraving layer, everything is on layer `CUT`.
* All holes are **Ø3.4** (M3 free fit) except the **Ø38** fan bore.
* Slots are 3.4 mm wide × 16 mm long, rounded ends.
* Total cut area 3 × 0.045 m². Kerf compensation: leave it to the shop, the
  fits here are all clearance, nothing is press-fit.

## Power — one 12 V adapter, split before the board

The fan is 12 V and so is the board, so **do not tap anything on the PCB**.
Split on the DC side:

```
12 V 5 A adapter ──> Y splitter ─┬─> LAN9692 J23   (5.5 x 2.5 mm, centre +)
                                 └─> 40 mm 12 V fan
```

* The board's jack is **5.5 / 2.5 mm** (PJ-002BH, centre positive). Most cheap
  splitters are 5.5 / **2.1** — a 2.1 mm plug in a 2.5 mm jack makes poor
  contact. Buy the 2.5 mm one, or a 2.1→2.5 adapter for the board leg.
* Sizing: the board budgets 12 V @ 4.1 A worst case (<50 W); a 40 mm fan is
  about 0.15 A. **A 12 V 5 A adapter covers both.**
* The board's own PTC fuse (4 A hold / 8 A trip, 15 V) only protects its own
  leg. The fan leg is unfused — fine at 2 W, add an inline fuse if you care.
* Do **not** feed 24 V. The input TVS is an SMBJ13D, 13 V standoff.

The alternative is a 5 V fan off expansion header J4, which does budget
5 V @ 2 A — no splitter, but it puts fan inrush on the switch's own rail.

## Hardware

| Part | Size | Qty |
|---|---|---|
| M3 hex standoff, board → plate A | 10 mm F/F | 8 |
| M3 hex standoff, plate A → B | **45 mm** M/F | 4 |
| M3 hex standoff, plate B → C | **45 mm** M/F | 4 |
| M3 screw | 8 mm | ~20 |
| M3 nut | — | a few |
| 40 × 40 fan | 10 mm thick, 12 V | 1 |
| Rubber feet | self-adhesive | 4 |
| 12 V DC Y splitter | 5.5 × 2.5 mm | 1 |
| 12 V adapter | 5 A, 5.5 × 2.5 mm | 1 |

## What mounts where

| | Where | How |
|---|---|---|
| LAN9692 | plate A | 8 × M3 × 10 standoffs, its real hole pattern |
| 40 mm fan | under plate B, over the switch | 4 × M3 through the plate |
| **TC397 Application Kit** | plate B, zone at **(74, 90)** | its printed tray has 4 × Ø3.4 on the 45 mm square |
| **LilyGo T-ETH-Elite** | plate B, zone at **(178, 36)** | print `adapter_lilygo.stl`, bolt that down, drop the case in |

The two cases clear each other by 8.5 mm and the T-ETH-Elite sits 11.3 mm below
the fan. Swapping in two ESP32-S31 trays instead is `LAYOUT = 'two-s31'` at the
top of `make_plates.py` — same 45 mm square either way.

Stack height comes out ≈ 5 + 45 + 5 + 45 + 3 = **103 mm**.

## Why 45 mm between A and B

The board sits 10 mm above plate A on standoffs, the PCB is 1.5 mm, and the
tallest part with a sourced height is 13.5 mm (the MATEnet headers and the
RJ45) — so the board envelope tops out around 25 mm. A 10 mm fan hanging under
plate B then occupies 35–45 mm, leaving ~10 mm of plenum.

The five DC-DC daughter modules are the one height nobody has published. If
they turn out taller than ~20 mm, **change the four standoffs, not the plates** —
that is the whole point of building it this way.
