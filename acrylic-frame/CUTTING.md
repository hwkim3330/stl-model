# Cutting order — LAN9692 acrylic frame

Send `acrylic-frame-dxf.zip`. **Three plates** in two thicknesses:

| File | Material | Thickness | Qty |
|---|---|---|---|
| `plate-a-bottom-5T.dxf` | clear acrylic (PMMA) | **5 mm** | 1 |
| `plate-b-middle-5T.dxf` | clear acrylic (PMMA) | **5 mm** | 1 |
| `plate-c-top-3T.dxf` | clear acrylic | **3 mm** | 1 |

Optional: `nested-5T.dxf` and `nested-3T.dxf` in the same zip hold the same
plates pre-laid-out on one sheet per thickness, for a shop that prices by sheet
area rather than per part. Their outer rectangle is a reference outline on
layer `SHEET`, not a cut path. Ignore them unless the quote suggests otherwise.

* Units are **millimetres** (R12 DXF, `$INSUNITS = 4`).
* Every closed shape is a cut path — outline, holes and slots alike. There is no
  engraving layer, everything is on layer `CUT`.
* All holes are **Ø3.4** (M3 free fit), **Ø2.9** for M2.5 on plate D, and one
  **Ø36** fan bore. Ø36 rather than Ø38: at the fan's 32 mm screw pitch a Ø38
  bore leaves only 1.93 mm of acrylic to each screw hole, Ø36 leaves 2.93.
* The fan screws through plate B **into its own frame** — self-tapping M3 × 16,
  no nut, there is no room for one inside a fan. The screws that come in the
  fan's box are fatter and want ~Ø4.5 holes; if you would rather use those, set
  `FAN_SCREW_D = 4.5` and `FAN_BORE = 35.0` in `make_plates.py` and re-cut,
  otherwise the web to the bore drops to 2.38 mm.
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
* **Genders**: the adapter ends in a male plug, so the splitter must be *1
  female in → 2 male out*, and the fan lead therefore needs a **female barrel
  socket**, not a plug. Buying a plug for the fan leaves you male-to-male.
* On a Noctua, solder that socket onto the **included extension cable**, not
  onto the fan's own lead — the fan stays stock and reusable.
* Sizing: the board budgets 12 V @ 4.1 A worst case (<50 W); a 40 mm fan is
  about 0.15 A. **A 12 V 5 A adapter covers both.**
* The board's own PTC fuse (4 A hold / 8 A trip, 15 V) only protects its own
  leg. The fan leg is unfused — fine at 2 W, add an inline fuse if you care.
* Do **not** feed 24 V. The input TVS is an SMBJ13D, 13 V standoff.

The alternative is a 5 V fan off expansion header J4, which does budget
5 V @ 2 A — no splitter, but it puts fan inrush on the switch's own rail.

## Ask about the standoffs, but do not count on it

The shop cuts sheet. A 45 mm threaded M3 standoff is turned metal or moulded
nylon — a different trade — and lasering nine 5 mm acrylic rings to stack up to
45 mm is worse than a standoff in every way. Some shops do resell hardware as
an add-on though, so it costs nothing to ask in the order note. If they say no,
the whole hardware table below goes to a parts supplier instead.

### Why F/F standoffs, and why plate B has eight corner holes

An M/F standoff's male stud is 6 mm. Through a 5 mm plate that leaves 1 mm —
not enough for a nut underneath plate A, and not enough thread to bite into the
standoff below at plate B. So every joint is a plain **F/F standoff with a screw
at each end** instead.

That means a plate cannot share one hole between the column below it and the
column above it, so the two columns sit at different Y: the **A→B column at the
four corners** (8, 8) … (242, 172), and the **B→C column** at (8, 40), (242, 40),
(8, 140), (242, 140). Plate A carries only the lower set, plate C only the
upper, and **plate B carries both — eight holes**.

### Before you send this: check two hole patterns

Plate A's eight holes came out of the LAN9692's **drill file** and are exact.
The two small boards' holes came off **drawings**, and that is the only error in
this build that would scrap a plate. Put a ruler on the real boards and compare:

![check](img/hole_check.png)

They will look wrong, and that is expected — neither pattern is a rectangle. The
TC397 has two holes on its front edge plus one on the right at mid-height and
one on the left near the top. The T-ETH-Elite's four corner holes are 58.00 mm
apart at the bottom and 60.25 at the top.

The mounts are cut as **9 mm slots**, not round holes, so a misread of up to
±2.8 mm in X still bolts up. `MOUNT_SLOT = 3.4` in `make_plates.py` turns them
back into plain holes once you have measured.

### The small boards bolt straight to plate B

There are no sub-plates. Plate B is cut with each board's **own** mounting
pattern, so a board goes on four standoffs directly:

| | holes in plate B | worst web to anything else |
|---|---|---|
| TC397 | 4, its real pattern | 23.9 mm |
| T-ETH-Elite | 4, its real (asymmetric) pattern | 14.6 mm |

This replaced an earlier design where plate B had four *slots* per module on a
shared 45 mm square and each board rode on its own 3 mm sub-plate. The slots
existed to keep plate B generic, but they cost two extra plates, 8 extra screws
and 3 mm of height — and for the T-ETH-Elite they did not even work: its hole
span is 60.25 × 41.60 mm against a 45 mm square, so its screws landed **on top
of** the slots, overlapping by up to 3.18 mm.

One hole set per board instead of two is simpler, and the thinnest web on
plate B went from 3.36 mm to 14.6 mm. `DIRECT_MOUNT = False` in
`make_plates.py` brings the slots and plates D/E back if you would rather keep
plate B board-agnostic.

## Two separate orders

The laser shop cuts plates and nothing else. Standoffs, screws, the fan and the
DC splitter come from an electronics parts supplier — order them at the same
time so they arrive together, but they are not part of the acrylic job.

| Order | Where | What |
|---|---|---|
| 1 | laser / acrylic shop | `acrylic-frame-dxf.zip` — 3 plates |
| 2 | electronics parts supplier | the hardware table below |

**Nothing is 3D printed in this build.** The printed cases elsewhere in the
repo still work if you would rather box the small boards up, but plates D and E
replace them.

## Hardware

| Part | Size | Qty |
|---|---|---|
| M3 hex standoff, board → plate A | 10 mm **F/F** | 8 |
| M3 hex standoff, plate A → B | 45 mm **F/F** | 4 |
| M3 hex standoff, plate B → C | 45 mm **F/F** | 4 |
| M3 screw | 8 mm | ~20 |
| M3 nut | — | a few |
| 40 × 40 fan | 10 mm thick, **12 V**, 32 × 32 mm pitch | 1 |
| Rubber feet | self-adhesive | 4 |
| 12 V DC Y splitter | 5.5 × 2.5 mm | 1 |
| 12 V adapter | 5 A, 5.5 × 2.5 mm | 1 |

## Plates D and E — the small boards, bare

`plate-d-eth-elite-3T.dxf` replaces the printed T-ETH-Elite case and its
adapter with one 76 × 60 mm sheet: the board bolts to it on M2.5 standoffs and
it bolts to plate B on the usual 45 mm deck square. Lower, cheaper, nothing to
print.

This is now safe to cut because the hole pattern is confirmed. **The four holes
really are not a rectangle** — the bottom pair is 58.0 mm apart and the top pair
60.25 — and two independent LilyGo files agree on that to 0.04 mm, so it is the
design and not a CAD slip:

| Source | bottom pair | top pair |
|---|---|---|
| `shell/3D/T-ETH-ELite.7z` (3D CAD) | 58.00 | 60.25 |
| `shell/T-ETH-ELite.dxf` (2D mechanical) | 58.04 | 60.24 |

Holes from the PCB's bottom-left corner: **(3.33, 4.63), (61.33, 4.63),
(2.98, 46.23), (63.23, 46.20)**, Ø2.5 → cut Ø2.9 for M2.5 free fit. The PCB is
**66.191 × 49.192 mm** — LilyGo's "50 × 67 mm" is rounded, and the sub-plate
uses the measured figure. Closest board hole to a deck hole is 6.27 mm, so
nothing clashes.

Needs 4 × M2.5 × 6 standoffs and 4 × M2.5 screws instead of the printed case.

## Why the TC397 keeps its printed case

Mounting the bare boards on standoffs straight to plate B would be neater, and
for the LAN9692 that is exactly what plate A does — it has **8 × M3 holes** in
the drill file. The other two do not have a pattern worth drilling to:

* **TC397 Application Kit** — only **2 mounting holes**, Ø6 pads at (11, 4) and
  (89, 4), both on the same edge (figure 7-7 of the Application Kit manual, and
  all four corners were checked). Two screws on one edge leaves the opposite
  edge — the one with POWER, USB, RJ45, CAN and the SD slot — cantilevered
  every time something is plugged in.
The T-ETH-Elite is the opposite case — its hole pattern *is* confirmed, so
plate D above lets it mount bare. The TC397's printed case stays. **Standoff-mounting them is a fine idea — the blocker is only the coordinates,
and one caliper session removes it.** Measure the T-ETH-Elite's four Ø2.5 hole
centres and the TC397's two Ø6 centres, and a small 3 mm acrylic sub-plate
replaces each printed case: the boards then sit ~10 mm off plate B instead of
inside a 38 mm box, the stack gets shorter, and nothing needs printing.

Slots instead of holes would absorb the uncertainty in principle, but not here:
the T-ETH-Elite's hole span is 41.6 mm in Y against the 45 mm deck square, so a
slot long enough to cover the CAD's 2.25 mm discrepancy comes within 0.7 mm of
a deck hole. Too thin to survive in 3 mm acrylic. Measured holes, not slots.

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
