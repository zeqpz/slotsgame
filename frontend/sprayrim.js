// Live spray-paint rims round everything with the sprayed outline: the board, the HUD bar
// and its buttons, the spin hexagon, the bet steppers, the bonus panel, the intro plates, the
// rules panel, the autoplay picker, the win popup, the volume tubes. Each art ships without its
// outline (assets/rim/<art>.webp) and with its outline's shape as a distance field
// (assets/rim/<art>_sdf.png, tools/sprayrim/make_rims.py); the outline is drawn live over it:
// sharp at any size, its rough edges boiling like a redrawn cartoon line, spray-paint flames
// licking up off it in flat cartoon bands with drops of overspray riding them, over a soft glow.
// The colours are the wall tag's (art/STYLE.md): a violet sprayed band between dark keylines,
// neon-lime fire (a dark lime edge, lime, a hot yellow-lime band, a near-white core) and a lime
// glow, violet drops. Chosen 2026-10-27 over a lime band with violet fire (too loud against the
// lime symbols) and violet throughout (no lime left to tie it to the tag's neon).
//
// One WebGL context draws them all: each rim is rendered in turn and copied into a plain 2D
// canvas that sits inside its element, so it moves, scales, tilts and stacks with the element.
// Only what is on screen is drawn, at most 30 times a second. No WebGL: the page keeps the art's
// own painted outlines (the html.sprayfx class is what swaps them out).
//
// A rim with `flare` can be stoked like blowing on a fire (SprayFX.stoke): its flames whoosh up
// - taller by up to `flare` of their height, brighter, quicker - and settle back. Its canvas is
// sized for the tallest of them from the start, so a stoke never reallocates anything.
//
//   SprayFX.start({ rules: [...], boxes: [...] })
//   SprayFX.stoke(el, { peak, hold })
(function () {
  "use strict";
  const VS = "attribute vec2 a; void main(){ gl_Position = vec4(a, 0., 1.); }";
  const FS = `
precision highp float;
uniform vec2 uRes;        // canvas device px
uniform float uPx;        // device px per css px
uniform vec4 uBox;        // the element's box in canvas css px, y down: x0, y0, x1, y1
uniform float uMode;      // 0 = rounded box, 1 = distance field
uniform vec3 uRound;      // box mode: inset, corner radius, band (css px)
uniform vec2 uSrc;        // field mode: the art's size, source px
uniform vec3 uField;      // pad (src px), step (src px per level), texel (src px)
uniform float uFit;       // 0 = linear (stretch / contain), 1 = nine-slice
uniform vec4 uLin;        // linear: css px per src px x, y; offset x, y (css)
uniform vec4 uMapX, uMapY;// nine-slice per axis: border b0, b1 (css), slice s0, s1 (src px)
uniform float uBandSrc;   // field mode: the outline's width, src px
uniform float uL, uFlame, uTime, uBoil, uSeed, uGlow;
uniform float uBlow;      // a stoke: the flames this much taller (0 = at rest), brighter and wider-glowing with it
uniform vec3 uShadow;     // the drop shadow under the outline: offset down, blur (css px), alpha
uniform sampler2D uSdf;
uniform vec3 uRimKey, uRimDeep, uRimMid, uRimFleck;           // the sprayed band: keylines, paint, flecks
uniform vec3 uFireKey, uFireBody, uFireLight, uFireCore;      // the flames: outline, body, hot band, core
uniform vec3 uGlowC, uDropC;                                  // the glow off the edge, the overspray drops

float h21(vec2 p) { p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
float vn(vec2 p) {
  vec2 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f);
  return mix(mix(h21(i), h21(i + vec2(1., 0.)), f.x), mix(h21(i + vec2(0., 1.)), h21(i + vec2(1., 1.)), f.x), f.y);
}
float fbm(vec2 p) { float a = .5, s = 0.; for (int i = 0; i < 4; i++) { s += a * vn(p); p = p * 2.03 + vec2(17.1, 9.2); a *= .5; } return s; }
// Noise carried along dir without ever drifting far: two copies of the pattern each slide one
// cycle's length and jump back, crossfaded so a jump is never seen (the flow-map trick). Moving
// the pattern by dir * time directly let any wobble in dir grow with the clock and smear the
// flames into streaks across the outline.
float flow(vec2 q, vec2 dir, float T, bool rich) {
  float ph = fract(T), ph2 = fract(T + .5), w = abs(2. * ph - 1.);
  vec2 o1 = mod(floor(T), 61.) * vec2(.37, .71), o2 = mod(floor(T + .5), 61.) * vec2(.53, .29) + 7.3;
  float a = rich ? fbm(q - dir * ph + o1) : vn(q - dir * ph + o1);
  float b = rich ? fbm(q - dir * ph2 + o2) : vn(q - dir * ph2 + o2);
  float v = ((a - .5) * (1. - w) + (b - .5) * w) / sqrt((1. - w) * (1. - w) + w * w);   // keeps the contrast through the fade
  return .5 + v;
}
vec2 slice(float x, float W, float Ws, vec4 m) {   // css -> src, and src px per css px
  if (m.x > 0. && x < m.x) return vec2(x * m.z / m.x, m.z / m.x);
  if (m.y > 0. && x > W - m.y) return vec2(Ws - (W - x) * m.w / m.y, m.w / m.y);
  float k = (Ws - m.z - m.w) / max(W - m.x - m.y, 1e-3);
  return vec2(m.z + (x - m.x) * k, k);
}
float field(vec2 uv) {
  vec2 t = (uv + uField.x) / (uSrc + 2. * uField.x);
  return (texture2D(uSdf, t).r * 255. - 128.) * uField.y;
}
float roundBox(vec2 lp, vec2 WH) {   // to the rim's OUTER edge, css px
  vec2 c = WH * .5, h = c - uRound.x;
  vec2 q = abs(lp - c) - h + uRound.y;
  return length(max(q, 0.)) + min(max(q.x, q.y), 0.) - uRound.y;
}

void main() {
  vec2 p = vec2(gl_FragCoord.x, uRes.y - gl_FragCoord.y) / uPx;   // canvas css px, y down
  vec2 lp = p - uBox.xy, WH = uBox.zw - uBox.xy;
  float aa = .7 / uPx;
  float reach = max(uFlame * (1. + uBlow) * 2.1, uShadow.x + uShadow.y) + 6. * aa;
  float D, band, beyond; vec2 n;   // beyond: how far out this is, as the cut-off below measures it
  if (uMode < .5) {
    float o = roundBox(lp, WH);
    beyond = o;
    if (o < -uRound.z - 6. * aa - .5 * uL || o > reach) { gl_FragColor = vec4(0.); return; }
    vec2 e = vec2(.75, 0.);
    vec2 g = vec2(roundBox(lp + e.xy, WH) - roundBox(lp - e.xy, WH), roundBox(lp + e.yx, WH) - roundBox(lp - e.yx, WH));
    n = g / max(length(g), 1e-4);
    band = uRound.z; D = o + band;
  } else {
    vec2 ux = uFit > .5 ? slice(lp.x, WH.x, uSrc.x, uMapX) : vec2((lp.x - uLin.z) / uLin.x, 1. / uLin.x);
    vec2 uy = uFit > .5 ? slice(lp.y, WH.y, uSrc.y, uMapY) : vec2((lp.y - uLin.w) / uLin.y, 1. / uLin.y);
    vec2 uv = vec2(ux.x, uy.x), J = vec2(ux.y, uy.y);              // src px, src px per css px
    float s = field(uv), jm = .5 * (J.x + J.y);
    beyond = (s - uBandSrc) / jm;
    if (s / jm < -6. * aa - .5 * uL || beyond > reach) { gl_FragColor = vec4(0.); return; }
    float h = uField.z * 2.;                                        // two texels: a steadier slope
    vec2 g = vec2(field(uv + vec2(h, 0.)) - field(uv - vec2(h, 0.)), field(uv + vec2(0., h)) - field(uv - vec2(0., h))) / (2. * h);
    vec2 gc = g * J;                                               // the field's slope per css px
    float gm = max(length(gc), 1e-3);
    n = gc / gm; D = s / gm; band = uBandSrc / gm;
  }
  // every noise is at least a few device px across, or it turns to static
  float fmin = 2.6 / uPx;
  vec2 bo = vec2(fract(uBoil * .618) * 97., fract(uBoil * .382) * 61.);
  float boil = (vn(p / max(.3 * uL, fmin) + bo) - .5) * .16 * uL;
  float dOut = D - band + (fbm(p / max(.95 * uL, 2. * fmin) + uSeed) - .5) * .36 * uL + boil;
  float dIn = D + (fbm(p / max(.7 * uL, 2. * fmin) + uSeed + 5.3) - .5) * .3 * uL + boil * .8;

  // the drop shadow (drawn here, under the outline: a CSS drop-shadow on the element would put
  // this canvas through Chromium's filter path, which misplaces the whole layer)
  float ds = dOut - uShadow.x * n.y;
  float sh = uShadow.z * (1. - smoothstep(0., max(uShadow.y, 1e-3), ds)) * smoothstep(-aa, aa, dOut);
  vec4 col = vec4(0., 0., 0., sh);
  // glow off the outer edge, breathing
  // (outside only: inside, it stopped in a hard straight line where the shader stops drawing -
  // a boxy band of blue round the inside of every outline)
  float glow = uGlow * (1. + 1.6 * uBlow) * exp(-max(dOut, 0.) / (uFlame * .55 * (1. + .7 * uBlow)))
             * (.2 + .08 * sin(uTime * 2.3 + p.x * .013 + p.y * .011)) * smoothstep(-2. * aa, 2. * aa, dOut);
  col = vec4(uGlowC * glow, glow) + col * (1. - glow);

  // flames: tongues that climb out of the rim (outward, pulled upward)
  vec2 dir = normalize(n + vec2(0., -.85));
  float fl = max(1.15 * uFlame, 5. * fmin);                           // tongues about as wide as they are tall
  float lick = flow(p / fl, dir, uTime * 1.4, true);
  float lick2 = flow(p / max(.45 * uFlame, 3.5 * fmin), dir, uTime * 2.2 + .3, false);
  float height = uFlame * (1. + uBlow) * (.6 + .9 * smoothstep(.3, .75, fbm(p / max(3. * uFlame, 10. * fmin) + vec2(uTime * .27, uTime * .19) + uSeed)));
  // a stoke also fills the tongues out, so more of each burns cyan and white-hot
  float f = lick * 1.38 + lick2 * .14 - max(dOut, 0.) / height + .09 * uBlow;
#ifdef GL_OES_standard_derivatives
  float fw = max(fwidth(f) * .7, .006);
#else
  float fw = .03;
#endif
  float b0 = smoothstep(.42 - fw, .42 + fw, f);   // the dark outline round each tongue
  float b1 = smoothstep(.49 - fw, .49 + fw, f);   // the body
  float b2 = smoothstep(.61 - fw, .61 + fw, f);   // the hot band
  float b3 = smoothstep(.74 - fw, .74 + fw, f);   // white-hot core
  float outside = smoothstep(-2. * aa, 2. * aa, dOut);
  vec3 fc = mix(uFireKey, uFireBody, b1); fc = mix(fc, uFireLight, b2); fc = mix(fc, uFireCore, b3);
  float fa = b0 * outside;
  // overspray: round drops that ride up off the tongues' tips (no flicker: they drift)
  float C = max(1.8 * uL, 3.6 * fmin);
  vec2 dp = p / C + vec2(0., uTime * .55);
  vec2 cell = floor(dp), fc2 = fract(dp) - .5;
  vec2 off = (vec2(h21(cell * 1.7 + 3.1), h21(cell * 2.3 + 7.7)) - .5) * .5;
  float rr = mix(.1, .2, h21(cell * 3.1 + uSeed));
  float dd = (length(fc2 - off) - rr) * C;                                // css px
  float drop = step(.8, h21(cell + uSeed)) * smoothstep(aa, -aa, dd);
  drop *= smoothstep(.1, .3, f) * (1. - b0) * outside * exp(-max(dOut, 0.) / (uFlame * 1.3 * (1. + uBlow)));
  fc = mix(fc, uDropC, drop); fa = max(fa, drop);
  // the tongues and drops are gone before the cut-off, whatever fwidth says there: at the cut, half
  // of each 2x2 pixel block has stopped drawing, its derivatives are garbage, and the bands lit a
  // 1 px line all round the rim (seen once a stoke's headroom put the cut-off on the canvas)
  fa *= 1. - smoothstep(.82 * reach, .95 * reach, beyond);
  col = vec4(fc * fa, fa) + col * (1. - fa);

  // the rim: sprayed paint between a dark keyline on each edge
  float ra = smoothstep(aa, -aa, dOut) * smoothstep(-aa, aa, dIn);
  if (ra > 0.) {
    vec3 c = mix(uRimDeep, uRimMid, smoothstep(.25, .8, fbm(p / max(.6 * uL, 2. * fmin) + uSeed * 2.)));
    c = mix(c, uRimFleck, smoothstep(.6, .67, fbm(p / max(.32 * uL, 2. * fmin) + 3. + uSeed)));
    float kw = max(.1 * uL, 1.3 / uPx);
    float k = 1. - smoothstep(kw - aa, kw + aa, min(-dOut, dIn));
    float S2 = max(.5 * uL, 2.4 * fmin);
    vec2 sc = floor(p / S2), sf = fract(p / S2) - .5;
    float sp = step(.92, h21(sc + uSeed)) * smoothstep(aa, -aa, (length(sf) - .22) * S2);   // black specks
    c = mix(c, uRimKey, max(k, sp));
    c *= .94 + .12 * h21(floor(gl_FragCoord.xy * .5));                                      // spray grain (still)
    col = vec4(c * ra, ra) + col * (1. - ra);
  }
  gl_FragColor = col;
}`;
  // The colours (art/STYLE.md): the band is sprayed in one paint, the fire burns in another. A QA
  // page can try another set by naming it (or giving the colours) in window.SPRAYRIM_COLORS before
  // this script runs.
  const THEMES = {
    // violet band, neon-lime fire and glow
    a: { rimKey: [.11, .024, .21], rimDeep: [.424, .141, .706], rimMid: [.706, .329, .894], rimFleck: [.894, .706, .988],
         fireKey: [.10, .20, .024], fireBody: [.424, .988, .329], fireLight: [.894, .988, .518], fireCore: [.965, 1.0, .90],
         glow: [.424, .988, .329], drop: [.706, .329, .894] },
    // lime band, violet fire and glow
    b: { rimKey: [.078, .157, .016], rimDeep: [.33, .60, .06], rimMid: [.612, .894, .141], rimFleck: [.894, .988, .518],
         fireKey: [.165, .031, .314], fireBody: [.612, .235, .863], fireLight: [.894, .706, .988], fireCore: [1.0, .957, 1.0],
         glow: [.706, .329, .894], drop: [.612, .894, .141] },
    // violet throughout, the fire's hot band in the pink tint
    c: { rimKey: [.11, .024, .21], rimDeep: [.424, .141, .706], rimMid: [.706, .329, .894], rimFleck: [.894, .706, .988],
         fireKey: [.165, .031, .314], fireBody: [.612, .235, .863], fireLight: [.894, .518, .80], fireCore: [1.0, .94, .98],
         glow: [.706, .329, .894], drop: [.424, .141, .706] },
  };
  const pick = window.SPRAYRIM_COLORS;
  const COLORS = Object.assign({}, THEMES.a, typeof pick === "string" ? THEMES[pick] : pick);
  const MAX_SIDE = 2048;

  let gl = null, glc = null, U = null, META = null, ok = false, alive = true;
  const TEX = {};
  const targets = [];

  function setup() {
    // At its largest from the start: a WebGL canvas that grows mid-game is reallocated, and the
    // reallocation waits for the GPU to finish everything queued (a round's opening pop grew it
    // and stalled the page 50-120 ms, twice, as the reveal began). Every rim fits MAX_SIDE.
    glc = document.createElement("canvas"); glc.width = MAX_SIDE; glc.height = MAX_SIDE;
    gl = glc.getContext("webgl", { premultipliedAlpha: true, alpha: true, antialias: false, preserveDrawingBuffer: true });
    if (!gl) return false;
    const deriv = !!gl.getExtension("OES_standard_derivatives");
    const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)); return s; };
    const prog = gl.createProgram();
    gl.attachShader(prog, sh(gl.VERTEX_SHADER, VS));
    gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, (deriv ? "#extension GL_OES_standard_derivatives : enable\n" : "") + FS));
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog));
    gl.useProgram(prog);
    const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(prog, "a"); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    U = {};
    const CU = { uRimKey: "rimKey", uRimDeep: "rimDeep", uRimMid: "rimMid", uRimFleck: "rimFleck", uFireKey: "fireKey",
                 uFireBody: "fireBody", uFireLight: "fireLight", uFireCore: "fireCore", uGlowC: "glow", uDropC: "drop" };
    for (const n of ["uRes", "uPx", "uBox", "uMode", "uRound", "uSrc", "uField", "uFit", "uLin", "uMapX", "uMapY", "uBandSrc", "uL", "uFlame", "uTime", "uBoil", "uSeed", "uGlow", "uBlow", "uShadow", "uSdf", ...Object.keys(CU)]) U[n] = gl.getUniformLocation(prog, n);
    for (const [u, k] of Object.entries(CU)) gl.uniform3fv(U[u], COLORS[k]);   // set once: every rim shares them
    gl.uniform1i(U.uSdf, 0);
    gl.disable(gl.BLEND);
    glc.addEventListener("webglcontextlost", e => { e.preventDefault(); stopAll(); });
    return true;
  }

  function loadField(name, base) {
    return new Promise(res => {
      const im = new Image();
      im.onload = () => {
        const t = gl.createTexture();
        gl.bindTexture(gl.TEXTURE_2D, t);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.LUMINANCE, gl.LUMINANCE, gl.UNSIGNED_BYTE, im);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
        TEX[name] = { t, w: im.naturalWidth, h: im.naturalHeight };
        res(true);
      };
      im.onerror = () => res(false);
      im.src = `${base}/${name}_sdf.png`;
    });
  }

  // border-image widths as drawn (css px), from the computed style: 1-4 values, px or multiples of the border
  function borderImageWidths(el) {
    const cs = getComputedStyle(el), v = (cs.borderImageWidth || "1").trim().split(/\s+/);
    const bw = [cs.borderTopWidth, cs.borderRightWidth, cs.borderBottomWidth, cs.borderLeftWidth].map(parseFloat);
    const four = [v[0], v[1] ?? v[0], v[2] ?? v[0], v[3] ?? v[1] ?? v[0]];
    return four.map((s, i) => s.endsWith("px") ? parseFloat(s) : s.endsWith("%") ? 0 : (parseFloat(s) || 0) * bw[i]);
  }

  function attach(el, o) {
    if (el.__rim) return;
    const host = o.host ? o.host(el) : el;
    if (!host) return;
    if (getComputedStyle(host).position === "static") host.style.position = "relative";
    const cv = document.createElement("canvas");
    cv.className = "sprayrim" + (o.cls ? " " + o.cls : "");
    cv.setAttribute("aria-hidden", "true");
    Object.assign(cv.style, { position: "absolute", pointerEvents: "none", zIndex: String(o.z ?? -1) });
    host.appendChild(cv);
    const t = { el, host, o, cv, ctx: cv.getContext("2d"), seed: Math.random() * 50, key: "" };
    el.__rim = t;
    targets.push(t);
  }

  function scan(rules) {
    for (const r of rules) {
      for (const el of document.querySelectorAll(r.sel)) attach(el, r);
    }
    for (let i = targets.length - 1; i >= 0; i--) {
      const t = targets[i];
      if (!t.el.isConnected) { t.cv.remove(); targets.splice(i, 1); }
    }
  }

  function geometry(t) {
    const { el, host, o } = t;
    const W = el.offsetWidth, H = el.offsetHeight;
    if (!W || !H) return null;
    const r = el.getBoundingClientRect();
    if (!r.width || r.right < -200 || r.bottom < -200 || r.left > innerWidth + 200 || r.top > innerHeight + 200) return null;
    if (o.active && !o.active(el)) return null;
    const shown = r.width / W;                                    // fit-to-screen and the element's own transforms
    let px = Math.min((window.devicePixelRatio || 1) * shown, 3);
    const g = { W, H, px };
    if (o.box) {                                                   // a rounded box
      const mn = Math.min(W, H) + 2 * (o.grow || 0);
      g.band = mn * o.band; g.inset = mn * o.inset - (o.grow || 0); g.radius = mn * o.radius;
      g.L = g.band;
    } else {
      const m = META && META[o.art];
      if (!m || !TEX[o.art]) return null;
      g.m = m;
      if (o.fit === "slice") {
        const [st, sr, sb, sl] = o.slice;                          // fractions of the art (top/bottom of its height, sides of its width)
        if (!t.bw || performance.now() - t.bwAt > 500) { t.bw = borderImageWidths(el); t.bwAt = performance.now(); }
        const [bt, br, bb, bl] = t.bw;
        g.mapX = [bl, br, sl * m.w, sr * m.w]; g.mapY = [bt, bb, st * m.h, sb * m.h];
        const jx = bl > 0 ? sl * m.w / bl : m.w / W, jy = bt > 0 ? st * m.h / bt : m.h / H;
        g.J = (jx + jy) / 2;
      } else {
        let kx = W / m.w, ky = H / m.h, ox = 0, oy = 0;
        if (o.fit === "contain") {
          const k = Math.min(kx, ky); kx = ky = k;
          const pos = o.pos || [.5, .5];
          ox = (W - m.w * k) * pos[0]; oy = (H - m.h * k) * pos[1];
        }
        g.lin = [kx, ky, ox, oy]; g.J = 2 / (kx + ky);
      }
      g.L = m.band / g.J;
    }
    g.flame = Math.max((o.flameK || 1.6) * g.L, o.flameMin || 6);
    if (o.flameMax) g.flame = Math.min(g.flame, o.flameMax);
    const sh = o.shadow || [0, 0, 0];
    g.shadow = sh;
    g.margin = Math.ceil(Math.max(g.flame * 2.15 + 8, sh[0] + sh[1] + 6));
    const room = o.box ? Infinity : (g.m.pad - 4) / g.J;          // the field only reaches so far past the art
    if (g.margin > room) { g.margin = Math.floor(room); g.flame = Math.max(2, (g.margin - 8) / 2.15); }
    // a rim that can be stoked has room for its tallest flames from the start, as far as the field
    // reaches; g.flare is how much taller they may grow here
    g.flare = 0;
    if (o.flare && !still) {
      const m = Math.min(Math.ceil(g.flame * (1 + o.flare) * 2.15 + 8), Math.floor(room));
      if (m > g.margin) g.margin = m;
      g.flare = Math.max(0, Math.min(o.flare, (g.margin - 8) / 2.15 / g.flame - 1));
    }
    const cw = W + 2 * g.margin, ch = H + 2 * g.margin;
    // A pop, a bounce or a lean-in scales the element for a moment: keep the density the canvas
    // already has through it rather than reallocating the canvas on every frame of the move (the
    // element's own transform scales the canvas with it). A real change - a resize, a new fit -
    // is more than this and is followed.
    if (t.px0 && Math.abs(px / t.px0 - 1) < .2) px = t.px0; else t.px0 = px;
    px = Math.min(px, MAX_SIDE / cw, MAX_SIDE / ch);
    g.px = px; g.cw = cw; g.ch = ch;
    g.dw = Math.max(1, Math.round(cw * px)); g.dh = Math.max(1, Math.round(ch * px));
    // where the element sits in its host (when the canvas lives in a parent)
    if (host !== el) {
      const hr = host.getBoundingClientRect(), hs = hr.width / (host.offsetWidth || 1) || 1;
      g.ox = (r.left - hr.left) / hs - host.clientLeft; g.oy = (r.top - hr.top) / hs - host.clientTop;
    } else { g.ox = -el.clientLeft; g.oy = -el.clientTop; }   // an absolute child sits inside the border: the box starts that far out
    return g;
  }

  function render(t, g, now) {
    const { cv } = t;
    const key = `${g.dw}x${g.dh}|${g.margin}|${Math.round(g.ox)}|${Math.round(g.oy)}`;
    if (key !== t.key) {
      t.key = key;
      if (cv.width !== g.dw || cv.height !== g.dh) { cv.width = g.dw; cv.height = g.dh; }
      Object.assign(cv.style, { left: (g.ox - g.margin) + "px", top: (g.oy - g.margin) + "px", width: g.cw + "px", height: g.ch + "px" });
    }
    if (glc.width < g.dw || glc.height < g.dh) { glc.width = Math.max(glc.width, g.dw); glc.height = Math.max(glc.height, g.dh); }
    gl.viewport(0, 0, g.dw, g.dh);
    gl.uniform2f(U.uRes, g.dw, g.dh); gl.uniform1f(U.uPx, g.dw / g.cw);
    gl.uniform4f(U.uBox, g.margin, g.margin, g.margin + g.W, g.margin + g.H);
    gl.uniform3f(U.uShadow, g.shadow[0], g.shadow[1], g.shadow[2]);
    gl.uniform1f(U.uL, g.L); gl.uniform1f(U.uFlame, g.flame); gl.uniform1f(U.uSeed, t.seed); gl.uniform1f(U.uGlow, t.o.glow ?? 1);
    const tt = now / 1000, lvl = g.flare ? stokeLevel(t.el, now) : 0;
    // the flames' own clock, which runs quicker while they are stoked
    t.clock = (t.clock ?? tt) + (t.at !== undefined ? Math.min(.1, tt - t.at) : 0) * (1 + 1.5 * lvl); t.at = tt;
    gl.uniform1f(U.uTime, (t.clock + t.seed) % 900); gl.uniform1f(U.uBoil, Math.floor(tt * 8) % 7919 + 1);
    gl.uniform1f(U.uBlow, lvl * g.flare);
    if (t.o.box) {
      gl.uniform1f(U.uMode, 0); gl.uniform3f(U.uRound, g.inset, g.radius, g.band);
    } else {
      const m = g.m, T = TEX[t.o.art];
      gl.uniform1f(U.uMode, 1);
      gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, T.t);
      gl.uniform2f(U.uSrc, m.w, m.h); gl.uniform3f(U.uField, m.pad, m.step, (m.w + 2 * m.pad) / T.w);
      gl.uniform1f(U.uBandSrc, m.band);
      if (g.mapX) { gl.uniform1f(U.uFit, 1); gl.uniform4fv(U.uMapX, g.mapX); gl.uniform4fv(U.uMapY, g.mapY); }
      else { gl.uniform1f(U.uFit, 0); gl.uniform4fv(U.uLin, g.lin); }
    }
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    t.ctx.globalCompositeOperation = "copy";
    t.ctx.drawImage(glc, 0, glc.height - g.dh, g.dw, g.dh, 0, 0, g.dw, g.dh);
  }

  let raf = 0, lastScan = 0, rules = [], half = 0;
  const lastHalf = [0, 0];
  const still = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  // The rims are measured and drawn just AFTER the browser has laid out and painted the frame
  // (a message posted from the animation frame runs once the frame is done), so reading the
  // elements' boxes never forces a style and layout pass of its own in the middle of a frame
  // that the round is still changing. What is drawn shows on the next frame.
  const after = new MessageChannel();
  after.port1.onmessage = draw;
  // Half the rims are drawn on one frame and the other half on another: each half keeps its own
  // clock and redraws at most 30 times a second, but no frame carries all of them at once.
  function loop(now) {
    if (!alive) return;
    raf = requestAnimationFrame(loop);
    if (document.hidden) return;
    const h = half ^ 1;
    if (now - lastHalf[h] < 1000 / 30 - 2) return;
    half = h; lastHalf[h] = now;
    after.port2.postMessage([h, now]);
  }
  function draw(e) {
    if (!alive) return;
    const [h, now] = e.data;
    if (now - lastScan > 500) { lastScan = now; scan(rules); }
    targets.forEach((t, i) => {
      if ((i & 1) !== h) return;
      const g = geometry(t);
      if (!g) { if (t.key) { t.ctx.clearRect(0, 0, t.cv.width, t.cv.height); t.key = ""; } return; }
      if (still && t.key && t.drawn) return;
      render(t, g, still ? 0 : now);
      t.drawn = true;
    });
  }

  // A breath on the fire. The flames rise fast and die back slowly, from wherever they were; a hold
  // is a gentle breath kept up underneath (a pointer resting on a plate) until it is let go.
  // The level is 0..1 of the rim's flare.
  const ATTACK = .1, DECAY = .45;   // s: up in a breath, back down over a second or so
  function envelope(s, now) {
    const a = (now - s.at) / 1000;
    if (a < 0) return s.base;
    if (a < ATTACK) { const v = a / ATTACK; return s.base + (s.peak - s.base) * (1 - (1 - v) * (1 - v)); }
    return s.peak * Math.exp(-(a - ATTACK) / DECAY);
  }
  function stokeLevel(el, now) {
    const s = el.__stoke;
    if (!s) return 0;
    s.held += (s.hold - s.held) * .18;   // once a redraw: the hold eases in and out
    return Math.max(envelope(s, now), s.held);
  }
  function stoke(el, { peak = 1, hold = 0 } = {}) {
    if (!el || still) return;
    const now = performance.now();
    const s = el.__stoke || (el.__stoke = { at: -1e9, base: 0, peak: 0, hold: 0, held: 0 });
    if (peak > 0) { s.base = Math.min(1, envelope(s, now)); s.peak = Math.max(peak, s.base); s.at = now; }
    s.hold = hold;
  }

  function stopAll() {
    alive = false; cancelAnimationFrame(raf);
    for (const t of targets) { t.cv.remove(); if (t.el) delete t.el.__rim; }
    targets.length = 0;
    document.documentElement.classList.remove("sprayfx");
  }

  async function start(opt) {
    try { if (!setup()) return false; } catch (e) { console.warn("spray rims unavailable:", e.message); return false; }
    const base = opt.base || "assets/rim";
    for (const b of opt.boxes || []) for (const el of document.querySelectorAll(b.sel)) { attach(el, b); if (b.onAttach) b.onAttach(el); }
    ok = true;
    raf = requestAnimationFrame(loop);
    try { META = await (await fetch(`${base}/rims.json`)).json(); } catch (e) { META = null; }
    if (!META || !alive) return true;
    await Promise.all(Object.keys(META).map(n => loadField(n, base)));
    if (!alive) return true;
    rules = opt.rules || [];
    document.documentElement.classList.add("sprayfx");   // the arts lose their painted outlines: the live ones take over
    scan(rules);
    return true;
  }
  window.SprayFX = { start, stop: stopAll, stoke, get ok() { return ok; }, targets };
})();
