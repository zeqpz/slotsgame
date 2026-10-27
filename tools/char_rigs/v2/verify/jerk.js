// node jerk.js <root> <char> <out.json> [clips]
// The game's playback: idle, then the clip, then idle again (state timeScale .8, defaultMix .2, 60 fps).
// Per bone: the largest frame-to-frame change of velocity (second difference of the drawn world position,
// px at a 1600 px tall figure), and the RMS of the third difference (jerk), over the whole sequence.
const K = require('./labkit.js'); const fs = require('fs');
const [root, char, out, ONLY0] = process.argv.slice(2);
(async () => {
  const { browser, page } = await K.open({ w: 400, h: 400 });
  const anims = await K.load(page, 'r', root, char, {});
  const clips = (ONLY0 ? ONLY0.split(',') : anims.map(a => a[0])).filter(n => anims.some(a => a[0] === n));
  const res = await page.evaluate(([clips, char]) => {
    const { actor, data } = lab.rigs().r;
    const st = actor.state, sk = actor.skeleton;
    const H = data.height || 1500, k = 1600 / H;
    const out = {};
    for (const clip of clips) {
      if (clip === 'idle' || clip.startsWith('cash_toss') || clip === 'smoke_loop' || clip === 'ember_loop') continue;
      st.clearTracks(); sk.setToSetupPose(); st.timeScale = .8; st.data.defaultMix = .2;
      st.setAnimation(0, 'idle', true);
      if (char === 'smoke-skull' && data.findAnimation('ember_loop')) st.setAnimation(1, 'ember_loop', true);
      const dur = data.findAnimation(clip).duration, N = Math.round((1.5 + dur / .8 + 1.0) * 60);
      const P = [];
      for (let f = 0; f <= N; f++) {
        if (f === 90) { st.setAnimation(0, clip, false); st.addAnimation(0, 'idle', true, 0); }
        if (f) st.update(1 / 60);
        st.apply(sk); sk.updateWorldTransform(spine.Physics.update);
        P.push(sk.bones.map(b => [b.worldX * k, b.worldY * k]));
      }
      const names = sk.bones.map(b => b.data.name), per = [];
      const skipBone = /^(wisp|smoke|ash_|ember)/;
      const clipEnd = 90 + Math.round(dur / .8 * 60);
      // enter starts from (and exit ends on) the hidden pose, behind the canvas fade: their first / last 0.15 s are not judged
      const skipF = f => (clip === 'enter' && f >= 90 && f < 99) || (clip === 'exit' && f > clipEnd - 9);
      for (let i = 0; i < names.length; i++) {
        if (skipBone.test(names[i])) continue;
        let acc = 0, accAt = 0, j2 = 0, nj = 0;
        for (let f = 3; f <= N; f++) {
          if (skipF(f) || skipF(f - 1) || skipF(f - 2) || skipF(f - 3)) continue;
          const ax = P[f][i][0] - 2 * P[f - 1][i][0] + P[f - 2][i][0], ay = P[f][i][1] - 2 * P[f - 1][i][1] + P[f - 2][i][1];
          const a = Math.hypot(ax, ay); if (a > acc) { acc = a; accAt = f; }
          const jx = P[f][i][0] - 3 * P[f - 1][i][0] + 3 * P[f - 2][i][0] - P[f - 3][i][0];
          const jy = P[f][i][1] - 3 * P[f - 1][i][1] + 3 * P[f - 2][i][1] - P[f - 3][i][1];
          j2 += jx * jx + jy * jy; nj++;
        }
        per.push([names[i], +acc.toFixed(3), +((accAt - 90) / 60 * .8).toFixed(3), +Math.sqrt(j2 / nj).toFixed(4)]);
      }
      per.sort((a, b) => b[1] - a[1]);
      out[clip] = { all: per, top: per.slice(0, 6), maxAcc: per[0][1], rmsJerkMean: +(per.reduce((s, p) => s + p[3], 0) / per.length).toFixed(4),
                    rmsJerkMax: Math.max(...per.map(p => p[3])) };
    }
    return out;
  }, [clips, char]);
  fs.writeFileSync(out, JSON.stringify(res, null, 1));
  for (const [c, r] of Object.entries(res)) console.log(c.padEnd(13), 'max accel', String(r.maxAcc).padStart(7), 'px/f^2 (', r.top[0][0], 'at', r.top[0][2], 's)  rms jerk mean', r.rmsJerkMean, 'max', r.rmsJerkMax);
  await browser.close();
})();
