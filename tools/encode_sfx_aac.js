// Encode the sound effects' fallback copies to AAC-LC in ADTS (frontend/assets/sfx_*.aac), for browsers
// without Opus (older iOS Safari): the game plays the .ogg wherever Opus works and this .aac elsewhere.
// It replaced the shipped .wav fallbacks (2026-11-08: 21 MB of WAV for ~2 MB of AAC). There is no ffmpeg on
// the build machine, so this drives Chrome's WebCodecs AAC encoder (installed Chrome: the bundled
// Chromium has no AAC) through Playwright. Reads the WAV masters from argv[3] (default frontend/assets).
//   node tools/encode_sfx_aac.js <path-to-playwright-module> [wav-dir]
const path = require("path"), fs = require("fs");
const { chromium } = require(process.argv[2] || "playwright");
const OUT = path.join(__dirname, "..", "frontend", "assets");
const SRC = process.argv[3] || OUT;   // the WAV masters (removed from the build 2026-11-08: git history / the tools/sfx pipeline)
const BITRATE = { 1: 64000, 2: 128000 };
(async () => {
  const b = await chromium.launch({ channel: "chrome", headless: true });
  const ctx = await b.newContext();
  await ctx.route("https://enc.test/**", r => r.fulfill({ contentType: "text/html", body: "<!doctype html><title>enc</title>" }));
  const page = await ctx.newPage();
  await page.goto("https://enc.test/");   // WebCodecs needs a secure context
  let before = 0, after = 0;
  for (const f of fs.readdirSync(SRC).filter(f => /^sfx_.*\.wav$/.test(f)).sort()) {
    const wav = fs.readFileSync(path.join(SRC, f));
    const out = await page.evaluate(async ({ b64, bitrates }) => {
      const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
      const SR = 48000;
      const buf = await new OfflineAudioContext(1, 1, SR).decodeAudioData(bytes.buffer.slice(0));
      const ch = Math.min(2, buf.numberOfChannels), frames = buf.length, parts = [];
      const enc = new AudioEncoder({ output: c => { const d = new Uint8Array(c.byteLength); c.copyTo(d); parts.push(d); }, error: e => { throw e; } });
      enc.configure({ codec: "mp4a.40.2", sampleRate: SR, numberOfChannels: ch, bitrate: bitrates[ch], aac: { format: "adts" } });
      const step = 1024, padded = frames + step * 2;   // a little trailing silence flushes the encoder
      for (let i = 0; i < padded; i += step) {
        const n = Math.min(step, padded - i), data = new Float32Array(n * ch);
        for (let c = 0; c < ch; c++) { const s = buf.getChannelData(c); for (let k = 0; k < n; k++) data[c * n + k] = i + k < frames ? s[i + k] : 0; }
        enc.encode(new AudioData({ format: "f32-planar", sampleRate: SR, numberOfFrames: n, numberOfChannels: ch, timestamp: Math.round(i / SR * 1e6), data }));
      }
      await enc.flush();
      const total = parts.reduce((a, p) => a + p.length, 0), all = new Uint8Array(total); let o = 0;
      for (const p of parts) { all.set(p, o); o += p.length; }
      let s = ""; for (let i = 0; i < all.length; i += 0x8000) s += String.fromCharCode.apply(null, all.subarray(i, i + 0x8000));
      return btoa(s);
    }, { b64: wav.toString("base64"), bitrates: BITRATE });
    const aac = Buffer.from(out, "base64");
    fs.writeFileSync(path.join(OUT, f.replace(/\.wav$/, ".aac")), aac);
    before += wav.length; after += aac.length;
  }
  console.log(`WAV ${(before / 1048576).toFixed(1)} MB -> AAC ${(after / 1048576).toFixed(1)} MB`);
  await b.close();
})();
