// node gameshot.js <old|new|repo> <out.png> [W=1440] [H=900] [dpr=1] [mobile=0] [clip=idle] [t=0]
// The real game (fakergs, no server), the characters frozen on one pose so before and after line up.
// 'old' serves the backed-up rigs, 'new' the scratch build, 'repo' whatever frontend/assets/spine holds.
const { chromium } = require('C:/Users/CooperHinkel/Documents/ClaudeRoblox/.tools/pw/node_modules/playwright');
const RGS = require('./fakergs.js'); const path = require('path'); const fs = require('fs');
const [which, out, W0, H0, D0, MOB, CLIP, T0] = process.argv.slice(2);
const W = +(W0 || 1440), H = +(H0 || 900), DPR = +(D0 || 1), mobile = MOB === '1', clip = CLIP || 'idle', T = +(T0 || 0);
const SRC = { old: process.env.SMUKIEZ_RIG_BEFORE || path.join(require('os').tmpdir(), 'smukiez-chars-v2', 'before') }[which];   // 'new'/'repo': the repo's own assets
const MIME = { '.json': 'application/json', '.atlas': 'text/plain', '.webp': 'image/webp', '.png': 'image/png' };
(async () => {
  const b = await chromium.launch({ args: ['--use-angle=d3d11', '--ignore-gpu-blocklist'] });
  const ctx = await b.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: DPR, isMobile: mobile, hasTouch: mobile });
  await RGS.install(ctx);
  if (SRC) {
    await ctx.route(/\/assets\/spine\/(smukiez|smoke-skull)\/[^/?]+/, r => {
      const u = new URL(r.request().url()); const parts = decodeURIComponent(u.pathname).split('/');
      const f = path.join(SRC, parts[parts.length - 2], parts[parts.length - 1]);
      if (!fs.existsSync(f)) return r.fulfill({ status: 404, body: 'nf' });
      r.fulfill({ status: 200, contentType: MIME[path.extname(f)] || 'application/octet-stream', body: fs.readFileSync(f) });
    });
  }
  const page = await ctx.newPage();
  const errs = []; page.on('pageerror', e => errs.push(e.message)); page.on('console', m => { if (m.type() === 'warning' || m.type() === 'error') errs.push(m.text()); });
  await page.goto(RGS.ORIGIN + `/index.html?sessionID=gs&rgs_url=${RGS.ORIGIN}&lang=en&device=${mobile ? 'mobile' : 'desktop'}`);
  await page.waitForFunction(() => document.querySelector('.features.up'), null, { timeout: 120000 });
  await page.waitForTimeout(400); await page.click('.features');
  await page.waitForFunction(() => !document.querySelector('.features') && window.__chars && window.__chars.length === 2, null, { timeout: 60000 });
  await page.waitForTimeout(3500);
  const info = await page.evaluate(([clip, T]) => window.__chars.map(c => {
    const st = c.actor.state; st.clearTracks(); c.actor.skeleton.setToSetupPose();
    const has = c.data.animations.some(a => a.name === clip);
    const e = st.setAnimation(0, has ? clip : 'idle', false); e.trackTime = T; e.mixDuration = 0;
    if (c.data.findAnimation('ember_loop')) { const e2 = st.setAnimation(1, 'ember_loop', true); e2.mixDuration = 0; }
    st.timeScale = 0; c.actor.update(0);
    const r = c.app.canvas.getBoundingClientRect();
    return { name: c.name, box: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)], scale: +c.actor.scale.x.toFixed(4) };
  }), [clip, T]);
  await page.waitForTimeout(600);
  await page.screenshot({ path: out });
  console.log(JSON.stringify(info), 'errors', JSON.stringify(errs.filter(e => /spine|rig|atlas|character|smoke/i.test(e))));
  await b.close();
})();
