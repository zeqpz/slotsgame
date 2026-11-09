// Shoot the game's character rig (frontend/charrig.js) at every <step>-th frame of every clip, as the parity check
// against Blender's renders (parity.py). Serves the repo itself on a free local port and drives a headless Chrome
// (real GPU) over the DevTools protocol; nothing leaves the machine.
//   node tools/blender/chars/rig/parity.mjs <char> <dd> [step=3] [clips=all]
// -> art/blender/chars/<char>/qa/rig/<dd>/<clip>/####.png (premultiplied RGBA over the whole frame at density dd)
// Then: python tools/blender/chars/rig/parity.py <char> <dd>
// Chrome: CHROME env var, else C:/Program Files/Google/Chrome/Application/chrome.exe. Node >= 22.
import fs from "node:fs"; import path from "node:path"; import http from "node:http"; import zlib from "node:zlib";
import { spawn } from "node:child_process"; import os from "node:os";

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1")), "../../../..");
const [char, dd, stepArg, clipsArg] = process.argv.slice(2);
const STEP = +(stepArg || 3);
const CHROME = process.env.CHROME || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".webp": "image/webp", ".bin": "application/octet-stream" };

const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(new URL(req.url, "http://x").pathname));
  if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { "content-type": TYPES[path.extname(p)] || "application/octet-stream", "cache-control": "no-store" });
  fs.createReadStream(p).pipe(res);
}).listen(0, "127.0.0.1");
await new Promise(r => server.on("listening", r));
const PORT = server.address().port;

function png(w, h, rgba) {   // rows bottom-up (readPixels) -> PNG, top-down
  const raw = Buffer.alloc((w * 4 + 1) * h);
  for (let y = 0; y < h; y++) rgba.copy(raw, y * (w * 4 + 1) + 1, (h - 1 - y) * w * 4, (h - y) * w * 4);
  const chunk = (t, d) => { const l = Buffer.alloc(4); l.writeUInt32BE(d.length); const td = Buffer.concat([Buffer.from(t), d]); const c = Buffer.alloc(4); c.writeUInt32BE(zlib.crc32(td) >>> 0); return Buffer.concat([l, td, c]); };
  const ih = Buffer.alloc(13); ih.writeUInt32BE(w, 0); ih.writeUInt32BE(h, 4); ih[8] = 8; ih[9] = 6;
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk("IHDR", ih), chunk("IDAT", zlib.deflateSync(raw, { level: 3 })), chunk("IEND", Buffer.alloc(0))]);
}

const prof = fs.mkdtempSync(path.join(os.tmpdir(), "rigparity-"));
const dbg = 9400 + Math.floor(Math.random() * 400);
const chrome = spawn(CHROME, ["--headless=new", `--remote-debugging-port=${dbg}`, `--user-data-dir=${prof}`, "--no-first-run",
  "--ignore-gpu-blocklist", "--window-size=1600,1600", "about:blank"], { stdio: "ignore" });
let wsUrl;
for (let i = 0; i < 100 && !wsUrl; i++) { try { wsUrl = (await (await fetch(`http://127.0.0.1:${dbg}/json/version`)).json()).webSocketDebuggerUrl; } catch { await sleep(100); } }
const ws = new WebSocket(wsUrl); await new Promise(r => ws.onopen = r);
let id = 0; const wait = new Map();
ws.onmessage = e => { const m = JSON.parse(e.data); if (m.id && wait.has(m.id)) { wait.get(m.id)(m); wait.delete(m.id); } };
const send = (method, params = {}, sessionId) => new Promise(r => { const i = ++id; wait.set(i, r); ws.send(JSON.stringify({ id: i, method, params, sessionId })); });
try {
  const { result: { targetId } } = await send("Target.createTarget", { url: "about:blank" });
  const { result: { sessionId } } = await send("Target.attachToTarget", { targetId, flatten: true });
  const ev = async expr => { const r = await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true }, sessionId); if (r.result.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails).slice(0, 500)); return r.result.result.value; };
  const man = JSON.parse(fs.readFileSync(path.join(ROOT, "frontend/assets/chars", char, "manifest.json"), "utf8"));
  const d = man.density_of[dd], ad = man.densities.find(n => man.density_of[n] >= d * 1.4 - 1e-9) || man.densities[man.densities.length - 1];
  await send("Page.navigate", { url: `http://127.0.0.1:${PORT}/tools/blender/chars/rig/parity.html?char=${char}&dd=${dd}&atlas=${ad}` }, sessionId);
  for (let i = 0; i < 300; i++) { try { if (await ev("window.P ? P.then(r => (window.R = r, 1)) : 0")) break; } catch {} await sleep(100); }
  const info = await ev("({ W: R.W, H: R.H, linear: R.linear })");
  console.log(char, dd, "atlas", ad, info);
  const want = clipsArg && clipsArg !== "all" ? clipsArg.split(",") : Object.keys(man.clips);
  for (const clip of want) {
    const n = man.clips[clip].frames, out = path.join(ROOT, "art/blender/chars", char, "qa/rig", dd, clip);
    fs.rmSync(out, { recursive: true, force: true }); fs.mkdirSync(out, { recursive: true });
    const fr = []; for (let i = 0; i < n; i += STEP) fr.push(i); if (fr[fr.length - 1] !== n - 1) fr.push(n - 1);
    for (const i of fr) fs.writeFileSync(path.join(out, String(i).padStart(4, "0") + ".png"), png(info.W, info.H, Buffer.from(await ev(`R.shot(${JSON.stringify(clip)}, ${i})`), "base64")));
    console.log(clip, fr.length, "frames");
  }
} finally { ws.close(); chrome.kill(); server.close(); await sleep(300); try { fs.rmSync(prof, { recursive: true, force: true }); } catch {} process.exit(0); }
