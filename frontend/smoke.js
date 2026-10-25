// The skull's cigar smoke, live (owner, 2026-10-24: the painted plume was the picture copied over
// itself and faded; it is cut off the figure and the smoke is made to move like smoke).
//
// A stream of particles leaves the ember. Off the cigar it is a thin clean thread; as it climbs
// it warms, quickens and starts to turn in a swirling draft (the curl of a few travelling waves:
// it folds and curls the smoke without bunching or thinning it), so the thread wavers, rolls
// over into curls and billows, and puffs of it break away; at the top every puff shrinks away
// to nothing. Particles keep to the air, not the skull, so when the head turns or bobs the
// stream bends behind it the way real smoke does.
//
// It is drawn in the characters' own cartoon paint: every particle is four discs - the white
// sticker edge, the black line, a grey shade, and a white fill set up and to the left - drawn
// layer by layer, so overlapping discs merge into one outlined shape whose lower-right rim is
// shaded, like the plume the art had. In the rig's own Pixi scene, over the figure, so it takes
// the figure's lean, turn, fade and walk-off.
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

  const LOOK = { sticker: 0xffffff, line: 0x141416, shade: 0xa8a8ae, fill: 0xf6f6f8 };
  const RATE = 60;          // particles a second off the ember
  // how long the smoke lasts, by when it left the cigar: it varies slowly along the stream, never
  // particle to particle - neighbours that ended at different moments broke the top into beads
  const lifeAt = tb => 3.6 + .3 * Math.sin(tb * .61) + .15 * Math.sin(tb * 1.7 + 2);
  // the waver: the stream swings side to side at the cigar's pace, and every bit keeps the swing
  // it left with, growing as it climbs - an S-wave running up the column, the way a cigar's
  // thread wavers before it breaks into curls
  const swayAt = tb => Math.sin(tb * 2.6 + .4) + .45 * Math.sin(tb * 6.1 + 2.7) + .2 * Math.sin(tb * 11.3);

  function disc() {         // one antialiased white disc every layer tints
    const c = document.createElement("canvas"); c.width = c.height = 128;
    const g = c.getContext("2d"); g.fillStyle = "#fff"; g.beginPath(); g.arc(64, 64, 62, 0, TAU); g.fill();
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
    const tex = disc();
    const root = new PIXI.Container(), layers = {};
    for (const k of ["sticker", "line", "shade", "fill"]) { layers[k] = new PIXI.Container(); root.addChild(layers[k]); }
    app.stage.addChild(root);

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
      const p = { x, y, vx, vy, age: 0, life: 3, puff, sway: 0, r: 0 };
      parts.push(p);
      return p;
    };
    // the drawing: a stamp is one disc in every layer; the stream is stamped at every particle
    // and, wherever the draft has pulled two neighbours further apart than they are wide, in
    // between them too - so it is always one ribbon, never a string of bubbles - unless it is
    // stretched so thin that it tears, and then it comes apart into wisps with round ends
    const stamps = [];
    let used = 0;
    const MAX_STAMPS = 900, PX = 1 / 62;   // the disc's radius in its texture
    const stamp = (x, y, r, S) => {
      if (used >= MAX_STAMPS) return;
      let sp = stamps[used];
      if (!sp) {
        sp = {};
        for (const k in layers) { const s2 = new PIXI.Sprite(tex); s2.anchor.set(.5); s2.tint = LOOK[k]; layers[k].addChild(s2); sp[k] = s2; }
        stamps.push(sp);
      }
      used++;
      const o = S * (4.5 + .1 * r / S), st = S * 3;
      sp.sticker.position.set(x, y); sp.sticker.scale.set((r + o + st) * PX);
      sp.line.position.set(x, y); sp.line.scale.set((r + o) * PX);
      sp.shade.position.set(x, y); sp.shade.scale.set(r * PX);
      sp.fill.position.set(x - r * .2, y - r * .22); sp.fill.scale.set(r * .8 * PX);
      for (const k in sp) sp[k].visible = true;
    };

    app.ticker.add(tk => {
      const dt = Math.min(.05, tk.deltaMS / 1000);
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
      // a slow draft across the street, leaning the column one way and then the other - mostly
      // a little to his right (the screen's left), up past his face rather than across it
      const draft = S * (-6 + 12 * Math.sin(t * .19 + .7) + 6 * Math.sin(t * .47 + 2.2));
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
        // cigar), then shrinking away to nothing as it spreads
        p.r = S * (4 + p.puff * 40 * smooth((u - .3) / .42)) * (1 - smooth((u - .72) / .28));
      }
      used = 0;
      const MIN = S * 1.2;
      // which neighbours still hold together (both drawn, not torn apart)
      const linked = (a, b) => b && Math.min(a.r, b.r) > MIN && Math.hypot(b.x - a.x, b.y - a.y) <= Math.min(a.r, b.r) * 9;
      for (let i = 0; i < parts.length; i++) {
        const a = parts[i], b = parts[i + 1], toNext = linked(a, b);
        // a speck left on its own where a wisp tore reads as a bubble: only a real puff stands alone
        if (a.r > MIN && (toNext || linked(a, parts[i - 1]) || a.r > S * 7)) stamp(a.x, a.y, a.r, S);
        if (!toNext) continue;
        const rm = Math.min(a.r, b.r), d = Math.hypot(b.x - a.x, b.y - a.y);
        const n = Math.ceil(d / (rm * .55)) - 1;
        for (let j = 1; j <= n; j++) {
          const f = j / (n + 1);
          stamp(a.x + (b.x - a.x) * f, a.y + (b.y - a.y) * f, a.r + (b.r - a.r) * f, S);
        }
      }
      for (let i = used; i < stamps.length; i++) for (const k in stamps[i]) stamps[i][k].visible = false;
    });
    return (window.__cigarSmoke = { parts: () => parts.length, stamps: () => used });   // QA handle
  }

  window.CigarSmoke = { attach };
})();
