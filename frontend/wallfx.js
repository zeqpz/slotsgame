// The live wall (assets/wallfx, tools/sprayrim/make_wall_fx.py):
// - wet paint oozes out of the wall. Out of each hole's pool (blob_<i>.webp, cut from the wall art)
//   and off the ends of the drips painted into the SMUKIEZ tag, a fresh run of thick, glossy paint
//   now and then: a bead gathers at the end of a drip (the pool swelling as it fills), runs down
//   the bricks slowing as it leaves paint behind, hangs, fattens, pinches off a drop that falls to
//   the pavement and splats with a little crown of droplets, and the run it leaves springs back,
//   stays wet, thins and is gone. Every tip keeps its own clock, so a few runs are on the go at once,
//   each at its own stage.
// - the paint is shaded live as a liquid. Every piece of it (a run's segments, its bead, a drop, a
//   splat) is a rounded height field, all of them melted into one shape (a smooth union), so a bead
//   swells out of its run and a drop pinches off it; the light is the scene's (art/STYLE.md): a key
//   light from the upper left that puts a sharp wet highlight down the left of every run and a hot
//   spot on every bead, the shadow side in the paint's own deep colour, a thin cool rim on the lower
//   right, the dark ink edge the painted paint has, and a soft shadow thrown down and to the right on
//   the bricks. The colours are the art's own (wallfx.json, sampled by make_wall_fx.py) and the paint
//   on the wall is dimmed exactly as #bgwall dims the art under it, so it is the wall's own paint
//   moving, not a sticker on top of it.
// - the SMUKIEZ tag's green outline is a neon sign (#tagglow): its tube in seven stretches (tube_<k>,
//   so one can drop out), riding the tag's wander, hop and pop (index.html).
// - the sign flickers on one clock (the flicker, below): a seeded schedule played as Web Animations on
//   the tube and its light, and read by everything else it lights (neon()) on the same frame - the
//   wet paint here and both figures (neonRim, index.html). surge() flares it on a big win.
// - its light falls on the wall (#walllight): the tube's light on the wall's relief (wall_height.webp:
//   brick faces, mortar, cracks; wall_wet.png: the wet paint shines), baked here once per layout from
//   where the tag stands, laid on the bricks in color-dodge (so it lights the faces and leaves the
//   joints dark) and locked to the wall, not to the tag's wander; the clock only sets its opacity.
// - light() says where the sign's light comes from for any point on the page, how strong it is there,
//   and how much of it each stretch of the tube gives (so a stretch dropping out dims what it lit).
//
// One WebGL context shades all the paint: each run's area is rendered in turn and copied into a plain
// 2D canvas of its own that sits in the wall (#wallpaint, inside #bgwall over the light: it rides the
// wall's lean and hop) or in the tag (#tagdrip, a .tagfx layer: it rides the tag's wander, hop and pop
// too), so the paint stays locked to what it runs down. Only what is on screen and not under the board
// is drawn, only while something is moving, and only round what moves; at most 30 times a second (every
// frame while the sign flickers). Idle, nothing runs until the next drip is due. No WebGL: the art's own
// painted paint and the old spill of light (#tagspill). Reduced motion: no paint moving, a steady sign.
(function () {
  "use strict";
  const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let NP = 24;                                  // pieces of paint one draw can carry (uniforms: 2 x NP vec4; setup() fits it to the GPU)
  const G = 6800;                               // gravity, art px / s^2 (the wall is ~2.3 m: a brick course is ~72 px)
  const MAX_ACTIVE = 5;                         // runs on the go at once across the page
  const SPEC_DIM = .5;                          // the wet highlight dimmed half as much as the paint by the night
  const NEON = [110, 255, 70];                  // the tube's lime (make_wall_fx.py tag())
  const NEON_PAINT = .9;                        // the sign's glint and edge light on the wet paint, where its light is 1
  // the tube's light on the wall (bake()): its height off the wall and its reach, in wall-art px (a
  // stretch of tube lights the bricks round it the same whatever size the tag is drawn; a smaller tag
  // just has less tube); how much falls on a face square-on to the wall (the rest by how the face
  // turns to the tube); the gain, for a tag 2627 art px wide (a 1440x900 screen); how sharp the relief
  // is; how much light gets into a joint; how much the wet paint shines
  const WALL_LIGHT = { z: 58, reach: 330, flat: .45, gain: 6, ref: 2627, relief: 3.5, joint: .22, shine: 7 };
  let ART = [3840, 2160], FLOOR = .8755, TAG = [3303, 1674];
  let regions = [], layer = null, tagLayer = null, meta = null, raf = 0, wake = 0, last = 0;
  let checked = 0, aimed = 0, placedTag = "", started = false, frozen = false;
  let dimA = [.5, .62], tint = [20, 18, 24];   // read off #bgwall's gradient in place()
  let lit = null;                               // the light on the wall: { cv, ctx, tex, map, ... } (bake())

  const rnd = (a, b) => a + Math.random() * (b - a);
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const smooth = v => (v = clamp(v, 0, 1), v * v * (3 - 2 * v));
  const ease = v => 1 - Math.pow(1 - clamp(v, 0, 1), 2.2);

  // The tag's drip layer: a .tagfx like its glow and its light, so the tag's wander, hop and pop carry
  // it. Made here, as the page is read, so the tag's wander (index.html, which collects every .tagfx
  // when it starts) takes it along from the first frame.
  (function makeTagLayer() {
    const bg = document.getElementById("bgwall"), glow = document.getElementById("tagglow");
    if (!bg || REDUCED) return;
    tagLayer = document.createElement("div");
    tagLayer.id = "tagdrip"; tagLayer.className = "tagfx"; tagLayer.setAttribute("aria-hidden", "true");
    bg.insertBefore(tagLayer, glow || null);
  })();

  // ------------------------------------------------------------------ the tag's light
  // The glowing tube is a few dozen weighted points (wallfx.json tube.pts, make_wall_fx.py: the tube's
  // pixels clustered stretch by stretch), laid over #tagglow's box wherever that is on the page. For a
  // point, the light comes from the tube round it weighted by closeness - inverse square, softened, so
  // the nearest stretch leads and the rest of the sign still pulls - and its strength is how much tube
  // there is how close (1 where the boy stands on a desktop screen, beside the tag's left end).
  const SOFT = .12, REF = [.05, .6];            // SOFT in tag heights; REF: where the light is called 1, in tag heights from the box's top left
  let metaLoad = null, norm = 0;
  function loadMeta() {
    if (!metaLoad) metaLoad = fetch("assets/wallfx/wallfx.json").then(r => r.json()).then(m => {
      meta = m;
      if (meta.tube) {
        const aw = (meta.tag && meta.tag.size ? meta.tag.size[0] / meta.tag.size[1] : 2);
        for (const [px, py, w] of meta.tube.pts) { const du = px * aw - REF[0], dv = py - REF[1]; norm += w / (du * du + dv * dv + SOFT * SOFT); }
      }
      return m;
    }).catch(() => null);
    return metaLoad;
  }
  // where a page point's light comes from (page px), how strong it is there, and the share of it from
  // each stretch of the tube; null until the tube is read, or while the tag is not on screen
  function light(x, y) {
    if (!meta || !meta.tube) { loadMeta(); return null; }
    const box = document.getElementById("tagglow"), r = box && box.getBoundingClientRect();
    if (!r || !r.width || !r.height) return null;
    const H = r.height, u = (x - r.left) / H, v = (y - r.top) / H, aw = r.width / H, n = meta.tube.n;
    const seg = new Float32Array(n);
    let sw = 0, su = 0, sv = 0;
    for (const [px, py, w, s] of meta.tube.pts) {
      const pu = px * aw, du = pu - u, dv = py - v;
      const k = w / (du * du + dv * dv + SOFT * SOFT);
      sw += k; su += k * pu; sv += k * py; seg[s] += k;
    }
    if (!sw) return null;
    for (let s = 0; s < n; s++) seg[s] /= sw;
    return { x: r.left + su / sw * H, y: r.top + sv / sw * H, k: sw / (norm || 1), seg };
  }

  // ------------------------------------------------------------------ the sign's flicker
  // One clock for everything the sign lights: the tube (#tagglow, and each stretch of it), its light on
  // the bricks (#walllight), the wet paint here and both figures. A sign that stays on, with a faint
  // hum, and every 6-15 s an event: most often a stutter (two to four quick blinks inside a second),
  // now and then a longer sputter, rarely one stretch of the tube dropping out for a moment; a surge
  // (surge()) flares it and makes it buzz on a big win. The schedule is seeded, made a little ahead,
  // and played as Web Animations on opacity, 20 s at a time - the compositor runs the page's part of
  // it - and neon() reads the very same curve for the paint and the figures on the same frame. It runs
  // on its own clock (virtual ms) so a test can slow it down. Reduced motion: a steady sign.
  const FLK = { WIN: 20000, STEP: 200, EDGE: 6, GAP: [6000, 15000], MAX: 1.42 };
  let fl = null, flEls = null, nSeg = 0;
  const tl = () => document.timeline.currentTime ?? performance.now();
  const vnow = () => (fl ? fl.vt0 + (tl() - fl.rt0) * fl.rate : tl());
  function rng32(a) {
    return () => { a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  }
  // an event at t (virtual ms): steps on the whole sign (g) or on one stretch (s: [[k, steps]]), each
  // [from, to, level], and the bright catch as it comes back on (tail: [at, how much, how fast])
  function makeEvent(t, type, r, k) {
    const g = [], s = [];
    let x = t, tail = null;
    const span = (list, d, lvl) => { list.push([x, x + d, lvl]); x += d; };
    if (type === "stutter") {                    // a few quick blinks, the tube weak in between
      const n = 2 + Math.floor(r() * 3), dur = 200 + r() * 600;
      for (let i = 0; i < n; i++) {
        span(g, 30 + r() * 60, .03 + r() * .2);
        if (i < n - 1) span(g, Math.max(30, dur / n - 60) * (.6 + r() * .8), .78 + r() * .22);
      }
      tail = [x, .05 + r() * .04, 140];
    } else if (type === "sputter") {             // a longer fight to stay lit
      const end = t + 1200 + r() * 1200;
      span(g, 50 + r() * 60, .04 + r() * .1);
      while (x < end) { const u = r(); span(g, 40 + r() * 100, u < .22 ? .03 + r() * .12 : u < .66 ? .3 + r() * .4 : .85 + r() * .2); }
      tail = [x, .12, 220];
    } else {                                     // one stretch of the tube goes out for a moment
      const st = [];
      span(st, 40 + r() * 30, .05); span(st, 50 + r() * 40, .9); span(st, 400 + r() * 1000, .03 + r() * .04);
      span(st, 40 + r() * 20, .9); span(st, 30 + r() * 30, .08);
      s.push([k ?? Math.floor(r() * nSeg), st]);
    }
    return { t0: t, end: x, type, g, s, tail };
  }
  const stepAt = (steps, t) => { for (const [a, b, l] of steps) if (t >= a && t < b) return l; return 1; };
  // the sign at t: the whole of it (g), each stretch (seg), and the sheen (0 while a stretch is out)
  function levelsAt(t) {
    let g = 1 + .02 * Math.sin(t / 2700 * 6.2832 + fl.ph[0]) + .012 * Math.sin(t / 890 * 6.2832 + fl.ph[1]);
    const seg = fl.seg.fill(1);
    let sheen = 1;
    for (const ev of fl.events) {
      if (t < ev.t0 - 100 || t > ev.end + 1500) continue;
      g *= stepAt(ev.g, t);
      if (ev.tail && t >= ev.tail[0]) g *= 1 + ev.tail[1] * Math.exp(-(t - ev.tail[0]) / ev.tail[2]);
      for (const [k, st] of ev.s) { seg[k] *= stepAt(st, t); if (t >= ev.t0 - 60 && t < ev.end + 60) sheen = 0; }
    }
    for (const su of fl.surges) {                // a flare, and a buzz through it
      const u = t - su.t0;
      if (u < 0 || u > su.ms) continue;
      const env = Math.min(1, u / 70) * (1 - smooth((u - su.ms * .35) / (su.ms * .65)));
      g *= (1 + .42 * su.k * env) * (1 + .16 * su.k * env * (Math.sin(u * .0817) > 0 ? 1 : -1));   // ~13 Hz
    }
    return { g: Math.min(g, FLK.MAX), seg, sheen };
  }
  // the schedule from t0 to t1 sampled for the animations: a step of the hum every 200 ms, both sides of
  // every edge of an event (each blink is a 12 ms ramp), the catch, the surges' buzz
  function buildWin(t0, t1) {
    const r = fl.rng;
    while (fl.nextAt < t1 + 2000) {
      const u = r(), ev = makeEvent(fl.nextAt, u < .6 ? "stutter" : u < .85 ? "sputter" : "drop", r);
      fl.events.push(ev);
      fl.nextAt = Math.max(ev.end + 1500, fl.nextAt + FLK.GAP[0] + r() * (FLK.GAP[1] - FLK.GAP[0]));
    }
    fl.events = fl.events.filter(ev => ev.end + 2000 > t0);
    fl.surges = fl.surges.filter(su => su.t0 + su.ms > t0);
    const ts = [], E = FLK.EDGE, busy = [], dropping = new Set();
    for (let t = t0; t < t1; t += FLK.STEP) ts.push(t);
    ts.push(t1);
    const add = t => { if (t > t0 && t < t1) ts.push(t); };
    const edges = steps => { for (const [a, b] of steps) { add(a - E); add(a + E); add(b - E); add(b + E); } };
    for (const ev of fl.events) {
      if (ev.end + 1500 < t0 || ev.t0 > t1) continue;
      busy.push([ev.t0 - 40, ev.end + 500]);
      edges(ev.g);
      for (const [k, st] of ev.s) { dropping.add(k); edges(st); edges([[ev.t0 - 60, ev.end + 60]]); }
      if (ev.tail) for (let i = 1; i <= 10; i++) add(ev.tail[0] + i * ev.tail[2] * .35);
    }
    for (const su of fl.surges) { busy.push([su.t0 - 40, su.t0 + su.ms + 40]); for (let t = su.t0; t <= su.t0 + su.ms + 40; t += 19) add(t); }
    ts.sort((a, b) => a - b);
    const T = [];
    for (const t of ts) if (!T.length || t - T[T.length - 1] > .5) T.push(t);
    const n = T.length, g = new Float32Array(n), w = new Float32Array(n), sh = new Float32Array(n);
    const seg = Array.from({ length: nSeg }, (_, k) => (dropping.has(k) ? new Float32Array(n) : null));
    const share = meta.tube.segs.map(s => s.share);
    for (let i = 0; i < n; i++) {
      const L = levelsAt(T[i]);
      g[i] = L.g; sh[i] = L.sheen;
      let on = 0;
      for (let k = 0; k < nSeg; k++) { on += share[k] * L.seg[k]; if (seg[k]) seg[k][i] = L.seg[k]; }
      w[i] = L.g * on;                           // the light on the wall: what is lit of the tube, at the sign's level
    }
    return { t0, t1, T: Float64Array.from(T), g, w, sh, seg, dropping: dropping.size > 0, busy };
  }
  // play a stretch of the schedule: opacity on the tube, the wall's light, and - when a stretch drops
  // out - that stretch and the sheen; started together on the clock, the next stretch queued at the end
  function playWin(win) {
    const old = fl.anims, dur = win.t1 - win.t0, start = fl.rt0 + (win.t0 - fl.vt0) / fl.rate;
    fl.anims = [];
    const run = (el, base, arr) => {
      if (!el || !arr) return;
      const kf = Array.from(arr, (v, i) => ({ offset: clamp((win.T[i] - win.t0) / dur, 0, 1), opacity: clamp(base * v, 0, 1) }));
      kf[0].offset = 0; kf[kf.length - 1].offset = 1;
      const a = el.animate(kf, { duration: dur, fill: "forwards", easing: "linear" });
      a.playbackRate = fl.rate; a.startTime = start;
      fl.anims.push(a);
    };
    run(flEls.glow, flEls.base.glow, win.g);
    run(flEls.wall, flEls.base.wall, win.w);
    if (win.dropping) {
      run(flEls.sheen, flEls.base.sheen, win.sh);
      win.seg.forEach((arr, k) => run(flEls.segs[k], flEls.base.seg, arr));
    }
    for (const a of old) a.cancel();
    fl.win = win;
    if (fl.anims[0]) fl.anims[0].onfinish = () => { if (fl.win === win) { const t = Math.max(win.t1, vnow()); playWin(buildWin(t, t + FLK.WIN)); } };
  }
  function sampleWin(arr, t) {
    const T = fl.win.T;
    let lo = 0, hi = T.length - 1;
    if (t <= T[0]) return arr[0];
    if (t >= T[hi]) return arr[hi];
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (T[m] <= t) lo = m; else hi = m; }
    return arr[lo] + (arr[hi] - arr[lo]) * (t - T[lo]) / (T[hi] - T[lo]);
  }
  // The sign's level now, 1 steady: for a point that takes `seg` of its light from each stretch (light()),
  // what is lit of the tube for it; without, the whole sign.
  function neon(seg) {
    if (!fl || !fl.win) return 1;
    const w = fl.win, t = vnow();
    let g = sampleWin(w.g, t);
    if (seg && w.dropping) {
      let s = 0, tot = 0;
      for (let k = 0; k < seg.length; k++) { s += seg[k] * (w.seg[k] ? sampleWin(w.seg[k], t) : 1); tot += seg[k]; }
      if (tot) g *= s / tot;
    }
    return g;
  }
  // the light on the wall's level now (as #walllight shows it), and whether the sign is busy flickering
  const wallLevel = () => (fl && fl.win ? sampleWin(fl.win.w, vnow()) : 1);
  function flickering() {
    if (!fl || !fl.win) return false;
    const t = vnow();
    for (const [a, b] of fl.win.busy) if (t >= a && t <= b) return true;
    return false;
  }
  function flickerStart() {
    const glowEl = document.getElementById("tagglow");
    if (!glowEl || !meta || !meta.tube) return;
    nSeg = meta.tube.n;
    const op = el => (el ? parseFloat(getComputedStyle(el).opacity) : 1);
    const segs = [...glowEl.querySelectorAll(":scope > i.seg")];
    const wall = (lit && lit.cv) || document.getElementById("tagspill");
    flEls = { glow: glowEl, wall, sheen: glowEl.querySelector(":scope > .sheen"), segs,
              base: { glow: op(glowEl), wall: op(wall), sheen: op(glowEl.querySelector(":scope > .sheen")), seg: segs.length ? op(segs[0]) : 1 } };
    if (REDUCED) return;                         // a steady sign
    const seed = (window.SMUKIEZ_NEON_SEED >>> 0) || (Math.random() * 4294967296 >>> 0);
    const r = rng32(seed);
    fl = { seed, rng: r, rate: 1, vt0: tl(), rt0: tl(), events: [], surges: [], anims: [], win: null,
           seg: new Float32Array(nSeg), ph: [r() * 6.28, r() * 6.28] };
    fl.nextAt = fl.vt0 + 2500 + r() * 6000;     // the first event a few seconds in
    playWin(buildWin(fl.vt0, fl.vt0 + FLK.WIN));
  }
  // A surge: the sign flares and buzzes for `ms`, as hard as `strength` (1 a big win), then settles.
  function surge(strength = 1, ms = 1600) {
    if (!fl) return;
    const t = vnow();
    fl.surges.push({ t0: t, ms: Math.max(200, +ms || 1600), k: clamp(+strength || 1, 0, 2) });
    playWin(buildWin(t, t + FLK.WIN));
    go();
  }
  // tests: an event of a given kind a quarter of a second from now, and the clock's speed
  function forceEvent(type = "stutter", k) {
    if (!fl) return null;
    const t = vnow() + 250;
    fl.events = fl.events.filter(ev => ev.end < t - 200 || ev.t0 > t + 6000);
    const ev = makeEvent(t, type, fl.rng, k);
    fl.events.push(ev);
    fl.nextAt = Math.max(fl.nextAt, ev.end + 6000);
    playWin(buildWin(vnow(), vnow() + FLK.WIN));
    go();
    return { t0: ev.t0, end: ev.end, type, seg: ev.s.length ? ev.s[0][0] : -1 };
  }
  function setRate(rate) {
    if (!fl) return;
    fl.vt0 = vnow(); fl.rt0 = tl(); fl.rate = rate;
    for (const a of fl.anims) a.playbackRate = rate;
  }

  // ------------------------------------------------------------------ the paint's shader
  // Every piece of paint is a rounded height field, P = r^2 - s^2 (s: the distance from its middle
  // line, r: its radius there), positive on the paint. The pieces are melted together by a smooth
  // maximum, so where a bead meets its run, or a drop is pinching off, the paint bridges between them
  // as liquid does. The paint's surface is h = sqrt(P) - a round bead, or the round back of a run.
  // It is coloured the way the wall art paints its drips (make_wall_fx.py samples them): a body a shade
  // lighter on the lit side with the art's spray grain, a crisp dark band down the shadow side (lower
  // right) and a thin one on the lit side, the ink line round it, a narrow white streak down the left;
  // where the film is thin the wall's relief shows through it. Each piece also carries where a point
  // lies across it (-1 its left edge .. 1 its right) and its radius there, melted like the rest.
  const VS = "attribute vec2 a; void main(){ gl_Position = vec4(a, 0., 1.); }";
  const FS = NP => `
precision highp float;
uniform vec4 uView;     // canvas w, h (device px); device px per region px; -
uniform vec4 uOrg;      // the region's top left (region px); its height (region px); 1 = draw the pool
uniform vec4 uA[${NP}]; // a piece: x1, y1, r1, kind (0 a run segment, joined hard; 1 a flat ellipse; 2 a round piece melted in; +10 fades in from its first end)
uniform vec4 uB[${NP}]; // ... x2, y2, r2 (an ellipse: x2, y2 unused, r2 its half height), alpha
uniform vec4 uShadow;   // the shadow thrown on the bricks: offset x, y, softness (region px), strength
uniform vec4 uDim;      // the wall's darkening at the region's top and bottom (alpha), its tint (r, g in .zw)
uniform vec4 uMix;      // the tint's blue; how strongly the wet highlight is dimmed; the pieces in use; the grain
uniform vec4 uCel;      // the ink line (of the radius, and at least, region px); the dark band (of the radius) on the lit and the shadow side
uniform vec3 uBase, uDeep, uHi, uLine;
uniform vec4 uNeon;     // the sign: the way to it (x, y), its glint's strength now (its light here x its flicker); -
uniform vec3 uNeonC;
uniform vec4 uPool;     // the pool's sprite: its box at rest, x, y, w, h (region px)
uniform vec4 uSwell;    // ... the point it swells about (x, y) and how far (sx, sy)
uniform sampler2D uSpr;
uniform sampler2D uLit; // the tube's light on the wall (#walllight's own picture: the colour it dodges the wall with)
uniform vec4 uLitMap;   // region px -> its uv: u = x * .x + .z, v = y * .y + .w
uniform vec4 uLitK;     // 1 = this paint is on the lit wall; #walllight's opacity now (its level x the flicker); the reach of its smoothing (region px); how much of the wall's relief shows through
uniform vec2 uRelMap;   // region px -> the relief's uv (0: no relief under this paint)
uniform sampler2D uRel; // the wall's relief (wall_height.webp)

vec4 scene(vec2 p, out vec3 ex) {    // P, dP/dx, dP/dy, alpha; ex: across the piece (-1 .. 1), its radius there, and
                                      // on a round piece (a bead, a drop) how far down it the point is (-1 .. 1; 2 elsewhere)
  vec4 acc = vec4(-1e6, 0., 0., 0.);
  ex = vec3(0., 1., 2.);
  for (int i = 0; i < ${NP}; i++) {
    if (float(i) >= uMix.z) break;
    vec4 A = uA[i], B = uB[i];
    float kind = mod(A.w, 10.);
    vec4 c; float kk; vec3 e;
    if (kind < .5 || kind > 1.5) {
      vec2 ba = B.xy - A.xy, pa = p - A.xy;
      float l2 = dot(ba, ba);
      float t = clamp(dot(pa, ba) / max(l2, 1e-4), 0., 1.);
      vec2 d = pa - ba * t;
      float r = mix(A.z, B.z, t);
      c = vec4(r * r - dot(d, d), -2. * d, B.w * (A.w >= 10. ? smoothstep(0., .75, t) : 1.));
      e = vec3(dot(d, l2 > 1. ? normalize(vec2(ba.y, -ba.x)) : vec2(1., 0.)) / max(r, .01), r,   // right of its way down is +
               kind > 1.5 && l2 < r * r ? clamp(d.y / max(r, .01), -1., 1.) : 2.);
      float rm = min(A.z, B.z);
      kk = kind > 1.5 ? .32 * rm * rm : .015 * rm * rm;
    } else {
      vec2 R = vec2(A.z, B.z), u = (p - A.xy) / R;
      c = vec4((1. - dot(u, u)) * R.y * R.y, -2. * R.y * R.y * u / R, B.w);
      e = vec3(0., R.y, 2.);                     // a puddle: no streak, its band as deep as it is
      kk = .32 * R.y * R.y;
    }
    kk = max(kk, .5);
    float h = clamp(.5 + .5 * (c.x - acc.x) / kk, 0., 1.);
    acc = vec4(mix(acc.x, c.x, h) + kk * h * (1. - h), mix(acc.yzw, c.yzw, h));
    ex = vec3(mix(ex.xy, e.xy, h), h > .5 ? e.z : ex.z);
  }
  return acc;
}
float hash(vec2 q) { q = fract(q * vec2(123.34, 456.21)); q += dot(q, q + 45.32); return fract(q.x * q.y); }
float vnoise(vec2 q) {
  vec2 i = floor(q), f = fract(q); f = f * f * (3. - 2. * f);
  return mix(mix(hash(i), hash(i + vec2(1., 0.)), f.x), mix(hash(i + vec2(0., 1.)), hash(i + vec2(1., 1.)), f.x), f.y);
}

void main() {
  vec2 fc = vec2(gl_FragCoord.x, uView.y - gl_FragCoord.y);
  vec2 p = uOrg.xy + fc / uView.z;
  float fy = clamp(fc.y / uView.y, 0., 1.);
  float dim = mix(uDim.x, uDim.y, fy);
  vec3 tint = vec3(uDim.zw, uMix.x);

  // the paint is drawn over the wall's light (#walllight), so it takes that light itself, the way the
  // wall does: dodged by the light's colour, as strongly as the light layer is showing now
  float litA = uLitK.x > .5 ? uLitK.y : 0.;
  vec2 lu = p * uLitMap.xy + uLitMap.zw;

  // the pool, swelling about its top as paint gathers in it
  vec4 pool = vec4(0.);
  if (uOrg.w > .5) {
    vec2 q = uSwell.xy + (p - uSwell.xy) / uSwell.zw;
    vec2 uv = (q - uPool.xy) / uPool.zw;
    if (uv.x >= 0. && uv.y >= 0. && uv.x <= 1. && uv.y <= 1.) pool = texture2D(uSpr, uv);
    pool.rgb = pool.rgb * (1. - dim) + tint * dim * pool.a;          // premultiplied, darkened as the wall
    if (litA > 0. && pool.a > .004) {                                 // and lit exactly as the wall round it
      vec3 c0 = pool.rgb / pool.a, cs = texture2D(uLit, lu).rgb;
      pool.rgb = mix(c0, min(vec3(1.), c0 / max(vec3(.001), 1. - cs)), litA) * pool.a;
    }
  }

  vec3 ex, exs;
  vec4 s = scene(p, ex);
  float g = max(length(s.yz), 1e-3);
  float dE = s.x / g;                                                // ~ the distance in from the paint's edge
  float cov = clamp(dE * uView.z + .5, 0., 1.) * s.w;

  // the shadow on the bricks (and on the pool), thrown down and to the right, and a tight contact
  // shadow right round the paint
  vec4 sh = scene(p - uShadow.xy, exs);
  float dS = sh.x / max(length(sh.yz), 1e-3);
  float shA = smoothstep(-uShadow.z, uShadow.z * .6, dS) * sh.w * uShadow.w;
  shA = max(shA, (1. - smoothstep(0., 2.5, -dE)) * step(dE, 0.) * s.w * .35);
  vec4 under = vec4(pool.rgb * (1. - shA), pool.a + shA * (1. - pool.a));

  vec3 col = vec3(0.);
  if (cov > 0.) {
    float hgt = sqrt(max(s.x, 0.));
    vec2 gh = s.yz / (2. * max(hgt, .35));
    float m = length(gh);
    if (m > 2.2) gh *= 2.2 / m;                                     // a contact angle: the paint's edge is never steeper
    vec3 n = normalize(vec3(-gh * .8, 1.));
    const vec3 L = vec3(-.4826, -.5791, .6574);                      // the key light, upper left, in front
    vec2 nx = n.xy / max(length(n.xy), 1e-4);                         // outward, in the wall's plane
    float a = clamp(ex.x, -1., 1.), r = max(ex.y, .5);
    // the shadow side: the lower right of every shape, the outline turned that way (0 on a flat top)
    float side = smoothstep(-.5, .5, dot(nx, vec2(.7071)) * smoothstep(.02, .3, 1. - n.z) + .5 * a);
    float bandW = r * mix(uCel.z, uCel.w, side), inkW = max(uCel.y, r * uCel.x);
    // the body, a shade lighter toward the lit side, with the spray grain of the art's paint
    vec3 alb = mix(uBase, mix(uBase, uHi, .14), smoothstep(.2, -.8, a));
    alb *= 1. + uMix.w * ((vnoise(p / 5.3) - .5) * 1.3 + (vnoise(p / 1.7 + 19.7) - .5) * .7);
    // the wall's relief showing through where the film is thin (and a touch under the thick of it)
    if (uRelMap.x > 0.) {
      vec2 ru = p * uRelMap, o = uRelMap * 4.;
      float hc = texture2D(uRel, ru).r;
      float ha = .25 * (texture2D(uRel, ru + vec2(o.x, 0.)).r + texture2D(uRel, ru - vec2(o.x, 0.)).r
                      + texture2D(uRel, ru + vec2(0., o.y)).r + texture2D(uRel, ru - vec2(0., o.y)).r);
      alb *= 1. + (hc - ha) * uLitK.w * mix(.22, 1., 1. - smoothstep(1.5, 6., hgt));
    }
    // the dark band, crisp as the art paints it
    alb = mix(alb, uDeep, 1. - smoothstep(bandW - .9, bandW + .9, dE));
    // the white streak down the left of a run and over a bead's top, not round its underside
    // (on a bead or a drop only its upper part: a short stroke high on the left, as the art paints a drip's round end)
    float under_ = max(nx.y, 0.) * (1. - n.z);
    float hiUp = ex.z > 1.5 ? 1. : 1. - smoothstep(-.5, -.1, ex.z);
    float streak = (1. - smoothstep(.05, .1, abs(a + .28))) * (1. - smoothstep(.1, .35, under_)) * smoothstep(4., 7., r) * hiUp
                 * smoothstep(bandW, bandW + 1.5, dE);
    alb = mix(alb, uHi, streak * .9);
    // and the ink line round it all
    alb = mix(alb, uLine, 1. - smoothstep(inkW - .7, inkW + .7, dE));
    col = alb * (1. - dim) + tint * dim;
    // a small hot spot on round paint (a bead, a drop) where it faces the key light
    vec3 H1 = normalize(L + vec3(0., 0., 1.));
    float spec = pow(max(dot(n, H1), 0.), 70.) * .85 * smoothstep(.05, .3, -nx.y * (1. - n.z));
    col += mix(uHi, vec3(1.), .5) * spec * (1. - dim * uMix.y);
    vec3 Ln = normalize(vec3(uNeon.xy, .45));                        // toward the sign
    // the tube's light on the paint: the wall's light here, smoothed over a brick or so (the run takes
    // the light of the wall it runs down, not of the joints behind it), turned by the paint's own
    // slope - most on the side that faces the sign - and dodged on as the wall's is
    if (litA > 0.) {
      vec2 o = abs(uLitMap.xy) * uLitK.z;
      vec3 ls = .25 * (texture2D(uLit, lu + vec2(o.x, 0.)).rgb + texture2D(uLit, lu - vec2(o.x, 0.)).rgb
                     + texture2D(uLit, lu + vec2(0., o.y)).rgb + texture2D(uLit, lu - vec2(0., o.y)).rgb);
      vec3 cs = clamp(ls * (.8 + .3 * max(dot(n, Ln), 0.)), 0., .8);   // about what the art round it takes, a little more facing the sign
      col = mix(col, min(vec3(1.), col / max(vec3(.001), 1. - cs)), litA);
    }
    // and its glint: the tube's reflection on the wet paint, in the tube's own lime, and its light along
    // the edge that faces it, taken by the paint as paint takes light - lime on violet hardly shows,
    // lime on lime does (light, not paint: after the darkening), flashing with the sign
    if (uNeon.z > .01) {
      float nn = max(dot(n, normalize(Ln + vec3(0., 0., 1.))), 0.);
      float edge = pow(max(dot(nx, uNeon.xy), 0.), 1.5) * (1. - n.z);
      float dif = uLitK.x > .5 ? 0. : .22 * max(dot(n, Ln), 0.);    // off the wall (the tag's runs): a little of its light too
      col += uNeon.z * (uNeonC * pow(nn, 60.) * 1.1 + uNeonC * alb * (edge * 1.3 + dif));
    }
  }
  gl_FragColor = vec4(col * cov, cov) + under * (1. - cov);
}`;

  // ------------------------------------------------------------------ the tube's light on the wall
  // Baked once per layout (place()), from where the tag stands at rest: for every point of the wall
  // round it, the light of each of the tube's points - falling off with distance, more of it on a face
  // turned toward that point (the relief's own slope, from wall_height), and a hot reflection of it on
  // the wet paint - and less of it down in a joint. The result is the colour #walllight dodges the wall
  // with; the clock only sets that layer's opacity.
  const BAKE_FS = NT => `
precision highp float;
uniform vec2 uSize;      // the light's canvas, device px
uniform vec4 uToWall;    // canvas px -> #bgwall px: x * .x + .z, y * .y + .w
uniform vec4 uToArt;     // #bgwall px -> the wall art's uv
uniform vec2 uTexel;     // a texel of the relief, uv
uniform vec3 uT[${NT}];  // the tube: x, y (#bgwall px), weight
uniform vec4 uK;         // the tube's height off the wall and its reach (#bgwall px); the light on a face square-on; gain
uniform vec4 uK2;        // how sharp the relief is; the light deep in a joint; how much the wet paint shines; how far it is baked (#bgwall px)
uniform vec4 uTagBox;    // the tag's box at rest, #bgwall px: x0, y0, x1, y1
uniform vec3 uLime;
uniform sampler2D uH, uWet;
float hgt(vec2 uv) { return texture2D(uH, uv).r; }
void main() {
  vec2 px = vec2(gl_FragCoord.x, uSize.y - gl_FragCoord.y);
  vec2 P = px * uToWall.xy + uToWall.zw;
  vec2 uv = P * uToArt.xy + uToArt.zw;
  float h = hgt(uv);
  vec2 tx = vec2(uTexel.x, 0.), ty = vec2(0., uTexel.y);
  vec3 N = normalize(vec3(-(hgt(uv + tx) - hgt(uv - tx)) * uK2.x, -(hgt(uv + ty) - hgt(uv - ty)) * uK2.x, 1.));
  float ring = 0.;                               // how far the point sits below the ground round it: 0 deep in a joint
  for (int i = 0; i < 8; i++) { float a = float(i) * .7854; ring += hgt(uv + vec2(cos(a), sin(a)) * uTexel * 3.); }
  float cav = clamp(1. - 2.2 * max(0., ring / 8. - h), 0., 1.);
  float wet = texture2D(uWet, uv).r;
  float E = 0., S = 0.;
  for (int j = 0; j < ${NT}; j++) {
    vec3 T = uT[j];
    vec3 L = vec3(T.xy - P, uK.x);
    float d2 = dot(L, L);
    L *= inversesqrt(d2);
    float fall = T.z / (1. + d2 / (uK.y * uK.y));
    E += fall * (uK.z + (1. - uK.z) * max(dot(N, L), 0.));
    S += fall * pow(max(dot(N, normalize(L + vec3(0., 0., 1.))), 0.), 48.);
  }
  // faded out before the baked area ends, so its edge never shows
  vec2 out_ = max(max(uTagBox.xy - P, P - uTagBox.zw), 0.);
  float win = 1. - smoothstep(uK2.w * .65, uK2.w, length(out_));
  E *= uK.w * mix(uK2.y, 1., cav) * win;
  gl_FragColor = vec4(clamp(E * uLime + S * win * uK2.z * wet * vec3(.8, 1., .75), 0., .78), 1.);
}`;

  let gl = null, glc = null, U = null, prog = null, bakeProg = null, BU = null, NT = 64, tubePts = [];
  const GL_ATTRS = { premultipliedAlpha: true, alpha: true, antialias: false, preserveDrawingBuffer: true };
  function setup() {
    glc = document.createElement("canvas"); glc.width = 512; glc.height = 2048;
    gl = glc.getContext("webgl", GL_ATTRS);
    if (!gl) return false;
    initGL();
    // a context the GPU takes away (a reset, a phone backgrounded short of memory) is asked back
    // (preventDefault), and everything on it is made again when it comes back
    glc.addEventListener("webglcontextlost", e => { e.preventDefault(); gl = null; for (const R of regions) R.cv.style.display = "none"; });
    glc.addEventListener("webglcontextrestored", restoreGL);
    return true;
  }
  function restoreGL() {
    gl = glc.getContext("webgl", GL_ATTRS);
    if (!gl || gl.isContextLost()) return;
    try { initGL(); } catch (e) { gl = null; console.warn("wall paint:", e.message); return; }
    const made = im => (im && im.complete && im.naturalWidth ? texture(im) : null);
    for (const R of regions) {
      R.tex = made(R.sprite);
      R.prev = null;
      R.ctx.clearRect(0, 0, R.cv.width, R.cv.height);
      R.cv.style.display = "block";
    }
    if (lit) {
      lit.tex = texture(null); lit.hT = made(lit.hImg); lit.wT = made(lit.wImg);
      if (lit.geo) bake(lit.geo);
    }
    go();
  }
  // the programs, the quad, the uniforms and the state, on the context as it is now (setup(), and again
  // after the context comes back)
  function initGL() {
    const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)); return s; };
    const link = fs => {
      const p = gl.createProgram();
      gl.attachShader(p, sh(gl.VERTEX_SHADER, VS)); gl.attachShader(p, sh(gl.FRAGMENT_SHADER, fs));
      gl.bindAttribLocation(p, 0, "a");          // both programs draw the same quad
      gl.linkProgram(p);
      if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p));
      return p;
    };
    // as many pieces as the GPU has room for: 2 vectors each, besides the 20 the shader's other uniforms take
    NP = clamp(Math.floor(((gl.getParameter(gl.MAX_FRAGMENT_UNIFORM_VECTORS) || 64) - 20) / 2), 16, 32);
    prog = link(FS(NP));
    // the bake takes as many of the tube's points as the GPU has room for (a phone may have 64 vectors)
    NT = clamp((gl.getParameter(gl.MAX_FRAGMENT_UNIFORM_VECTORS) || 64) - 12, 16, 64);
    try { bakeProg = link(BAKE_FS(NT)); } catch (e) { bakeProg = null; console.warn("wall light:", e.message); }
    if (bakeProg) {
      BU = {};
      for (const n of ["uSize", "uToWall", "uToArt", "uTexel", "uT", "uK", "uK2", "uTagBox", "uLime", "uH", "uWet"]) BU[n] = gl.getUniformLocation(bakeProg, n);
    }
    gl.useProgram(prog);
    const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
    U = {};
    for (const n of ["uView", "uOrg", "uA", "uB", "uShadow", "uDim", "uMix", "uCel", "uBase", "uDeep", "uHi", "uLine", "uNeon", "uNeonC", "uPool", "uSwell", "uSpr", "uLit", "uLitMap", "uLitK", "uRelMap", "uRel"]) U[n] = gl.getUniformLocation(prog, n);
    gl.uniform1i(U.uSpr, 0); gl.uniform1i(U.uLit, 1); gl.uniform1i(U.uRel, 2);
    // every sampler's unit holds a texture from the start (an empty unit makes the GPU warn on each draw)
    for (let u = 3; u >= 0; u--) { gl.activeTexture(gl.TEXTURE0 + u); texture(null); }
    gl.uniform3f(U.uNeonC, NEON[0] / 255, NEON[1] / 255, NEON[2] / 255);
    gl.disable(gl.BLEND);
    gl.enable(gl.SCISSOR_TEST);
    gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, true);
  }
  function texture(img) {
    const t = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, t);
    if (img) gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
    else gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);   // filled later
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    return t;
  }

  // #walllight: a canvas in the wall under the paint (so it lights the bricks, the painted pools and the
  // runs' shadows), with the relief it is baked from; it bakes as soon as both maps are in
  function wallLight(bg) {
    if (!bakeProg || !meta.relief) return;
    const cv = document.createElement("canvas");
    cv.id = "walllight"; cv.setAttribute("aria-hidden", "true");
    bg.insertBefore(cv, layer);
    lit = { cv, ctx: cv.getContext("2d"), tex: texture(null), hT: null, wT: null, rect: null, size: null, geo: null };
    // the tube's points, merged pairwise (along each stretch) down to what the bake has room for
    let pts = meta.tube.pts.map(p => p.slice());
    while (pts.length > NT) {
      const out = [];
      for (let i = 0; i < pts.length; i += 2) {
        const a = pts[i], b = pts[i + 1];
        if (!b || b[3] !== a[3]) { out.push(a); if (b) out.push(b); continue; }
        const w = a[2] + b[2];
        out.push([(a[0] * a[2] + b[0] * b[2]) / w, (a[1] * a[2] + b[1] * b[2]) / w, w, a[3]]);
      }
      if (out.length === pts.length) { pts = pts.slice(0, NT); break; }
      pts = out;
    }
    tubePts = pts;
    // (the pictures are kept: a context that comes back after a loss makes its textures again from them)
    const load = (src, key) => { const im = new Image(); lit[key + "Img"] = im; im.onload = () => { if (!gl) return; lit[key] = texture(im); if (lit.hT && lit.wT && lit.geo) bake(lit.geo); }; im.src = src; };
    load("assets/wallfx/wall_height.webp", "hT");
    load("assets/wallfx/wall_wet.png", "wT");
  }
  // geo: #bgwall's size, the wall art's box in it, and the tag's box at rest (#bgwall px)
  function bake(geo) {
    if (!gl || !lit) return;
    lit.geo = geo;
    if (!lit.hT || !lit.wT) return;
    const { tag, art } = geo, L = WALL_LIGHT, s = art[2] / ART[0];   // #bgwall px per art px
    const reach = L.reach * s, far = Math.max(tag.w * .35, reach * 2.2);
    // the lit area: far round the tag, on the art and inside #bgwall
    const x0 = Math.max(art[0], 0, tag.left - far), x1 = Math.min(art[0] + art[2], geo.W, tag.left + tag.w + far);
    const y0 = Math.max(art[1], 0, tag.top - far), y1 = Math.min(art[1] + art[3], geo.H, tag.top + tag.h + far);
    if (x1 - x0 < 8 || y1 - y0 < 8) { lit.cv.style.display = "none"; lit.rect = null; return; }
    const lw = x1 - x0, lh = y1 - y0;
    // the light is soft and the relief a few px across: a canvas px per css px at most, no more than
    // two million of them (a phone's whole lit wall is a few hundred thousand)
    const dens = Math.min(1, Math.sqrt(2e6 / (lw * lh)), 2048 / lw, 2048 / lh);
    const cw = Math.max(1, Math.round(lw * dens)), ch = Math.max(1, Math.round(lh * dens));
    if (glc.width < cw || glc.height < ch) { glc.width = Math.max(glc.width, cw); glc.height = Math.max(glc.height, ch); }
    gl.useProgram(bakeProg);
    gl.viewport(0, 0, cw, ch); gl.scissor(0, 0, cw, ch);
    gl.uniform2f(BU.uSize, cw, ch);
    gl.uniform4f(BU.uToWall, lw / cw, lh / ch, x0, y0);
    gl.uniform4f(BU.uToArt, 1 / art[2], 1 / art[3], -art[0] / art[2], -art[1] / art[3]);
    gl.uniform2f(BU.uTexel, 1 / meta.relief.size[0], 1 / meta.relief.size[1]);
    const T = new Float32Array(NT * 3);
    tubePts.forEach(([u, v, w], j) => { T[j * 3] = tag.left + u * tag.w; T[j * 3 + 1] = tag.top + v * tag.h; T[j * 3 + 2] = w; });
    gl.uniform3fv(BU.uT, T);
    gl.uniform4f(BU.uK, L.z * s, reach, L.flat, L.gain * (tag.w / s) / L.ref);   // the light of all the tube there is
    gl.uniform4f(BU.uK2, L.relief, L.joint, L.shine, far);
    gl.uniform4f(BU.uTagBox, tag.left, tag.top, tag.left + tag.w, tag.top + tag.h);
    gl.uniform3f(BU.uLime, .42, .99, .33);
    gl.activeTexture(gl.TEXTURE2); gl.bindTexture(gl.TEXTURE_2D, lit.hT); gl.uniform1i(BU.uH, 2);
    gl.activeTexture(gl.TEXTURE3); gl.bindTexture(gl.TEXTURE_2D, lit.wT); gl.uniform1i(BU.uWet, 3);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    lit.cv.width = cw; lit.cv.height = ch;
    Object.assign(lit.cv.style, { display: "block", left: x0 + "px", top: y0 + "px", width: lw + "px", height: lh + "px" });
    lit.ctx.drawImage(glc, 0, glc.height - ch, cw, ch, 0, 0, cw, ch);
    // the same picture for the paint drawn over it (the bottom row first, as GL reads it)
    gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, lit.tex);
    gl.copyTexImage2D(gl.TEXTURE_2D, 0, gl.RGB, 0, 0, cw, ch, 0);
    gl.activeTexture(gl.TEXTURE0);
    gl.useProgram(prog);
    lit.rect = [x0, y0, lw, lh];
    document.getElementById("bgwall").classList.add("lit");
    mapLit();
  }

  // ------------------------------------------------------------------ one run's life
  // Its pieces at any moment come from its age: the root (from inside the painted drop it grows out
  // of, melting in, so the two are one paint), the run down the bricks in a few tapered segments, the
  // bead at its end; and the drops it lets go of, handed to the region to fall. Nothing of it ever
  // fades: once the first drop has gone, the rest of the run drains off the wall - the root pulls back
  // up into the painted drip and the run parts from it, its tail slides down the bricks narrowing from
  // the top, the paint gathers in the bead at the end, and that falls too (now and then with a small
  // bead after it). The run is gone when its last drop has left.
  // Its width is the painted drip's (make_wall_fx.py measures the bright paint at the drip's end; the
  // art's dark band and ink line round it come to about half as much again).
  const WIDE = .64;
  function newDrip(R, tip) {
    const r0 = tip.w * WIDE * rnd(.95, 1.03);
    const room = R.floor - tip.y - r0 * 4;
    const T = { gather: rnd(1, 1.7), run: rnd(2.6, 4.6), hang: rnd(.7, 1.4), pinch: rnd(.26, .38),
                recoil: .45, sever: rnd(.45, .65), slide: rnd(2.7, 3.7), last: rnd(.8, 1.1), sat: Math.random() < .45 ? rnd(.45, .7) : 0 };
    let acc = 0; const at = {};
    for (const [n, d] of Object.entries(T)) { at[n] = acc; acc += d; }
    const seed = rnd(0, 6.3), wob = r0 * rnd(.08, .16), lam = r0 * rnd(2.2, 3.4), drift = rnd(-.035, .035);
    return {
      tip, r0, T, at, end: acc, t: 0, seed, dropped: 0, lastDone: 0, satDone: 0,
      len: clamp(r0 * rnd(3.5, 8.5), r0 * 2, Math.max(r0 * 2, room)),
      xAt: (x0, y) => x0 + wob * Math.sin(y / lam + seed) - wob * Math.sin(seed) + drift * y,
      bulge: y => 1 + .07 * Math.sin(y / (r0 * 1.9) + seed * 1.7),
    };
  }

  // the run's state now: where its top, end and bead are, how thick it is, and whether the root still
  // holds it to the painted drip (root: 1 whole, 0 gone)
  function dripState(d) {
    const { r0, T, at } = d, t = d.t, ph = n => clamp((t - at[n]) / T[n], 0, 1);
    const s = { topY: r0 * .2, topR: 0, endY: 0, bead: 0, trailR: r0, endR: r0 * .93, neck: 1, sag: 0, swell: 0, root: 1 };
    const y1 = r0 * .55;                          // where the bead sits when it has just come out
    const e2 = y1 + d.len + r0 * .3;              // the run's end once it has hung
    if (t < at.run) {                             // a bead gathers at the drop's end, the pool filling
      const e = smooth(ph("gather"));
      s.endY = -r0 * .25 + (y1 + r0 * .25) * e; s.bead = r0 * (.7 + .38 * e); s.swell = e;
    } else if (t < at.hang) {                     // ... and runs down, slowing as it leaves paint behind
      const u = ph("run"), p = ease(u);
      s.endY = y1 + d.len * p; s.bead = r0 * (1.1 - .08 * p + .04 * Math.sin(u * Math.PI)); s.swell = 1 - .4 * p;
      s.endR = r0 * (.93 - .15 * p);
    } else if (t < at.pinch) {                    // it hangs and fattens
      const e = smooth(ph("hang"));
      s.endY = y1 + d.len + r0 * .3 * e; s.bead = r0 * (.96 + .3 * e); s.swell = .6 - .2 * e;
    } else if (t < at.recoil) {                   // a neck forms and the drop lets go
      const e = ph("pinch");
      s.endY = e2; s.bead = r0 * 1.26; s.sag = r0 * 1.1 * e * e; s.neck = 1 - smooth(e); s.swell = .4 * (1 - e);
    } else {                                      // the rest drains off the wall
      const u = t - at.recoil;
      // the end springs back up as the drop's weight goes, and settles
      const back = r0 * (.9 * (1 - Math.exp(-u * 7)) - .5 * Math.sin(u * 15) * Math.exp(-u * 5));
      const eR = e2 - back;
      s.endR = r0 * .8; s.trailR = r0 * .92;
      // the root pulls back up into the painted drip and the run parts from it, its top a tapered tail
      const sv = ph("sever"), cut = smooth(sv);
      s.root = 1 - cut;
      const topS = r0 * (.45 + .55 * cut);        // where the tail's tip is as it parts
      // ... which then slides down the bricks, slowly at first, until all of it has gathered at the end
      const v = ph("slide"), slide = v * v * (1.6 - .6 * v);
      const gap = Math.max(0, eR - topS);
      s.topY = topS + gap * slide;
      s.topR = r0 * (.08 + .25 * cut) * (1 - .5 * v);
      s.trailR = r0 * (.92 - .22 * slide); s.endR = r0 * (.8 - .2 * slide);
      // the bead at the end fills with what slides into it (its volume grows as the run's shortens)
      const b0 = r0 * .55, slid = gap * slide;
      s.bead = Math.min(r0 * 1.25, Math.cbrt(b0 * b0 * b0 + .55 * s.trailR * s.trailR * slid));
      s.endY = eR + r0 * .45 * slide;
      if (t >= at.last) {                         // the last bead hangs, necks and goes
        const e = ph("last");
        s.topY = s.endY; s.trailR = s.endR = s.bead * .5;
        s.sag = s.bead * .9 * smooth((e - .45) / .55) ** 2; s.neck = 1 - smooth((e - .4) / .6);
        if (d.lastDone) { s.bead = 0; s.neck = 1; s.sag = 0; }
      }
      if (t >= at.sat && T.sat) {                 // a small bead left on the wall where the last one parted, after it
        const e = ph("sat");
        s.topY = s.endY = eR + r0 * .45 + r0 * .5 * e; s.trailR = s.endR = 0;
        s.bead = d.satDone ? 0 : r0 * .34; s.sag = s.bead * .7 * smooth((e - .5) / .5) ** 2; s.neck = 1;
      }
    }
    return s;
  }

  // the run's pieces into the list (region px), at its tip as the pool's swell carries it
  function dripPieces(R, d, s, L) {
    const r0 = d.r0, tx = d.tx, ty = d.ty;     // the tip where the pool's swell has carried it this frame
    // the root: from inside the painted drop down to the tip, melting in, so the run grows out of it;
    // as the run parts, it pulls back up into the drop and narrows away
    if (s.root > 0) {
      const ry = ty + r0 * (.2 - .9 * (1 - s.root)), rr = Math.max(.3, s.trailR * d.bulge(r0 * .2) * s.root);
      L.push([tx, ty - r0 * 1.2, r0 * .78, 10, d.xAt(tx, r0 * .2), ry, rr, 1]);
    }
    const top = s.topY, end = Math.max(top, s.endY);
    if (end > top + 1 && s.trailR > 0) {
      const n = clamp(Math.round((end - top) / (r0 * 2.4)), 1, 5);
      let px = d.xAt(tx, top), py = ty + top;
      for (let i = 1; i <= n; i++) {
        const yy = top + (end - top) * i / n;
        const x = d.xAt(tx, yy), y = ty + yy;
        const rad = j => (j === 0 && s.root < 1 ? Math.max(s.topR, .3) : (s.trailR + (s.endR - s.trailR) * j / n) * d.bulge(top + (end - top) * j / n));
        // a tail's top narrows over its first stretch
        const r1 = rad(i - 1), r2 = i === 1 && s.root < 1 && n > 1 ? Math.min(rad(1), Math.max(s.topR, .3) + (end - top) / n * .35) : rad(i);
        // (the stretch after a tail's taper melts into it, so the tail rounds out instead of a shoulder)
        L.push([px, py, r1, i === 2 && s.root < 1 ? 2 : 0, x, y, r2, 1]);
        px = x; py = y;
      }
    }
    if (s.bead > .5) {                          // the bead, hanging off the end (and thinning to a neck as it lets go)
      const bx = d.xAt(tx, end), by = ty + end + s.bead * .55 + s.sag;
      if (s.neck < 1) {                         // the neck: a thin bridge from the run's end to the drop
        const nr = Math.max(.2, Math.max(s.endR, s.bead * .5) * s.neck * .9);
        L.push([bx, ty + end, nr, 2, bx, by - s.bead * .6, nr * .8 + s.bead * .12 * s.neck, 1]);
      }
      L.push([bx, by, s.bead, 2, bx, by + .01, s.bead, 1]);
    }
  }

  // a falling drop, drawn out along its speed; a landed one is a splat
  function dropPieces(p, L) {
    const st = clamp(p.v * .02, 0, p.r * 3.2);
    L.push([p.x, p.y - st, p.r * (st > 1 ? .62 : 1), 2, p.x, p.y, p.r * (1 - .08 * st / (p.r * 3.2 + 1e-3)), 1]);
  }
  // A flat piece (a puddle, a landed droplet) is never thinner than a fifth of its width: the shader's
  // distance off a flatter ellipse falls to half the true one, so its paint and shadow spread sideways
  // past the box redrawn round it (and were left behind on the pavement).
  const flat = (L, x, y, rx, ry) => { if (rx > .5) L.push([x, y, rx, 1, 0, 0, Math.max(ry, rx * .2, .6), 1]); };
  function splatPieces(s, L) {
    // the drop lands as a squashed blob, spreads into a puddle, and soaks into the pavement: it draws in
    // to nothing, thinning as it goes (the splash's droplets shrink away the same)
    const u = s.t, spread = ease(u / .16), soak = smooth((u - .3) / (s.life - .3));
    flat(L, s.x, s.y + s.r * .05, s.r * (1 + 1.7 * spread) * (1 - soak), s.r * (.78 - .44 * spread) * (1 - soak) * (1 - .5 * soak));
    for (const c of s.crown) {
      if (c.landed) { const k = 1 - smooth((u - c.landed) / 1.2); flat(L, c.x, c.y, c.r * 1.35 * k, c.r * .6 * k); }
      else { const st = clamp(Math.hypot(c.vx, c.vy) * .012, 0, c.r * 2.5); const k = st / (Math.hypot(c.vx, c.vy) || 1); L.push([c.x - c.vx * k, c.y - c.vy * k, c.r * .55, 2, c.x, c.y, c.r, 1]); }
    }
  }

  // ------------------------------------------------------------------ a region: a pool or a tag drip, and its runs
  // kind "wall": a pool in the wall (region px = art px); kind "tag": a tip of the tag (region px = tag px)
  function makeRegion(kind, src, i) {
    const cv = document.createElement("canvas");
    Object.assign(cv.style, { position: "absolute", display: "block", pointerEvents: "none" });
    const R = {
      kind, src, i, cv, ctx: cv.getContext("2d"), tips: [], drips: [], drops: [], splats: [], due: [],
      paint: src.paint, dirty: null, prev: null, vis: false, k: 1, scale: 1, sprite: null, tex: null, swell: 0,
      light: null, floor: 0, x0: 0, y0: 0, x1: 1, y1: 1, dim: [0, 0], alloc: false,
    };
    if (kind === "wall") {
      R.tips = src.tips.map(([x, y, w]) => ({ x: x * ART[0], y: y * ART[1], w: clamp(w * ART[0], 14, 46) }));
      R.box = [src.x * ART[0], src.y * ART[1], src.w * ART[0], src.h * ART[1]];
      R.sprite = new Image(); R.sprite.src = `assets/wallfx/blob_${i}.webp`;
      // the art's drips (measured across them): an ink line ~.12 of the radius (2.2 art px at least), a
      // dark band a fifth of it on the lit side and nearly two fifths on the shadow side, spray grain; the
      // wall's relief shows through
      R.cel = [.12, 2.2, .19, .38]; R.grain = .3; R.relief = .9; R.shadow = [6, 8, 6, .48];
    } else {
      R.tips = [{ x: src.x * TAG[0], y: src.y * TAG[1], w: clamp(src.w * TAG[0], 16, 40) }];
      R.box = null; R.cel = [.14, 2.6, .1, .26]; R.grain = .18; R.relief = 0; R.shadow = [8, 11, 8, .4];   // the tag's heavier ink, smoother airbrushed paint
    }
    R.due = R.tips.map(() => performance.now() + rnd(600, 9000));
    return R;
  }

  // the region's extent: its pool and tips, down to the pavement and a splash either side
  function extent(R) {
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity;
    for (const t of R.tips) { x0 = Math.min(x0, t.x - t.w * 4); x1 = Math.max(x1, t.x + t.w * 4); y0 = Math.min(y0, t.y - t.w * 1.6); }
    if (R.box) { const [bx, by, bw, bh] = R.box; x0 = Math.min(x0, bx - bw * .06); x1 = Math.max(x1, bx + bw * 1.06); y0 = Math.min(y0, by - bh * .05); }
    const splash = R.kind === "wall" ? 110 : 110 * R.unit;
    x0 = Math.min(x0, ...R.tips.map(t => t.x - splash)); x1 = Math.max(x1, ...R.tips.map(t => t.x + splash));
    R.x0 = x0; R.x1 = x1; R.y0 = y0; R.y1 = R.floor + (R.kind === "wall" ? 60 : 60 * R.unit);
  }

  function active(R) { return R.drips.length || R.drops.length || R.splats.length; }

  function step(R, dt, now) {
    // a tip whose time has come starts a run, if there is room for one
    for (let j = 0; j < R.tips.length; j++) {
      const running = R.drips.some(d => d.tip === R.tips[j]);
      // a tip whose run was dropped before it was done (a new layout drops the runs on the go: a
      // window resized, a pane shown again, a phone's address bar) starts again in a while, or every
      // resize would leave a few more tips dry for good
      if (R.due[j] === Infinity && !running) R.due[j] = now + rnd(1200, 3200);
      if (now < R.due[j] || running || !R.spawn) continue;   // (a region going out of view only finishes what it has)
      if (R.drips.length >= (R.tips.length > 2 ? 2 : 1) || regions.reduce((n, Q) => n + Q.drips.length, 0) >= MAX_ACTIVE) { R.due[j] = now + rnd(1200, 3200); continue; }
      R.drips.push(newDrip(R, R.tips[j]));
      R.due[j] = Infinity;                     // set again when this run is done
    }
    // the pool swells as paint gathers for a run, and settles back when the drop has gone
    let sw = 0;
    for (const d of R.drips) sw = Math.max(sw, dripState(d).swell);
    R.swell += (sw - R.swell) * Math.min(1, dt * 2.5);
    if (R.swell < .002 && !R.drips.length) R.swell = 0;
    const [ax, ay, sx, sy] = swellAt(R);
    for (let i = R.drips.length - 1; i >= 0; i--) {
      const d = R.drips[i];
      d.t += dt;
      d.tx = ax + (d.tip.x - ax) * sx; d.ty = ay + (d.tip.y - ay) * sy;
      const s = dripState(d);
      if (!d.dropped && d.t >= d.at.recoil) {  // the bead lets go
        d.dropped = 1;
        const by = d.ty + d.r0 * .55 + d.len + d.r0 * .3 + d.r0 * 1.26 * .55 + d.r0 * 1.1;
        R.drops.push({ x: d.xAt(d.tx, d.r0 * .55 + d.len + d.r0 * .3), y: by, r: d.r0 * 1.16, v: 90 });
      }
      // the last of the run, gathered in the bead at its end, lets go; and the small bead after it
      if (!d.lastDone && d.t >= d.at.last + d.T.last) {
        d.lastDone = 1;
        R.drops.push({ x: d.xAt(d.tx, s.endY), y: d.ty + s.endY + s.bead * .55 + s.sag, r: s.bead, v: 80 });
      }
      if (d.T.sat && !d.satDone && d.t >= d.at.sat + d.T.sat) {
        d.satDone = 1;
        R.drops.push({ x: d.xAt(d.tx, s.endY), y: d.ty + s.endY + d.r0 * .34 * .55 + s.sag, r: d.r0 * .34, v: 60 });
      }
      if (d.t >= d.end) {
        R.drips.splice(i, 1);
        R.due[R.tips.indexOf(d.tip)] = now + rnd(2600, 8500);
      }
    }
    const g = G * R.unit;
    for (let i = R.drops.length - 1; i >= 0; i--) {
      const p = R.drops[i];
      p.v += g * dt; p.y += p.v * dt;
      if (p.y + p.r * .3 >= R.floor) {         // the pavement: a splat and its crown of droplets
        R.drops.splice(i, 1);
        const n = 4 + Math.floor(Math.random() * 3), crown = [];
        for (let k = 0; k < n; k++) {
          const sgn = k % 2 ? 1 : -1, sp = rnd(.5, 1);
          crown.push({ x: p.x + sgn * p.r * .6, y: R.floor - p.r * .2, vx: sgn * rnd(120, 360) * sp * R.unit, vy: -rnd(220, 520) * sp * R.unit,
                       r: p.r * rnd(.18, .36), land: R.floor + rnd(-.1, .5) * p.r, landed: 0 });
        }
        R.splats.push({ x: p.x, y: R.floor, r: p.r, t: 0, life: rnd(2, 3), crown });
      }
    }
    for (let i = R.splats.length - 1; i >= 0; i--) {
      const s = R.splats[i];
      s.t += dt;
      for (const c of s.crown) {
        if (c.landed) continue;
        c.vy += g * dt; c.x += c.vx * dt; c.y += c.vy * dt;
        if (c.vy > 0 && c.y >= c.land) { c.y = c.land; c.landed = s.t; }
      }
      if (s.t > s.life) R.splats.splice(i, 1);
    }
  }
  // the pool's swell: the point it swells about (its top middle) and how far, x and y
  function swellAt(R) {
    if (!R.box) return [0, 0, 1, 1];
    const [bx, by, bw] = R.box, s = R.swell;
    return [bx + bw / 2, by + R.box[3] * .12, 1 + .022 * s, 1 + .055 * s];
  }

  function pieces(R) {
    const L = [];
    for (const d of R.drips) dripPieces(R, d, dripState(d), L);
    for (const p of R.drops) dropPieces(p, L);
    for (const s of R.splats) splatPieces(s, L);
    return L.length > NP ? L.slice(0, NP) : L;
  }
  // the box round the pieces (region px), with room for the shadow and the edge
  function bounds(R, L) {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const q of L) {
      const ell = (q[3] % 10) === 1, rx = ell ? q[2] : Math.max(q[2], q[6]), ry = ell ? q[6] : rx;
      const xa = ell ? q[0] : Math.min(q[0], q[4]), xb = ell ? q[0] : Math.max(q[0], q[4]);
      const ya = ell ? q[1] : Math.min(q[1], q[5]), yb = ell ? q[1] : Math.max(q[1], q[5]);
      x0 = Math.min(x0, xa - rx); x1 = Math.max(x1, xb + rx); y0 = Math.min(y0, ya - ry); y1 = Math.max(y1, yb + ry);
    }
    if (R.box && R.swell > 0) {
      const [bx, by, bw, bh] = R.box;
      x0 = Math.min(x0, bx - bw * .05); x1 = Math.max(x1, bx + bw * 1.05); y0 = Math.min(y0, by); y1 = Math.max(y1, by + bh * 1.08);
    }
    if (x0 > x1) return null;
    const m = R.shadow[2] + 4;
    return [x0 - m, y0 - m, x1 + R.shadow[0] + m, y1 + R.shadow[1] + m];
  }

  function draw(R, now) {
    const L = pieces(R);
    const b = bounds(R, L);
    // the device px box to redraw: round what is there now and what was there last frame
    const toDev = q => q && [Math.floor((q[0] - R.x0) * R.k), Math.floor((q[1] - R.y0) * R.k), Math.ceil((q[2] - R.x0) * R.k), Math.ceil((q[3] - R.y0) * R.k)];
    const cur = toDev(b), prev = R.prev;
    R.prev = cur;
    let u = cur && prev ? [Math.min(cur[0], prev[0]), Math.min(cur[1], prev[1]), Math.max(cur[2], prev[2]), Math.max(cur[3], prev[3])] : (cur || prev);
    if (!u) return;
    const W = R.cv.width, H = R.cv.height;
    // nothing left: the whole canvas cleared once, so no stray edge of a box's paint can stay behind
    if (!cur) { R.ctx.clearRect(0, 0, W, H); return; }
    u = [clamp(u[0], 0, W), clamp(u[1], 0, H), clamp(u[2], 0, W), clamp(u[3], 0, H)];
    const w = u[2] - u[0], h = u[3] - u[1];
    if (w <= 0 || h <= 0) return;
    R.ctx.clearRect(u[0], u[1], w, h);
    // shade the region's own canvas size in the GL canvas's bottom left, only inside the box
    gl.viewport(0, 0, W, H);
    gl.scissor(u[0], H - u[3], w, h);
    gl.uniform4f(U.uView, W, H, R.k, 0);
    gl.uniform4f(U.uCel, R.cel[0], R.cel[1], R.cel[2], R.cel[3]);
    const pool = R.box && R.swell > 0 && R.tex;
    gl.uniform4f(U.uOrg, R.x0, R.y0, R.y1 - R.y0, pool ? 1 : 0);
    if (pool) {
      gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, R.tex);
      gl.uniform4f(U.uPool, R.box[0], R.box[1], R.box[2], R.box[3]);
      const [ax, ay, sx, sy] = swellAt(R);
      gl.uniform4f(U.uSwell, ax, ay, sx, sy);
    }
    const A = new Float32Array(NP * 4), B = new Float32Array(NP * 4);
    L.forEach((q, i) => { A.set(q.slice(0, 4), i * 4); B.set(q.slice(4, 8), i * 4); });
    gl.uniform4fv(U.uA, A); gl.uniform4fv(U.uB, B);
    gl.uniform4f(U.uShadow, R.shadow[0], R.shadow[1], R.shadow[2], R.shadow[3]);
    gl.uniform4f(U.uDim, R.dim[0], R.dim[1], tint[0] / 255, tint[1] / 255);
    gl.uniform4f(U.uMix, tint[2] / 255, SPEC_DIM, L.length, R.grain);
    const c = v => v.map(x => x / 255);
    gl.uniform3fv(U.uBase, c(R.paint.base)); gl.uniform3fv(U.uDeep, c(R.paint.deep));
    gl.uniform3fv(U.uHi, c(R.paint.hi)); gl.uniform3fv(U.uLine, c(R.paint.line));
    // the sign's glint on the paint, flickering with the stretches that light it; on the wall, the
    // wall's light under it (#walllight, as strong as that layer is showing on this frame)
    const Lt = R.light, glint = Lt ? Math.min(1.2, Lt.k) * neon(Lt.seg) * NEON_PAINT : 0;
    gl.uniform4f(U.uNeon, Lt ? Lt.dx : 0, Lt ? Lt.dy : 0, glint, 0);
    const onLit = R.kind === "wall" && lit && lit.rect && R.litMap;
    if (onLit) { gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, lit.tex); gl.activeTexture(gl.TEXTURE0); gl.uniform4fv(U.uLitMap, R.litMap); }
    // the wall's relief under the paint on the wall (the tag's paint is on the tag)
    const rel = R.kind === "wall" && R.relief > 0 && lit && lit.hT;
    if (rel) { gl.activeTexture(gl.TEXTURE2); gl.bindTexture(gl.TEXTURE_2D, lit.hT); gl.activeTexture(gl.TEXTURE0); }
    gl.uniform2f(U.uRelMap, rel ? 1 / ART[0] : 0, rel ? 1 / ART[1] : 0);
    gl.uniform4f(U.uLitK, onLit ? 1 : 0, onLit ? (flEls ? flEls.base.wall : 1) * wallLevel() : 0, 14, rel ? R.relief : 0);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    R.ctx.drawImage(glc, u[0], glc.height - H + u[1], w, h, u[0], u[1], w, h);
    stats.px += w * h; stats.draws++;
  }

  // ------------------------------------------------------------------ on screen?
  // A region starts runs while the place they start (its pool, or its tip and the stretch below it)
  // is on screen and not under the board, and while its drips are big enough on screen to be seen at
  // all (the tag's are a couple of px across on a phone: there they stay painted). Once it may not
  // (the tag wandered it under the board's edge, the screen changed), its paint already on the go
  // still finishes - runs, drops, splats - and only then does the region stop drawing. The board is
  // taken at rest (its layout box, not its rect, which a reveal's pop swells ~13 px a side), and a
  // region must be well under it to go under (hyst px), and as far out to come back, so the tag's
  // wander along the board's edge (1.1vw either way) does not switch it back and forth.
  function boardBox() {
    const board = document.getElementById("board"), app = document.getElementById("app");
    if (!board || !board.offsetWidth) return null;
    let x = 0, y = 0, el = board;
    while (el && el !== app) {
      x += el.offsetLeft; y += el.offsetTop; el = el.offsetParent;
      if (el && el !== app) { x += el.clientLeft; y += el.clientTop; }   // an offset parent's border
    }
    if (el !== app || !app.offsetWidth) {          // not laid out under #app: its rect, as it is
      const r = board.getBoundingClientRect();
      return r.width ? [r.left, r.top, r.right, r.bottom] : null;
    }
    const ar = app.getBoundingClientRect(), fit = ar.width / app.offsetWidth;   // #app is scaled to fit the screen
    return [ar.left + x * fit, ar.top + y * fit, ar.left + (x + board.offsetWidth) * fit, ar.top + (y + board.offsetHeight) * fit];
  }
  function visibility() {
    const bb = boardBox(), vw = innerWidth, vh = innerHeight, hyst = Math.max(20, vw * .016);
    for (const R of regions) {
      let spawn = false;
      if (R.on) {
        const r = R.cv.getBoundingClientRect();
        if (r.width > 0 && r.height > 0) {
          const sx = r.width / (R.x1 - R.x0), sy = r.height / (R.y1 - R.y0), a = R.anchor;
          const x0 = r.left + (a[0] - R.x0) * sx, x1 = r.left + (a[2] - R.x0) * sx, y0 = r.top + (a[1] - R.y0) * sy, y1 = r.top + (a[3] - R.y0) * sy;
          const onScreen = x1 > 0 && y1 > 0 && x0 < vw && y0 < vh;
          let under = false;
          if (onScreen && bb) {
            const m = R.under ? -hyst : hyst;      // under: all of it inside the board, hyst px in (out, to stay under)
            under = x0 >= bb[0] + m && x1 <= bb[2] - m && y0 >= bb[1] + m && y1 <= bb[3] - m;
          }
          R.under = under;
          spawn = onScreen && !under;
        }
      }
      if (spawn && !R.alloc) alloc(R);
      R.spawn = spawn;
      if (spawn) R.vis = true;
      else if (R.vis && !active(R) && !R.prev) {   // done drawing: its tips wait for it to come back
        R.vis = false;
        R.swell = 0;
        R.ctx.clearRect(0, 0, R.cv.width, R.cv.height);
        const now = performance.now();
        R.due = R.due.map(() => now + rnd(1500, 6000));
      }
    }
  }
  function alloc(R) {
    R.alloc = true;
    R.cv.width = Math.max(1, Math.round((R.x1 - R.x0) * R.k)); R.cv.height = Math.max(1, Math.round((R.y1 - R.y0) * R.k));
    R.prev = null;
    if (glc.width < R.cv.width || glc.height < R.cv.height) { glc.width = Math.max(glc.width, R.cv.width); glc.height = Math.max(glc.height, R.cv.height); }
    if (R.sprite && !R.tex) {
      const up = () => { if (gl) R.tex = texture(R.sprite); };
      if (R.sprite.complete && R.sprite.naturalWidth) up(); else R.sprite.onload = up;
    }
  }

  // where each region's light comes from - the way to the tube from its tips - and how strong
  function aimLight() {
    for (const R of regions) {
      if (!R.vis) continue;
      const r = R.cv.getBoundingClientRect();
      if (!r.width) continue;
      const t = R.tips[0], x = r.left + (t.x - R.x0) / (R.x1 - R.x0) * r.width, y = r.top + (t.y - R.y0) / (R.y1 - R.y0) * r.height;
      const L = light(x, y);
      if (!L) { R.light = null; continue; }
      const dx = L.x - x, dy = L.y - y, dd = Math.hypot(dx, dy) || 1;
      R.light = { dx: dx / dd, dy: dy / dd, k: L.k, seg: L.seg };
    }
  }

  // ------------------------------------------------------------------ the clock
  const stats = { frames: 0, ms: 0, px: 0, draws: 0, max: 0 };
  function frame(now) {
    raf = 0;
    if (!gl) return;
    if (document.hidden) { last = 0; sleep(1000); return; }
    // 30 times a second, like the rims: slow paint needs no more, and on a high-refresh screen
    // every display frame (144, 165 a second) was redrawing every canvas - but every frame while the
    // sign flickers, so the light on the paint blinks with the light on the wall
    if (last && now - last < 1000 / 30 - 2 && !flickering()) { if (!raf) raf = requestAnimationFrame(frame); return; }
    const t0 = performance.now();
    const dt = Math.min(.05, last ? (now - last) / 1000 : 1 / 30); last = now;
    if (now - checked > 500) { checked = now; replaceIfMoved(); visibility(); }
    if (now - aimed > 2000) { aimed = now; aimLight(); }
    let busy = false;
    for (const R of regions) {
      if (!R.vis) continue;
      if (!frozen) step(R, dt, now);
      if (active(R) || R.prev) { draw(R, now); busy = true; }
    }
    const ms = performance.now() - t0;
    stats.frames++; stats.ms += ms; stats.max = Math.max(stats.max, ms);
    // one loop only: a new layout found inside this frame (place() -> go()) may have asked for the next
    // frame already
    if (busy) { if (!raf) raf = requestAnimationFrame(frame); }
    else if (!raf) { last = 0; sleep(); }
  }
  // idle: nothing moves, so nothing runs until the next run is due on a region on screen (looked at
  // again now and then: the layout, or what is under the board, may have changed meanwhile)
  function sleep(ms) {
    clearTimeout(wake);
    if (!regions.length) return;                 // no paint to move (reduced motion): nothing to wake for
    if (ms === undefined) {
      let next = Infinity;
      for (const R of regions) if (R.vis && R.spawn) for (const d of R.due) next = Math.min(next, d);
      ms = clamp(next - performance.now(), 50, 1500);
    }
    wake = setTimeout(() => { if (!raf) raf = requestAnimationFrame(frame); }, ms);
  }
  function go() { clearTimeout(wake); if (!raf && gl) raf = requestAnimationFrame(frame); }

  // ------------------------------------------------------------------ layout
  // The wall's gradient (#bgwall), so the paint on the wall is darkened as the art under it is.
  function readDim(wall) {
    const m = /linear-gradient\((?:[^,]*deg,\s*)?rgba?\(([^)]*)\)[^,]*,\s*rgba?\(([^)]*)\)/.exec(getComputedStyle(wall).backgroundImage || "");
    if (!m) return;
    const a = m[1].split(",").map(parseFloat), b = m[2].split(",").map(parseFloat);
    tint = [a[0], a[1], a[2]]; dimA = [a.length > 3 ? a[3] : 1, b.length > 3 ? b[3] : 1];
  }
  function place() {
    const wall = document.getElementById("bgwall");
    if (!wall || !layer || !meta) return;
    const W = wall.clientWidth, H = wall.clientHeight;
    if (!W || !H) return;
    readDim(wall);
    const mode = getComputedStyle(document.documentElement).getPropertyValue("--wall-scale").trim() || "contain";
    const s = (mode === "cover" ? Math.max : Math.min)(W / ART[0], H / ART[1]);
    const w = ART[0] * s, h = ART[1] * s, left = (W - w) / 2, top = (H - h) / 2;
    Object.assign(layer.style, { left: left + "px", top: top + "px", width: w + "px", height: h + "px" });
    const dpr = Math.min(devicePixelRatio || 1, 2);
    const floorBg = top + FLOOR * h;            // the pavement line in #bgwall's box
    // the tag's box as laid out (its wander, hop and pop are on top, and carry the layer with it)
    let tag = null;
    if (tagLayer && tagLayer.offsetWidth) {
      const tw = tagLayer.offsetWidth, th = tagLayer.offsetHeight;
      tag = { left: tagLayer.offsetLeft - tw / 2, top: tagLayer.offsetTop - th / 2, w: tw, h: th };
      const im = document.getElementById("walltag");
      // the fresh paint a touch more solid than the dry tag it runs out of
      tagLayer.style.opacity = String(Math.min(1, (im ? parseFloat(getComputedStyle(im).opacity) || 1 : 1) + .15));
      placedTag = [tag.left, tag.top, tw, th].map(Math.round).join();
    }
    for (const R of regions) {
      let sc, ox, oy, size;
      if (R.kind === "wall") { sc = s; R.unit = 1; R.floor = FLOOR * ART[1]; size = ART; }
      else {
        if (!tag) { R.vis = false; R.cv.width = R.cv.height = 1; continue; }
        sc = tag.w / TAG[0]; R.unit = (tag.w / TAG[0]) > 0 ? s / sc : 1;   // tag px per art px
        R.floor = (floorBg - tag.top) / sc; size = TAG;
      }
      extent(R);
      R.k = Math.min(sc * dpr, 2048 / Math.max(1, R.y1 - R.y0), 2048 / Math.max(1, R.x1 - R.x0));
      // where its runs start, and whether a run is big enough here to be seen (5 device px across)
      const tw = Math.min(...R.tips.map(t => t.w));
      R.on = tw * R.k >= 5;
      R.anchor = R.box ? [R.box[0], R.box[1], R.box[0] + R.box[2], Math.max(R.box[1] + R.box[3], ...R.tips.map(t => t.y + t.w * 2))]
        : [R.tips[0].x - R.tips[0].w * 2, R.tips[0].y - R.tips[0].w, R.tips[0].x + R.tips[0].w * 2, R.tips[0].y + R.tips[0].w * 6];
      const pc = (v, of) => (v / of * 100).toFixed(4) + "%";
      Object.assign(R.cv.style, { left: pc(R.x0, size[0]), top: pc(R.y0, size[1]), width: pc(R.x1 - R.x0, size[0]), height: pc(R.y1 - R.y0, size[1]) });
      // the wall's gradient runs down #bgwall's own box: its strength at this canvas's top and bottom
      R.dim = R.kind === "wall" ? [R.y0, R.y1].map(y => dimA[0] + (dimA[1] - dimA[0]) * clamp((top + y * s) / H, 0, 1)) : [0, 0];
      if (R.alloc) { R.alloc = false; R.drips.length = R.drops.length = R.splats.length = 0; R.swell = 0; }
      R.ctx.clearRect(0, 0, R.cv.width, R.cv.height);
      R.vis = R.spawn = R.under = false; R.prev = null;
    }
    lay = { s, left, top };
    // the sign's light on the wall, from where the tag hangs at rest (#walltag's own box: its wander,
    // hop and pop ride on top and leave the light where it is)
    const wt = document.getElementById("walltag");
    if (lit && wt && wt.offsetWidth) {
      const tw = wt.offsetWidth, th = wt.offsetHeight;
      const geo = { W, H, art: [left, top, w, h], tag: { left: wt.offsetLeft - tw / 2, top: wt.offsetTop - th / 2, w: tw, h: th } };
      // once per frame at most (a window dragged to a new size asks every few ms)
      if (!lit.geo || !lit.rect) bake(geo);
      else if (!lit.soon) { lit.soon = true; lit.geo = geo; requestAnimationFrame(() => { lit.soon = false; bake(lit.geo); }); }
      else lit.geo = geo;
    }
    mapLit();
    checked = 0; aimed = 0;
    go();
  }
  // each pool's place in the wall's light: region (art) px -> the light's uv (its bottom row first)
  let lay = null;
  function mapLit() {
    for (const R of regions) {
      R.litMap = null;
      if (R.kind !== "wall" || !lit || !lit.rect || !lay) continue;
      const [x0, y0, lw, lh] = lit.rect, { s, left, top } = lay;
      R.litMap = new Float32Array([s / lw, -s / lh, (left - x0) / lw, 1 - (top - y0) / lh]);
    }
  }
  // the phone layout moves the tag when the figures are placed (index.html placeScenery): follow it
  function replaceIfMoved() {
    if (!tagLayer || !tagLayer.offsetWidth) return;
    const tw = tagLayer.offsetWidth, th = tagLayer.offsetHeight;
    const key = [tagLayer.offsetLeft - tw / 2, tagLayer.offsetTop - th / 2, tw, th].map(Math.round).join();
    if (key !== placedTag) place();
  }

  // the tube in its stretches (#tagglow > i.seg, each placed in the tag's box), shown instead of the
  // whole tube once all their pictures are in
  function tubeStretches() {
    const g = document.getElementById("tagglow");
    if (!g || !meta.tube || g.querySelector(":scope > i.seg")) return;
    const sheen = g.querySelector(":scope > .sheen");
    let waiting = meta.tube.segs.length;
    meta.tube.segs.forEach((s, k) => {
      const el = document.createElement("i"), src = `assets/wallfx/tube_${k}.webp`, [x, y, w, h] = s.box;
      el.className = "seg";
      Object.assign(el.style, { left: (x * 100).toFixed(3) + "%", top: (y * 100).toFixed(3) + "%", width: (w * 100).toFixed(3) + "%", height: (h * 100).toFixed(3) + "%", backgroundImage: `url("${src}")` });
      g.insertBefore(el, sheen);
      const im = new Image();
      im.onload = im.onerror = () => { if (--waiting === 0) g.classList.add("segs"); };
      im.src = src;
    });
  }

  async function start() {
    if (started) return;
    started = true;
    layer = document.getElementById("wallpaint");
    const bg = document.getElementById("bgwall");
    if (!layer || !bg || !(await loadMeta())) return;
    if (meta.art) ART = meta.art;
    if (meta.floor) FLOOR = meta.floor;
    if (meta.tag && meta.tag.size) TAG = meta.tag.size;
    tubeStretches();
    let ok = false;
    try { ok = setup(); } catch (e) { gl = null; console.warn("wall paint:", e.message); }
    if (ok) wallLight(bg);                       // no WebGL: the old spill of light (#tagspill) stays
    flickerStart();
    if (ok && !REDUCED) {                        // reduced motion: the art's own paint, still
      regions = meta.blobs.map((b, i) => makeRegion("wall", b, i));
      for (const R of regions) layer.appendChild(R.cv);
      if (tagLayer && meta.tag) for (const [i, t] of meta.tag.tips.entries()) { const R = makeRegion("tag", t, i); regions.push(R); tagLayer.appendChild(R.cv); }
      // the tag's layer must ride the tag's wander: index.html hands the wander to every .tagfx it
      // found when it started; if this layer came too late for that, it joins at the next stretch
      const wt = document.getElementById("walltag");
      if (wt && tagLayer && wt._followers && !wt._followers.includes(tagLayer)) wt._followers.push(tagLayer);
    }
    place();
    aimLight();
    addEventListener("resize", place);
    if (window.ResizeObserver) new ResizeObserver(place).observe(bg);
    document.addEventListener("visibilitychange", () => { if (!document.hidden) go(); });
  }
  // every run somewhere in its life at once (screenshots, tests)
  function kick() {
    const now = performance.now();
    for (const R of regions) R.due = R.due.map(d => d === Infinity ? d : now + rnd(0, 300));
    checked = 0; go();
  }
  loadMeta();   // the tube is read once, for the paint here and for the characters
  window.WallFX = { start, place, regions: () => regions, light, neon, surge, kick, stats: () => Object.assign({}, stats),
                    wallLevel, _event: forceEvent, _rate: setRate,
                    // tests: hold the paint still (_freeze), or one run posed at an age (s, or "phase:fraction"),
                    // the paint held there; seed makes the same run every time
                    _freeze: f => { frozen = !!f; go(); },
                    _pose: (ri, tj, age, seed = 7) => {
                      const R = regions[ri]; if (!R || !R.tips[tj]) return null;
                      const keep = Math.random; let q = seed; Math.random = () => (q = (q * 16807) % 2147483647) / 2147483647;
                      R.drips.length = R.drops.length = R.splats.length = 0;
                      const d = newDrip(R, R.tips[tj]); Math.random = keep;
                      if (typeof age === "string") { const [ph, f] = age.split(":"); age = d.at[ph] + d.T[ph] * +f; }
                      d.t = age; d.tx = d.tip.x; d.ty = d.tip.y; d.dropped = +(age >= d.at.recoil); d.lastDone = +(age >= d.at.last + d.T.last);
                      R.drips.push(d); R.swell = dripState(d).swell; frozen = true; go();
                      return { r0: d.r0, len: d.len, at: d.at, T: d.T, end: d.end };
                    },
                    _state: (ri, i = 0) => { const R = regions[ri], d = R && R.drips[i]; return d ? Object.assign({ t: d.t }, dripState(d)) : null; },
                    // tests: the held paint moved on by sec, 30 steps a second, and drawn (a film frame by frame)
                    _step: sec => {
                      const n = Math.max(1, Math.round(sec * 30)), now = performance.now();
                      for (let i = 0; i < n; i++) for (const R of regions) if (R.vis) step(R, 1 / 30, now);
                      for (const R of regions) if (R.vis && (active(R) || R.prev)) draw(R, now);
                      return regions.reduce((c, R) => c + R.drips.length + R.drops.length + R.splats.length, 0);
                    }, _clock: () => fl && { now: vnow(), rate: fl.rate, seed: fl.seed, win: fl.win && [fl.win.t0, fl.win.t1] } };
})();
