// The live wall (assets/wallfx, tools/sprayrim/make_wall_fx.py):
// - the paint in the cracked holes is alive. Each blob of the wall art is redrawn over itself,
//   slowly swelling and sagging, and paint drips from its tips - one drip at a time per blob,
//   the next only once the last is gone: a bead swells out of the tip, runs down the bricks
//   slowing as it thins, fattens, pinches off a drop that falls to the pavement and splats
//   flat, and then the rest of the run lets go of the tip and slides off the wall after it,
//   the last of it falling as a smaller drop. Nothing fades out: all the paint leaves by falling.
// - it is drawn the way the wall art paints (the blob's own fill, its dark line, the pale shine
//   down the right, a soft shadow on the bricks), and then dimmed exactly as #bgwall dims the
//   art under it - the same gradient laid over the paint (source-atop) - so it is the wall's
//   own paint moving, not a sticker on top of it.
// - the SMUKIEZ tag's green outline glows like neon (#tagglow) and throws its light on the bricks
//   round it (#tagspill) - both CSS, they ride the tag's wander, hop and pop (index.html).
// - that neon is the light of the scene: light() says where it comes from for any point on the
//   page and how strong it is there, neon() is the sign's flicker right now. The wet paint here
//   takes its green on the edges that face the sign; the two characters take it as a rim light
//   from behind (neonRim, index.html).
// One small canvas per blob (its tips down to the pavement), drawn on animation frames.
(function () {
  "use strict";
  const ART = [3840, 2167];                     // bonus_wall.webp; everything below is in its px
  const FLOOR = .875 * ART[1];                  // the pavement's edge
  const DIM = [.78, .9], TINT = "20,18,24";     // #bgwall's gradient over the art, top to bottom (index.html)
  const G = 2600;                               // gravity, art px / s^2: a drop crosses the wall in about a second
  const NEON = [110, 255, 70];                  // the tube's lime (make_wall_fx.py tag())
  const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let regions = [], layer = null, raf = 0, last = 0;

  const rnd = (a, b) => a + Math.random() * (b - a);
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const smooth = v => v * v * (3 - 2 * v);
  const rgb = (c, k = 1) => `rgb(${c.map(v => Math.round(v * k)).join(",")})`;

  // ------------------------------------------------------------------ the tag's light
  // The glowing tube is read off tag_glow.webp (its alpha, 128 px across - squared, so the tube
  // outshines its own halo) and laid over #tagglow's box wherever that is on the page. For a
  // point, the light comes from the tube round it weighted by closeness - inverse square,
  // softened, so the nearest stretch leads and the rest of the sign still pulls - and its
  // strength is how much tube there is how close: 1 a short way off the tube's end.
  const GLOW_W = 128, SOFT = .12, NORM = .5;     // SOFT in tag heights; NORM: the light called 1 (the pair stand in about that)
  let glow = null, glowLoad = null;
  function loadGlow() {
    if (glowLoad) return glowLoad;
    glowLoad = new Promise(res => {
      const im = new Image();
      im.onload = () => {
        const w = GLOW_W, h = Math.max(1, Math.round(GLOW_W * im.naturalHeight / im.naturalWidth));
        const c = document.createElement("canvas"); c.width = w; c.height = h;
        const x = c.getContext("2d", { willReadFrequently: true });
        x.drawImage(im, 0, 0, w, h);
        const px = x.getImageData(0, 0, w, h).data, pts = [];
        for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) {
          const a = px[(j * w + i) * 4 + 3] / 255;
          if (a > .05) pts.push((i + .5) / w, (j + .5) / h, a * a);
        }
        glow = { aspect: w / h, pts: new Float32Array(pts), n: w * h };
        res(glow);
      };
      im.onerror = () => res(null);
      im.src = "assets/wallfx/tag_glow.webp";
    });
    return glowLoad;
  }
  // where a page point's light comes from (page px) and how strong it is there; null until the
  // tube is read, or while the tag is not on screen
  function light(x, y) {
    if (!glow) { loadGlow(); return null; }
    const box = document.querySelector("#tagglow > i"), r = box && box.getBoundingClientRect();
    if (!r || !r.width || !r.height) return null;
    const H = r.height, u = (x - r.left) / H, v = (y - r.top) / H, aw = r.width / H, P = glow.pts;
    let sw = 0, su = 0, sv = 0;
    for (let n = 0; n < P.length; n += 3) {
      const pu = P[n] * aw, pv = P[n + 1], du = pu - u, dv = pv - v;
      const k = P[n + 2] / (du * du + dv * dv + SOFT * SOFT);
      sw += k; su += k * pu; sv += k * pv;
    }
    if (!sw) return null;
    // the sum is over the image's pixels: times a pixel's area (in tag heights squared) it is the
    // same light at any size the glow is read at
    return { x: r.left + su / sw * H, y: r.top + sv / sw * H, k: sw * aw / glow.n / NORM };
  }
  // The sign's flicker now, about 1 on average: #tagglow's own neonTag animation (its opacity
  // times its brightness) read at its current time, so what the tube lights flickers with it.
  // Asking a CSS animation for its state flushes the page's style, and this is asked every frame
  // by both figures and the wall, so the animation is read four times a second and the flicker
  // followed on the document's clock in between.
  let neonAnim = null, neonTrack = null, neonRead = -1e9, neonStart = 0, neonDur = 1;
  function neon() {
    if (REDUCED) return 1;
    const now = document.timeline.currentTime ?? performance.now();
    if (now - neonRead > 250) {
      neonRead = now;
      if (!neonAnim || neonAnim.playState !== "running") {
        const el = document.getElementById("tagglow");
        neonAnim = (el && el.getAnimations().find(a => a.animationName === "neonTag")) || null;
        neonTrack = neonAnim ? neonTracks(neonAnim.effect.getKeyframes()) : null;
      }
      if (neonAnim) { neonDur = neonAnim.effect.getTiming().duration || 1; neonStart = now - (neonAnim.currentTime || 0); }
    }
    if (!neonTrack) return 1;
    return neonAt(neonTrack, ((((now - neonStart) % neonDur) + neonDur) % neonDur) / neonDur) / neonTrack.mean;
  }
  // the keyframes as a track per property, each closed at both ends with the plain value
  function neonTracks(kf) {
    const op = [], br = [];
    for (const f of kf) {
      const o = f.computedOffset ?? f.offset;
      if (f.opacity !== undefined && f.opacity !== "") op.push([o, parseFloat(f.opacity)]);
      const m = /brightness\(([\d.]+)\)/.exec(f.filter || "");
      if (m) br.push([o, parseFloat(m[1])]);
    }
    for (const t of [op, br]) {
      if (!t.length || t[0][0] > 0) t.unshift([0, 1]);
      if (t[t.length - 1][0] < 1) t.push([1, 1]);
    }
    const track = { op, br, mean: 1 };
    let s = 0;
    for (let i = 0; i < 240; i++) s += neonAt(track, i / 240);
    track.mean = s / 240 || 1;
    return track;
  }
  function neonAt(track, p) {
    const at = t => {
      let i = 1;
      while (i < t.length - 1 && t[i][0] < p) i++;
      const [o0, v0] = t[i - 1], [o1, v1] = t[i];
      return v0 + (v1 - v0) * clamp((p - o0) / ((o1 - o0) || 1), 0, 1);
    };
    return at(track.op) * at(track.br);
  }

  // ------------------------------------------------------------------ one drip's life
  // Its shape at any moment, from its age: the run (top, end, widths, an optional neck), the
  // bead hanging off the end, and the drops it lets go of (handed to the region to fall).
  function newDrip(R) {
    let k = Math.floor(Math.random() * R.tips.length);
    if (R.tips.length > 1 && k === R.lastTip) k = (k + 1) % R.tips.length;   // the tips take turns
    R.lastTip = k;
    const tip = R.tips[k], w = tip.w, rb = w * .56;   // the bead a little fatter than the run, as paint gathers
    const room = FLOOR - tip.y;
    const T = { emerge: rnd(.9, 1.4), run: rnd(2.2, 3.6), hang: rnd(.6, 1.1), pinch: .28, recoil: .55, rest: rnd(.35, .8), drain: rnd(1.1, 1.5) };
    let acc = 0; const at = {};
    for (const [n, d] of Object.entries(T)) { at[n] = acc; acc += d; }
    const seed = rnd(0, 6.3), xAt = y => tip.x + w * .07 * Math.sin((y - tip.y) / (w * 2.4) + seed);   // a slight wander down the bricks
    return { tip, w, rb, len: Math.min(room * .45, w * rnd(3.5, 6.5)), T, at, end: acc, t: 0, xAt, dropped: 0 };
  }

  function dripShape(R, d) {
    const { tip, w, rb, T, at } = d, t = d.t, lw = R.lw;
    const top0 = tip.y - lw * 1.5;               // the run starts under the blob's own line
    const e1 = tip.y + rb * .7;                  // where the end hangs once it is out
    const e2 = e1 + d.len;                       // ... and once it has run
    const s = { top: top0, end: e1, ht: w / 2, hb: w / 2 * .92, bead: 0, beadY: 0, neck: 1, cap: false };
    const ph = (n) => clamp((t - at[n]) / T[n], 0, 1);
    if (t < at.run) {                            // a bead swells out of the tip
      const v = smooth(ph("emerge"));
      s.end = tip.y - rb * .2 + (e1 - tip.y + rb * .2) * v;
      s.bead = rb * (.45 + .55 * v);
    } else if (t < at.hang) {                    // and runs down, slowing as the paint thins
      const v = ph("run"), p = 1 - Math.pow(1 - v, 2.2);
      s.end = e1 + d.len * p; s.hb = w / 2 * (.95 - .13 * p);
      s.bead = rb * (1 + .06 * Math.sin(v * Math.PI));
    } else if (t < at.pinch) {                   // its bead fattens
      const v = smooth(ph("hang"));
      s.end = e2 + rb * .25 * v; s.hb = w / 2 * .82; s.bead = rb * (1.06 + .16 * v);
    } else if (t < at.recoil) {                  // a neck forms and the drop lets go
      const v = ph("pinch");
      s.end = e2 + rb * .25; s.hb = w / 2 * .82; s.bead = rb * 1.22; s.neck = 1 - .86 * smooth(v);
      s.beadY = s.bead * .7 * v * v;
    } else if (t < at.drain) {                   // the run's end springs back up, then settles
      const v = ph("recoil");
      s.hb = w / 2 * .82; s.end = e2 + rb * .25 - rb * (.35 * smooth(Math.min(1, v * 2)) + .45 * Math.sin(v * Math.PI) * Math.exp(-2.5 * v));
    } else {                                     // the rest lets go of the tip and slides off after it
      const v = ph("drain"), q = Math.pow(v, 2.2);
      const rest = e2 + rb * .25 - rb * .35;
      s.hb = w / 2 * (.82 - .12 * v);
      s.end = rest + rb * 2.6 * Math.pow(v, 2.6);
      s.bead = rb * .72 * smooth(v);             // the paint gathers at the end as it goes
      const lenNow = s.end - top0;
      s.top = top0 + Math.max(0, lenNow - Math.max(s.hb, s.bead) * 1.3) * q;
      s.ht = w / 2 * (1 - .45 * v); s.cap = s.top > tip.y - lw;
    }
    return s;
  }

  // the drip's outline as one path (all sub-paths wound the same way, so they fill as one shape
  // and cast one shadow); g grows every part by g (the dark line round it)
  function dripPath(ctx, R, d, s, g) {
    const xAt = d.xAt;
    const len = Math.max(0, s.end - s.top), N = 22, neckL = Math.min(len, s.bead * 1.6);
    const hw = y => {
      const u = len ? (y - s.top) / len : 1;
      let h = s.ht + (s.hb - s.ht) * Math.pow(u, .8);
      if (s.neck < 1 && y > s.end - neckL) h *= 1 - (1 - s.neck) * smooth((y - (s.end - neckL)) / neckL);
      return h + g;
    };
    if (len > 0) {
      const ys = Array.from({ length: N + 1 }, (_, i) => s.top + len * i / N);
      ctx.moveTo(xAt(ys[0]) + hw(ys[0]), ys[0]);
      for (const y of ys) ctx.lineTo(xAt(y) + hw(y), y);
      for (let i = N; i >= 0; i--) ctx.lineTo(xAt(ys[i]) - hw(ys[i]), ys[i]);
      ctx.closePath();
      if (s.cap) { ctx.moveTo(xAt(s.top) + hw(s.top), s.top); ctx.arc(xAt(s.top), s.top, hw(s.top), 0, Math.PI * 2); }
      const re = s.neck < 1 ? hw(s.end) : s.hb + g;
      ctx.moveTo(xAt(s.end) + re, s.end); ctx.arc(xAt(s.end), s.end, re, 0, Math.PI * 2);
    }
    if (s.bead > 0) {
      const by = s.end + s.bead * .72 + s.beadY, r = s.bead * (1 + .06 * (s.beadY / Math.max(1, s.bead))) + g;
      ctx.moveTo(xAt(s.end) + r, by); ctx.ellipse(xAt(s.end), by, r, r * (1 + .1 * (s.beadY / Math.max(1, s.bead))), 0, 0, Math.PI * 2);
    }
  }

  // a falling drop: a teardrop drawn out by its speed; a landed one: a splat sinking flat
  function dropPath(ctx, p, g) {
    if (p.splat !== undefined) {
      const v = clamp(p.splat / .5, 0, 1), rx = p.r * (1.15 + 1.1 * smooth(v)) + g, ry = p.r * .55 * Math.pow(1 - v, 1.3) + g * (1 - v);
      if (ry <= .2) return;
      ctx.moveTo(p.x + rx, FLOOR - ry * .5); ctx.ellipse(p.x, FLOOR - ry * .5, rx, ry, 0, 0, Math.PI * 2);
      return;
    }
    const e = clamp(p.v / 1800, 0, .75), r = p.r * (1 - .14 * e) + g;
    const ay = p.y - (p.r * (1.25 + 1.7 * e) + g * 1.4), d = p.y - ay;
    const tx = r * Math.sqrt(Math.max(0, 1 - (r / d) ** 2)), ty = p.y - r * r / d;
    ctx.moveTo(p.x - tx, ty); ctx.lineTo(p.x, ay); ctx.lineTo(p.x + tx, ty); ctx.closePath();
    ctx.moveTo(p.x + r, p.y); ctx.ellipse(p.x, p.y, r, r * (1 + .12 * e), 0, 0, Math.PI * 2);
  }

  // ------------------------------------------------------------------ a blob and its drips
  function makeRegion(b, i) {
    const tips = b.tips.map(([x, y, w]) => ({ x: x * ART[0], y: y * ART[1], tw: w * ART[0], w: clamp(w * ART[0] * .85, 20, 44) }));
    const bx = b.x * ART[0], by = b.y * ART[1], bw = b.w * ART[0], bh = b.h * ART[1];
    const x0 = Math.min(bx - bw * .06, ...tips.map(t => t.x - 90)), x1 = Math.max(bx + bw * 1.06, ...tips.map(t => t.x + 90));
    const y0 = by - bh * .1, y1 = FLOOR + 40;
    const cv = document.createElement("canvas");
    const pc = (v, of) => (v / of * 100).toFixed(3) + "%";
    Object.assign(cv.style, { left: pc(x0, ART[0]), top: pc(y0, ART[1]), width: pc(x1 - x0, ART[0]), height: pc(y1 - y0, ART[1]) });
    const img = new Image(); img.src = `assets/wallfx/blob_${i}.webp`;
    const lcv = document.createElement("canvas");   // off the page: where the lit edge is cut out
    return {
      b, tips, x0, y0, x1, y1, cv, ctx: cv.getContext("2d"), img, box: [bx, by, bw, bh], lcv, lctx: lcv.getContext("2d"), light: null,
      fill: b.fill || (b.colour === "green" ? [127, 234, 95] : [225, 130, 198]), line: b.line || [104, 30, 100], hi: b.hi || [194, 206, 237], lw: b.lw || 10,
      drip: null, wait: rnd(.4, 5), lastTip: -1, drops: [], ooze: rnd(5.5, 9), ph: rnd(0, 6.3), dim: [DIM[0], DIM[1]], k: 1,
    };
  }

  function step(R, dt, now) {
    if (!R.drip) { R.wait -= dt; if (R.wait <= 0) R.drip = newDrip(R); }
    const d = R.drip;
    if (d) {
      d.t += dt;
      const s = dripShape(R, d);
      if (!d.dropped && d.t >= d.at.recoil) {     // the bead lets go
        d.dropped = 1;
        const ye = d.tip.y + d.rb * .7 + d.len + d.rb * .25;   // where the pinch left the bead (dripShape)
        R.drops.push({ x: d.xAt(ye), y: ye + d.rb * 1.22 * 1.42, r: d.rb * 1.22, v: 120 });
      }
      if (d.t >= d.end) {                         // the last of the run goes after it
        R.drops.push({ x: d.xAt(s.end), y: s.end + s.bead * .72, r: Math.max(s.bead, s.hb), v: 140 });
        R.drip = null; R.wait = rnd(1.8, 4.5);
      }
    }
    for (const p of R.drops) {
      if (p.splat !== undefined) { p.splat += dt; continue; }
      p.v += G * dt; p.y += p.v * dt;
      if (p.y + p.r * .6 >= FLOOR) { p.splat = 0; p.y = FLOOR; }
    }
    R.drops = R.drops.filter(p => p.splat === undefined || p.splat < .5);
  }

  function draw(R, now) {
    const { ctx, cv } = R, k = R.k;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, cv.width, cv.height);
    ctx.setTransform(k, 0, 0, k, -R.x0 * k, -R.y0 * k);
    const d = R.drip, s = d && dripShape(R, d);
    const shape = (g, withDrip = true) => {
      ctx.beginPath();
      if (withDrip && d) dripPath(ctx, R, d, s, g);
      for (const p of R.drops) dropPath(ctx, p, g);
    };
    // 1. the dark line and the soft shadow it throws on the bricks (shadow sizes are device px)
    ctx.save();
    ctx.shadowColor = "rgba(0,0,0,.55)"; ctx.shadowBlur = 12 * k; ctx.shadowOffsetX = -7 * k; ctx.shadowOffsetY = 6 * k;
    ctx.fillStyle = rgb(R.line); shape(R.lw); ctx.fill("nonzero");
    ctx.restore();
    // 2. the blob, breathing: it swells and sags from its top, never smaller than the art's own
    const a = now / 1000 / R.ooze * Math.PI * 2 + R.ph;
    blob(ctx, R, a);
    // 3. the paint: the run's top is painted over the blob's line where it flows out of the tip's
    //    rounded end, so the two are one shape; no higher, so the blob keeps its own shape and shine
    ctx.fillStyle = rgb(R.fill);
    if (d) {
      ctx.save(); ctx.beginPath(); ctx.rect(R.x0, d.tip.y - Math.min(R.lw * 1.3, d.tip.tw * .35), R.x1 - R.x0, R.y1); ctx.clip();
      ctx.beginPath(); dripPath(ctx, R, d, s, 0); ctx.fill("nonzero");
      ctx.restore();
    }
    shape(0, false); ctx.fill("nonzero");
    // 4. the shine: a pale streak down the run's right side, a glint on every bead and drop
    ctx.strokeStyle = ctx.fillStyle = rgb(R.hi); ctx.lineCap = "round";
    if (d && s.end - s.top > d.w) {
      const xAt = d.xAt;
      const ya = Math.max(s.top + s.ht, d.tip.y + R.lw), yb = s.end - Math.max(s.hb, 4);
      if (yb > ya) {
        ctx.lineWidth = d.w * .14; ctx.beginPath();
        for (let i = 0; i <= 12; i++) { const y = ya + (yb - ya) * i / 12; ctx[i ? "lineTo" : "moveTo"](xAt(y) + s.hb * .5 + (s.ht - s.hb) * .3 * (1 - i / 12), y); }
        ctx.stroke();
      }
    }
    const glint = (x, y, r) => { ctx.beginPath(); ctx.ellipse(x + r * .38, y - r * .3, r * .17, r * .3, -.5, 0, Math.PI * 2); ctx.fill(); };
    if (d && s.bead > 3) glint(d.xAt(s.end), s.end + s.bead * .72 + s.beadY, s.bead);
    for (const p of R.drops) if (p.splat === undefined) glint(p.x, p.y, p.r);
    // 5. dimmed exactly as the wall: #bgwall's gradient over everything drawn here
    ctx.globalCompositeOperation = "source-atop";
    const gr = ctx.createLinearGradient(0, R.y0, 0, R.y1);
    gr.addColorStop(0, `rgba(${TINT},${R.dim[0]})`); gr.addColorStop(1, `rgba(${TINT},${R.dim[1]})`);
    ctx.fillStyle = gr; ctx.fillRect(R.x0, R.y0, R.x1 - R.x0, R.y1 - R.y0);
    ctx.globalCompositeOperation = "source-over";
    // 6. the tag's neon on the wet paint: a thin line of its green along every edge that faces the
    //    sign, flickering with the sign. The paint's shape less the same shape a step toward the
    //    light is exactly its lit edge; it is softened (rounded off, and a little of it glancing
    //    past onto the bricks) and screened on, so it lights the paint rather than covering it.
    //    Light, not paint: on after the dimming.
    const L = R.light, lit = L ? Math.min(1.2, L.k) * neon() : 0;
    if (lit > .02) {
      const lc = R.lctx, W = R.lcv.width, H = R.lcv.height;
      lc.setTransform(1, 0, 0, 1, 0, 0); lc.globalCompositeOperation = "source-over"; lc.clearRect(0, 0, W, H);
      lc.setTransform(k, 0, 0, k, -R.x0 * k, -R.y0 * k);
      silhouette(lc, R, d, s, a);
      lc.globalCompositeOperation = "destination-out";
      lc.translate(-L.dx * R.lw * NEON_EDGE.depth, -L.dy * R.lw * NEON_EDGE.depth);
      silhouette(lc, R, d, s, a);
      lc.setTransform(1, 0, 0, 1, 0, 0); lc.globalCompositeOperation = "source-in";
      lc.fillStyle = rgb(NEON); lc.fillRect(0, 0, W, H);
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.globalCompositeOperation = "screen"; ctx.globalAlpha = Math.min(1, lit * NEON_EDGE.alpha);
      ctx.filter = `blur(${(R.lw * NEON_EDGE.soft * k).toFixed(2)}px)`;
      ctx.drawImage(R.lcv, 0, 0);
      ctx.filter = "none"; ctx.globalAlpha = 1; ctx.globalCompositeOperation = "source-over";
    }
  }
  // the neon's line on the paint's lit edge, in widths of the paint's dark line: how deep it
  // reaches in, how far it is softened, and how strong it is where the light is 1
  const NEON_EDGE = { depth: .55, soft: .45, alpha: .45 };   // alpha .45: dimmed with the tag, then 35% brighter (owner, 2026-10-25)

  // the blob's own paint, breathing on its clock a: it swells and sags from its top, never
  // smaller than the art's own
  function blob(c, R, a) {
    if (!R.img.complete || !R.img.naturalWidth) return;
    const [bx, by, bw, bh] = R.box, s1 = .5 - .5 * Math.cos(a);
    c.save();
    c.translate(bx + bw / 2, by + bh * .08);
    c.transform(1.004 + .022 * s1, 0, Math.tan(-.009 * Math.sin(a)), 1.008 + .05 * s1, 0, 0);
    c.drawImage(R.img, -bw / 2, -bh * .08, bw, bh);
    c.restore();
  }
  // all the paint as one shape - the blob, the run and its bead, the drops - out to the outside
  // of the dark line, where the light catches it
  function silhouette(c, R, d, s, a) {
    blob(c, R, a);
    c.beginPath();
    if (d) dripPath(c, R, d, s, R.lw);
    for (const p of R.drops) dropPath(c, p, R.lw);
    c.fill("nonzero");
  }

  // where each blob's light comes from - the way to the tube from its middle - and how strong
  function aimLight() {
    if (!layer || !regions.length) return;
    const lr = layer.getBoundingClientRect();
    if (!lr.width || !lr.height) return;
    for (const R of regions) {
      const [bx, by, bw, bh] = R.box;
      const x = lr.left + (bx + bw / 2) / ART[0] * lr.width, y = lr.top + (by + bh / 2) / ART[1] * lr.height;
      const L = light(x, y);
      if (!L) { R.light = null; continue; }
      const dx = L.x - x, dy = L.y - y, dd = Math.hypot(dx, dy) || 1;
      R.light = { dx: dx / dd, dy: dy / dd, k: L.k };
    }
  }

  function frame(now) {
    raf = requestAnimationFrame(frame);
    // 30 times a second, like the rims: slow paint needs no more, and on a high-refresh screen
    // every display frame (144, 165 a second) was redrawing every canvas
    if (last && now - last < 1000 / 30 - 2) return;
    const dt = Math.min(.05, last ? (now - last) / 1000 : 0); last = now;
    if (now - aimed > 2000) { aimed = now; aimLight(); }   // the tag wanders and the layout moves: keep aiming
    for (const R of regions) { step(R, dt, now); draw(R, now); }
  }
  let aimed = 0;

  // ------------------------------------------------------------------ layout
  function place() {
    const wall = document.getElementById("bgwall");
    if (!wall || !layer) return;
    const W = wall.clientWidth, H = wall.clientHeight;
    if (!W || !H) return;
    const mode = getComputedStyle(document.documentElement).getPropertyValue("--wall-scale").trim() || "contain";
    const s = (mode === "cover" ? Math.max : Math.min)(W / ART[0], H / ART[1]);
    const w = ART[0] * s, h = ART[1] * s, left = (W - w) / 2, top = (H - h) / 2;
    Object.assign(layer.style, { left: left + "px", top: top + "px", width: w + "px", height: h + "px" });
    const dpr = Math.min(devicePixelRatio || 1, 2);
    for (const R of regions) {
      R.k = s * dpr;
      R.cv.width = Math.max(1, Math.round((R.x1 - R.x0) * R.k)); R.cv.height = Math.max(1, Math.round((R.y1 - R.y0) * R.k));
      R.lcv.width = R.cv.width; R.lcv.height = R.cv.height;
      // the wall's gradient runs down #bgwall's own box: its strength at this canvas's top and bottom
      R.dim = [R.y0, R.y1].map(y => DIM[0] + (DIM[1] - DIM[0]) * clamp((top + y * s) / H, 0, 1));
    }
    aimLight();
  }

  async function start() {
    layer = document.getElementById("wallpaint");
    if (!layer || REDUCED) return;               // reduced motion: the art's own paint, still
    let meta;
    try { meta = await (await fetch("assets/wallfx/wallfx.json")).json(); } catch (e) { return; }
    regions = meta.blobs.map(makeRegion);
    for (const R of regions) layer.appendChild(R.cv);
    place();
    loadGlow().then(aimLight);
    addEventListener("resize", place);
    if (window.ResizeObserver) new ResizeObserver(place).observe(document.getElementById("bgwall"));
    if (!raf) raf = requestAnimationFrame(frame);
  }
  loadGlow();   // the light is read off the tube once, for the paint here and for the characters
  window.WallFX = { start, place, regions: () => regions, light, neon };
})();
