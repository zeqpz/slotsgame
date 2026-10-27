// Headless rig lab: Chromium + lab.html, rigs served from several roots.
const { chromium } = require('C:/Users/CooperHinkel/Documents/ClaudeRoblox/.tools/pw/node_modules/playwright');
const fs = require('fs'); const path = require('path');
const REPO = require('path').resolve(__dirname, '../../../..').replace(/\\/g, '/');
const HERE = __dirname;
const ROOTS = {
  cur: REPO + '/frontend/assets/spine',
  src: REPO + '/art/characters-src',
  // 'base': the rigs before (a copy of frontend/assets/spine from git, SMUKIEZ_RIG_BEFORE); 'new': the repo's
  base: process.env.SMUKIEZ_RIG_BEFORE || (require('os').tmpdir() + '/smukiez-chars-v2/before'),
  new: REPO + '/frontend/assets/spine',

};
const MIME = { '.html': 'text/html', '.js': 'application/javascript', '.json': 'application/json', '.atlas': 'text/plain', '.png': 'image/png', '.webp': 'image/webp' };
const ORIGIN = 'http://lab.test';

async function open({ w = 1200, h = 1200, dpr = 1 } = {}) {
  const browser = await chromium.launch({ args: ['--use-angle=d3d11', '--ignore-gpu-blocklist', '--enable-gpu-rasterization'] });
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: dpr });
  await ctx.route(ORIGIN + '/**', route => {
    const u = new URL(route.request().url()); const p = decodeURIComponent(u.pathname);
    let file = null;
    if (p === '/lab.html') file = HERE + '/lab.html';
    else if (p.startsWith('/spine/')) file = REPO + '/frontend/assets/spine/' + p.slice(7);
    else if (p.startsWith('/rig/')) { const [, , root, ...rest] = p.split('/'); file = ROOTS[root] + '/' + rest.join('/'); }
    if (!file || !fs.existsSync(file)) return route.fulfill({ status: 404, body: 'nf ' + p });
    route.fulfill({ status: 200, contentType: MIME[path.extname(file)] || 'application/octet-stream', body: fs.readFileSync(file) });
  });
  const page = await ctx.newPage();
  page.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') console.log('[page]', m.text()); });
  page.on('pageerror', e => console.log('[pageerror]', e.message));
  await page.goto(ORIGIN + '/lab.html');
  await page.evaluate(([w, h]) => lab.init(w, h, 1), [w, h]);
  return { browser, page, w, h };
}
// root: 'cur' | 'src' | 'base' | 'build'; name: rig name. src keeps pages flat in the folder; others use <name>/
function rigBase(root, name) { return root === 'src' ? `/rig/src` : `/rig/${root}/${name}`; }
async function load(page, key, root, name, opts = {}) {
  return page.evaluate(([k, b, n, o]) => lab.load(k, b, n, o), [key, rigBase(root, name), name, opts]);
}
async function shot(page, file, clip) {
  await page.evaluate(() => lab.render());
  await page.screenshot({ path: file, clip, omitBackground: false });
}
module.exports = { open, load, shot, REPO, HERE, ROOTS };
