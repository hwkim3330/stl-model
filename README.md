# stl-model

3D-printable enclosures for the boards on the KETI TSN bench.

| Model | Board | Parts | Material volume |
|---|---|---|---|
| [`lan9692-evb-case/`](lan9692-evb-case/) | Microchip EVB-LAN9692-LM (EV09P11A) | tray + vented lid | 77.7 + 44.5 cm³ |
| [`lilygo-t-eth-elite-case/`](lilygo-t-eth-elite-case/) | LilyGo T-ETH-Elite + PoE base board | bottom + top | 12.0 + 5.2 cm³ |

Both are sized for JLC3DP; see each folder's README for the material and
ordering notes.

## Ordering

JLC3DP and JLCPCB share one cart, so these can ship together with a PCB order —
from the JLC3DP order page use the PCB/PCBA tab in the nav bar, then combine
payment. <https://jlc3dp.com/help/article/how-to-combine-orders-for-jlc3dp-and-jlcpcb-products>

| | LilyGo case | LAN9692 tray + lid |
|---|---|---|
| Material | MJF PA12-HP Nylon | MJF PA12-HP Nylon, or FDM ABS/PETG to save money |
| Why | flexing button tabs, PoE heat, no support marks | PA12 prints it as-is; at 122 cm³ the volume-priced MJF just costs ~7× the small case |

Both parts print fine in PA12 if you would rather keep one material — the split
is purely a cost call, and mixing processes does not stop the order from
shipping together.
