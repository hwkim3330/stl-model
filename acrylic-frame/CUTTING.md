# Cutting order — LAN9692 acrylic frame

**Send `combined-order.dxf`.** One 700 × 600 mm sheet laid out the way the
shop's own example sheet is: a framed cell per part, part name and quantity at
the top left, material / thickness / size stacked at the top right, and the
overall dimensions on each part. The individual plate files are in the same zip
if they would rather have them separately.

![order drawing](img/order_drawing.png)

Text on the drawing is ASCII so it always renders, whatever CAD the shop uses.
The Korean equivalents for the order mail:

```
투명 아크릴 5T   250 x 180 mm   1EA   (하판 A, 중판 B)
투명 아크릴 3T   250 x 180 mm   1EA   (상판 C)
투명 아크릴 3T   110 x 110 mm   1EA   (보조판 E)
투명 아크릴 3T    76 x  60 mm   1EA   (보조판 D)
CUT 레이어 = 절단,  ENGRAVE 레이어 = 각인만,  DIM/SHEET 레이어 = 가공 없음
```

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

Plate C carries **"KETI"** at 32 mm high on layer `ENGRAVE`, in the clear area
left of the intake slots. Ask the shop for **각인 (engrave)** on that layer — a
second operation, usually a small extra charge.

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

Two of the four mounts per board are cut as **9 mm slots** rather than round
holes, so a misread of ±2.8 mm in X still bolts up; the other two are round and
locate the board so it cannot slide while being tightened. Setting
`MOUNT_SLOT = 0` in `make_plates.py` turns all of them into plain holes once the
boards have been measured. (`3.4` is not enough — it only rounds the Ø3.4 TC397
mounts and leaves the Ø2.9 T-ETH-Elite pair as short stadiums.)

## Two separate orders

The laser shop cuts plates and nothing else. Standoffs, screws, the fan and the
DC parts come from an electronics supplier. **Nothing is 3D printed.**

| Order | Where | What |
|---|---|---|
| 1 | laser / acrylic shop | `combined-order.dxf` |
| 2 | electronics parts supplier | the tables below, and `BOM.csv` |

Some shops resell M3 hardware, so it costs nothing to ask in the order note — but
a 45 mm threaded standoff is turned metal or moulded nylon, a different trade.

## Hardware

Part numbers in `BOM.csv`. Split it across three suppliers: **RS Korea** for
screws, nuts, standoffs and feet; **DigiKey Korea** for the washers, the power
supply and the barrel socket; a domestic shop for the fan and the Y splitter.

| Part | Size | Qty | Part number | Note |
|---|---|---:|---|---|
| Hex standoff F/F | M3 × 10 mm | 8 | RS 224-0443 | LAN9692 on plate A |
| Hex standoff F/F | M3 × 45 mm | 8 | RS 224-0449 | 4 for A→B, 4 for B→C |
| Hex standoff F/F | M3 × 8 mm | 4 | Würth 970080324 | TC397 |
| Hex standoff F/F | M2.5 × 8 mm | 4 | Würth 970080144 | T-ETH-Elite |
| Screw, pan head | M3 × 6 / 8 / 10 mm | 12 / 16 / 12 | RS 190-428 / 797-6193 / 528-744 | `BOM.csv` says which goes where |
| Screw, pan head | **M3 × 25 mm** | 4 | RS 914-1490 | fan only — see below |
| Screw, pan head | M2.5 × 6 / 10 mm | 4 / 4 | RS 528-716 / 797-6190 | T-ETH-Elite |
| Nut, nyloc | M3 | 12 | RS 521-917 | 4 for the fan, rest spare |
| Washer, nylon | M3 | 20 | Essentra MFW030A | under any head landing on acrylic |
| Nylon standoff, adhesive base | 8 mm | 2 | — | fallback props for the TC397 |
| Rubber foot | self-adhesive | 4 | RS 136-8964 | under plate A |

The two 45 mm and 10 mm standoffs are confirmed **Female/Female** on RS's own
page; RS's M/F parts in the same range have a 6 mm stud, which is exactly why
they cannot be used here. The rest of the numbers came in unverified — read the
description before you click buy.

### Buying it all domestically instead

The part numbers above exist to pin the *specification*, not the shop — every
line is a generic item, so a domestic order is reasonable. How far that was
actually confirmed, rather than assumed:

| Line | Domestic stock |
|---|---|
| M3 standoffs, screws, nyloc nuts, nylon washers | **found** — see the order below. 50 mm in place of 45 mm |
| **M2.5 F/F 8 mm standoff** | **not found in that order, and it is the one real gap** |
| female 5.5 × 2.5 pigtail | **found**: `AM2826`. Its sibling `AM2825` is the male version — easy to order by mistake |
| Y splitter | **found**: `NC066`, listed 5.5 × 2.5. The same Coms family also ships a 2.1, so check the part on arrival |
| 12 V 5 A adapter | not in that order |

Whichever way it is bought, three things decide whether it assembles:

| Check | Why |
|---|---|
| standoff is **암‑암 (F/F)**, not 암‑수 | a male stud cannot cross a 5 mm plate and still bite |
| barrel is **5.5 × 2.5**, not 5.5 × 2.1 | the board's PJ-002BH is 2.5; 2.1 contacts badly |
| socket is **female**, splitter is **female‑in / male‑out** | the adapter is male, so anything else leaves you male-to-male |

**If 45 mm standoffs are not stocked, use 50 mm.** The plates are 2D and do not
depend on it: the stack simply becomes 5 + 50 + 5 + 50 + 3 = 113 mm, and both
gaps get *more* clearance — more room over the LAN9692's unmeasured DC-DC
modules, more over the TC397. Going the other way is what needs care: 40 mm
leaves only about 2 mm above a 38 mm TC397 case.

A domestic order also settles 세금계산서 in one step, which a foreign
distributor does not.

### What was actually bought

디바이스마트, 2026-08-18. This is the set the frame was assembled from, so it
is the list to repeat rather than the imported part numbers above.

| Design line | Bought | Qty |
|---|---|---:|
| M3 F/F 10 mm — LAN9692 | PCB서포트 **플라스틱** F-10mm | 10 |
| M3 F/F 45 mm — columns | PCB서포트 금속 **F-50mm** | 10 |
| M3 F/F 8 mm — TC397 | M3 알루미늄 서포트 Female 8mm `SZH-ZR058` | 4 |
| M3 × 6 / 8 / 10 | 둥근머리 십자볼트 (니켈) | 20 each |
| M3 × 25 — fan | 스텐 둥근머리 십자볼트 M3x25 | 20 |
| M2.5 × 6 / 10 | 스텐 둥근머리 십자볼트 | 20 each |
| M3 nyloc nut | 로크(나일론)너트 M3 | 10 |
| M3 nylon washer | `MFW030A` | 20 |
| fan | Noctua NF-A4x10 FLX | 1 |
| female 5.5 × 2.5 pigtail | `AM2826` DC 2선 to DC 잭 Female(암), 0.3 m | 1 |
| male 5.5 × 2.5 pigtail | `VLT-CAB124` 27 cm AWG18 | 2 |
| female jack, screwless | `VLT-DC037` 푸쉬 터미널 | 1 |
| Y splitter | `NC066` Coms 2분배 35 cm, on/off | 1 |
| Y junction, solderless | 원터치 커넥터 WAGO `221-413` (3핀) | 2 |

**Still to buy: 4 × M2.5 F/F 8 mm standoffs** for the T-ETH-Elite. Nothing
substitutes — plate B's holes for that board are Ø2.9, so an M3 screw will not
pass, and an M2.5 screw will not bite in an M3 standoff. Everything else on the
frame assembles without them; only that one board waits. **And a 12 V 5 A
adapter**, 5.5 × 2.5 centre positive, which is not in the order.

Two things to do differently from the tables above, given what arrived:

* **Use M3 × 10, not M3 × 8, into the plastic 10 mm standoffs.** Plate A is 5 mm,
  so an M3 × 8 engages only 3 mm, and 3 mm of plastic thread under the weight of
  the board is thin. There are 8 spare M3 × 10 after the columns and the TC397.
* **Feed the board through the WAGO and the AWG18 pigtail, not through NC066.**
  The board can draw 4.1 A and the splitter's wire gauge is not published;
  Coms cables in this family are usually 20–22 AWG. NC066 is better used on the
  fan leg, where the load is 0.05 A and its switch is actually handy.

The WAGO 221-413 is a 3-conductor lever connector, so two of them make the whole
Y — one for +12 V, one for ground, each taking the adapter in and the board and
fan out. No soldering anywhere in the power path.

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

Stack height ≈ 5 + 45 + 5 + 45 + 3 = **103 mm**, or **113 mm** on the
50 mm standoffs that were actually bought.

## Electrical

| Part | Spec | Qty | Part number |
|---|---|---:|---|
| Fan | 40 × 40 × 10 mm, **12 V**, 0.6 W | 1 | Noctua NF-A4x10 FLX |
| DC adapter | 12 V 5 A, barrel 5.5 × 2.5 × 11 mm, centre + | 1 | Mean Well **GST60A12-P1M** |
| Barrel socket, female → bare leads | 5.5 × 2.5 mm, 18 AWG, 305 mm | 1 | Tensility **10-02879** (DK 839-10-02879-ND) |
| DC splitter | barrel 5.5 × 2.5, **1 female in → 2 male out** | 1 | domestic, generic |

```
GST60A12-P1M ──> Y splitter ─┬─> LAN9692 J23    (5.5 x 2.5, centre +)
  12 V 5 A                   └─> 10-02879 socket ──> Noctua NF-A4x10
```

* Nothing is tapped on the PCB — **the board has no fan header.**
* The board's jack is 5.5 / **2.5** mm (PJ-002BH). Most cheap splitters are
  5.5 / 2.1 and contact badly; get the 2.5. On the Mean Well the suffix is what
  decides it — **P1M is 2.5 mm, P1J is 2.1** on the otherwise identical supply.
* **Genders**: the adapter is male, so the splitter is female-in / male-out and
  the fan lead needs a **female socket**. A plug leaves you male-to-male.
* Never feed 24 V: the board's input TVS is an SMBJ13D, 13 V standoff.

### Wiring the fan to the socket

The 10-02879 is a female barrel jack on a 305 mm 18 AWG red/black pigtail, rated
6 A — far more than the fan's 0.05 A. Join it to the fan's **included extension
cable**, not to the fan's own lead: if the socket ever has to change, the fan is
still original.

1. Cut the extension cable a comfortable distance from its female end and keep
   the length that plugs into the fan.
2. The Noctua lead has three conductors. **Only two are used** — supply and
   ground. The third is the tacho signal and goes nowhere; cut it back and
   insulate it separately.
3. **Meter the socket before soldering.** Which of red/black is the centre pin
   is not in Tensility's datasheet, and the centre pin is the one that must be
   +12 V. Put a plug in the socket, or probe the barrel's inner sleeve, and
   check continuity to each lead.
4. Solder centre-pin lead → fan supply, sleeve lead → fan ground. Heatshrink
   each joint separately, then a larger piece over both.
5. Before it goes near the board: plug the socket into the adapter on its own
   and confirm the fan spins and blows **downward**, toward plate A. The label
   side of a fan is its outlet.

Getting this backwards will not usually kill a Noctua — it stalls or turns the
wrong way — but a reversed feed reaching the LAN9692 through the splitter would
be a different story, which is why the fan is tested on its own first.

### Why M3 × 25 for the fan and not M3 × 20

```
plate B      5.0 mm
fan frame   10.0        Noctua NF-A4x10, published
washer       0.5
nyloc nut    4.0        DIN 985 is taller than a plain M3 nut
-------------------
            19.5 mm engaged
```

An M3 × 20 has 0.5 mm to spare, and a nyloc needs the screw to come *through*
the nylon insert to lock at all. M3 × 25 leaves 5.5 mm proud, which is untidy and
works. The Ø3.4 holes in plate B do not change either way. The screws in the
fan's own box are fatter and want Ø4.5 holes — do not use them.

## The one measurement still worth taking

The LAN9692's five DC-DC daughter modules have no published height. The fan
underside sits at z = 39 mm and the PCB top at 16.5, so anything up to
**22.5 mm** above the PCB clears it — allowing 3 mm of margin, check that the
tallest module is under about **19 mm**. If it is taller, lengthen the four A→B
standoffs; the plates do not change.
