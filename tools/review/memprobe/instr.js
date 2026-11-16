// Memory instrumentation, injected before the page's own scripts.
(() => {
  const M = window.__mem = { canvases: [], bitmaps: [], audio: [], textures: [], imgs: [], gls: [], peak: {}, samples: [] };
  const track = (arr, o) => { arr.push(new WeakRef(o)); };
  const gc0 = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function (type, opts) {
    const c = gc0.call(this, type, opts);
    if (c && !this.__mt) {
      this.__mt = { type, opts: opts ? JSON.stringify(opts) : "", stack: (new Error().stack || "").split("\n").slice(2, 4).join(" | ").replace(/\s+/g, " ").slice(0, 220) };
      track(M.canvases, this);
      if (/webgl/.test(type)) { track(M.gls, c); c.__canvas = this; }
    }
    return c;
  };
  if (window.OffscreenCanvas) {
    const og = OffscreenCanvas.prototype.getContext;
    OffscreenCanvas.prototype.getContext = function (type, opts) {
      const c = og.call(this, type, opts);
      if (c && !this.__mt) { this.__mt = { type, opts: "", stack: "offscreen" }; track(M.canvases, this); }
      return c;
    };
  }
  const cib = window.createImageBitmap;
  window.createImageBitmap = function (...a) {
    const st = (new Error().stack || "").split("\n").slice(2, 3).join("").trim().slice(0, 160);
    return cib.apply(this, a).then(b => { b.__st = st; b.__mt = 1; track(M.bitmaps, b); return b; });
  };
  const dad = BaseAudioContext.prototype.decodeAudioData;
  BaseAudioContext.prototype.decodeAudioData = function (buf, ...rest) {
    const p = dad.call(this, buf, ...rest);
    p.then(b => track(M.audio, b), () => {});
    return p;
  };
  const sd = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, "src");
  Object.defineProperty(HTMLImageElement.prototype, "src", {
    configurable: true, enumerable: true,
    get() { return sd.get.call(this); },
    set(v) { if (!this.__mt) { this.__mt = 1; track(M.imgs, this); } sd.set.call(this, v); },
  });
  const srcW = s => s ? (s.naturalWidth || s.videoWidth || s.displayWidth || s.width || 0) : 0;
  const srcH = s => s ? (s.naturalHeight || s.videoHeight || s.displayHeight || s.height || 0) : 0;
  const BPP = (fmt, type, gl) => {
    let ch = 4;
    if (gl) { if (fmt === gl.RGB) ch = 3; else if (fmt === gl.ALPHA || fmt === gl.LUMINANCE || fmt === 0x1903 /*RED*/) ch = 1; else if (fmt === gl.LUMINANCE_ALPHA) ch = 2; }
    let b = 1; if (type === 0x1406 /*FLOAT*/) b = 4; else if (type === 0x8D61 || type === 0x140B /*HALF*/) b = 2;
    return Math.max(4, ch) * b;   // GPUs pad RGB to RGBA
  };
  for (const P of [window.WebGLRenderingContext && WebGLRenderingContext.prototype, window.WebGL2RenderingContext && WebGL2RenderingContext.prototype].filter(Boolean)) {
    const bind = P.bindTexture, act = P.activeTexture, ti = P.texImage2D, ts = P.texStorage2D, del = P.deleteTexture, gm = P.generateMipmap, ct = P.createTexture;
    P.activeTexture = function (u) { this.__unit = u; return act.call(this, u); };
    P.bindTexture = function (t, tex) { (this.__b || (this.__b = {}))[(this.__unit || 0) + ":" + t] = tex; return bind.call(this, t, tex); };
    P.createTexture = function () { const t = ct.call(this); if (t) { t.__lv = {}; t.__gl = this; track(M.textures, t); } return t; };
    const cur = (gl, target) => { const t = target >= 0x8515 && target <= 0x851A ? 0x8513 : target; return gl.__b && gl.__b[(gl.__unit || 0) + ":" + t]; };
    P.texImage2D = function (...a) {
      const r = ti.apply(this, a);
      const tex = cur(this, a[0]);
      if (tex && tex.__lv) {
        let w, h, fmt, type;
        if (a.length >= 9) { w = a[3]; h = a[4]; fmt = a[6]; type = a[7]; } else { w = srcW(a[5]); h = srcH(a[5]); fmt = a[3]; type = a[4]; }
        // a texture's source kept by the page after its upload (Pixi holds it for a re-upload): an ImageBitmap made in a
        // worker never passed window.createImageBitmap, so it is counted here (closed bitmaps read 0 x 0)
        const src = a.length >= 9 ? a[8] : a[5];
        if (window.ImageBitmap && src instanceof ImageBitmap && !src.__mt) { src.__mt = 1; src.__st = "texture source"; track(M.bitmaps, src); }
        tex.__lv[a[0] + ":" + a[1]] = w * h * BPP(fmt, type, this);
        tex.__wh = w + "x" + h;
      }
      return r;
    };
    if (ts) P.texStorage2D = function (target, levels, ifmt, w, h) {
      const r = ts.call(this, target, levels, ifmt, w, h);
      const tex = cur(this, target);
      if (tex && tex.__lv) { let s = 0, ww = w, hh = h; for (let i = 0; i < levels; i++) { s += ww * hh * 4; ww = Math.max(1, ww >> 1); hh = Math.max(1, hh >> 1); } tex.__lv.s = s; tex.__wh = w + "x" + h; }
      return r;
    };
    P.generateMipmap = function (t) { const r = gm.call(this, t); const tex = cur(this, t); if (tex && tex.__lv) tex.__mip = 1; return r; };
    P.deleteTexture = function (t) { if (t) t.__dead = 1; return del.call(this, t); };
  }
  const sum = (arr, f) => { let s = 0; for (const r of arr) { const o = r.deref(); if (o) s += f(o) || 0; } return s; };
  M.quick = () => {
    const live = M.canvases.map(r => r.deref()).filter(Boolean);
    let c2d = 0, cgl = 0, n2d = 0, ngl = 0, nlost = 0;
    for (const c of live) {
      const px = c.width * c.height * 4;
      if (/webgl/.test(c.__mt.type)) {
        const o = c.__mt.opts || "";
        // front + back buffer (+ depth/stencil 4 B/px if asked; Pixi asks for stencil)
        cgl += px * 2 + (/"depth":false/.test(o) && !/"stencil":true/.test(o) ? 0 : px) ; ngl++;
      } else if (px) { c2d += px; n2d++; }
    }
    for (const g of M.gls.map(r => r.deref()).filter(Boolean)) if (g.isContextLost && g.isContextLost()) nlost++;
    const tex = sum(M.textures, t => t.__dead ? 0 : Object.values(t.__lv).reduce((a, b) => a + b, 0) * (t.__mip ? 4 / 3 : 1));
    const bmp = sum(M.bitmaps, b => b.width * b.height * 4);
    const aud = sum(M.audio, b => b.length * b.numberOfChannels * 4);
    const heap = performance.memory ? performance.memory.usedJSHeapSize : 0;
    return { c2d, n2d, cgl, ngl, nlost, tex, bmp, nbmp: M.bitmaps.filter(r => r.deref() && r.deref().width).length, aud, naud: M.audio.filter(r => r.deref()).length, heap };
  };
  M.startSampler = (ms = 400) => {
    clearInterval(M._s);
    M.peak = {};
    M._s = setInterval(() => {
      const q = M.quick(); q.t = Math.round(performance.now());
      q.total = q.c2d + q.cgl + q.tex + q.bmp + q.aud;
      M.samples.push(q);
      for (const k in q) if (typeof q[k] === "number" && !(M.peak[k] >= q[k])) M.peak[k] = q[k];
    }, ms);
  };
  M.stopSampler = () => clearInterval(M._s);
  M.detail = () => {
    const cv = M.canvases.map(r => r.deref()).filter(Boolean).map(c => ({
      type: c.__mt.type, w: c.width, h: c.height, mb: +(c.width * c.height * 4 / 1e6).toFixed(2), inDom: !!c.isConnected,
      id: c.id || c.className || (c.parentElement && (c.parentElement.id || c.parentElement.className)) || "", st: c.__mt.stack, opts: c.__mt.opts,
    })).filter(c => c.w * c.h > 0);
    const tex = M.textures.map(r => r.deref()).filter(t => t && !t.__dead && Object.keys(t.__lv).length).map(t => ({ wh: t.__wh, mb: +(Object.values(t.__lv).reduce((a, b) => a + b, 0) * (t.__mip ? 4 / 3 : 1) / 1e6).toFixed(2), gl: t.__gl && t.__gl.__canvas ? (t.__gl.__canvas.id || t.__gl.__canvas.className || t.__gl.__canvas.__mt.stack.slice(0, 80)) : "" }));
    const bmp = M.bitmaps.map(r => r.deref()).filter(b => b && b.width).map(b => ({ wh: b.width + "x" + b.height, st: b.__st }));
    const aud = M.audio.map(r => r.deref()).filter(Boolean).map(b => ({ s: +b.duration.toFixed(2), ch: b.numberOfChannels, sr: b.sampleRate, mb: +(b.length * b.numberOfChannels * 4 / 1e6).toFixed(3) }));
    return { cv, tex, bmp, aud };
  };
  // decoded pictures referenced by the page: <img> elements (DOM or held) and CSS urls on any element/pseudo
  M.pics = () => {
    const urls = new Map();
    const add = (u, where) => { try { u = new URL(u, location.href).pathname.replace(/^\//, ""); } catch (e) { return; } const o = urls.get(u); if (!o || (/^(held|css-hidden)/.test(o) && !/^(held|css-hidden)/.test(where))) urls.set(u, where); };
    // (2026-11-16: an <img> or a CSS picture on an element with no box - display: none on it or on an ancestor - is
    // neither painted nor decoded, so it counts as hidden; the model used to read the element's own display only)
    for (const r of M.imgs) { const i = r.deref(); if (i && !i.isConnected && i.currentSrc && !i.currentSrc.startsWith("data:") && !i.currentSrc.startsWith("blob:")) add(i.currentSrc, "held"); }
    for (const i of document.querySelectorAll("img")) if (i.currentSrc && !i.currentSrc.startsWith("data:") && !i.currentSrc.startsWith("blob:")) {
      const vis = i.getClientRects().length > 0 && getComputedStyle(i).visibility !== "hidden" && getComputedStyle(i).display !== "none";
      add(i.currentSrc, (vis ? "img:" : "css-hidden:img:") + (i.id || i.className || "").toString().slice(0, 30));
    }
    const els = document.querySelectorAll("*");
    for (const el of els) {
      const boxed = el.getClientRects().length > 0;
      for (const pseudo of [null, "::before", "::after"]) {
        const cs = getComputedStyle(el, pseudo);
        if (pseudo && cs.content === "none") continue;
        for (const prop of ["backgroundImage", "maskImage", "webkitMaskImage", "borderImageSource", "listStyleImage"]) {
          const v = cs[prop];
          if (!v || v === "none" || v.indexOf("url(") < 0) continue;
          for (const m of v.matchAll(/url\("?([^")]+)"?\)/g)) if (!m[1].startsWith("data:")) add(m[1], (cs.display === "none" || !boxed ? "css-hidden:" : "css:") + (el.id || el.className || el.tagName).toString().slice(0, 30));
        }
      }
    }
    return [...urls.entries()];
  };
  // frame timing
  M.frames = [];
  M.startFrames = () => {
    M.frames = []; M._fr = true; let last = performance.now(); M._t0 = last;
    const f = t => { if (!M._fr) return; M.frames.push(t - last); last = t; requestAnimationFrame(f); };
    requestAnimationFrame(f);
    M.long = [];
    try { M._po && M._po.disconnect(); M._po = new PerformanceObserver(l => { for (const e of l.getEntries()) M.long.push([Math.round(e.duration), Math.round(e.startTime - M._t0)]); }); M._po.observe({ type: "longtask" }); } catch (e) {}
  };
  M.stopFrames = () => {
    M._fr = false;
    const a = M.frames.slice(1).sort((x, y) => x - y);
    const q = p => a.length ? +a[Math.min(a.length - 1, Math.floor(p * a.length))].toFixed(1) : 0;
    return { n: a.length, p50: q(.5), p95: q(.95), p99: q(.99), worst: a.length ? +a[a.length - 1].toFixed(1) : 0, over20: a.filter(x => x > 20).length, over33: a.filter(x => x > 33.4).length, long: M.long.length, longSum: M.long.reduce((x, y) => x + y[0], 0),
      longMax: M.long.reduce((x, y) => Math.max(x, y[0]), 0), longFirstSec: M.long.filter(x => x[1] < 1000), longList: M.long.slice(0, 12) };
  };
})();
