// The board's symbols, drawn in one WebGL canvas (perf, 2026-11-04).
//
// Every symbol used to be a 2D canvas of its own inside its cell - 49 of them, each redrawn at 30 fps and
// each its own compositor layer - and on a phone the browser spent most of every frame committing those
// layers (owner: "not running well enough for mobile devices"). Now one Pixi canvas, laid in the board
// between the multiplier values and the reels, draws them all from per-clip atlases (each clip's Blender
// frames, resized once to the size the screen shows them). The cells stay in the page exactly as they
// were - every drop, tumble, burst, pop, spotlight and camera move is still the same CSS on the same
// elements, firing the same events the game waits on - they simply hold no picture any more: this canvas
// reads where each cell is (its layout, plus its animated transform and opacity while it is moving) and
// draws the symbol there. A resting board reads nothing and only redraws when an idle steps a frame.
// What a cell still shows itself (a Multi's value on its brick, the flat icons of the first seconds or of
// reduced motion) stays in the cell, over this canvas, as before.
//
//   BoardGL.init()                     -> Promise<boolean>   (false: the 2D path carries on)
//   BoardGL.atlas(id, clip, url, k)    -> Promise<{ frames }>
//   BoardGL.touch()                    the board needs drawing
(function () {
  "use strict";
  const PAD = 72;        // css px the canvas reaches past the board: the reels clip 60 px out at the sides; pops and bursts swell past the edge
  const MAX_RES = 2;     // device px per css px at most (a 3x phone draws its board at 2x: a third of the pixels to fill)
  const TOP_CLIP = { spinning: 0, tumbling: 24 }, SIDE_CLIP = 60;   // the reels' clip-paths (.reel.spinning / .reel.tumbling)

  let app = null, board = null, root = null, tried = null;
  let dirty = true, geoDirty = true, res = 1, W = 0, H = 0;
  const C = [];          // C[r][y]: per cell { cell, box, cont, spr, sm, cls, m, op, z, act, reread, at }
  const R = [];          // per reel { el, x, y, w, h, clip, cont, mask }
  const smearTex = new Map();
  const id3 = () => new DOMMatrix();

  function resolution() {
    const fit = board && board.offsetWidth ? board.getBoundingClientRect().width / board.offsetWidth : 1;
    return Math.max(.5, Math.min(MAX_RES, window.devicePixelRatio || 1) * (fit > 0 ? fit : 1));
  }

  async function init() {
    if (tried) return tried;
    tried = (async () => {
      if (/[?&]boardgl=0\b/.test(location.search) || typeof PIXI === "undefined") return false;
      board = document.getElementById("board");
      if (!board) return false;
      try {
        app = new PIXI.Application();
        await app.init({ backgroundAlpha: 0, antialias: false, autoDensity: true, resolution: resolution(), width: 4, height: 4, preference: "webgl" });
      } catch (e) { console.warn("board canvas unavailable:", e.message); app = null; return false; }
      app.ticker.remove(app.render, app);
      app.canvas.className = "boardgl";
      app.canvas.setAttribute("aria-hidden", "true");
      const ml = document.getElementById("multLayer");
      board.insertBefore(app.canvas, ml ? ml.nextSibling : board.firstChild);
      root = new PIXI.Container();
      root.sortableChildren = true;
      app.stage.addChild(root);
      board.classList.add("gl");
      // what moves a cell: its own animations and transitions, and its icon box's (the spotlight's fade)
      // which part of the cell moves: the cell (its transform, opacity), its icon box (the spotlight's fade)
      // or its motion blur - only that part is read while it does (the Multi's value and the rest draw themselves)
      const part = (c, t) => t === c.cell ? "aCell" : t === c.cell.ico ? "aIco" : t === c.cell.smear ? "aSm" : null;
      const on = e => { const c = cellOf(e.target), k = c && part(c, e.target); if (k) { c[k]++; c.act++; c.at = performance.now(); dirty = true; } };
      const off = e => { const c = cellOf(e.target), k = c && part(c, e.target); if (k) { c[k] = Math.max(0, c[k] - 1); c.act = Math.max(0, c.act - 1); c.reread = true; dirty = true; } };
      for (const t of ["animationstart", "transitionrun"]) board.addEventListener(t, on, true);
      for (const t of ["animationend", "animationcancel", "transitionend", "transitioncancel"]) board.addEventListener(t, off, true);
      addEventListener("resize", () => { geoDirty = true; });
      if (typeof ResizeObserver === "function") new ResizeObserver(() => { geoDirty = true; }).observe(board);
      app.ticker.add(tick, null, PIXI.UPDATE_PRIORITY.LOW);
      document.addEventListener("visibilitychange", () => { dirty = true; geoDirty = true; });
      BoardGL.on = true;
      return true;
    })();
    return tried;
  }

  function cellOf(t) {
    const el = t && t.closest ? t.closest(".cell") : null;
    return el && el._gl;
  }

  // ---------------------------------------------------------------- atlases
  // One clip's frames as one texture: the sheet decoded off the main thread and resized as a whole, on a
  // whole-pixel grid, to k of its size; each frame a rectangle of it. Built a couple at a time.
  let busy = 0;
  const waiting = [];
  const slot = () => busy < 2 ? (busy++, Promise.resolve()) : new Promise(r => waiting.push(r));
  const free = () => { const n = waiting.shift(); if (n) n(); else busy--; };
  async function atlas(id, clip, url, k) {
    await slot();
    try {
      const m = SYMF.man.symbols[id], sh = m.sheets[SYMF.density][clip], n = m.clips[clip].frames;
      const cols = sh.cols, rows = Math.ceil(n / cols);
      const blob = await fetch(url).then(r => r.ok ? r.blob() : Promise.reject(new Error(url + " -> HTTP " + r.status)));
      const sheet = await createImageBitmap(blob);
      const fw = k < 1 ? Math.max(1, Math.round(sh.w * k)) : sh.w, fh = k < 1 ? Math.max(1, Math.round(sh.h * k)) : sh.h;
      let bmp = sheet;
      if (k < 1) {
        bmp = await createImageBitmap(sheet, 0, 0, cols * sh.w, rows * sh.h, { resizeWidth: cols * fw, resizeHeight: rows * fh, resizeQuality: "high" });
        sheet.close();
      }
      const base = PIXI.Texture.from(bmp);
      base.source.scaleMode = "linear";
      try { app.renderer.texture.initSource(base.source); } catch (e) { /* uploaded on first draw instead */ }
      const frames = [];
      for (let f = 0; f < n; f++) frames.push(new PIXI.Texture({ source: base.source, frame: new PIXI.Rectangle((f % cols) * fw, Math.floor(f / cols) * fh, fw, fh) }));
      return { frames, fw, fh, k };
    } finally { free(); }
  }

  function smearTexture(cell) {
    const bg = cell.smear && cell.smear.style.backgroundImage;
    const u = bg && /url\("?([^")]+)"?\)/.exec(bg);
    if (!u) return null;
    let t = smearTex.get(u[1]);
    if (t === undefined) {
      smearTex.set(u[1], null);
      const im = new Image();
      im.onload = () => { smearTex.set(u[1], PIXI.Texture.from(im)); dirty = true; };
      im.src = u[1];
      return null;
    }
    return t;
  }

  // ---------------------------------------------------------------- layout
  // where each cell and reel sits inside the board (offsets walked up to it, like cellCentre: #app is
  // scaled to fit, so a rect would not be a layout length)
  function offsetIn(el) {
    let x = 0, y = 0, e = el;
    while (e && e !== board) {
      x += e.offsetLeft; y += e.offsetTop;
      e = e.offsetParent;
      if (e && e !== board) { x += e.clientLeft; y += e.clientTop; }
    }
    return { x, y };
  }
  function layout() {
    geoDirty = false;
    if (!board.offsetWidth) return;
    W = board.offsetWidth + 2 * PAD; H = board.offsetHeight + 2 * PAD;
    const r2 = resolution();
    if (r2 !== res || app.renderer.width !== Math.round(W * r2) || app.renderer.height !== Math.round(H * r2)) {
      res = r2;
      app.renderer.resolution = res;
      app.renderer.resize(W, H);
    }
    Object.assign(app.canvas.style, { left: -PAD - board.clientLeft + "px", top: -PAD - board.clientTop + "px", width: W + "px", height: H + "px" });
    for (let r = 0; r < cellEls.length; r++) {
      const reel = reelEls[r];
      if (!R[r]) {
        const cont = new PIXI.Container(); cont.sortableChildren = true;
        const mask = new PIXI.Graphics();
        R[r] = { el: reel, clip: "", cont, mask };
        root.addChild(cont); root.addChild(mask); mask.visible = false;
      }
      const p = offsetIn(reel);
      Object.assign(R[r], { x: p.x, y: p.y, w: reel.offsetWidth, h: reel.offsetHeight, clip: "?" });
      for (let y = 0; y < cellEls[r].length; y++) {
        const cell = cellEls[r][y];
        if (!C[r]) C[r] = [];
        let c = C[r][y];
        if (!c) {
          const cont = new PIXI.Container(), sm = new PIXI.Sprite(), spr = new PIXI.Sprite();
          sm.visible = false; spr.visible = false;
          cont.addChild(sm, spr);
          c = C[r][y] = { cell, cont, spr, sm, cls: null, m: null, op: 1, ico: 1, z: 0, act: 0, aCell: 0, aIco: 0, aSm: 0, reread: true, at: 0, order: r * 100 + y, smop: 0, smm: null, tex: null };
          cell._gl = c;
          root.addChild(cont);
        }
        const q = offsetIn(cell);
        c.box = { x: q.x, y: q.y, w: cell.offsetWidth, h: cell.offsetHeight, cw: cell.clientWidth, ch: cell.clientHeight, bl: cell.clientLeft, bt: cell.clientTop };
        c.reread = true;
      }
    }
    dirty = true;
  }

  // ---------------------------------------------------------------- what CSS is doing to a cell now
  function matrixOf(cs) {
    const o = cs.transformOrigin.split(" ").map(parseFloat);
    let m = id3().translate(o[0] || 0, o[1] || 0);
    if (cs.translate && cs.translate !== "none") { const t = cs.translate.split(" ").map(parseFloat); m = m.translate(t[0] || 0, t[1] || 0); }
    if (cs.rotate && cs.rotate !== "none") m = m.rotate(parseFloat(cs.rotate.split(" ").pop()) || 0);
    if (cs.scale && cs.scale !== "none") { const s = cs.scale.split(" ").map(parseFloat); m = m.scale(s[0], s.length > 1 ? s[1] : s[0]); }
    if (cs.transform && cs.transform !== "none") m = m.multiply(new DOMMatrix(cs.transform));
    return m.translate(-(o[0] || 0), -(o[1] || 0));
  }
  // a 2D matrix about the element's own top left; the common case (only `transform`, a matrix) without DOMMatrix
  function mat(cs) {
    const tf = cs.transform, tr = cs.translate, ro = cs.rotate, sc = cs.scale;
    const plain = (!sc || sc === "none") && (!tr || tr === "none") && (!ro || ro === "none");
    if (plain && tf === "none") return null;
    if (plain && tf.startsWith("matrix(")) {
      const v = tf.slice(7, -1).split(","), a = +v[0], b = +v[1], c = +v[2], d = +v[3];
      const o = cs.transformOrigin, i = o.indexOf(" "), ox = parseFloat(o) || 0, oy = parseFloat(o.slice(i + 1)) || 0;
      return { a, b, c, d, e: +v[4] + ox - (a * ox + c * oy), f: +v[5] + oy - (b * ox + d * oy) };
    }
    const M = matrixOf(cs);
    return { a: M.a, b: M.b, c: M.c, d: M.d, e: M.e, f: M.f };
  }
  function read(c, all) {
    if (all || c.aCell) {
      const cs = getComputedStyle(c.cell);
      c.m = mat(cs);
      c.op = parseFloat(cs.opacity);
      c.z = parseInt(cs.zIndex, 10) || 0;
    }
    if (all || c.aIco) c.ico = c.cell.ico ? parseFloat(getComputedStyle(c.cell.ico).opacity) : 1;
    const s = c.cell.smear;
    if (s && (all || c.aSm)) {
      const ss = getComputedStyle(s);
      c.smop = parseFloat(ss.opacity);
      c.smm = c.smop > .005 ? mat(ss) : null;
    } else if (!s) c.smop = 0;
  }

  // ---------------------------------------------------------------- the frame
  function tick() {
    if (document.hidden || !board) return;
    if (geoDirty) layout();
    if (!C.length) return;
    const now = performance.now();
    // the reels' clips while tiles are on the move
    for (const rr of R) {
      if (!rr) continue;
      const cl = rr.el.classList, clip = cl.contains("spinning") ? "spinning" : cl.contains("tumbling") ? "tumbling" : "";
      if (clip === rr.clip) continue;
      rr.clip = clip; dirty = true; rr.cont.zIndex = 0;
      if (clip) {
        const t = TOP_CLIP[clip];
        rr.mask.clear().rect(PAD + rr.x - SIDE_CLIP, PAD + rr.y - t, rr.w + 2 * SIDE_CLIP, rr.h + 2 * t).fill(0xffffff);
        rr.mask.visible = true; rr.cont.mask = rr.mask;
      } else { rr.cont.mask = null; rr.mask.visible = false; }
    }
    for (let r = 0; r < C.length; r++) {
      const rr = R[r], hiddenReel = rr && rr.clip === "spinning";
      for (const c of C[r]) {
        if (!c) continue;
        const cell = c.cell;
        if (cell.className !== c.cls) { c.cls = cell.className; c.reread = true; }
        if (c.act > 0 && now - c.at > 4000 && !cell.getAnimations({ subtree: true }).length) c.act = c.aCell = c.aIco = c.aSm = 0;
        if (c.act > 0 || c.reread) { read(c, c.reread); c.reread = false; dirty = true; }
        // the symbol: the frame its rig is showing (symDraw), on the clip's box inside the rig
        const ico = cell.ico, rig = ico && ico.firstElementChild;
        const g = rig && rig._gclip ? SYMF.sheets.get(rig._name + "_" + rig._gclip) : null;
        const tex = g && g.atlas ? g.atlas.frames[rig._gf] : null;
        const show = !!tex && !hiddenReel && c.op * c.ico > .003;
        if (tex !== c.tex) { c.tex = tex; dirty = true; }
        if (!show) { if (c.spr.visible || c.sm.visible) { c.spr.visible = false; c.sm.visible = false; dirty = true; } continue; }
        // the cell in the board, as CSS has it now
        const b = c.box, mm = new PIXI.Matrix();
        if (c.m) mm.set(c.m.a, c.m.b, c.m.c, c.m.d, c.m.e + PAD + b.x, c.m.f + PAD + b.y);
        else mm.set(1, 0, 0, 1, PAD + b.x, PAD + b.y);
        c.cont.setFromMatrix(mm);
        const parent = rr && rr.clip ? rr.cont : root;
        if (c.cont.parent !== parent) parent.addChild(c.cont);
        c.cont.zIndex = c.z * 1000 + c.order;
        if (rr && rr.clip) rr.cont.zIndex = Math.max(rr.cont.zIndex || 0, c.cont.zIndex);
        // the rig: the icon's footprint scaled into the cell's 88% box, centred; the clip's box inside it
        const m = rig._m, rw = m.icon[0] * 10, rh = m.icon[1] * 10, bx = m.clips[rig._gclip].box;
        const sR = Math.min(b.cw * .88 / rw, b.ch * .88 / rh);
        c.spr.texture = tex;
        c.spr.x = b.w / 2 + ((bx[0] + m.icon[0] / 2) * 10 - rw / 2) * sR;
        c.spr.y = b.h / 2 + ((bx[1] + m.icon[1] / 2) * 10 - rh / 2) * sR;
        c.spr.width = bx[2] * 10 * sR; c.spr.height = bx[3] * 10 * sR;
        c.spr.alpha = c.op * c.ico;
        c.spr.visible = true;
        // the motion blur behind a falling tile (.smear: left 6%, 88% wide, its foot 6% up, 2.1 boxes tall)
        const st = c.smop > .005 ? smearTexture(cell) : null;
        if (st) {
          const sw = b.cw * .88, sh = b.ch * .88 * 2.1, sx = b.bl + b.cw * .06, sy = b.bt + b.ch * .94 - sh;
          // its own transform (the stretch) is about its own box: then the box is moved to where it sits
          const sm = c.smm ? new PIXI.Matrix(c.smm.a, c.smm.b, c.smm.c, c.smm.d, c.smm.e, c.smm.f) : new PIXI.Matrix();
          sm.translate(sx, sy);
          c.sm.texture = st;
          c.sm.setFromMatrix(sm);
          c.sm.scale.set(c.sm.scale.x * sw / st.width, c.sm.scale.y * sh / st.height);
          c.sm.alpha = c.smop * c.op * c.ico;
          c.sm.visible = true;
        } else if (c.sm.visible) c.sm.visible = false;
      }
    }
    if (dirty) { dirty = false; app.render(); }
  }

  window.BoardGL = { on: false, init, atlas, touch: () => { dirty = true; }, MAX_RES, get app() { return app; } };
})();
