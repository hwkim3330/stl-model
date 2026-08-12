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

## Hardware

| Part | Size | Qty |
|---|---|---|
| M3 hex standoff, board → plate A | 10 mm F/F | 8 |
| M3 hex standoff, plate A → B | **45 mm** M/F | 4 |
| M3 hex standoff, plate B → C | **40 mm** M/F | 4 |
| M3 screw | 8 mm | ~20 |
| M3 nut | — | a few |
| 40 × 40 fan | 10 mm thick, 12 V | 1 |
| Rubber feet | self-adhesive | 4 |

Stack height comes out ≈ 5 + 45 + 5 + 40 + 3 = **98 mm**.

## Why 45 mm between A and B

The board sits 10 mm above plate A on standoffs, the PCB is 1.5 mm, and the
tallest part with a sourced height is 13.5 mm (the MATEnet headers and the
RJ45) — so the board envelope tops out around 25 mm. A 10 mm fan hanging under
plate B then occupies 35–45 mm, leaving ~10 mm of plenum.

The five DC-DC daughter modules are the one height nobody has published. If
they turn out taller than ~20 mm, **change the four standoffs, not the plates** —
that is the whole point of building it this way.
