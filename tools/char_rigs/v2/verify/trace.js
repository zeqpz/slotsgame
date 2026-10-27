// node trace.js <root> <char> <clip> <bone> <t0> <t1>: per 60 fps frame (game playback) the bone's world pos and chain locals
const K = require('./labkit.js');
const [root, char, clip, bone, t0, t1] = process.argv.slice(2);
(async () => {
  const { browser, page } = await K.open({ w: 300, h: 300 });
  await K.load(page, 'r', root, char, {});
  const rows = await page.evaluate(([clip, bone, t0, t1]) => {
    const { actor, data } = lab.rigs().r; const st = actor.state, sk = actor.skeleton;
    st.clearTracks(); sk.setToSetupPose(); st.timeScale = .8; st.data.defaultMix = .2;
    st.setAnimation(0, 'idle', true);
    const dur = data.findAnimation(clip).duration, N = Math.round((1.5 + dur / .8 + 1.0) * 60), out = [];
    for (let f = 0; f <= N; f++) {
      if (f === 90) { st.setAnimation(0, clip, false); st.addAnimation(0, 'idle', true, 0); }
      if (f) st.update(1 / 60);
      st.apply(sk); sk.updateWorldTransform(spine.Physics.update);
      const ct = (f - 90) / 60 * .8;
      if (ct >= t0 && ct <= t1) {
        const b = sk.findBone(bone), h = sk.findBone('head'), be = sk.findBone('beanie');
        out.push([+ct.toFixed(3), +b.worldX.toFixed(2), +b.worldY.toFixed(2), +h.rotation.toFixed(2), +h.scaleX.toFixed(4), +h.scaleY.toFixed(4), +be.rotation.toFixed(2), +b.rotation.toFixed(2), +h.y.toFixed(2)]);
      }
    }
    return out;
  }, [clip, bone, +t0, +t1]);
  let p = null, q = null;
  for (const r of rows) { const a = p && q ? Math.hypot(r[1] - 2 * p[1] + q[1], r[2] - 2 * p[2] + q[2]) : 0; console.log(r.join('\t'), '\tacc', a.toFixed(2)); q = p; p = r; }
  await browser.close();
})();
