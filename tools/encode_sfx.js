// Encode the sound effects to Opus-in-Ogg next to their WAVs (frontend/assets/sfx_*.ogg).
// There is no ffmpeg on the build machine, so this drives Chromium's WebCodecs AudioEncoder
// through Playwright and muxes the packets into Ogg by hand. The game plays the .ogg wherever
// the browser takes Opus and falls back to the .wav elsewhere.
//   node tools/encode_sfx.js <path-to-playwright-module>
const path = require('path'), fs = require('fs');
const { chromium } = require(process.argv[2] || 'playwright');
const DIR = path.join(__dirname, '..', 'frontend', 'assets');
const BITRATE = { 1: 64000, 2: 96000 };

(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext();
  await ctx.route('https://enc.test/**', r => r.fulfill({ contentType: 'text/html', body: '<!doctype html><title>enc</title>' }));
  const page = await ctx.newPage();
  await page.goto('https://enc.test/');   // WebCodecs needs a secure context
  let before = 0, after = 0;
  for (const f of fs.readdirSync(DIR).filter(f => /^sfx_.*\.wav$/.test(f)).sort()) {
    const wav = fs.readFileSync(path.join(DIR, f));
    const out = await page.evaluate(async ({ b64, bitrates }) => {
      const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
      // decode and resample to 48 kHz (Opus's own rate) in one go
      const probe = new OfflineAudioContext(1, 1, 48000);
      const buf = await probe.decodeAudioData(bytes.buffer.slice(0));
      const ch = Math.min(2, buf.numberOfChannels), frames = buf.length, SR = 48000;
      const packets = []; let head = null;
      const enc = new AudioEncoder({
        output: (chunk, meta) => {
          if (meta && meta.decoderConfig && meta.decoderConfig.description && !head) head = new Uint8Array(meta.decoderConfig.description);
          const d = new Uint8Array(chunk.byteLength); chunk.copyTo(d); packets.push({ d, dur: chunk.duration });
        },
        error: e => { throw e; },
      });
      enc.configure({ codec: 'opus', sampleRate: SR, numberOfChannels: ch, bitrate: bitrates[ch] });
      const step = 960;   // 20 ms
      const padded = frames + step * 4;   // trailing silence flushes the encoder; the final granule trims it
      for (let i = 0; i < padded; i += step) {
        const n = Math.min(step, padded - i), data = new Float32Array(n * ch);
        for (let c = 0; c < ch; c++) {
          const src = buf.getChannelData(c);
          for (let k = 0; k < n; k++) data[c * n + k] = i + k < frames ? src[i + k] : 0;
        }
        enc.encode(new AudioData({ format: 'f32-planar', sampleRate: SR, numberOfFrames: n, numberOfChannels: ch, timestamp: Math.round(i / SR * 1e6), data }));
      }
      await enc.flush();
      // pre-skip: from the encoder's own OpusHead when it offers one, else the measured 312
      const preskip = head && head.length >= 12 && String.fromCharCode(...head.slice(0, 8)) === 'OpusHead' ? head[10] | (head[11] << 8) : 312;
      // ---- Ogg muxing ----
      const crcTable = new Uint32Array(256);
      for (let i = 0; i < 256; i++) { let r = i << 24; for (let k = 0; k < 8; k++) r = (r & 0x80000000) ? ((r << 1) ^ 0x04c11db7) : (r << 1); crcTable[i] = r >>> 0; }
      const crc = a => { let c = 0; for (const x of a) c = ((c << 8) ^ crcTable[((c >>> 24) ^ x) & 255]) >>> 0; return c; };
      const serial = Math.floor(Math.random() * 0xffffffff) >>> 0;
      const pages = []; let seq = 0;
      const page = (pkts, granule, flags) => {
        const lace = [];
        for (const p of pkts) { let n = p.length; while (n >= 255) { lace.push(255); n -= 255; } lace.push(n); }
        const hdr = new Uint8Array(27 + lace.length); const dv = new DataView(hdr.buffer);
        hdr.set([79, 103, 103, 83]); hdr[4] = 0; hdr[5] = flags;
        dv.setUint32(6, granule % 0x100000000, true); dv.setUint32(10, Math.floor(granule / 0x100000000), true);
        dv.setUint32(14, serial, true); dv.setUint32(18, seq++, true); hdr[26] = lace.length; hdr.set(lace, 27);
        const body = new Uint8Array(pkts.reduce((s, p) => s + p.length, 0)); let o = 0; for (const p of pkts) { body.set(p, o); o += p.length; }
        const all = new Uint8Array(hdr.length + body.length); all.set(hdr); all.set(body, hdr.length);
        dv.setUint32(22, 0, true); const c = crc(all); new DataView(all.buffer).setUint32(22, c, true);
        pages.push(all);
      };
      const opusHead = new Uint8Array(19); const hv = new DataView(opusHead.buffer);
      opusHead.set([..."OpusHead"].map(c => c.charCodeAt(0))); opusHead[8] = 1; opusHead[9] = ch;
      hv.setUint16(10, preskip, true); hv.setUint32(12, buf.sampleRate || 48000, true); hv.setInt16(16, 0, true); opusHead[18] = 0;
      const vendor = [..."smukiez sfx"].map(c => c.charCodeAt(0));
      const tags = new Uint8Array(8 + 4 + vendor.length + 4); const tv = new DataView(tags.buffer);
      tags.set([..."OpusTags"].map(c => c.charCodeAt(0))); tv.setUint32(8, vendor.length, true); tags.set(vendor, 12); tv.setUint32(12 + vendor.length, 0, true);
      page([opusHead], 0, 2); page([tags], 0, 0);
      const end = preskip + frames;   // the last granule trims the padding off exactly
      // Every packet that runs past the end goes in the final page, so that page's granule is
      // the only one that cuts - a decoder trims the end only from the last page.
      const cum = []; let g = 0;
      for (const p of packets) { g += Math.round(p.dur * 48000 / 1e6); cum.push(g); }
      const firstBeyond = Math.max(1, cum.findIndex(v => v > end) < 0 ? packets.length - 1 : cum.findIndex(v => v > end));
      let batch = [], size = 0;
      packets.forEach((p, i) => {
        batch.push(p.d); size += p.d.length;
        const last = i === packets.length - 1;
        if (last) { page(batch, end, 4); return; }
        if (i === firstBeyond - 1 || (i < firstBeyond - 1 && (size > 3800 || batch.length >= 50))) {
          page(batch, cum[i], 0); batch = []; size = 0;
        }
      });
      const total = pages.reduce((s, p) => s + p.length, 0), outb = new Uint8Array(total); let o = 0;
      for (const p of pages) { outb.set(p, o); o += p.length; }
      // round trip: the browser must decode it back to the same length
      const back = await new OfflineAudioContext(1, 1, 48000).decodeAudioData(outb.buffer.slice(0));
      let s = ''; for (let i = 0; i < outb.length; i += 0x8000) s += String.fromCharCode(...outb.subarray(i, i + 0x8000));
      return { b64: btoa(s), frames, back: back.length, ch, preskip };
    }, { b64: wav.toString('base64'), bitrates: BITRATE });
    const ogg = Buffer.from(out.b64, 'base64');
    fs.writeFileSync(path.join(DIR, f.replace(/\.wav$/, '.ogg')), ogg);
    before += wav.length; after += ogg.length;
    console.log(`${f.padEnd(26)} ${String(wav.length).padStart(8)} -> ${String(ogg.length).padStart(7)} B  ${out.ch}ch  frames ${out.frames} decoded ${out.back}${Math.abs(out.back - out.frames) > 2 ? '  <-- LENGTH MISMATCH' : ''}`);
  }
  console.log(`total ${(before / 1048576).toFixed(2)} MB -> ${(after / 1048576).toFixed(2)} MB`);
  await b.close();
})();
