// node render.js <jobs.json>
// jobs: [{root, char, anim|null, t, out, W, H, scale, cx, cy, hide:[slots], only:[slots], bg:'transparent'|'#rrggbb', amb:[[track, anim, t]]}]
// (cx, cy) = skeleton point (y up) placed at the canvas centre; scale = px per skeleton unit.
const K = require('./labkit.js');
const fs = require('fs');
const jobs = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
(async () => {
  const W = Math.max(...jobs.map(j => j.W)), H = Math.max(...jobs.map(j => j.H));
  const { browser, page } = await K.open({ w: W, h: H });
  const loaded = {};
  for (const j of jobs) {
    const key = j.root + ':' + j.char;
    if (!loaded[key]) {
      loaded[key] = await K.load(page, key, j.root, j.char, {});
    }
    await page.evaluate(k => lab.show(k), key);
    await page.evaluate(([k, a, t, amb]) => lab.pose(k, a, t, amb), [key, j.anim || null, j.t || 0, j.amb || []]);
    await page.evaluate(([k, hide, only]) => {
      const sk = lab.rigs()[k].actor.skeleton;
      sk.slots.forEach(s => {
        const n = s.data.name;
        if ((hide && hide.includes(n)) || (only && !only.includes(n))) s.color.a = 0;
      });
      const a = lab.rigs()[k].actor; a._stateChanged = true; if (a.onViewUpdate) a.onViewUpdate();
    }, [key, j.hide || null, j.only || null]);
    // runtime y is down: skeleton (cx, cy) -> runtime (cx, -cy)
    await page.evaluate(([k, s, cx, cy, w, h]) => lab.view(k, s, cx, -cy, w / 2, h / 2), [key, j.scale, j.cx, j.cy, j.W, j.H]);
    await page.evaluate(bg => { document.body.style.background = bg; document.documentElement.style.background = bg; }, j.bg || 'transparent');
    await page.evaluate(() => lab.render());
    await page.screenshot({ path: j.out, clip: { x: 0, y: 0, width: j.W, height: j.H }, omitBackground: (j.bg || 'transparent') === 'transparent' });
    console.log('wrote', j.out);
  }
  await browser.close();
})();
