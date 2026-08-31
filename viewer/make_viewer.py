#!/usr/bin/env python3
"""Build a single self-contained HTML viewer for the models in this repo.

    python3 make_viewer.py        # -> ../docs/index.html

Output lands in docs/ because that is what GitHub Pages serves, so the page is
just a file in this repository - versioned with the models it shows, and not
dependent on anything outside it.

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
    out['frame'] = dict(label='Acrylic frame', **pack(parts, cols),
                        facts=[['plates', '4 x 250 x 180 x 3 mm clear'],
                               ['stack', '3+50+3+50+3+50+3 = 162 mm'],
                               ['column', '12 x M/F standoff, 4 corners'],
                               ['boards', '6'],
                               ['thinnest web', '3.36 mm']])

    ex = A.exploded(list(zip(parts, cols)))
    out['exploded'] = dict(label='Exploded',
                           **pack([p for p, _ in ex], [c for _, c in ex]),
                           facts=[['plate A', 'LAN9692 EVB'],
                                  ['plate B', 'fan, TC397, T-ETH-Elite, 2 x injection'],
                                  ['plate C', 'Raspberry Pi 4B, KA7_UNO CAN'],
                                  ['plate D', 'guard']])

    import ka7_mock
    p, c = ka7_mock.build(colors=True)
    out['ka7'] = dict(label='KA7_UNO CAN', **pack(p, c),
                      labels=[[n, x, y, ka7_mock.PCB_T] for n, x, y in ka7_mock.LABELS],
                      facts=[['outline', '70.000 x 90.000 mm'],
                             ['mounts', '4 x Ø3.5, 63 x 83 pitch'],
                             ['components', f'{len(ka7_mock.DATA["components"])}'],
                             ['layers', '6'],
                             ['source', 'fabrication DXF + drill']])

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
    out['lan9692'] = dict(label='LAN9692 EVB', **pack(parts2, cols2),
                          facts=[['outline', '213.360 x 149.860 mm'],
                                 ['mounts', '8, from drill tool T23 Ø3.048'],
                                 ['parts', 'placed from pick-and-place'],
                                 ['ports', '7 x MATEnet, 4 x SFP+, RJ45']])
    return out


HTML = """<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KETI TSN bench &mdash; model viewer</title>
<style>
  /* Cool neutrals biased toward the acrylic blue; the DXF CUT-layer orange is
     held back for the one live measurement. Tokens first, so the theme toggle
     and the OS preference both drive the same variables. */
  :root {
    --ground: #eceef1;  --panel: #fbfcfd;  --edge: #cfd6de;
    --ink: #10141a;     --ink-2: #55606d;  --ink-3: #8b95a3;
    --accent: #1f6f9e;  --accent-ink: #fff;
    --signal: #b45f16;
    --pcb: #1d6b3a;
    --canvas-bg: 0.925,0.933,0.945;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --ground: #14171b; --panel: #1b1f25; --edge: #2c333c;
      --ink: #e6e9ee;    --ink-2: #9aa5b2; --ink-3: #6b737f;
      --accent: #4f9fd0; --accent-ink: #0d1116;
      --signal: #e0913f;
      --pcb: #3f9a63;
      --canvas-bg: 0.078,0.090,0.106;
    }
  }
  :root[data-theme="light"] {
    --ground: #eceef1;  --panel: #fbfcfd;  --edge: #cfd6de;
    --ink: #10141a;     --ink-2: #55606d;  --ink-3: #8b95a3;
    --accent: #1f6f9e;  --accent-ink: #fff; --signal: #b45f16;
    --pcb: #1d6b3a;     --canvas-bg: 0.925,0.933,0.945;
  }
  :root[data-theme="dark"] {
    --ground: #14171b; --panel: #1b1f25; --edge: #2c333c;
    --ink: #e6e9ee;    --ink-2: #9aa5b2; --ink-3: #6b737f;
    --accent: #4f9fd0; --accent-ink: #0d1116; --signal: #e0913f;
    --pcb: #3f9a63;    --canvas-bg: 0.078,0.090,0.106;
  }

  * { box-sizing: border-box; }
  html, body { height: 100%; }
  body {
    margin: 0; background: var(--ground); color: var(--ink);
    font: 400 13px/1.55 ui-monospace, "DejaVu Sans Mono", "SF Mono", Menlo, monospace;
    overflow: hidden; -webkit-font-smoothing: antialiased;
  }
  #stage { position: fixed; inset: 0; }
  canvas { display: block; width: 100%; height: 100%; touch-action: none; }
  #overlay { position: absolute; inset: 0; pointer-events: none; }

  /* silkscreen labels, projected onto the board */
  .pin {
    position: absolute; transform: translate(-50%, -50%);
    display: flex; align-items: center; gap: 5px;
    font-size: 10.5px; letter-spacing: .02em; white-space: nowrap;
    color: var(--ink); opacity: .96;
  }
  .pin::before {
    content: ""; width: 5px; height: 5px; flex: none; border-radius: 50%;
    background: var(--signal); box-shadow: 0 0 0 2px var(--ground);
  }
  .pin span {
    background: color-mix(in srgb, var(--panel) 86%, transparent);
    padding: 1px 4px; border: 1px solid var(--edge); border-radius: 2px;
  }

  /* rail */
  .rail {
    position: absolute; top: 0; left: 0; bottom: 0; width: 288px;
    display: flex; flex-direction: column; gap: 0;
    background: color-mix(in srgb, var(--panel) 94%, transparent);
    border-right: 1px solid var(--edge); backdrop-filter: blur(8px);
    overflow-y: auto;
  }
  .rail > * { padding: 14px 16px; border-bottom: 1px solid var(--edge); }
  .rail > *:last-child { border-bottom: 0; }

  .brand h1 {
    margin: 0; font-size: 11px; font-weight: 700; letter-spacing: .14em;
    text-transform: uppercase; color: var(--ink-2);
  }
  .brand p {
    margin: 3px 0 0; font-size: 15px; font-weight: 700; letter-spacing: -.01em;
    color: var(--ink); text-wrap: balance;
  }

  .pick { display: flex; flex-direction: column; gap: 5px; }
  .pick button {
    font: inherit; font-size: 12px; text-align: left; cursor: pointer;
    padding: 7px 10px; border: 1px solid var(--edge); border-radius: 3px;
    background: transparent; color: var(--ink-2);
    display: flex; justify-content: space-between; gap: 10px;
  }
  .pick button:hover { border-color: var(--accent); color: var(--ink); }
  .pick button:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
  .pick button[aria-pressed="true"] {
    background: var(--accent); border-color: var(--accent); color: var(--accent-ink);
    font-weight: 700;
  }
  .pick button b { font-weight: inherit; }
  .pick button i {
    font-style: normal; font-size: 11px; opacity: .7;
    font-variant-numeric: tabular-nums;
  }

  dl.facts {
    margin: 0; display: grid; grid-template-columns: auto 1fr;
    gap: 3px 12px; font-size: 11.5px; font-variant-numeric: tabular-nums;
  }
  dl.facts dt { color: var(--ink-3); }
  dl.facts dd { margin: 0; color: var(--ink); overflow-wrap: anywhere; }

  .live { display: grid; gap: 3px; font-size: 11.5px;
          font-variant-numeric: tabular-nums; }
  .live div { display: flex; justify-content: space-between; gap: 10px; }
  .live span:first-child { color: var(--ink-3); }
  .live span:last-child { color: var(--signal); font-weight: 700; }

  .toggles { display: flex; gap: 6px; flex-wrap: wrap; }
  .toggles button {
    font: inherit; font-size: 11px; cursor: pointer; padding: 5px 9px;
    border: 1px solid var(--edge); border-radius: 3px;
    background: transparent; color: var(--ink-2);
  }
  .toggles button[aria-pressed="true"] {
    background: color-mix(in srgb, var(--accent) 16%, transparent);
    border-color: var(--accent); color: var(--ink);
  }
  .toggles button:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }

  .hint { font-size: 11px; color: var(--ink-3); line-height: 1.6;
          font-family: ui-sans-serif, system-ui, sans-serif; }
  .hint kbd {
    font: inherit; font-family: inherit; border: 1px solid var(--edge);
    border-bottom-width: 2px; border-radius: 3px; padding: 0 4px;
    color: var(--ink-2);
  }

  @media (max-width: 720px) {
    .rail { width: 100%; height: 46%; bottom: auto; border-right: 0;
            border-bottom: 1px solid var(--edge); }
    #overlay .pin { display: none; }
  }
  @media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>

<div id="stage">
  <canvas id="c"></canvas>
  <div id="overlay"></div>

  <div class="rail">
    <div class="brand">
      <h1>KETI TSN bench</h1>
      <p id="title">Acrylic frame</p>
    </div>

    <div class="pick" id="pick" role="group" aria-label="model"></div>

    <dl class="facts" id="facts"></dl>

    <div class="live">
      <div><span>bounding box</span><span id="bbox">&mdash;</span></div>
      <div><span>triangles</span><span id="faces">&mdash;</span></div>
      <div><span>eye distance</span><span id="dist">&mdash;</span></div>
    </div>

    <div class="toggles">
      <button id="tlabels" aria-pressed="false">silkscreen</button>
      <button id="tfit">fit</button>
      <button id="ttheme">theme</button>
    </div>

    <p class="hint">
      <kbd>drag</kbd> orbit &middot; <kbd>wheel</kbd> zoom &middot;
      <kbd>right-drag</kbd> pan. Geometry is quantised to 0.004&nbsp;mm; component
      heights on the CAN board are inferred from footprint, everything else comes
      from fabrication data.
    </p>
  </div>
</div>

<script>
const MODELS = __DATA__;
const cv = document.getElementById('c');
const gl = cv.getContext('webgl2', {antialias: true});
if (!gl) document.body.innerHTML =
  '<p style="padding:2rem;font:14px system-ui">This viewer needs WebGL2.</p>';

const VS = `#version 300 es
in vec3 p; in float cid;
uniform mat4 mvp; uniform mat4 mv;
out vec3 vpos; out float vcid;
void main(){ vpos=(mv*vec4(p,1.)).xyz; vcid=cid; gl_Position=mvp*vec4(p,1.); }`;

const FS = `#version 300 es
precision highp float;
in vec3 vpos; in float vcid;
uniform vec3 pal[64];
out vec4 o;
void main(){
  vec3 n = normalize(cross(dFdx(vpos), dFdy(vpos)));
  if (n.z < 0.) n = -n;
  float key = max(dot(n, normalize(vec3(0.38,0.26,0.89))), 0.);
  float fill = max(dot(n, normalize(vec3(-0.5,-0.3,0.4))), 0.) * 0.22;
  float rim = pow(1.0 - abs(n.z), 3.0) * 0.09;
  vec3 c = pal[int(vcid+0.5)] * (0.30 + 0.72*key + fill) + rim;
  o = vec4(pow(clamp(c,0.,1.), vec3(0.4545)), 1.);
}`;

function sh(t, src){
  const s = gl.createShader(t); gl.shaderSource(s, src); gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw gl.getShaderInfoLog(s);
  return s;
}
const prog = gl.createProgram();
gl.attachShader(prog, sh(gl.VERTEX_SHADER, VS));
gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, FS));
gl.linkProgram(prog); gl.useProgram(prog);
const U = n => gl.getUniformLocation(prog, n);

const b64 = s => { const r = atob(s), u = new Uint8Array(r.length);
  for (let i=0;i<r.length;i++) u[i]=r.charCodeAt(i); return u; };

let cur=null, curKey=null, vao=null, nverts=0;
let yaw=-0.72, pitch=0.50, dist=400, centre=[0,0,0], pan=[0,0];
let showLabels=false;

function fit(){
  const s = cur.span;
  centre = [cur.lo[0]+s[0]/2, cur.lo[1]+s[1]/2, cur.lo[2]+s[2]/2];
  dist = Math.max(...s) * 2.05; pan = [0,0];
}

function load(key){
  const m = MODELS[key]; cur = m; curKey = key;
  const q = new Uint16Array(b64(m.pos).buffer);
  const pos = new Float32Array(q.length);
  for (let i=0;i<q.length;i++) pos[i] = m.lo[i%3] + q[i]/65535*m.span[i%3];
  if (vao) gl.deleteVertexArray(vao);
  vao = gl.createVertexArray(); gl.bindVertexArray(vao);
  const bp = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, bp);
  gl.bufferData(gl.ARRAY_BUFFER, pos, gl.STATIC_DRAW);
  const lp = gl.getAttribLocation(prog,'p');
  gl.enableVertexAttribArray(lp); gl.vertexAttribPointer(lp,3,gl.FLOAT,false,0,0);
  const bc = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, bc);
  gl.bufferData(gl.ARRAY_BUFFER, b64(m.cid), gl.STATIC_DRAW);
  const lc = gl.getAttribLocation(prog,'cid');
  gl.enableVertexAttribArray(lc);
  gl.vertexAttribPointer(lc,1,gl.UNSIGNED_BYTE,false,0,0);
  const flat = new Float32Array(64*3);
  m.palette.forEach((c,i) => flat.set(c, i*3));
  gl.uniform3fv(U('pal'), flat);
  nverts = pos.length/3;

  document.getElementById('title').textContent = m.label;
  document.getElementById('bbox').textContent =
    m.span.map(v => v.toFixed(1)).join(' \u00d7 ') + ' mm';
  document.getElementById('faces').textContent = m.faces.toLocaleString();
  const fl = document.getElementById('facts'); fl.textContent = '';
  (m.facts || []).forEach(([k,v]) => {
    const dt = document.createElement('dt'); dt.textContent = k;
    const dd = document.createElement('dd'); dd.textContent = v;
    fl.append(dt, dd);
  });
  const tl = document.getElementById('tlabels');
  tl.disabled = !m.labels;
  tl.style.opacity = m.labels ? 1 : .4;
  fit(); draw();
}

const sub=(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]];
const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const norm=a=>{const l=Math.hypot(...a)||1;return [a[0]/l,a[1]/l,a[2]/l];};
function mul(A,B){ const C=new Array(16).fill(0);
  for(let i=0;i<4;i++)for(let j=0;j<4;j++)for(let k=0;k<4;k++)
    C[j*4+i]+=A[k*4+i]*B[j*4+k];
  return C; }

let MVP = null, VW = 0, VH = 0;

function draw(){
  const dpr = Math.min(devicePixelRatio||1, 2);
  const r = cv.getBoundingClientRect();
  VW = Math.max(r.width, 1); VH = Math.max(r.height, 1);
  cv.width = Math.round(VW*dpr); cv.height = Math.round(VH*dpr);
  gl.viewport(0,0,cv.width,cv.height);
  gl.enable(gl.DEPTH_TEST); gl.disable(gl.CULL_FACE);
  const bg = getComputedStyle(document.documentElement)
    .getPropertyValue('--canvas-bg').split(',').map(Number);
  gl.clearColor(bg[0], bg[1], bg[2], 1);
  gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
  if (!cur) return;

  const cy=Math.cos(yaw), sy=Math.sin(yaw), cp=Math.cos(pitch), sp=Math.sin(pitch);
  const eye=[centre[0]+dist*cp*sy, centre[1]-dist*cp*cy, centre[2]+dist*sp];
  const f=norm(sub(centre,eye)), rt=norm(cross(f,[0,0,1])), up=cross(rt,f);
  const t=[-dot(rt,eye)+pan[0], -dot(up,eye)+pan[1], dot(f,eye)];
  const mv=[rt[0],up[0],-f[0],0, rt[1],up[1],-f[1],0, rt[2],up[2],-f[2],0,
            t[0],t[1],t[2],1];
  const asp=cv.width/cv.height, n=dist*0.02, fa=dist*6, ft=1/Math.tan(0.42);
  const P=[ft/asp,0,0,0, 0,ft,0,0, 0,0,(fa+n)/(n-fa),-1, 0,0,2*fa*n/(n-fa),0];
  MVP = mul(P, mv);
  gl.uniformMatrix4fv(U('mv'), false, mv);
  gl.uniformMatrix4fv(U('mvp'), false, MVP);
  gl.bindVertexArray(vao);
  gl.drawArrays(gl.TRIANGLES, 0, nverts);

  document.getElementById('dist').textContent = dist.toFixed(0) + ' mm';
  labels();
}

function screenOf(p){
  const X=MVP[0]*p[0]+MVP[4]*p[1]+MVP[8]*p[2]+MVP[12];
  const Y=MVP[1]*p[0]+MVP[5]*p[1]+MVP[9]*p[2]+MVP[13];
  const W=MVP[3]*p[0]+MVP[7]*p[1]+MVP[11]*p[2]+MVP[15];
  if (W <= 0) return null;
  return [(X/W*0.5+0.5)*VW, (0.5-Y/W*0.5)*VH];
}

const ov = document.getElementById('overlay');
function labels(){
  ov.textContent = '';
  if (!showLabels || !cur.labels) return;
  // bus and function names first, bare pin numbers last, then drop anything
  // that would land on top of a label already placed
  const ranked = cur.labels.map((l,i) => [l, /[A-Za-z]{3}/.test(l[0]) ? 0 : 1, i])
    .sort((a,b) => a[1]-b[1] || a[2]-b[2]);
  const placed = [];
  for (const [[name,x,y,z]] of ranked) {
    const s = screenOf([x,y,z]);
    if (!s || s[0] < 300 || s[0] > VW-8 || s[1] < 8 || s[1] > VH-8) continue;
    if (placed.some(p => Math.abs(p[0]-s[0]) < 62 && Math.abs(p[1]-s[1]) < 15)) continue;
    placed.push(s);
    const d = document.createElement('div');
    d.className = 'pin';
    d.style.left = s[0] + 'px'; d.style.top = s[1] + 'px';
    const sp = document.createElement('span'); sp.textContent = name;
    d.appendChild(sp); ov.appendChild(d);
  }
}

let drag=null;
cv.addEventListener('pointerdown', e => {
  drag={x:e.clientX,y:e.clientY,b:e.button}; cv.setPointerCapture(e.pointerId); });
cv.addEventListener('pointerup', () => drag=null);
cv.addEventListener('pointercancel', () => drag=null);
cv.addEventListener('pointermove', e => {
  if (!drag) return;
  const dx=e.clientX-drag.x, dy=e.clientY-drag.y;
  drag.x=e.clientX; drag.y=e.clientY;
  if (drag.b === 2) { pan[0]-=dx*dist/900; pan[1]+=dy*dist/900; }
  else { yaw+=dx*0.008; pitch=Math.max(-1.5,Math.min(1.5,pitch+dy*0.008)); }
  draw();
});
cv.addEventListener('contextmenu', e => e.preventDefault());
cv.addEventListener('wheel', e => {
  e.preventDefault(); dist*=Math.exp(e.deltaY*0.0011); draw(); }, {passive:false});
addEventListener('resize', draw);

const pick = document.getElementById('pick');
Object.entries(MODELS).forEach(([k,m],i) => {
  const b = document.createElement('button');
  b.type='button'; b.setAttribute('aria-pressed', String(i===0));
  const nm=document.createElement('b'); nm.textContent=m.label;
  const ct=document.createElement('i'); ct.textContent=m.faces.toLocaleString();
  b.append(nm, ct);
  b.onclick = () => {
    [...pick.children].forEach(o => o.setAttribute('aria-pressed', String(o===b)));
    load(k);
  };
  pick.appendChild(b);
});

const tl = document.getElementById('tlabels');
tl.onclick = () => { showLabels = !showLabels;
  tl.setAttribute('aria-pressed', String(showLabels)); draw(); };
document.getElementById('tfit').onclick = () => { fit(); draw(); };
document.getElementById('ttheme').onclick = () => {
  const dark = document.documentElement.getAttribute('data-theme') === 'dark'
    || (!document.documentElement.getAttribute('data-theme')
        && matchMedia('(prefers-color-scheme: dark)').matches);
  document.documentElement.setAttribute('data-theme', dark ? 'light' : 'dark');
  draw();
};
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', draw);

load(Object.keys(MODELS)[0]);
</script>
"""


if __name__ == '__main__':
    data = models()
    out = os.path.join(HERE, '..', 'docs', 'index.html')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w').write(HTML.replace('__DATA__', json.dumps(data)))
    kb = os.path.getsize(out) / 1024
    print(f"wrote docs/index.html  ({kb:.0f} kB, self-contained)")
    for k, m in data.items():
        print(f"  {k:9s} {m['faces']:7d} faces  "
              f"{m['span'][0]:6.1f} x {m['span'][1]:6.1f} x {m['span'][2]:6.1f} mm  "
              f"{len(m['palette'])} colours")
