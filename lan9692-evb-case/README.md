# EVB-LAN9692-LM enclosure

Open-ended tray + vented lid for the Microchip EVB-LAN9692-LM automotive
12-port TSN evaluation board (EV09P11A). No off-the-shelf model for this board
exists, so the geometry is generated from Microchip's released manufacturing
data (Gerbers + Excellon, `04-12092-R1`, 30 Apr 2026).

![assembly](img/assembly.png)

| | |
|---|---|
| Tray | 236.4 × 172.9 × 40 mm, 74.3 cm³ |
| Lid | 236.4 × 172.9 × 7 mm, 44.2 cm³ |
| Assembled height | 39.5 mm |
| Fasteners | 8 × M3 × 8 (PCB), 4 × M3 × 10 (lid) |

## Design

Both long edges of the board are solid connectors — 7× MATEnet and 4× SFP+ on
the front, RJ45 / USB-C / 12 V jack / 2× SMA / OCuLink on the rear — so **the
tray is deliberately open at both ends**. Nothing has to line up with a
connector, the cages and PHYs get unobstructed airflow, and the part costs
roughly half of what a closed box would.

The board is carried by 8 screw standoffs under its mounting holes plus a
1.6 mm ledge running the full length of both side walls, so the SFP end cannot
droop when a transceiver is plugged in. The side walls stand 4.5 mm proud of
the PCB top face to protect the board edges. The lid is optional and screws to
four corner posts that sit diagonally outboard of the PCB corners.

![tray](img/tray_iso.png)

## Where the dimensions come from

`extract_board_data.py` reads them out of the released fab data. Download the
Gerber set from the [EV09P11A page](https://www.microchip.com/en-us/development-tool/EV09P11A)
(Gerbers, 30 Apr 2026), unzip, and run it:

```
board outline      213.360 x 149.860 mm   (corners 0.000,0.000 .. 213.360,149.860)
                   = 8.400 x 5.900 in
mounting holes     8 x Ø3.048 mm
  corner inset 3.556 mm = 0.140 in
bottom-side pads   1734 apertures inside the outline
  nearest to left edge  5.60 mm
  nearest to right edge 2.75 mm
  nearest to any mounting hole centre 5.42 mm (Ø7.0 boss needs 3.5) -> OK
  RAIL_IN = 1.6: 0 pad(s) under the rail -> OK
  RAIL_IN = 3.0: 2 pad(s) under the rail -> too wide
```

* **Outline 213.360 × 149.860 mm** from the BOARD (`.GM2`) layer — exactly
  8.400 × 5.900 in. The user's guide rounds this to "214 x 150 mm", so the
  drawing-derived numbers this model used to carry were scaled 0.3% too large.
  That layer also holds the fab drawing frame, so the outline is taken as the
  tightest rectangle of real outline lines that still encloses the drill
  pattern, not as the layer extent.
* **8 × Ø3.048 mm (0.120 in) PTH** mounting holes — tool T23 in the drill
  report, straight out of `04-12092-R1-RoundHoles.TXT`:

  | # | X (mm) | Y (mm) |  | # | X (mm) | Y (mm) |
  |---|---|---|---|---|---|---|
  | 1 | 3.556 | 146.304 | | 5 | 205.187 | 71.330 |
  | 2 | 101.600 | 146.304 | | 6 | 208.788 | 51.816 |
  | 3 | 209.804 | 146.304 | | 7 | 133.350 | 51.562 |
  | 4 | 205.187 | 129.330 | | 8 | 3.556 | 24.892 |

* **Bottom-side keepouts** from the bottom paste (`.GBP`) layer, which is where
  bottom-side parts actually sit. It clears every standoff by 5.42 mm and has no
  aperture within 1.6 mm of either side edge — so the support rails are safe at
  1.6 mm and would clip two pads at 3.0 mm. The assembly layers (`.GM10/.GM11`)
  also contain designator text and hole symbols and are useless as a keepout
  source.
* **PCB thickness 1.535 mm**, 4 layers — §A.2 of the user's guide.

Still not derived from data: `INNER_H = 26`, the clearance above the board.
Gerbers carry no heights. The board photos in Figures 4-1/4-2 put the tallest
parts (vertical expansion header, red DC/DC modules, SMA jacks) under 20 mm, but
print the tray first and measure before ordering the lid.

## Regenerating

```bash
pip3 install --break-system-packages trimesh manifold3d
python3 lan9692_case.py            # -> lan9692_tray.stl, lan9692_lid.stl
python3 assembly_preview.py        # -> assembly.png
python3 render_preview.py lan9692_tray.stl tray.png --elev 28 --azim -50
```

Every dimension is a constant at the top of `lan9692_case.py`. `MAKE_LID =
False` skips the lid; `INNER_H` sets the clearance above the board; `RAIL_IN =
0` removes the side ledges if the board turns out to have bottom-side parts
within 1.6 mm of its left/right edges.

`render_preview.py` is a small software rasteriser so previews work on a
headless box with no GL stack.

## Assembly

1. Remove any rubber foot that covers a mounting hole (the board ships with
   feet, visible in Figure 4-2). Feet that clear the holes can stay — they are
   about 5 mm tall against the tray's 8 mm of underboard space.
2. Drop the board in — it lands on the eight standoffs and the two side ledges.
3. 8 × M3 × 8 thread-forming screws into the standoffs. The pilots are 2.9 mm;
   if a hole is off by a few tenths, open that pilot up to 3.2 mm.
4. Lid: 4 × M3 × 10 into the corner posts.

## Printing

FDM in ABS or PETG, both parts flat on the bed, no supports needed — every
overhang is either a through-hole or the top of a post. 0.2 mm layers, ≥4
perimeters on the tray so the standoffs and posts hold a thread. PLA works but
creeps under a warm board.

MJF PA12 also prints it as-is (min wall 1.0 mm, everything here is ≥2.0 mm) and
gives much better threads, but at 122 cm³ for the pair it is the expensive
option.

## What happens if the derived numbers are off

Everything load-bearing degrades gracefully, on purpose:

* **Board width tolerance** — the wall gap is 1.2 mm per side, chosen from the
  process tolerance (MJF ±0.4% = ±0.85 mm at 213 mm, FDM shrinkage similar),
  not from a nominal fit. The board is located by its screws, not the walls.
* **A screw that will not start** — the standoff top is a flat 7 mm boss, so the
  board rests on it regardless; drill that one pilot to 3.2 mm and the other
  seven hold.
* **`INNER_H` too low** — only the lid is affected, and the lid is a separate
  STL. Print the tray first, measure the real stack height, then order it.

The outline, the hole pattern and the bottom-side keepouts are now fab data
rather than estimates, so the remaining risk is concentrated in `INNER_H`, which
only the lid depends on.
