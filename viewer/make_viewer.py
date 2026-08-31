#!/usr/bin/env python3
"""Build a single self-contained HTML viewer for the models in this repo.

    python3 make_viewer.py        # -> index.html, then just open it

One file, no server, no network. Everything is inlined: the geometry as
base64 and the renderer as about a hundred lines of WebGL2. Nothing is fetched,
so it works on a machine that has never seen the internet.

Geometry is quantised to int16 across each model's own bounding box - 250 mm over
65535 steps is 0.004 mm, far finer than anything here is drawn to - and normals
are not transmitted at all: the fragment shader recovers a flat face normal from
screen-space derivatives. That leaves 7 bytes per vertex, so the whole four-plate
assembly with six boards on it fits in a file you can email.
"""
import base64
import json
import os
import struct
import sys

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, '..', 'acrylic-frame'),
                os.path.join(HERE, '..', 'lan9692-evb-case'),
                os.path.join(HERE, '..', 'esp32-s31-coreboard-case'),
                os.path.join(HERE, '..', 'ka7-uno-can-board')]


def pack(parts, cols):
    """(parts, colours) -> quantised buffers plus the palette."""
    palette, idx = [], []
    for c in cols:
        c = tuple(round(float(v), 4) for v in (c if np.ndim(c) == 1 else c[0]))
        if c not in palette:
            palette.append(c)
        idx.append(palette.index(c))

    tris = np.vstack([p.triangles.reshape(-1, 3) for p in parts])
    cid = np.concatenate([np.full(len(p.faces) * 3, i, np.uint8)
                          for p, i in zip(parts, idx)])
    lo, hi = tris.min(0), tris.max(0)
    span = np.maximum(hi - lo, 1e-6)
    q = np.round((tris - lo) / span * 65535).astype(np.uint16)
    return dict(pos=base64.b64encode(q.tobytes()).decode(),
                cid=base64.b64encode(cid.tobytes()).decode(),
                lo=[round(float(v), 4) for v in lo],
                span=[round(float(v), 4) for v in span],
                palette=[list(c) for c in palette],
                faces=len(tris) // 3)


def models():
    out = {}

    import assembly as A
    parts, cols = A.build()
    out['frame'] = dict(label='Acrylic frame, four plates', **pack(parts, cols))

    ex = A.exploded(list(zip(parts, cols)))
    out['exploded'] = dict(label='Frame, exploded',
                           **pack([p for p, _ in ex], [c for _, c in ex]))

    import ka7_mock
    p, c = ka7_mock.build(colors=True)
    out['ka7'] = dict(label='KA7_UNO REV1 CAN board', **pack(p, c))

    import board_mock
    m, fc = board_mock.build(0.0, colors=True)
    # board_mock hands back per-face colours; group them into runs
    parts2, cols2 = [], []
    fc = np.asarray(fc)
    if fc.ndim == 2 and len(fc) == len(m.faces):
        for c0 in {tuple(r) for r in fc}:
            sel = np.all(fc == np.array(c0), axis=1)
            parts2.append(m.submesh([np.where(sel)[0]], append=True))
            cols2.append(c0)
    else:
        parts2, cols2 = [m], [(0.09, 0.36, 0.20)]
    out['lan9692'] = dict(label='LAN9692 EVB', **pack(parts2, cols2))
    return out


HTML = """<meta charset="utf-8">
<title>stl-model viewer</title>
<style>
  :root { color-scheme: light dark; }
  * { box-sizing: border-box; }
  body { margin: 0; font: 14px/1.5 ui-sans-serif, system-ui, sans-serif;
         background: #f4f5f7; color: #1b1f24; overflow: hidden; }
  @media (prefers-color-scheme: dark) {
    body { background: #16181c; color: #e8eaed; }
    .panel { background: #21242a; border-color: #33373f; }
    button { background: #2b2f36; color: #e8eaed; border-color: #3a3f48; }
    button[aria-pressed=true] { background: #3d6ea5; border-color: #4b82bd; }
  }
  canvas { display: block; width: 100vw; height: 100vh; }
  .panel { position: fixed; top: 14px; left: 14px; padding: 12px 14px;
           background: #fff; border: 1px solid #dfe3e8; border-radius: 10px;
           box-shadow: 0 2px 10px rgba(0,0,0,.07); max-width: 300px; }
  h1 { margin: 0 0 8px; font-size: 15px; font-weight: 650; letter-spacing: -.01em; }
  .row { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
  button { font: inherit; padding: 5px 10px; border: 1px solid #d3d8de;
           border-radius: 7px; background: #f7f8fa; cursor: pointer; }
  button[aria-pressed=true] { background: #2f6fb0; border-color: #2f6fb0;
                              color: #fff; }
  dl { margin: 0; display: grid; grid-template-columns: auto 1fr; gap: 2px 10px;
       font-variant-numeric: tabular-nums; }
  dt { opacity: .62; } dd { margin: 0; }
  .hint { margin: 10px 0 0; font-size: 12px; opacity: .6; }
</style>
<canvas id="c"></canvas>
<div class="panel">
  <h1>stl-model</h1>
  <div class="row" id="pick"></div>
  <dl>
    <dt>size</dt><dd id="size">—</dd>
    <dt>faces</dt><dd id="faces">—</dd>
  </dl>
  <p class="hint">drag to orbit · wheel to zoom · right-drag to pan</p>
</div>
<script>
const MODELS = __DATA__;
const gl = document.getElementById('c').getContext('webgl2', {antialias: true});
if (!gl) document.body.innerHTML = '<p style="padding:2em">needs WebGL2</p>';

const VS = `#version 300 es
in vec3 p; in float cid;
uniform mat4 mvp; uniform mat4 mv;
out vec3 vpos; out float vcid;
void main(){ vpos = (mv * vec4(p,1.)).xyz; vcid = cid; gl_Position = mvp*vec4(p,1.); }`;

const FS = `#version 300 es
precision highp float;
in vec3 vpos; in float vcid;
uniform vec3 pal[64];
out vec4 o;
void main(){
  vec3 n = normalize(cross(dFdx(vpos), dFdy(vpos)));
  if (n.z < 0.) n = -n;
  float d = max(dot(n, normalize(vec3(0.36,0.30,0.88))), 0.);
  float rim = pow(1.0 - abs(n.z), 2.5) * 0.10;
  vec3 c = pal[int(vcid + 0.5)] * (0.34 + 0.70*d) + rim;
  o = vec4(pow(c, vec3(0.4545)), 1.);
}`;

function sh(t, src){ const s = gl.createShader(t); gl.shaderSource(s, src);
  gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw gl.getShaderInfoLog(s);
  return s; }
const prog = gl.createProgram();
gl.attachShader(prog, sh(gl.VERTEX_SHADER, VS));
gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, FS));
gl.linkProgram(prog); gl.useProgram(prog);
const U = n => gl.getUniformLocation(prog, n);

function b64(s){ const raw = atob(s); const u = new Uint8Array(raw.length);
  for (let i=0;i<raw.length;i++) u[i]=raw.charCodeAt(i); return u; }

let cur = null, vao = null, nverts = 0;
function load(key){
  const m = MODELS[key];
  const q = new Uint16Array(b64(m.pos).buffer);
  const pos = new Float32Array(q.length);
  for (let i=0;i<q.length;i++) pos[i] = m.lo[i%3] + q[i]/65535*m.span[i%3];
  const cid = b64(m.cid);
  if (vao) gl.deleteVertexArray(vao);
  vao = gl.createVertexArray(); gl.bindVertexArray(vao);
  const bp = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, bp);
  gl.bufferData(gl.ARRAY_BUFFER, pos, gl.STATIC_DRAW);
  const lp = gl.getAttribLocation(prog, 'p');
  gl.enableVertexAttribArray(lp); gl.vertexAttribPointer(lp, 3, gl.FLOAT, false, 0, 0);
  const bc = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, bc);
  gl.bufferData(gl.ARRAY_BUFFER, cid, gl.STATIC_DRAW);
  const lc = gl.getAttribLocation(prog, 'cid');
  gl.enableVertexAttribArray(lc); gl.vertexAttribPointer(lc, 1, gl.UNSIGNED_BYTE, false, 0, 0);
  const flat = new Float32Array(64*3);
  m.palette.forEach((c,i) => flat.set(c, i*3));
  gl.uniform3fv(U('pal'), flat);
  nverts = pos.length/3; cur = m;
  const s = m.span;
  document.getElementById('size').textContent =
    `${s[0].toFixed(0)} × ${s[1].toFixed(0)} × ${s[2].toFixed(0)} mm`;
  document.getElementById('faces').textContent = m.faces.toLocaleString();
  centre = [m.lo[0]+s[0]/2, m.lo[1]+s[1]/2, m.lo[2]+s[2]/2];
  dist = Math.max(...s) * 2.1; pan = [0,0];
  draw();
}

let yaw = -0.72, pitch = 0.52, dist = 400, centre = [0,0,0], pan = [0,0];
function draw(){
  const dpr = Math.min(devicePixelRatio||1, 2);
  const c = gl.canvas;
  c.width = innerWidth*dpr; c.height = innerHeight*dpr;
  gl.viewport(0,0,c.width,c.height);
  gl.enable(gl.DEPTH_TEST); gl.disable(gl.CULL_FACE);
  const bg = matchMedia('(prefers-color-scheme: dark)').matches
    ? [0.086,0.094,0.11,1] : [0.957,0.961,0.968,1];
  gl.clearColor(...bg); gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
  if (!cur) return;

  const cy=Math.cos(yaw), sy=Math.sin(yaw), cp=Math.cos(pitch), sp=Math.sin(pitch);
  // orbit around Z-up, looking in from the side
  const eye = [centre[0] + dist*cp*sy, centre[1] - dist*cp*cy, centre[2] + dist*sp];
  const f = norm(sub(centre, eye));
  const r = norm(cross(f, [0,0,1]));
  const u = cross(r, f);
  const t = [-dot(r,eye) + pan[0], -dot(u,eye) + pan[1], dot(f,eye)];
  const mv = [r[0],u[0],-f[0],0, r[1],u[1],-f[1],0, r[2],u[2],-f[2],0, t[0],t[1],t[2],1];
  const asp = c.width/c.height, n = dist*0.02, fa = dist*6, ft = 1/Math.tan(0.42);
  const P = [ft/asp,0,0,0, 0,ft,0,0, 0,0,(fa+n)/(n-fa),-1, 0,0,2*fa*n/(n-fa),0];
  gl.uniformMatrix4fv(U('mv'), false, mv);
  gl.uniformMatrix4fv(U('mvp'), false, mul(P, mv));
  gl.bindVertexArray(vao);
  gl.drawArrays(gl.TRIANGLES, 0, nverts);
}
const sub=(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]];
const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const norm=a=>{const l=Math.hypot(...a)||1;return [a[0]/l,a[1]/l,a[2]/l];};
function mul(A,B){const C=new Array(16).fill(0);
  for(let i=0;i<4;i++)for(let j=0;j<4;j++)for(let k=0;k<4;k++)
    C[j*4+i]+=A[k*4+i]*B[j*4+k];
  return C;}

let drag = null;
const cv = gl.canvas;
cv.addEventListener('pointerdown', e => { drag = {x:e.clientX, y:e.clientY, b:e.button};
  cv.setPointerCapture(e.pointerId); });
cv.addEventListener('pointerup', () => drag = null);
cv.addEventListener('pointermove', e => {
  if (!drag) return;
  const dx = e.clientX-drag.x, dy = e.clientY-drag.y;
  drag.x = e.clientX; drag.y = e.clientY;
  if (drag.b === 2) { pan[0] -= dx*dist/900; pan[1] += dy*dist/900; }
  else { yaw += dx*0.008; pitch = Math.max(-1.5, Math.min(1.5, pitch + dy*0.008)); }
  draw();
});
cv.addEventListener('contextmenu', e => e.preventDefault());
cv.addEventListener('wheel', e => { e.preventDefault();
  dist *= Math.exp(e.deltaY*0.0011); draw(); }, {passive:false});
addEventListener('resize', draw);
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', draw);

const pick = document.getElementById('pick');
Object.entries(MODELS).forEach(([k,m],i) => {
  const b = document.createElement('button');
  b.textContent = m.label; b.setAttribute('aria-pressed', i===0);
  b.onclick = () => { [...pick.children].forEach(o => o.setAttribute('aria-pressed', o===b));
    load(k); };
  pick.appendChild(b);
});
load(Object.keys(MODELS)[0]);
</script>
"""

if __name__ == '__main__':
    data = models()
    out = os.path.join(HERE, 'index.html')
    open(out, 'w').write(HTML.replace('__DATA__', json.dumps(data)))
    kb = os.path.getsize(out) / 1024
    print(f"wrote {os.path.basename(out)}  ({kb:.0f} kB, self-contained)")
    for k, m in data.items():
        print(f"  {k:9s} {m['faces']:7d} faces  "
              f"{m['span'][0]:6.1f} x {m['span'][1]:6.1f} x {m['span'][2]:6.1f} mm  "
              f"{len(m['palette'])} colours")
