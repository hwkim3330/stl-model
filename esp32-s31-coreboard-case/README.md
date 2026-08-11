# ESP32-S31-Function-CoreBoard-1 case

Tray + vented lid for Espressif's ESP32-S31 CoreBoard-1.

![assembly](img/assembly.png)

| | |
|---|---|
| Tray | 85.0 × 75.0 × 31.6 mm, 18.7 cm³ |
| Lid | 85.0 × 75.0 × 21.7 mm, 7.9 cm³ |
| Assembled height | 31.6 mm |
| Fasteners | 4 × M3 × 10 |

## What is data and what is not

**Exact**, from Espressif's published
[dimension drawing](https://dl.espressif.com/schematics/esp32-s31-function-coreboard-1-dimensions.dxf):

* **Outline 65.000 × 55.000 mm, corner radius 3.500 mm.** The four straight
  edges run 3.5…61.5 and 3.5…51.5, so the tray's board shelf follows the
  rounded outline rather than a plain rectangle.
* **Header grid**: pin 1 at (8.370, 53.270), 2.540 mm pitch, second row at
  y = 50.730 — a 2 × 20 header lying along the y = 55 edge. The lid slot
  (51.46 × 5.74 mm) comes from that.

**Not published, so not designed around:**

* **No mounting holes** appear anywhere in the dimension export. So the board is
  not screwed down — it rests on a 1.5 mm shelf that follows its outline and is
  held by four pads on the underside of the lid, with 0.3 mm of clearance so it
  is not stressed.
* **Port positions.** The user guide lists a USB Serial/JTAG port, a USB-C UART
  port, a USB 2.0 Type-A port, an RJ45 and a speaker header, but neither it nor
  the dimension drawing places them, and they are not recoverable from the
  silkscreen art in the DXF. Rather than guess, **both 65 mm edges are left
  fully open** — walls only on the two 55 mm edges. That is the same approach
  the LAN9692 tray takes, and it means no cut-out can be in the wrong place.
* **PCB thickness** is assumed 1.6 mm, the Espressif norm.

When the board arrives, measuring which edge carries the ports and the height
of the tallest part is enough to close the open side properly — the port
window table in `lan9692_box.py` shows the pattern to follow.

## Regenerating

```bash
pip3 install --break-system-packages trimesh manifold3d
python3 esp32_s31_case.py     # -> esp32_s31_tray.stl, esp32_s31_lid.stl
```

Constants at the top of the script: `INNER_H` sets the clearance above the
board (20 mm), `STANDOFF_H` the space beneath it (6 mm), `HDR_*` the header
slot.

## Printing

MJF PA12 or FDM PETG/ABS, both parts flat, no supports. At 27 cm³ for the pair
this is cheap in either process. 0.2 mm layers and ≥4 perimeters in FDM so the
corner posts hold an M3 thread.
