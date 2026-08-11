# stl-model

3D-printable enclosures for the boards on the KETI TSN bench.

| Model | Board | Parts | Material volume |
|---|---|---|---|
| [`lan9692-evb-case/`](lan9692-evb-case/) | Microchip EVB-LAN9692-LM (EV09P11A) | tray + vented lid | 74.3 + 44.2 cm³ |
| [`lilygo-t-eth-elite-case/`](lilygo-t-eth-elite-case/) | LilyGo T-ETH-Elite + PoE base board | bottom + top | 11.7 + 5.4 cm³ |

Both are dimensioned from primary sources, not from drawings or eyeballing:
the LAN9692 tray from Microchip's released Gerber/Excellon set, the LilyGo
`_fit` variants from measurements of the published STLs checked against LilyGo's
own board CAD. Each folder's README shows the numbers and how they were read.

## Ordering

JLC3DP and JLCPCB share one cart, so these can ship with a PCB order — from the
JLC3DP order page use the PCB/PCBA tab in the nav bar, then combine payment.
<https://jlc3dp.com/help/article/how-to-combine-orders-for-jlc3dp-and-jlcpcb-products>

| | LilyGo case | LAN9692 tray + lid |
|---|---|---|
| Files | the **`_fit`** pair, not the originals | `lan9692_tray.stl`, `lan9692_lid.stl` |
| Material | MJF PA12-HP Nylon | MJF PA12-HP Nylon, or FDM ABS/PETG to save money |
| Why | flexing button tabs, PoE heat, no support marks | PA12 prints it as-is; at 119 cm³ the volume-priced MJF costs ~7× the small case |

One material for everything is fine — the split is purely a cost call, and
mixing processes does not stop the order shipping together.

**Order the LAN9692 tray before the lid.** Everything else is fab data, but the
26 mm of clearance above the board is a judgement call from board photos, and it
is the only number the lid depends on. Print the tray, fit the board, measure,
then order.
