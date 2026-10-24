// The live wall (assets/wallfx, tools/sprayrim/make_wall_fx.py):
// - the paint oozes out of the cracked holes: each blob of the wall art is laid over itself and
//   slowly swells and sags, and runs of paint grow down from its tips, a drop gathering at the end
//   of each and falling to the pavement, then the run thins away and the next one starts;
// - the SMUKIEZ tag's green outline glows like neon (#tagglow) and throws its light on the bricks
//   round it (#tagspill) - both CSS, they ride the tag's wander, hop and pop (index.html).
// Everything here is plain elements on CSS animations: it costs no script per frame.
(function () {
  "use strict";
  const ART = [3840, 2167];                     // bonus_wall.webp
  const FLOOR = .875;                           // the pavement's edge, as a fraction of the art's height
  let meta = null;

  function place() {
    const wall = document.getElementById("bgwall"), layer = document.getElementById("wallpaint");
    if (!wall || !layer) return;
    const W = wall.clientWidth, H = wall.clientHeight;
    if (!W || !H) return;
    const mode = getComputedStyle(document.documentElement).getPropertyValue("--wall-scale").trim() || "contain";
    const s = (mode === "cover" ? Math.max : Math.min)(W / ART[0], H / ART[1]);
    const w = ART[0] * s, h = ART[1] * s;
    Object.assign(layer.style, { left: (W - w) / 2 + "px", top: (H - h) / 2 + "px", width: w + "px", height: h + "px" });
  }

  function build() {
    const layer = document.getElementById("wallpaint");
    if (!layer || !meta) return;
    const pct = v => (v * 100).toFixed(3) + "%";
    meta.blobs.forEach((b, i) => {
      const im = document.createElement("img");
      im.className = "wblob"; im.alt = ""; im.draggable = false;
      im.src = `assets/wallfx/blob_${i}.webp`;
      Object.assign(im.style, { left: pct(b.x), top: pct(b.y), width: pct(b.w), height: pct(b.h) });
      im.style.setProperty("--ooze", (5.5 + Math.random() * 3.5).toFixed(2) + "s");
      im.style.setProperty("--od", (-Math.random() * 6).toFixed(2) + "s");
      layer.appendChild(im);
      for (const [x, y, tw] of b.tips) {
        // a run from this tip: as wide as the paint there, long enough to fall a brick or two
        const cyc = 7 + Math.random() * 6, delay = -Math.random() * cyc;
        const run = document.createElement("i");
        run.className = "wdrip " + b.colour;
        const len = .045 + Math.random() * .05;            // of the art's height
        const wid = Math.max(.0035, Math.min(tw * .8, .009));
        Object.assign(run.style, { left: pct(x - wid / 2), top: pct(y - .004), width: pct(wid), height: pct(len) });
        run.style.setProperty("--cyc", cyc.toFixed(2) + "s"); run.style.setProperty("--dl", delay.toFixed(2) + "s");
        layer.appendChild(run);
        const drop = document.createElement("i");
        drop.className = "wdrop " + b.colour;
        const dw = wid * 1.5, dh = dw * ART[0] / ART[1];   // a round drop: its height as a fraction of the art's
        Object.assign(drop.style, { left: pct(x - dw / 2), top: pct(y + len - dh * .6), width: pct(dw), height: pct(dh) });
        drop.style.setProperty("--fall", ((FLOOR - (y + len)) / dh * 100).toFixed(1) + "%");   // to the pavement, in its own heights
        drop.style.setProperty("--cyc", cyc.toFixed(2) + "s"); drop.style.setProperty("--dl", delay.toFixed(2) + "s");
        layer.appendChild(drop);
      }
    });
    place();
  }

  async function start() {
    try { meta = await (await fetch("assets/wallfx/wallfx.json")).json(); } catch (e) { return; }
    build();
    addEventListener("resize", place);
    if (window.ResizeObserver) new ResizeObserver(place).observe(document.getElementById("bgwall"));
  }
  window.WallFX = { start, place };
})();
