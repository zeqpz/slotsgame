// Renders an SVG file to a PNG with a transparent background (Playwright Chromium).
//   node render.js in.svg out.png [size]
const { chromium } = require(process.env.PLAYWRIGHT || 'playwright');
const fs = require('fs');
(async () => {
  const [inp, out, sz] = process.argv.slice(2);
  const size = parseInt(sz || '1000', 10);
  const svg = fs.readFileSync(inp, 'utf8');
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: size, height: size }, deviceScaleFactor: 1 });
  await page.setContent(`<!doctype html><html><head><style>html,body{margin:0;padding:0;background:transparent;overflow:hidden}svg{display:block}</style></head><body>${svg}</body></html>`);
  await page.screenshot({ path: out, omitBackground: true, clip: { x: 0, y: 0, width: size, height: size } });
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
