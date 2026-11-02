// The game's own background, exactly as drawn in the game (the wall, the SMUKIEZ tag, its neon and its
// light, the drips), with the board, the HUD and the figures hidden: one shot per cover shape, the
// brightest of three (so the sign is not caught in a flicker).
const { chromium } = require('C:/Users/CooperHinkel/Documents/ClaudeRoblox/.tools/pw/node_modules/playwright');
const RGS = require('../verify/fakergs.js'); const path = require('path');
const SHAPES = [{ name: '16x9', w: 1920, h: 1080 }, { name: '3x4', w: 1080, h: 1440 }];
(async () => {
  const b = await chromium.launch({ args: ['--use-angle=d3d11', '--ignore-gpu-blocklist'] });
  for (const s of SHAPES) {
    const ctx = await b.newContext({ viewport: { width: s.w, height: s.h }, deviceScaleFactor: 2 });
    await RGS.install(ctx);
    const page = await ctx.newPage();
    const q = new URLSearchParams({ replay: 'true', game: 'smukiezs-city', version: '1', mode: 'base', event: '637', amount: '1000000', rgs_url: RGS.ORIGIN, lang: 'en', currency: 'USD', device: 'desktop' });
    await page.goto(RGS.ORIGIN + '/index.html?' + q);
    await page.waitForFunction(() => { const p = document.getElementById('replayPlay'); return p && !p.hidden; }, null, { timeout: 120000 });
    await page.waitForTimeout(4000);   // the wall's light baked, the drips running
    await page.addStyleTag({ content: 'body > *:not(#camfar) { visibility: hidden !important; } #camfar { visibility: visible !important; }' });
    let best = null;
    for (let i = 0; i < 3; i++) {
      await page.waitForTimeout(700);
      const buf = await page.screenshot({ type: 'png' });
      const lit = await page.evaluate(() => (window.WallFX && WallFX.neon ? WallFX.neon() : 1));
      if (!best || lit > best.lit) best = { buf, lit };
    }
    require('fs').writeFileSync(path.join(__dirname, `bg_${s.name}.png`), best.buf);
    console.log(s.name, 'neon', best.lit);
    await ctx.close();
  }
  await b.close();
})();
