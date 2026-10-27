// The skull's cigar smoke, live (owner, 2026-10-24: the painted plume was the picture copied over
// itself and faded; it is cut off the figure and the smoke is made to move like smoke).
//
// A stream of particles leaves the ember. Off the cigar it is a thin clean thread; as it climbs
// it warms, quickens and starts to turn in a swirling draft (the curl of a few travelling waves:
// it folds and curls the smoke without bunching or thinning it), so the thread wavers, rolls
// over into curls and billows, and puffs of it break away; at the top every puff gives way to a
// soft haze that keeps spreading as it thins out into the air (owner, 2026-10-25: more like real
// smoke - it was shrinking away like a balloon going down). Particles keep to the air, not the
// skull, so when the head turns or bobs the stream bends behind it the way real smoke does.
//
// It is drawn in the characters' own cartoon paint: every particle is three discs - the ink line,
// a cool grey shade, and a pale fill set up and to the left - drawn layer by layer, so overlapping
// discs merge into one outlined shape whose lower-right rim is shaded, like the plume the art had;
// behind them, a soft haze round every puff. The line fades in off the ember (a fresh thread is
// faint) and thins away as the smoke ages, so the curls are drawn and the spent smoke is soft.
// In the rig's own Pixi scene, over the figure, so it takes the figure's lean, turn, fade and walk-off.
(function () {
  "use strict";
  const TAU = Math.PI * 2;
  const smooth = v => (v = Math.max(0, Math.min(1, v)), v * v * (3 - 2 * v));
  const rnd = (a, b) => a + Math.random() * (b - a);

  // the swirl: travelling stream-function waves, in skeleton units - wavelength, the speed it
  // turns the smoke at, how fast it changes, and its heading
  const WAVES = [
    { l: 170, v: 120, w: .9, d: .3 }, { l: 110, v: 90, w: -1.4, d: 2.1 },
    { l: 260, v: 70, w: .5, d: 4.0 }, { l: 75, v: 55, w: 2.1, d: 1.2 }, { l: 140, v: 80, w: -.7, d: 5.3 },
  ].map(W => Object.assign(W, { ph: rnd(0, TAU), kx: Math.cos(W.d), ky: Math.sin(W.d) }));

  // cigar smoke is a cool blue-grey, not paper white
  const LOOK = { haze: 0xb7bcc8, line: 0x18191e, shade: 0x9fa4b1, fill: 0xebedf2 };
  const LAYERS = ["haze", "line", "shade", "fill"];   // drawn back to front
  const RATE = 60;          // particles a second off the ember (of the smoke's own, slowed time)
  const PACE = .35;         // the smoke runs at 35% speed: 65% slower (owner, 2026-10-24) - a lazy curl
  const ALPHA = .8;         // slightly see-through, the whole plume as one layer (owner, 2026-10-24)
  const HAZE = .1;          // one haze disc's strength: a few overlap at any point of the ribbon
  // how long the smoke lasts, by when it left the cigar: it varies slowly along the stream, never
  // particle to particle - neighbours that ended at different moments broke the top into beads
  const lifeAt = tb => 3.6 + .3 * Math.sin(tb * .61) + .15 * Math.sin(tb * 1.7 + 2);
  // the waver: the stream swings side to side at the cigar's pace, and every bit keeps the swing
  // it left with, growing as it climbs - an S-wave running up the column, the way a cigar's
  // thread wavers before it breaks into curls
  const swayAt = tb => Math.sin(tb * 2.6 + .4) + .45 * Math.sin(tb * 6.1 + 2.7) + .2 * Math.sin(tb * 11.3);

  function disc(soft) {     // one white disc every layer tints: crisp (antialiased), or soft to its rim
    const c = document.createElement("canvas"); c.width = c.height = 128;
    const g = c.getContext("2d");
    if (soft) {
      const gr = g.createRadialGradient(64, 64, 0, 64, 64, 62);
      gr.addColorStop(0, "rgba(255,255,255,1)"); gr.addColorStop(.55, "rgba(255,255,255,.55)"); gr.addColorStop(1, "rgba(255,255,255,0)");
      g.fillStyle = gr;
    } else g.fillStyle = "#fff";
    g.beginPath(); g.arc(64, 64, 62, 0, TAU); g.fill();
    return PIXI.Texture.from(c);
  }

  function attach(app, actor, cfg) {
    const sk = actor.skeleton;
    // the painted plume comes off the figure
    for (const n of cfg.hide || []) {
      const s = sk.findSlot(n);
      if (s) { s.data.attachmentName = null; s.setAttachment(null); }
    }
    const bone = sk.findBone(cfg.from || "ember");
    if (!bone) return;
    const tex = disc(false), soft = disc(true);
    const root = new PIXI.Container(), layers = {};
    // back to front; no white sticker edge since the skull lost his (2026-10-25). Every disc is a
    // particle, each layer one batch written straight into its buffer: as ~2,000 sprites in the
    // scene the plume cost the skull's frame more than the rest of him together
    for (const k of LAYERS) {
      layers[k] = new PIXI.ParticleContainer({ texture: k === "haze" ? soft : tex, dynamicProperties: { position: true, vertex: true, color: true } });
      root.addChild(layers[k]);
    }
    app.stage.addChild(root);
    // the plume fades as one picture, so where its puffs overlap they do not show through each other.
    // A particle batch has no bounds of its own, so the fade is told it covers the stage
    if (PIXI.AlphaFilter) {
      root.filters = [new PIXI.AlphaFilter({ alpha: ALPHA })];
      const area = () => { root.filterArea = new PIXI.Rectangle(0, 0, app.screen.width, app.screen.height); };
      area(); app.renderer.on("resize", area);
    } else root.alpha = ALPHA;

    // where the ember is, after the rig poses each frame (in the stage's px)
    const at = { x: 0, y: 0, ok: false };
    const prev = actor.afterUpdateWorldTransforms;
    actor.afterUpdateWorldTransforms = o => {
      if (prev) prev(o);
      const p = { x: bone.worldX, y: bone.worldY };
      actor.skeletonToPixiWorldCoordinates(p);
      at.x = p.x; at.y = p.y; at.ok = true;
    };

    const parts = [];
    let t = 0, owed = 0, last = null;
    const spawn = (x, y, vx, vy, puff) => {
      const p = { x, y, vx, vy, age: 0, life: 3, puff, sway: 0, r: 0, rh: 0, u: 0 };
      parts.push(p);
      return p;
    };
    // the drawing: a stamp is one disc in every layer; the stream is stamped at every particle
    // and, wherever the draft has pulled two neighbours further apart than they are wide, in
    // between them too - so it is always one ribbon, never a string of bubbles - unless it is
    // stretched so thin that it tears, and then it comes apart into wisps with round ends
    // the discs, made once and reused frame to frame; each frame a layer lists only those it shows
    const pool = {}, shown = {};
    for (const k of LAYERS) { pool[k] = []; shown[k] = layers[k].particleChildren; }
    const put = (k, x, y, scale, alpha) => {
      const list = shown[k];
      let p = pool[k][list.length];
      if (!p) { p = new PIXI.Particle({ texture: k === "haze" ? soft : tex, anchorX: .5, anchorY: .5, tint: LOOK[k] }); pool[k].push(p); }
      p.x = x; p.y = y; p.scaleX = p.scaleY = scale; p.alpha = alpha;
      list.push(p);
    };
    let used = 0;
    const MAX_STAMPS = 900, PX = 1 / 62;   // the disc's radius in its texture
    // one stamp: the puff (line, shade, fill) at r - none once it has given way - and its haze at rh;
    // u is how far through its life the smoke there is
    const stamp = (x, y, r, rh, u, S, MIN) => {
      if (used >= MAX_STAMPS) return;
      used++;
      const body = r > MIN;
      // the ink line comes in off the ember and thins away as the smoke ages
      const ink = smooth(u / .12) * (1 - smooth((u - .5) / .35)), o = S * (3.6 + .08 * r / S) * ink;
      if (body && o > S * .2) put("line", x, y, (r + o) * PX, 1);
      if (body) { put("shade", x, y, r * PX, 1); put("fill", x - r * .2, y - r * .22, r * .8 * PX, 1); }
      // the haze: from the billows on, spreading, and gone by the end of the smoke's life
      const hz = smooth((u - .25) / .3) * (1 - smooth((u - .72) / .28));
      if (hz > .02) put("haze", x, y, rh * PX, HAZE * hz);
    };

    app.ticker.add(tk => {
      const dt = Math.min(.05, tk.deltaMS / 1000) * PACE;
      if (!at.ok || !dt) return;
      t += dt;
      const S = Math.abs(actor.scale.x) || 1;   // px per skeleton unit
      // the stream: emitted along the ember's path since the last frame, so a quick turn of the
      // head leaves a continuous thread, not dots; the thickness swells and thins in slow pulses
      // (the draw on the cigar), which is what rolls up into the billows further up
      const from = last || { x: at.x, y: at.y };
      const evx = (at.x - from.x) / dt, evy = (at.y - from.y) / dt;
      owed += RATE * dt;
      const n = Math.floor(owed); owed -= n;
      for (let i = 0; i < n; i++) {
        // born part-way through the frame: already that much older and on its way, so the
        // stream is a continuous thread whatever the frame rate, never a string of beads
        const f = (i + 1) / n, early = (1 - f) * dt, te = t - early;
        // round lobes along the billows, like the plume the art had
        const puff = 1 + .34 * Math.sin(te * 1.9) + .22 * Math.sin(te * 4.7 + 1.1) + .16 * Math.sin(te * 8.3 + 2.3);
        const p = spawn(from.x + (at.x - from.x) * f, from.y + (at.y - from.y) * f - 4 * S,
          evx * .25, evy * .25 - 40 * S, Math.max(.55, puff));
        p.age = early; p.x += p.vx * early; p.y += p.vy * early;
        p.life = lifeAt(te); p.sway = swayAt(te);
      }
      last = { x: at.x, y: at.y };
      // a slow draft across the street, leaning the column one way and then the other. It acts
      // on the smoke as it ages (below), so the thread still rises straight past his face and it
      // is the billows that lean - mostly over his beanie, away from the board's edge
      const draft = S * (10 + 8 * Math.sin(t * .19 + .7) + 5 * Math.sin(t * .47 + 2.2));
      for (let i = parts.length - 1; i >= 0; i--) {
        const p = parts[i];
        p.age += dt;
        const u = p.age / p.life;
        if (u >= 1) { parts.splice(i, 1); continue; }
        // the swirl's pull at this spot, at this moment
        let cx = 0, cy = 0;
        for (const W of WAVES) {
          const k = TAU / (W.l * S), c = Math.cos(k * (W.kx * p.x + W.ky * p.y) + W.w * t + W.ph) * W.v * S;
          cx += W.ky * c; cy -= W.kx * c;
        }
        // none at the ember - a clean thread up past his face - then more and more once it has
        // broken into curls above the beanie
        const tb = smooth((u - .36) / .38) * 1.15;
        const rise = S * (85 + 270 * smooth(p.age / 1.2)) * (1 - .3 * u);
        // the waver's sideways push, strongest while the thread swings, easing as it billows
        const wave = S * 40 * p.sway * smooth(u / .25) * (1 - .6 * smooth((u - .5) / .4));
        const tx = draft * smooth(u * 2) + wave + cx * tb, ty = -rise + cy * tb;
        const k = Math.min(1, dt * 2.4);
        p.vx += (tx - p.vx) * k; p.vy += (ty - p.vy) * k;
        p.x += p.vx * dt; p.y += p.vy * dt;
        // a thin thread off the ember, then swelling into billows (in puffs, the draw on the
        // cigar); at the end the drawn puff gives way and its haze goes on spreading into the air
        const grow = S * (2.8 + p.puff * 40 * smooth((u - .3) / .42));
        p.r = grow * (1 - smooth((u - .66) / .26));
        p.rh = (grow + S * 34 * smooth((u - .45) / .55)) * 1.35;
        p.u = u;
      }
      used = 0;
      for (const k of LAYERS) shown[k].length = 0;
      const MIN = S * 1.2;
      // which neighbours still hold together (both drawn, not torn apart)
      const linked = (a, b) => b && Math.min(a.r, b.r) > MIN && Math.hypot(b.x - a.x, b.y - a.y) <= Math.min(a.r, b.r) * 9;
      for (let i = 0; i < parts.length; i++) {
        const a = parts[i], b = parts[i + 1], toNext = linked(a, b);
        // a speck left on its own where a wisp tore reads as a bubble: only a real puff stands alone;
        // a spent puff is its haze alone
        const own = a.r > MIN && (toNext || linked(a, parts[i - 1]) || a.r > S * 7);
        if (own || a.u > .6) stamp(a.x, a.y, own ? a.r : 0, a.rh, a.u, S, MIN);
        if (!toNext) continue;
        const rm = Math.min(a.r, b.r), d = Math.hypot(b.x - a.x, b.y - a.y);
        const n = Math.ceil(d / (rm * .55)) - 1;
        for (let j = 1; j <= n; j++) {
          const f = j / (n + 1);
          stamp(a.x + (b.x - a.x) * f, a.y + (b.y - a.y) * f, a.r + (b.r - a.r) * f, a.rh + (b.rh - a.rh) * f, a.u + (b.u - a.u) * f, S, MIN);
        }
      }
      for (const k of LAYERS) layers[k].update();   // the lists changed: each batch is rebuilt from them
    });
    return (window.__cigarSmoke = { parts: () => parts.length, stamps: () => used });   // QA handle
  }

  window.CigarSmoke = { attach };
})();
