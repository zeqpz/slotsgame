/* Upload a pushed commit of this repo to the game's scratch area on engine.io (Stake Engine) -
   from inside a logged-in dashboard tab. Route A in README.md.

   engine.io has no API key: it only trusts the logged-in browser session. So this runs IN the
   dashboard tab (paste it into the DevTools console, or run it with a browser tool), and the tab
   does all of it itself: it reads the commit's file list from GitHub, downloads each file from
   raw.githubusercontent.com, MD5s it, compares it with the scratch listing (whose etags are plain
   MD5s), and for every file that differs it mints a presigned upload URL and PUTs the bytes. No URL
   or token ever leaves the tab, and nothing has to run on your machine.

   1. Push the commit you want live, and copy its full 40-character SHA into CFG.commit below.
   2. Open https://studio.engine.io/teams/<team>/games/<game>/files, logged in (NOT the
      ...files?launch=true URL: the upload API answers "Forbidden" there).
   3. Run this whole file in that tab. It starts a job and returns at once.
   4. Poll it: run  __upStatus()  until phase is "done" (or "failed"). A front-end change takes
      a minute or so; the math books (~60-90 MB each) a few more.
   5. Check the result (`uploaded`, `verified`, `errors`), then publish (README.md, "Publish").

   Set CFG.dryRun = true first to see what would go up without uploading anything. */
(() => {
  const CFG = {
    team: "smukiez",
    game: "smukiezs-mural",
    repo: "zeqpz/slotsgame",              // public repo: the tab reads it without a token
    commit: "PASTE_THE_PUSHED_COMMIT_SHA_HERE",
    parts: {                               // engine.io bundle -> where it lives in the repo
      front: "frontend/",
      math: "math-sdk/games/smukiez_tag_run/library/publish_files/",
    },
    skip: [/(^|\/)__pycache__\//, /^frontend\/mock_rgs\.py$/],   // the local dev server is not part of the game
    only: null,        // e.g. ["front/index.html"]: just these bundle paths (null: every file in the parts)
    partsToDo: null,   // e.g. ["front"]: just these bundles (null: all of CFG.parts)
    dryRun: false,     // true: report what differs, upload nothing
    crlfSame: true,    // a text file whose scratch copy only differs by Windows line endings counts as unchanged
    bigFile: 20e6,     // files over this many bytes are fetched one at a time (memory)
    workers: 6,        // small files checked/uploaded this many at a time
  };

  // ---- MD5 (RFC 1321). SubtleCrypto has no MD5, and the scratch etags are MD5s. ----
  const K = new Int32Array(64);
  for (let i = 0; i < 64; i++) K[i] = Math.floor(Math.abs(Math.sin(i + 1)) * 4294967296) | 0;
  const R = [7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22, 5, 9, 14, 20, 5, 9, 14, 20, 5, 9, 14, 20, 5, 9, 14, 20,
             4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23, 6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21];
  function md5(bytes) {
    let a0 = 0x67452301, b0 = 0xefcdab89 | 0, c0 = 0x98badcfe | 0, d0 = 0x10325476;
    const M = new Int32Array(16);
    const block = (src, off) => {
      for (let j = 0; j < 16; j++) {
        const o = off + 4 * j;
        M[j] = src[o] | (src[o + 1] << 8) | (src[o + 2] << 16) | (src[o + 3] << 24);
      }
      let A = a0, B = b0, C = c0, D = d0;
      for (let i = 0; i < 64; i++) {
        let F, g;
        if (i < 16) { F = (B & C) | (~B & D); g = i; }
        else if (i < 32) { F = (D & B) | (~D & C); g = (5 * i + 1) & 15; }
        else if (i < 48) { F = B ^ C ^ D; g = (3 * i + 5) & 15; }
        else { F = C ^ (B | ~D); g = (7 * i) & 15; }
        F = (F + A + K[i] + M[g]) | 0;
        A = D; D = C; C = B;
        B = (B + ((F << R[i]) | (F >>> (32 - R[i])))) | 0;
      }
      a0 = (a0 + A) | 0; b0 = (b0 + B) | 0; c0 = (c0 + C) | 0; d0 = (d0 + D) | 0;
    };
    const n = bytes.length, full = n - (n % 64);
    for (let off = 0; off < full; off += 64) block(bytes, off);
    // the tail: what is left, a 1 bit, zeros, and the length in bits (64-bit little endian)
    const rest = n - full, tail = new Uint8Array(rest < 56 ? 64 : 128);
    tail.set(bytes.subarray(full));
    tail[rest] = 0x80;
    const bits = n * 8, lo = bits >>> 0, hi = Math.floor(bits / 4294967296) >>> 0, at = tail.length - 8;
    for (let i = 0; i < 4; i++) { tail[at + i] = (lo >>> (8 * i)) & 255; tail[at + 4 + i] = (hi >>> (8 * i)) & 255; }
    for (let off = 0; off < tail.length; off += 64) block(tail, off);
    const hex = x => [0, 8, 16, 24].map(s => ((x >>> s) & 255).toString(16).padStart(2, "0")).join("");
    return hex(a0) + hex(b0) + hex(c0) + hex(d0);
  }
  const TEXT = /\.(html?|js|mjs|css|json|txt|csv|svg|atlas|md|xml)$/i;
  function crlf(bytes) {   // the same text with Windows line endings (what a Windows working copy uploads)
    let extra = 0;
    for (let i = 0; i < bytes.length; i++) if (bytes[i] === 10 && (i === 0 || bytes[i - 1] !== 13)) extra++;
    if (!extra) return bytes;
    const out = new Uint8Array(bytes.length + extra);
    for (let i = 0, j = 0; i < bytes.length; i++) {
      if (bytes[i] === 10 && (i === 0 || bytes[i - 1] !== 13)) out[j++] = 13;
      out[j++] = bytes[i];
    }
    return out;
  }

  // ---- the job ----
  if (window.__up && !["done", "failed"].includes(window.__up.phase)) return "a job is already running: run __upStatus()";
  const S = window.__up = { phase: "starting", commit: CFG.commit, total: 0, checked: 0, same: 0, changed: [], uploaded: [],
                             verified: 0, errors: [], dryRun: CFG.dryRun, startedAt: new Date().toISOString() };
  window.__upStatus = () => ({ phase: S.phase, checked: `${S.checked}/${S.total}`, same: S.same, changed: S.changed,
                               uploaded: S.uploaded.map(u => `${u.key} ${u.size}`), verified: S.verified, errors: S.errors,
                               secs: S.secs });
  const api = async (url, opt) => {
    const r = await fetch(url, opt);
    const text = await r.text();
    if (!r.ok) throw new Error(`${opt && opt.method || "GET"} ${url.split("?")[0]} -> HTTP ${r.status} ${text.slice(0, 120)}`);
    try { return JSON.parse(text); } catch (e) { throw new Error(`${url.split("?")[0]}: not JSON: ${text.slice(0, 120)}`); }
  };
  const listing = async () => {
    const m = new Map();
    for (const part of Object.keys(CFG.parts)) {
      for (const f of await api(`/api/file/game/${CFG.team}/${CFG.game}/scratch/${part}`)) {
        m.set(f.key, { etag: String(f.etag).replace(/"/g, ""), size: f.size });
      }
    }
    return m;
  };

  (async () => {
    const t0 = performance.now();
    try {
      // the MD5 checks itself first
      const enc = s => new TextEncoder().encode(s);
      if (md5(enc("abc")) !== "900150983cd24fb0d6963f7d28e17f72" || md5(enc("")) !== "d41d8cd98f00b204e9800998ecf8427e") {
        throw new Error("md5 self-test failed");
      }
      if (!/^[0-9a-f]{40}$/.test(CFG.commit)) throw new Error("CFG.commit must be the full 40-character SHA of a pushed commit");
      S.phase = "listing scratch";
      const remote = await listing();
      S.phase = "reading the commit";
      const tree = await api(`https://api.github.com/repos/${CFG.repo}/git/trees/${CFG.commit}?recursive=1`);
      if (tree.truncated) throw new Error("the commit's file list came back truncated");
      const parts = Object.entries(CFG.parts).filter(([part]) => !CFG.partsToDo || CFG.partsToDo.includes(part));
      const files = [];
      for (const e of tree.tree) {
        if (e.type !== "blob" || CFG.skip.some(re => re.test(e.path))) continue;
        const hit = parts.find(([, dir]) => e.path.startsWith(dir));
        if (!hit) continue;
        const key = `${hit[0]}/${e.path.slice(hit[1].length)}`;
        if (CFG.only && !CFG.only.includes(key)) continue;
        files.push({ key, path: e.path, size: e.size });
      }
      if (!files.length) throw new Error("no files matched: check CFG.parts / CFG.only / CFG.commit");
      S.total = files.length;
      S.phase = "checking and uploading";
      const one = async f => {
        const raw = `https://raw.githubusercontent.com/${CFG.repo}/${CFG.commit}/${f.path.split("/").map(encodeURIComponent).join("/")}`;
        const r = await fetch(raw, { cache: "no-store" });
        if (!r.ok) throw new Error(`${f.path}: raw HTTP ${r.status}`);
        const bytes = new Uint8Array(await r.arrayBuffer());
        if (bytes.length !== f.size) throw new Error(`${f.path}: got ${bytes.length} bytes, the commit says ${f.size}`);
        const sum = md5(bytes), have = remote.get(f.key);
        const same = have && (have.etag === sum || (CFG.crlfSame && TEXT.test(f.key) && have.etag === md5(crlf(bytes))));
        S.checked++;
        if (same) { S.same++; return; }
        S.changed.push(f.key);
        if (CFG.dryRun) return;
        const mint = await api("/api/file/upload", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ team: CFG.team, game: CFG.game, path: f.key, size: bytes.length }),   // path keeps its front/ or math/ prefix
        });
        if (!mint.url) throw new Error(`${f.key}: no upload url in the answer`);
        const put = await fetch(mint.url, { method: "PUT", body: bytes });
        if (!put.ok) throw new Error(`${f.key}: PUT -> HTTP ${put.status}`);
        S.uploaded.push({ key: f.key, size: bytes.length, md5: sum });
      };
      const run = async (list, n) => {
        const q = list.slice();
        await Promise.all(Array.from({ length: Math.max(1, n) }, async () => {
          while (q.length) {
            const f = q.shift();
            try { await one(f); } catch (e) { S.errors.push(String(e && e.message || e)); }
          }
        }));
      };
      await run(files.filter(f => f.size <= CFG.bigFile), CFG.workers);
      await run(files.filter(f => f.size > CFG.bigFile), 1);
      // every upload checked against a fresh listing: its etag must be the MD5 of what was sent
      if (S.uploaded.length) {
        S.phase = "verifying";
        const after = await listing();
        for (const u of S.uploaded) {
          const got = after.get(u.key);
          if (got && got.etag === u.md5) S.verified++;
          else S.errors.push(`${u.key}: scratch has ${got ? got.etag : "nothing"} after the upload, sent ${u.md5}`);
        }
      }
      S.phase = S.errors.length ? "failed" : "done";
    } catch (e) {
      S.errors.push(String(e && e.message || e));
      S.phase = "failed";
    }
    S.secs = Math.round((performance.now() - t0) / 1000);
  })();
  return "started: run __upStatus() until phase is done";
})();
