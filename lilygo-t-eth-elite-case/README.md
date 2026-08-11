# LilyGo T-ETH-Elite case

Fits the LilyGo T-ETH-Elite on the **PoE base board** (no shield board), with
openings for USB-C, RJ45 and the microSD slot.

**Original design is not mine:**

* Author: **Cicicok**
* Source: <https://www.printables.com/model/1154843-lilygo-t-eth-elite-case>
* License: **Creative Commons — Attribution (CC BY)**

| File | Bounding box | Volume | |
|---|---|---|---|
| `lilygo_t-eth_elite_case_bottom.stl` | 72.0 × 53.0 × 24.9 mm | 11.95 cm³ | as published |
| `lilygo_t-eth_elite_case_top.stl` | 72.0 × 53.0 × 5.0 mm | 5.17 cm³ | as published |
| `lilygo_t-eth_elite_case_bottom_fit.stl` | 72.0 × 53.0 × 24.9 mm | 11.73 cm³ | **modified**, see below |
| `lilygo_t-eth_elite_case_top_fit.stl` | 72.0 × 53.0 × 5.0 mm | 5.38 cm³ | **modified**, see below |

## Why the `_fit` variants exist

The original is FDM-native — the author printed it on an MK3S+ at 0.2 mm layers
with no supports — and every feature is drawn at its nominal size. That is fine
on a printer you can iterate on, and a problem for a part you order once.
Measured off the STLs and checked against
[LilyGo's official board CAD](https://github.com/Xinyuan-LilyGO/LilyGO-T-ETH-Series/blob/master/shell/3D/T-ETH-ELite.7z)
(PCB 66.191 × 49.192 × 1.575 mm, 72.500 × 49.352 × 18.822 mm over the connectors):

| Feature | As published | `_fit` | Why |
|---|---|---|---|
| Insert lip wall | **0.50 mm** | 1.00 mm | one extrusion width on a 0.4 mm nozzle; under MJF's 1.0 mm minimum wall |
| Lip ↔ cavity | 68.010 into 68.006 | 0.348 mm/side | nominal **interference** before any process tolerance |
| USB-C opening | 8.99 × 3.11 mm | 10.0 × 4.0 mm | plug shell is 8.34 × 2.56; MJF holes come out undersized |
| RJ45 opening | 16.11 × 14.20 mm | 16.8 × 14.8 mm | 8P8C plug with latch is ~11.7 × 13.5 |
| microSD opening | 14.00 × 2.20 mm | unchanged | already clears a card |
| Buttons | 10.50 × 4.01 mm ×2 | unchanged | cut the tabs free after printing either way |

The lip is the one that would actually stop the case closing, and it is fixed
from the *bottom* side: the clearance is taken off the bottom's 2.0 mm rim wall
(1.65 mm left) instead of off the 0.5 mm lip, and the lip is thickened inward so
its outer face — the surface the author dimensioned the fit around — does not
move.

```bash
python3 fit_for_print.py   # regenerates both *_fit.stl and prints the checks
```

## Printing / ordering

Order the **`_fit`** pair in **MJF PA12-HP Nylon**:

* the button tabs have to flex — resin snaps them;
* it sits on a PoE board that runs warm, and PA12's heat deflection is 175 °C
  against roughly 50–60 °C for SLA resin, which also yellows under UV;
* no supports, so no witness marks in the port openings;
* ±0.3 mm tolerance and 1.0 mm minimum wall are both met by the `_fit` parts —
  the originals are not (that 0.5 mm lip).

The originals are kept here unmodified for anyone printing on their own FDM
machine, where the 0.5 mm lip is a normal single-wall feature.

Either way the **buttons have to be cut free** after printing. On MJF the thin
tabs holding them may break during depowdering and the loose buttons can get
lost in the powder — worth ordering two sets, it is a 17 cm³ part.
