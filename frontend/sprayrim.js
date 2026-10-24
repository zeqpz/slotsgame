// Live spray-paint rims: the board's sprayed outline and the bonus panel's blue rim, drawn every
// frame by a small WebGL shader instead of being a stretched picture. Drawn at the screen's own
// resolution, so they are sharp at any size. The rim boils the way a hand-redrawn cartoon line
// does: its rough edges wobble in small random jumps, about 8 times a second. Spray-paint flames
// lick off its outer edge and climb, each tongue drawn in flat cartoon bands (navy outline, blue,
// cyan, a white-hot core) with overspray specks round the tips, over a soft blue glow that
// breathes.
//
//   const rim = SprayRim(host, { kind: "box", grow, ... })      the board (a rounded box)
//   const rim = SprayRim(host, { kind: "sdf", sdf: url, ... })  any outline, from a distance field
//   rim.stop()
//
// Draws only while its host is on screen and the tab is visible, at most 30 times a second.
// Reduced motion: one still frame. No WebGL: returns null, and the page keeps its picture.
(function () {
  "use strict";
  const VS = "attribute vec2 a; void main(){ gl_Position = vec4(a, 0., 1.); }";
  const FS = `precision highp float;
uniform vec2 uRes;          // canvas, css px
uniform vec4 uBox;          // the shape's box in canvas css px, y up: x0, y0, x1, y1
uniform float uMode;        // 0 = rounded box, 1 = distance-field texture
uniform float uInset, uRadius, uBand, uFlame, uTime, uBoil, uPx, uSeed, uSdfScale, uOutward;
uniform sampler2D uSdf;
uniform vec3 uNavy, uDeep, uMid, uLight, uCore;

float h21(vec2 p) { p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
float vn(vec2 p) {
  vec2 i = floor(p), f = fract(p); f = f * f * (3. - 2. * f);
  return mix(mix(h21(i), h21(i + vec2(1., 0.)), f.x), mix(h21(i + vec2(0., 1.)), h21(i + vec2(1., 1.)), f.x), f.y);
}
float fbm(vec2 p) { float a = .5, s = 0.; for (int i = 0; i < 4; i++) { s += a * vn(p); p = p * 2.03 + vec2(17.1, 9.2); a *= .5; } return s; }

// signed distance (css px) to the rim's OUTER edge: negative inside
float shapeD(vec2 p) {
  if (uMode < .5) {
    vec2 c = (uBox.xy + uBox.zw) * .5, h = (uBox.zw - uBox.xy) * .5 - uInset;
    vec2 q = abs(p - c) - h + uRadius;
    return length(max(q, 0.)) + min(max(q.x, q.y), 0.) - uRadius;
  }
  vec2 sz = uBox.zw - uBox.xy;
  vec2 uv = (p - uBox.xy) / sz;
  vec2 o = max(abs(uv - .5) - .5, 0.) * sz;                     // beyond the texture: add the way out
  float s = (texture2D(uSdf, vec2(uv.x, 1. - uv.y)).r * 255. - 128.) * uSdfScale;
  return s + length(o) - uBand * uOutward;                       // the rim sits outside the plate's edge
}

void main() {
  vec2 p = gl_FragCoord.xy / uPx;
  float d0 = shapeD(p);
  if (d0 < -uBand - 8. || d0 > uFlame * 1.6 + 24.) { gl_FragColor = vec4(0.); return; }
  float aa = .8 / uPx;
  // rough edges, fixed, and a small boil that jumps to a new shape uBoil times a second
  vec2 bo = vec2(fract(uBoil * .618) * 97., fract(uBoil * .382) * 61.);
  float boil = (vn(p / 7. + bo) - .5) * 2.6 + (vn(p / 2.6 + bo * 1.7) - .5) * .9;
  float dOut = d0 + (fbm(p / 23. + uSeed) - .5) * 8. + boil;
  float dIn = d0 + uBand + (fbm(p / 17. + uSeed + 5.3) - .5) * 7. + boil * .8;    // > 0: past the inner edge, inside the band
  // outward direction (for the flames), from the field
  vec2 e = vec2(1.5, 0.);
  vec2 g = vec2(shapeD(p + e.xy) - shapeD(p - e.xy), shapeD(p + e.yx) - shapeD(p - e.yx));
  vec2 n = g / max(length(g), 1e-4);

  vec4 col = vec4(0.);
  // --- glow: a soft blue haze off the outer edge, breathing
  float dg = max(dOut, 0.);
  float glow = exp(-dg / (uFlame * .55)) * (.2 + .08 * sin(uTime * 2.3 + p.x * .013 + p.y * .011));
  col = vec4(uMid * glow, glow);

  // --- flames: tongues climbing out of the rim, moving outward and a little upward
  float tt = uTime;
  vec2 q = p / 24.;
  vec2 dir = normalize(n + vec2(0., .85));            // outward, pulled upward: fire climbs up the sides
  float lick = fbm(q * vec2(1., .8) - dir * tt * 1.7);
  float lick2 = vn(p / 9. - dir * tt * 3.4);
  // how far the tongues reach: a slow wander along the rim, so they flare up here and there
  float height = uFlame * (.55 + 1.5 * smoothstep(.3, .75, fbm(p / 90. + vec2(tt * .27, -tt * .19) + uSeed)));
  float f = lick * 1.38 + lick2 * .22 - max(dOut, 0.) / height;
  float fw = .028;
  float band0 = smoothstep(.42 - fw, .42 + fw, f);     // the navy outline round each tongue
  float band1 = smoothstep(.49 - fw, .49 + fw, f);     // blue
  float band2 = smoothstep(.61 - fw, .61 + fw, f);     // cyan
  float band3 = smoothstep(.74 - fw, .74 + fw, f);     // white-hot core
  float near = smoothstep(-2., 2., dOut);              // flames only off the outer edge
  vec3 fc = mix(uNavy, uDeep, band1); fc = mix(fc, uLight, band2); fc = mix(fc, uCore, band3);
  float fa = band0 * near;
  // overspray: specks round the tongues' tips, flickering with the boil
  vec2 cell = floor(p / 5.); vec2 inCell = fract(p / 5.) - .5;
  float r = h21(cell + bo);
  float speck = step(.9, r) * smoothstep(.36, .2, length(inCell + (vec2(h21(cell * 1.7), h21(cell * 2.3)) - .5) * .4));
  speck *= smoothstep(.2, .34, f) * (1. - band0) * near;
  fc = mix(fc, uDeep, speck * (1. - fa)); fa = max(fa, speck * .9);
  col = vec4(fc * fa, fa) + col * (1. - fa);

  // --- the rim itself: sprayed blue between a navy keyline on each edge
  float inOut = smoothstep(aa, -aa, dOut);
  float inIn = smoothstep(-aa, aa, dIn);
  float ra = inOut * inIn;
  if (ra > 0.) {
    vec3 c = mix(uDeep, uMid, smoothstep(.25, .8, fbm(p / 15. + uSeed * 2.)));
    c = mix(c, uLight, smoothstep(.6, .66, fbm(p / 8. + 3. + uSeed)));          // light sprayed blotches
    float k = 1. - smoothstep(2.4 - aa, 2.4 + aa, min(-dOut, dIn));            // keylines on both edges
    vec2 sc = floor(p / 6.); vec2 sf = fract(p / 6.) - .5;
    float sp = step(.93, h21(sc + uSeed)) * smoothstep(.3, .14, length(sf));   // black specks
    c = mix(c, uNavy, max(k, sp));
    c *= .93 + .14 * h21(floor(gl_FragCoord.xy * .5) + bo);                    // spray grain
    col = vec4(c * ra, ra) + col * (1. - ra);
  }
  gl_FragColor = col;
}`;

  const COLORS = { navy: [.02, .06, .26], deep: [.04, .24, .78], mid: [.12, .47, 1.0], light: [.5, .85, 1.0], core: [.93, .99, 1.0] };

  function SprayRim(host, opt) {
    opt = Object.assign({ kind: "box", grow: 0, margin: 70, inset: .01, band: .03, radius: .02, flame: 34, fps: 30, z: 3, seed: Math.random() * 50, outward: 1 }, opt || {});
    const cv = document.createElement("canvas");
    cv.className = "sprayrim" + (opt.className ? " " + opt.className : "");
    cv.setAttribute("aria-hidden", "true");
    const M = opt.margin;
    Object.assign(cv.style, { position: "absolute", left: (-M - opt.grow) + "px", top: (-M - opt.grow) + "px", width: `calc(100% + ${2 * (M + opt.grow)}px)`, height: `calc(100% + ${2 * (M + opt.grow)}px)`, pointerEvents: "none", zIndex: String(opt.z) });
    const gl = cv.getContext("webgl", { premultipliedAlpha: true, alpha: true, antialias: false });
    if (!gl) return null;
    const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)); return s; };
    let prog;
    try {
      prog = gl.createProgram();
      gl.attachShader(prog, sh(gl.VERTEX_SHADER, VS)); gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, FS));
      gl.linkProgram(prog);
      if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog));
    } catch (e) { console.warn("spray rim unavailable:", e.message); return null; }
    gl.useProgram(prog);
    const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(prog, "a"); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    const U = {}; for (const n of ["uRes", "uBox", "uMode", "uInset", "uRadius", "uBand", "uFlame", "uTime", "uBoil", "uPx", "uSeed", "uSdfScale", "uOutward", "uSdf", "uNavy", "uDeep", "uMid", "uLight", "uCore"]) U[n] = gl.getUniformLocation(prog, n);
    const C = Object.assign({}, COLORS, opt.colors || {});
    gl.uniform3fv(U.uNavy, C.navy); gl.uniform3fv(U.uDeep, C.deep); gl.uniform3fv(U.uMid, C.mid); gl.uniform3fv(U.uLight, C.light); gl.uniform3fv(U.uCore, C.core);
    gl.uniform1f(U.uMode, opt.kind === "sdf" ? 1 : 0); gl.uniform1f(U.uSeed, opt.seed); gl.uniform1f(U.uOutward, opt.outward);
    let ready = opt.kind !== "sdf", sdfW = 1;
    if (opt.kind === "sdf") {
      const tex = gl.createTexture(), im = new Image();
      im.onload = () => {
        gl.bindTexture(gl.TEXTURE_2D, tex);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, gl.RGB, gl.UNSIGNED_BYTE, im);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
        gl.uniform1i(U.uSdf, 0);
        ready = true; dirty = true;
      };
      im.src = opt.sdf;
      sdfW = opt.sdfSourceWidth || 900;
    }
    host.appendChild(cv);
    let W = 0, H = 0, px = 1, dirty = true;
    const fit = () => {
      const w = host.offsetWidth, h = host.offsetHeight;
      if (!w || !h) return false;
      const shown = host.getBoundingClientRect().width / w || 1;          // the page's fit-to-screen scale
      const cw = w + 2 * (M + opt.grow), ch = h + 2 * (M + opt.grow);
      px = Math.min((window.devicePixelRatio || 1) * shown, 2560 / cw, 2);
      const bw = Math.round(cw * px), bh = Math.round(ch * px);
      if (bw !== cv.width || bh !== cv.height) { cv.width = bw; cv.height = bh; dirty = true; }
      if (cw !== W || ch !== H) dirty = true;
      W = cw; H = ch;
      const g = opt.grow, x0 = M, y0 = M, x1 = W - M, y1 = H - M;    // the shape's box: the host grown by `grow`
      const mn = Math.min(x1 - x0, y1 - y0);
      gl.viewport(0, 0, cv.width, cv.height);
      gl.uniform2f(U.uRes, W, H); gl.uniform4f(U.uBox, x0, y0, x1, y1); gl.uniform1f(U.uPx, cv.width / W);
      if (opt.kind === "sdf") {
        // one field step is SDF_PX source px; the source is sdfW px wide over the host's width
        gl.uniform1f(U.uSdfScale, (opt.sdfStep || .75) * ((x1 - x0) / sdfW + (y1 - y0) / (opt.sdfSourceHeight || sdfW * (y1 - y0) / (x1 - x0))) / 2);
        gl.uniform1f(U.uBand, opt.bandPx || mn * opt.band); gl.uniform1f(U.uInset, 0); gl.uniform1f(U.uRadius, 0);
      } else {
        gl.uniform1f(U.uInset, mn * opt.inset); gl.uniform1f(U.uBand, mn * opt.band); gl.uniform1f(U.uRadius, mn * opt.radius);
      }
      gl.uniform1f(U.uFlame, opt.flame);
      return true;
    };
    const draw = now => {
      if (!ready || !fit()) return;
      const t = now / 1000;
      gl.uniform1f(U.uTime, t);
      gl.uniform1f(U.uBoil, Math.floor(t * (opt.boil || 8)) + 1);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    };
    const still = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
    let raf = 0, last = 0, alive = true;
    const loop = now => {
      if (!alive) return;
      raf = requestAnimationFrame(loop);
      if (document.hidden || !host.offsetParent || (opt.active && !opt.active())) return;
      if (still) { if (dirty) { draw(0); dirty = false; } return; }
      if (now - last < 1000 / opt.fps - 2) return;
      last = now;
      draw(now);
    };
    raf = requestAnimationFrame(loop);
    if (window.ResizeObserver) new ResizeObserver(() => { dirty = true; }).observe(host);
    cv.addEventListener("webglcontextlost", e => { e.preventDefault(); alive = false; cancelAnimationFrame(raf); cv.remove(); if (opt.onLost) opt.onLost(); });
    return { canvas: cv, stop() { alive = false; cancelAnimationFrame(raf); cv.remove(); } };
  }
  window.SprayRim = SprayRim;
})();
