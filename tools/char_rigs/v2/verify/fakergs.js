// In-process stand-in for frontend/mock_rgs.py: serves the front end and answers the wallet and
// replay calls from inside Playwright's router, so tests need no server process.
// install(ctx, { hooks }) -> origin 'http://smukiez.test'
const fs = require('fs');
const path = require('path');
const ROOT = 'C:/Users/CooperHinkel/Documents/ClaudeRoblox/slotsgame-current';
const FRONT = path.resolve(process.env.SMUKIEZ_FRONT || path.join(ROOT, "frontend"));
const LIB = path.join(ROOT, 'math-sdk/games/smukiez_tag_run/library');
const ORIGIN = 'http://smukiez.test';
const UNIT = 1000000;
const BET_LEVELS = [10000, 20000, 50000, 100000, 200000, 400000, 600000, 800000, 1000000, 1200000, 1400000, 1600000, 1800000, 2000000, 3000000, 4000000, 5000000, 6000000, 7000000, 8000000, 9000000, 10000000, 12000000, 14000000, 16000000, 18000000, 20000000, 30000000, 40000000, 50000000, 75000000, 100000000, 150000000, 200000000, 250000000, 300000000, 350000000, 400000000, 450000000, 500000000, 750000000, 1000000000];
const MODES = Object.fromEntries(JSON.parse(fs.readFileSync(path.join(LIB, 'publish_files/index.json'), 'utf8')).modes.map(m => [m.name, Number(m.cost)]));
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'application/javascript; charset=utf-8', '.css': 'text/css', '.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp', '.wav': 'audio/wav', '.ogg': 'audio/ogg', '.aac': 'audio/aac', '.m4a': 'audio/mp4', '.ttf': 'font/ttf', '.otf': 'font/otf', '.json': 'application/json', '.atlas': 'text/plain', '.skel': 'application/octet-stream' };

const books = {};
function mode(name) {
  if (books[name]) return books[name];
  const jsonl = path.join(LIB, `beta_cache/books_${name}.jsonl`);
  const offsets = JSON.parse(fs.readFileSync(jsonl + '.idx', 'utf8'));
  const ids = [], cum = []; let total = 0n;
  for (const line of fs.readFileSync(path.join(LIB, `publish_files/lookUpTable_${name}_0.csv`), 'utf8').split('\n')) {
    if (!line.trim()) continue;
    const [id, w] = line.trim().split(',');
    const wb = BigInt(w); if (wb <= 0n) continue;
    total += wb; ids.push(Number(id)); cum.push(total);
  }
  const fd = fs.openSync(jsonl, 'r');
  const read = id => {
    const off = offsets[String(id)]; if (off === undefined) return null;
    const chunks = []; let pos = off;
    for (;;) {
      const b = Buffer.alloc(1 << 20); const n = fs.readSync(fd, b, 0, b.length, pos);
      if (!n) break; const nl = b.subarray(0, n).indexOf(10);
      if (nl >= 0) { chunks.push(b.subarray(0, nl)); break; }
      chunks.push(b.subarray(0, n)); pos += n;
    }
    return JSON.parse(Buffer.concat(chunks).toString('utf8'));
  };
  const draw = () => {
    const roll = BigInt(Math.floor(Math.random() * 2 ** 52)) * total / (2n ** 52n);
    let lo = 0, hi = cum.length - 1;
    while (lo < hi) { const mid = (lo + hi) >> 1; if (cum[mid] > roll) hi = mid; else lo = mid + 1; }
    return read(ids[lo]);
  };
  return (books[name] = { read, draw });
}

const SERVED = { bytes: 0, files: [] };   // what the page fetched from the front end
const SESSIONS = new Map();
function wallet(sid) {
  if (!SESSIONS.has(sid)) {
    const cur = sid.includes('@') ? sid.split('@').pop().toUpperCase() : 'USD';
    SESSIONS.set(sid, { balance: 1000000 * UNIT, currency: cur, round: null, counter: 52600000 });
  }
  return SESSIONS.get(sid);
}

async function install(ctx, { hooks = {}, stats = null } = {}) {
  await ctx.route(ORIGIN + '/**', async route => {
    const req = route.request();
    const u = new URL(req.url());
    const p = decodeURIComponent(u.pathname);
    const json = (obj, status = 200) => route.fulfill({ status, contentType: 'application/json', headers: { 'Access-Control-Allow-Origin': '*' }, body: JSON.stringify(obj) });
    if (req.method() === 'OPTIONS') return route.fulfill({ status: 204, headers: { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': '*' } });
    if (p.startsWith('/bet/replay/')) {
      const [game, ver, m, ev] = p.split('/').slice(3);
      if (!MODES[m]) return json({ error: 'ERR_VAL', message: 'unknown mode' }, 400);
      const book = mode(m).read(Number(ev));
      if (!book) return json({ error: 'ERR_GEN', message: 'no such event' }, 500);
      return json({ state: book.events || [], payoutMultiplier: book.payoutMultiplier / 100, costMultiplier: MODES[m] });
    }
    if (p.startsWith('/wallet/') || p === '/bet/event') {
      let body = {}; try { body = JSON.parse(req.postData() || '{}'); } catch (e) { return json({ error: 'ERR_VAL' }, 400); }
      if (!body.sessionID) return json({ error: 'ERR_IS' }, 400);
      const w = wallet(body.sessionID);
      const bal = () => ({ amount: w.balance, currency: w.currency });
      if (stats) stats.push(p);
      if (p === '/wallet/authenticate') {
        let out = { balance: bal(), config: { minBet: BET_LEVELS[0], maxBet: BET_LEVELS[BET_LEVELS.length - 1], stepBet: BET_LEVELS[0], defaultBetLevel: UNIT, betLevels: BET_LEVELS, gameModes: Object.entries(MODES).map(([mode, c]) => ({ mode, costMultiplier: c })), jurisdiction: { socialCasino: false, disabledFullscreen: false, disabledTurbo: false } } };
        if (w.round) out.round = w.round;
        if (hooks.auth) out = hooks.auth(out, w) || out;
        return json(out);
      }
      if (p === '/wallet/balance') { let out = { balance: bal() }; if (hooks.balance) out = hooks.balance(out, w) || out; return json(out); }
      if (p === '/wallet/play') {
        if (hooks.play) { const r = hooks.play(body, w); if (r) return json(r.body, r.status || 200); }
        if (w.round) return json({ error: 'ERR_VAL', message: 'round open' }, 400);
        const { amount, mode: m } = body;
        if (!MODES[m] || !Number.isInteger(amount)) return json({ error: 'ERR_VAL' }, 400);
        const price = Math.round(amount * MODES[m]);
        if (price > w.balance) return json({ error: 'ERR_IPB' }, 400);
        w.balance -= price;
        const book = hooks.book ? hooks.book(m) : mode(m).draw();
        const mult = book.payoutMultiplier / 100, payout = Math.round(mult * amount);
        const rnd = { betID: ++w.counter, amount, payout, payoutMultiplier: mult, active: payout > 0, mode: m, state: book.events || [] };
        w.round = payout > 0 ? rnd : null;
        return json({ balance: bal(), round: rnd });
      }
      if (p === '/wallet/end-round') {
        if (hooks.endRound) { const r = hooks.endRound(body, w); if (r) return json(r.body, r.status || 200); }
        if (!w.round) return json({ error: 'ERR_VAL', message: 'no open round' }, 400);
        w.balance += w.round.payout; w.round = null;
        return json({ balance: bal() });
      }
      if (p === '/bet/event') return json({ event: body.event });
      return json({ error: 'ERR_VAL' }, 404);
    }
    const file = path.join(FRONT, p === '/' ? 'index.html' : p);
    if (!file.startsWith(FRONT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) return route.fulfill({ status: 404, body: 'not found' });
    const body = fs.readFileSync(file); SERVED.bytes += body.length; SERVED.files.push([p, body.length]);
    return route.fulfill({ status: 200, contentType: MIME[path.extname(file).toLowerCase()] || 'application/octet-stream', body });
  });
  return ORIGIN;
}
module.exports = { install, ORIGIN, mode, MODES, UNIT, SERVED };
