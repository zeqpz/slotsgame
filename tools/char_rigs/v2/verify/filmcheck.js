// node filmcheck.js <root> <char> <outdir> [N=24] [scale=.5] [clips,..]
// Every clip at N evenly spaced times, alpha kept (transparent background), plus meta.json.
// The skull is filmed with ember_loop on track 1 (as the game runs it).
const K = require('./labkit.js'); const fs = require('fs'); const path = require('path');
const [root, char, outdir, N0, S0, ONLY0] = process.argv.slice(2);
const N = +(N0 || 24), S = +(S0 || .5), ONLY = ONLY0 ? ONLY0.split(',') : null;
(async () => {
  const W = 1000, H = 1000;
  const { browser, page } = await K.open({ w: W, h: H });
  const anims = await K.load(page, 'r', root, char, {});
  await page.evaluate(() => { lab.show('r'); document.body.style.background = 'transparent'; document.documentElement.style.background = 'transparent'; });
  const out = path.join(K.HERE, 'shots', outdir); fs.mkdirSync(out, { recursive: true });
  const cy = char === 'smoke-skull' ? 740 : 810;
  await page.evaluate(([s, cy, W, H]) => lab.view('r', s, 0, -cy, W / 2, H / 2), [S, cy, W, H]);
  const meta = { char, root, anims, scale: S, cy, frames: [] };
  const hide = char === 'smoke-skull' ? ['smoke', 'wisp_a', 'wisp_b'] : [];
  for (const [anim, dur] of anims) {
    if (ONLY && !ONLY.includes(anim)) continue;
    if (['smoke_loop', 'ember_loop', 'cash_toss', 'cash_toss_alt_1', 'cash_toss_alt_2', 'cash_toss_alt_3'].includes(anim)) continue;
    for (let i = 0; i < N; i++) {
      const t = dur * i / (N - 1);
      const amb = char === 'smoke-skull' && anims.some(a => a[0] === 'ember_loop') ? [[2, 'ember_loop', t]] : [];
      await page.evaluate(([a, t, amb, hide]) => {
        lab.pose('r', a, t, amb);
        const r = lab.rigs().r, sk = r.actor.skeleton;
        for (const n of hide) { const s = sk.findSlot(n); if (s) s.color.a = 0; }
        r.actor._stateChanged = true; if (r.actor.onViewUpdate) r.actor.onViewUpdate();
      }, [anim, t, amb, hide]);
      const tag = `${char}__${anim}__${String(i).padStart(2, '0')}`;
      await page.evaluate(() => lab.render());
      await page.screenshot({ path: path.join(out, tag + '.png'), clip: { x: 0, y: 0, width: W, height: H }, omitBackground: true });
      const mot = await page.evaluate(() => { const sk = lab.rigs().r.actor.skeleton; const b = sk.findBone('motion') || sk.findBone('root');
        return [b.a, b.b, b.c, b.d, b.worldX, b.worldY]; });
      meta.frames.push({ anim, i, t, tag, motion: mot });
    }
  }
  fs.writeFileSync(path.join(out, 'meta.json'), JSON.stringify(meta));
  console.log('filmed', meta.frames.length, 'frames ->', out);
  await browser.close();
})();
