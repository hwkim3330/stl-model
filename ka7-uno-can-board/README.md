# KETI KA7_UNO REV1

A model of the CAN board, built from its own fabrication set. Not an enclosure —
this exists so [`../acrylic-frame/`](../acrylic-frame/) can show the real board on
plate C instead of a featureless block, and so the plate's holes come from fab
data rather than a ruler.

![the board](ka7_uno_rev1.png)

## What the board is

Six layers, **70.000 × 90.000 mm**, dated 2026-08-27 on its own silkscreen. From
the BOM and the silkscreen it is a multi-protocol automotive node:

| | |
|---|---|
| CAN FD | 2 × `TCAN1044V` — `CAN0`, `CAN1`, each with `Term#1` / `Term#2` jumpers |
| 10BASE-T1S | `LAN8671C` and `TJA1410A` — `T1S0`, `T1S1`, each with a NodeID selector and an `end / drop` jumper |
| Ethernet | `LAN8830`, `LAN8870` — `ETH0` with LINK / LED2 / LED3 |
| LIN | `LIN0`, `LIN1`, each with GND / BUS / 12V |
| Other | `POWER IN`, 5.0 V_VIN and 3.3 V rails, `RESET`, `TEST_LED`, `TEST_SW_IN`, an 8-way selector, L1–L4 LEDs |

The CAN, LIN and power terminals are all on the **left edge**; the two T1S pairs
are along the **top edge**. That is why the board sits where it does on plate C.

## What is exact and what is not

| | source | |
|---|---|---|
| Outline 70.000 × 90.000 | `BOARD_OUTLINE` layer of `TOP.dxf` | exact |
| 4 × Ø3.5 mount holes, 3.5 mm in from each edge | `ThruHoleNonPlated.ncd` **and** `MOUNTING_HOLES_LAYER_TOP` — two files agreeing | exact |
| 206 component positions | clustered from `PART_PADS_SMD_TOP`, `PART_PADS_LAYER_TOP`, `PART_HOLES_LAYER_TOP` | positions exact |
| 77 silkscreen labels | the `TEXT` entities | exact |
| Component **heights** | — | **guessed** |

There is no pick-and-place file in the Gerber set and no height data anywhere in
a Gerber set, so a component is recovered as a cluster of pads and its height is
inferred from its own footprint: an edge part with real area is a connector at
11 mm, otherwise 0.6–3.0 mm by area and pad count. `extract_ka7.py` documents the
thresholds. 0.9 mm is the clustering gap — 0.5 splits an 0402's two pads into two
"components", 1.3 starts fusing neighbouring ICs.

The tallest part therefore comes out at **12.6 mm** over the plate, and
`../acrylic-frame/assembly.py` checks that against plate D rather than assuming
it: there is 24.4 mm of room, so the guess would have to be out by nearly double
to matter.

## Files

```bash
python3 extract_ka7.py TOP.dxf   # -> ka7_uno_rev1.json   (run once, needs the fab set)
python3 ka7_mock.py              # -> ka7_uno_rev1.stl    (offline, JSON only)
```

The fabrication set is not in this repo — it is KETI's, it is 900 kB of Gerber,
and `ka7_uno_rev1.json` carries everything the model needs. `ka7_uno_rev1.stl` is
a preview, not something to print or cut, so `check_stls.py` skips it.
