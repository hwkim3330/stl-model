# Cutting order — LAN9692 acrylic frame

**Send `combined-all-plates.dxf`.** One 580 × 430 mm sheet with all five plates
laid out and annotated with thickness, colour and quantity — the format acrylic
shops ask for. The individual plate files are in the same zip if they would
rather have them separately.

| Plate | File | Material | Size | Qty |
|---|---|---|---|---:|
| A — bottom | `plate-a-bottom-5T.dxf` | clear acrylic (PMMA) | 250 × 180 mm | 1 |
| B — middle | `plate-b-middle-5T.dxf` | clear acrylic | 250 × 180 mm | 1 |
| C — top | `plate-c-top-3T.dxf` | clear acrylic | 250 × 180 mm | 1 |
| D — T-ETH-Elite sub-plate | `plate-d-eth-elite-3T.dxf` | clear acrylic | 76 × 60 mm | 1 |
| E — TC397 sub-plate | `plate-e-tc397-3T.dxf` | clear acrylic | 110 × 110 mm | 1 |

**A and B are 5 mm. C, D and E are 3 mm.** All clear.

* Units are **millimetres** (R12 DXF, `$INSUNITS = 4`).
* Everything on layer **`CUT`** is a cut path — outline, holes and slots alike.
* Layer **`ENGRAVE`** is the lettering on the top plate: **engrave, do not cut.**
  Single-stroke vector text, so no font is needed.
* Layers `TEXT` and `SHEET` are drawing annotation and stock outline; neither
  cuts nor engraves.
* Holes: **Ø3.4** (M3 free fit), **Ø2.9** (M2.5), and one **Ø36** fan bore.
  Ø36 rather than Ø38 because at the fan's 32 mm screw pitch a Ø38 bore would
  leave only 1.93 mm of acrylic to each screw hole; Ø36 leaves 2.93.
* Kerf compensation: leave it to the shop. Every fit here is a clearance fit.

## Engraving on the top plate

Plate C carries **"KETI"** at 14 mm and **"LAN9692 TSN BENCH"** at 7 mm on layer
`ENGRAVE`. Ask the shop for **각인 (engrave)** on that layer — it is a second
operation and usually a small extra charge.

The real KETI logo is not in here: engraving artwork has to be **vector**
(AI / SVG / DXF). Send me the logo file and it drops onto the same layer. Change
or remove the wording in `ENGRAVE` at the top of `make_plates.py`.

## Why plates D and E are included

Plate B is cut **both** ways: with each small board's own mounting pattern, so a
board can bolt straight down, **and** with a 35 × 45 mm four-hole deck pattern,
so a sub-plate can be used instead. D and E are those sub-plates. Cutting all
five keeps the choice open — they are small and ride in offcut, and plate B never
has to be re-cut to change what sits on it.

The deck pattern is 35 × 45 mm rather than a square because a 45 mm square could
not clear the T-ETH-Elite's own mount slots. 35 × 45 clears both boards by more
than 4.8 mm.

## Check two hole patterns before sending

Plate A's eight holes came out of the LAN9692's **Excellon drill file** and are
exact. The two small boards' holes came off **drawings**, and that is the only
error here that could scrap a plate:

![check](img/hole_check.png)

They look wrong because neither pattern is a rectangle. The TC397 has two holes
on its front edge plus one on the right at mid-height and one on the left near
the top; the T-ETH-Elite's corner holes are 58.00 mm apart at the bottom against
60.25 at the top — two independent LilyGo files agree on that to 0.04 mm.

| | source | if the hole is not there |
|---|---|---|
| LAN9692, 8 holes | drill file | n/a, exact |
| TC397 (11, 4), (89, 4) | Ø6 pads, unambiguous in figure 7-7 | n/a |
| TC397 (96.99, 59), (16, 82) | Ø4 pads, dimensioned but not proven | leave that screw out and prop the corner with an adhesive nylon standoff |
| T-ETH-Elite, 4 holes | LilyGo 2D DXF + 3D CAD | measure and re-cut plate B |

The board mounts are cut as **9 mm slots**, not round holes, so a misread of
±2.8 mm in X still bolts up. `MOUNT_SLOT = 3.4` in `make_plates.py` turns them
into plain holes once measured.

## Two separate orders

The laser shop cuts plates and nothing else. Standoffs, screws, the fan and the
DC parts come from an electronics supplier. **Nothing is 3D printed.**

| Order | Where | What |
|---|---|---|
| 1 | laser / acrylic shop | `combined-all-plates.dxf` |
| 2 | electronics parts supplier | the tables below, and `BOM.csv` |

Some shops resell M3 hardware, so it costs nothing to ask in the order note — but
a 45 mm threaded standoff is turned metal or moulded nylon, a different trade.

## Hardware

| Part | Size | Qty | Note |
|---|---|---:|---|
| Hex standoff F/F | M3 × 10 mm | 8 | LAN9692 on plate A |
| Hex standoff F/F | M3 × 45 mm | 8 | 4 for A→B, 4 for B→C |
| Hex standoff F/F | M3 × 8 mm | 4 | TC397 |
| Hex standoff F/F | M2.5 × 8 mm | 4 | T-ETH-Elite |
| Screw, pan head | M3 × 6 / 8 / 10 / 20 mm | 8 / 16 / 12 / 4 | `BOM.csv` says which goes where |
| Screw, pan head | M2.5 × 6 / 10 mm | 4 / 4 | T-ETH-Elite |
| Nut | M3 | 12 | 4 for the fan, rest spare |
| Washer | M3 nylon | 20 | under any head landing on acrylic |
| Nylon standoff, adhesive base | 8 mm | 2 | fallback props for the TC397 |
| Rubber foot | self-adhesive | 4 | under plate A |

**The LAN9692's own drill is Ø3.048 mm**, so an M3 screw is a very tight fit
through the board. Try one by hand first; if it binds, use M2.5 for the
board→plate A joint. The Ø3.4 acrylic hole takes either.

### Why F/F standoffs, and why plate B has eight corner holes

An M/F standoff's male stud is 6 mm. Through a 5 mm plate that leaves 1 mm — not
enough for a nut under plate A, and not enough thread to bite into the standoff
below at plate B. So every joint is a plain **F/F standoff with a screw at each
end**, and a plate cannot share one hole between the column below it and the one
above. The **A→B column sits at the four corners** (8, 8) … (242, 172), the
**B→C column** at (8, 40), (242, 40), (8, 140), (242, 140).

Stack height ≈ 5 + 45 + 5 + 45 + 3 = **103 mm**.

## Electrical

| Part | Spec | Qty |
|---|---|---:|
| Fan | 40 × 40 × 10 mm, **12 V** — Noctua NF-A4x10 FLX | 1 |
| DC adapter | 12 V 5 A, barrel 5.5 × 2.5 mm, centre + | 1 |
| DC splitter | barrel 5.5 × 2.5, **1 female in → 2 male out** | 1 |
| Barrel socket (female), solder type | 5.5 × 2.5 mm | 1 |

```
12 V 5 A adapter ──> splitter ─┬─> LAN9692 J23   (5.5 x 2.5, centre +)
                               └─> 40 mm 12 V fan
```

* Nothing is tapped on the PCB — **the board has no fan header.**
* The board's jack is 5.5 / **2.5** mm (PJ-002BH). Most cheap splitters are
  5.5 / 2.1 and contact badly; get the 2.5.
* **Genders**: the adapter is male, so the splitter is female-in / male-out and
  the fan lead needs a **female socket**. A plug leaves you male-to-male.
* On a Noctua, solder that socket to the **included extension cable**, not the
  fan's own lead.
* The fan bolts through plate B with **M3 × 20 and a nut** — the screws in the
  fan's box are fatter and would want Ø4.5 holes.
* Never feed 24 V: the board's input TVS is an SMBJ13D, 13 V standoff.

## The one measurement still worth taking

The LAN9692's five DC-DC daughter modules have no published height. The fan
underside sits at z = 39 mm and the PCB top at 16.5, so anything up to
**22.5 mm** above the PCB clears it — allowing 3 mm of margin, check that the
tallest module is under about **19 mm**. If it is taller, lengthen the four A→B
standoffs; the plates do not change.
