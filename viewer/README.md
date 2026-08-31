# Offline viewer

```bash
python3 make_viewer.py     # -> index.html
xdg-open index.html        # or just double-click it
```

**One file, no server, no network.** Geometry and renderer are both inlined, so it
opens on a machine that has never seen the internet — and it will still open in
five years, when whatever CDN a Three.js page pointed at has moved.

| | |
|---|---|
| Acrylic frame | the four plates with all six boards on them |
| Frame, exploded | the same, pulled apart |
| KA7_UNO REV1 | the CAN board, 206 components |
| LAN9692 EVB | the switch board from its pick-and-place data |

Drag to orbit, wheel to zoom, right-drag to pan.

## How it stays small

1.1 MB for 19,168 faces, which is small enough to email. Two things get it there:

* **Positions are quantised to `uint16`** across each model's own bounding box.
  250 mm over 65535 steps is 0.004 mm — finer than anything in this repo is drawn
  to, let alone cut to.
* **Normals are not transmitted at all.** The fragment shader recovers a flat face
  normal from screen-space derivatives (`dFdx`/`dFdy` of the view-space position),
  which is what gives the faceted look, and it flips the result toward the camera
  so inconsistent winding in a multi-body preview cannot produce black faces.

That leaves 7 bytes per vertex: six for the position, one for a palette index.

## It is checked, not just written

There is no browser here to try it in, so the camera maths is verified headlessly
against the generated file — the script block is pulled out of `index.html`, run
under `node` with the DOM and WebGL stubbed, and asserted on:

```
4 models embedded, each face count matching its buffer lengths
palette within the 64 the shader declares
the orbit centre lands at view z = -dist, on the camera axis
all 8 bounding-box corners fall inside the frustum, for every model
```

That last one is the useful one: it is the check that catches a sign error in the
view matrix, which is exactly the bug this had on the first pass — the model was
behind the camera and the page would have rendered an empty background.
