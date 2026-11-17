/* Stake Engine RGS client.
 *
 * The game is served from
 *   https://{team}.cdn.stake-engine.com/{gameID}/{version}/index.html
 *       ?sessionID=..&lang=..&device=..&rgs_url=..
 * so every connection detail arrives in the query string. rgs_url is explicitly
 * documented as "should not be hardcoded, as it may change dynamically" — it is read
 * from the URL on every load and never baked into the bundle.
 *
 * Money is an integer with six decimal places: 1_000_000 == 1.00 of the currency.
 * Keep it in integers everywhere and only divide at the display layer, or rounding
 * drift shows up in the balance.
 */
const RGS = (() => {
  const UNIT = 1000000;

  const CURRENCY = {
    USD: { symbol: "$", decimals: 2 },            CAD: { symbol: "CA$", decimals: 2 },
    JPY: { symbol: "¥", decimals: 0 },            EUR: { symbol: "€", decimals: 2 },
    RUB: { symbol: "₽", decimals: 2 },            CNY: { symbol: "CN¥", decimals: 2 },
    PHP: { symbol: "₱", decimals: 2 },            INR: { symbol: "₹", decimals: 2 },
    IDR: { symbol: "Rp", decimals: 0 },           KRW: { symbol: "₩", decimals: 0 },
    BRL: { symbol: "R$", decimals: 2 },           MXN: { symbol: "MX$", decimals: 2 },
    DKK: { symbol: "KR", decimals: 2, after: true },
    PLN: { symbol: "zł", decimals: 2, after: true },
    VND: { symbol: "₫", decimals: 0, after: true },
    TRY: { symbol: "₺", decimals: 2 },
    CLP: { symbol: "CLP", decimals: 0, after: true },
    ARS: { symbol: "ARS", decimals: 2, after: true },
    PEN: { symbol: "S/", decimals: 2, after: true },
    // the social-casino coins read "10.00 SC" / "10.00 GC" - never with a $ in front
    XGC: { symbol: "GC", decimals: 2, after: true },
    XSC: { symbol: "SC", decimals: 2, after: true },
    XEC: { symbol: "SC", decimals: 2, after: true },
  };
  const CURRENCY_SOCIAL = new Set(["XGC", "XSC", "XEC"]);
  // A currency missing from the table (new ones appear: XEC broke games in 2026) takes its symbol and
  // precision from Intl when the browser knows the code, else shows the code after the amount.
  const intlCache = {};
  function intlMeta(code) {
    if (!code) return { symbol: "", decimals: 2, after: true };
    if (intlCache[code]) return intlCache[code];
    let meta = { symbol: code, decimals: 2, after: true };
    try {
      const f = new Intl.NumberFormat("en", { style: "currency", currency: code, currencyDisplay: "narrowSymbol" });
      const parts = f.formatToParts(1);
      const sym = (parts.find(p => p.type === "currency") || {}).value;
      const after = parts.findIndex(p => p.type === "currency") > parts.findIndex(p => p.type === "integer");
      const s = sym || code;
      // a bare letter code reads "1,234.56 CHF", as the table writes CLP and ARS
      meta = { symbol: s, decimals: f.resolvedOptions().maximumFractionDigits, after: after || /^[A-Za-z]{2,}$/.test(s) };
    } catch (e) { /* not an ISO code Intl knows: keep the code */ }
    return (intlCache[code] = meta);
  }
  // thousands grouped: 1,000,000.00 - the integer part only
  const group = s => s.replace(/^(\d+)/, d => d.replace(/\B(?=(\d{3})+(?!\d))/g, ","));

  const q = new URLSearchParams(location.search);
  const sessionID = q.get("sessionID") || "";
  const lang = q.get("lang") || "en";
  const device = q.get("device") || "desktop";
  const raw = (q.get("rgs_url") || "").trim().replace(/\/+$/, "");
  const root = raw ? (/^https?:\/\//i.test(raw) ? raw : "https://" + raw) : "";
  // social=true means the game is loaded on a social casino (Stake.us): restricted gambling
  // vocabulary must not appear anywhere in the UI. The jurisdiction flag says the same
  // thing after authenticate; the URL param is there before it.
  // `let`: authenticate turns it on when the jurisdiction says socialCasino (read RGS.social after it).
  let social = q.get("social") === "true";
  const urlCurrency = (q.get("currency") || "").trim();

  const state = {
    currency: "USD",
    balance: 0,          // integer, 6dp
    config: null,        // minBet / maxBet / stepBet / betLevels / jurisdiction
    round: null,         // active or last-completed round from authenticate
    authenticated: false,
  };

  class RgsError extends Error {
    constructor(code, message, status) {
      super(message || code);
      this.code = code;
      this.status = status;
    }
  }

  // The docs specify error *codes* (ERR_IS, ERR_IPB, ...) but not the envelope they
  // arrive in, so pull the code from any of the shapes a JSON error body might use.
  function errorCode(data, status) {
    const c = data && (data.statusCode || data.code || data.error ||
                       (data.status && data.status.code));
    // A server that lost the session (a restarted local server, say) may call it ERR_VAL; it is a session
    // problem, not the bet's, so don't send the player off trying other amounts.
    if (data && /unknown session|session not authenticated|session .* does not exist/i.test(String(data.message || ""))) return "ERR_IS";
    if (typeof c === "string" && /^ERR_/.test(c)) return c;
    // The RGS rate-limits bursts of requests ("Slow down"); a 429 body is sometimes plain text.
    if (status === 429 || (data && /slow down|too many/i.test(String(data.message || "")))) return "ERR_ACT";
    return status >= 500 ? "ERR_GEN" : "ERR_VAL";
  }

  async function call(path, body) {
    if (!root) throw new RgsError("ERR_VAL", "rgs_url missing from the game URL");
    if (!sessionID) throw new RgsError("ERR_IS", "sessionID missing from the game URL");
    let res;
    try {
      res = await fetch(root + path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(Object.assign({ sessionID }, body || {})),
      });
    } catch (e) {
      throw new RgsError("ERR_GEN", "network error contacting the RGS");
    }
    let data = null;
    try { data = await res.json(); } catch (e) { /* empty or non-JSON body */ }
    if (!res.ok) throw new RgsError(errorCode(data, res.status), (data && data.message) || res.statusText, res.status);
    return data || {};
  }

  // /authenticate, /balance and /play wrap the wallet as { balance: { amount, currency } };
  // /end-round answers with the bare { amount, currency }. Accept either.
  function absorb(data) {
    if (!data) return data;
    const b = (data.balance && typeof data.balance === "object") ? data.balance
            : (typeof data.amount === "number" && data.currency) ? data
            : null;
    if (b) {
      if (typeof b.amount === "number") state.balance = b.amount;
      if (b.currency) state.currency = b.currency;
    }
    return data;
  }

  // The RGS calls a round's event stream `state`; the math books call the same array
  // `events`. Alias it once here so the presentation layer only ever reads one name.
  function normalizeRound(r) {
    if (!r || typeof r !== "object") return null;
    if (!Array.isArray(r.events) && Array.isArray(r.state)) r.events = r.state;
    return r;
  }

  return {
    UNIT, sessionID, lang, device, rgsUrl: root, urlCurrency,
    get social() { return social; },
    get state() { return state; },
    RgsError,

    /** Must succeed before any other wallet call, or the rest return ERR_IS. A launch can
     *  meet a passing server error or a dropped connection on this very first call, so a
     *  general error or a rate-limit is tried again - four tries over about 3.5 s - before
     *  the player is told the game can't connect. Anything else (an expired session...) is
     *  final at once. */
    async authenticate() {
      let d = null, lastErr = null;
      for (let attempt = 0; attempt < 4; attempt++) {
        if (attempt) await new Promise(res => setTimeout(res, 500 * 2 ** (attempt - 1)));
        try { d = absorb(await call("/wallet/authenticate", {})); lastErr = null; break; }
        catch (e) {
          lastErr = e;
          console.warn(`authenticate try ${attempt + 1}: ${e.code}${e.status ? " (HTTP " + e.status + ")" : ""} ${e.message}`);
          if (e.code !== "ERR_GEN" && e.code !== "ERR_ACT") throw e;
        }
      }
      if (lastErr) throw lastErr;
      if (d.config) state.config = d.config;
      // the jurisdiction can make this a social-casino session even without the URL flag
      const j = (state.config && state.config.jurisdiction) || {};
      if (j.socialCasino === true) social = true;
      state.round = normalizeRound(d.round);
      state.authenticated = true;
      return d;
    },

    async balance() { return absorb(await call("/wallet/balance", {})); },

    /** amount is the BASE bet; the RGS debits amount x the mode's cost multiplier. */
    async play(amount, mode) {
      const body = { amount, mode };
      if (urlCurrency) body.currency = urlCurrency;   // the lobby names the wallet to play with
      const d = absorb(await call("/wallet/play", body));
      state.round = normalizeRound(d.round);
      return d;
    },

    /** Settles the round and pays out. Nothing else may happen on the round after this.
     *  A round that paid nothing is closed by the RGS on /play already and comes back
     *  active:false — calling end-round on one answers ERR_VAL. The balance the /play
     *  response carried is the settled one, so leave those rounds alone. */
    async endRound() {
      const open = state.round;
      state.round = null;
      if (open && open.active === false) return null;
      // Developers on the engine.io server see a sporadic 500 from end-round even though
      // the round settles fine — retry briefly, then confirm with authenticate rather
      // than tell the player their win failed when it didn't.
      let lastErr = null;
      for (let attempt = 0; attempt < 3; attempt++) {
        try { return absorb(await call("/wallet/end-round", {})); }
        catch (e) {
          lastErr = e;
          if (e.code !== "ERR_GEN" && e.code !== "ERR_ACT") throw e;
          await new Promise(res => setTimeout(res, 350 * (attempt + 1)));
        }
      }
      try {
        const d = absorb(await call("/wallet/authenticate", {}));
        const still = d.round && d.round.active === true;
        if (!still) return d;                     // settled on their side after all
        state.round = normalizeRound(d.round);    // genuinely still open — surface it
      } catch (e) { /* fall through to the original error */ }
      throw lastErr;
    },

    /** Bet Replay: the lobby opens the game with replay=true plus the round's coordinates.
     *  No session is involved — anyone with the link can watch the round. */
    replayParams() {
      return {
        replay: q.get("replay") === "true",
        game: q.get("game") || "",
        version: q.get("version") || "",
        mode: q.get("mode") || "",
        event: q.get("event") || "",
        amount: Number(q.get("amount")) || 0,
        currency: urlCurrency,
      };
    },

    /** GET {rgs_url}/bet/replay/{game}/{version}/{mode}/{event} ->
     *  { state: [events], payoutMultiplier, costMultiplier }. Unauthenticated by design. */
    async replay(p) {
      if (!root) throw new RgsError("ERR_VAL", "rgs_url missing from the game URL");
      const path = ["bet", "replay", p.game, p.version, p.mode, p.event].map(encodeURIComponent).join("/");
      let res;
      try { res = await fetch(root + "/" + path); }
      catch (e) { throw new RgsError("ERR_GEN", "network error contacting the RGS"); }
      let data = null;
      try { data = await res.json(); } catch (e) { /* empty */ }
      if (!res.ok || !data || !Array.isArray(data.state)) throw new RgsError(errorCode(data, res.status), "replay not found", res.status);
      return data;
    },

    /** Cost multiplier for a mode, from the RGS config when it supplies one. */
    costOf(mode) {
      const modes = (state.config && state.config.gameModes) || [];
      const m = modes.find(x => x.mode === mode);
      return (m && typeof m.costMultiplier === "number") ? m.costMultiplier : null;
    },

    /** The highest BASE bet a mode allows: its own cap (gameModes[].maxBet) when the RGS names a
     *  positive one, else the session's config.maxBet, else null (no cap known). A cap of 0 or a
     *  missing one means "no cap of its own" - the RGS sends maxBet 0 for every mode under XGC,
     *  and every mode is playable there (Engine review 2026-11-16: reading 0 as "switched off"
     *  turned every bonus card to LOWER THE PLAY and refused every base spin under GC). */
    maxBetOf(mode) {
      const c = state.config || {};
      const m = (c.gameModes || []).find(x => x.mode === mode);
      if (m && typeof m.maxBet === "number" && m.maxBet > 0) return m.maxBet;
      return (typeof c.maxBet === "number" && c.maxBet > 0) ? c.maxBet : null;
    },

    /** Whether a mode can be played at this base bet: not above its cap. Never false for a cap of 0. */
    modeAllowed(mode, amount) {
      const max = this.maxBetOf(mode);
      return max === null || amount <= max;
    },

    /** Optional progress marker so a disconnect can resume mid-round. */
    async event(name) {
      try { return await call("/bet/event", { event: name }); }
      catch (e) { return null; }   // never let bookkeeping break a round
    },

    /** The token the player is playing with, as the balance label names it. The social
     *  coins go by their short codes: their long names carry words social mode forbids. */
    currencyName(code) {
      const c = code || state.currency;
      if (c === "XSC" || c === "XEC") return "SC";
      if (c === "XGC") return "GC";
      return c;
    },

    /** extra = how many digits past the currency's usual precision may show when the
     *  amount needs them. Reviewers' current rule (May–Jun 2026): the balance is capped
     *  at the usual 2, bets and wins may carry up to 4 when a sub-cent value needs it. */
    money(amount, currency, extra = 2) {
      const meta = CURRENCY[currency || state.currency] || intlMeta(currency || state.currency);
      const a = amount || 0;
      const v = a / UNIT;
      const maxDec = Math.min(6, meta.decimals + Math.max(0, extra));
      const unit = Math.pow(10, 6 - meta.decimals);
      let s = v.toFixed(meta.decimals);
      if (extra > 0 && unit > 1 && a % unit !== 0) {
        s = v.toFixed(maxDec).replace(/0+$/, "");
        if (s.split(".")[1] && s.split(".")[1].length < meta.decimals) s = v.toFixed(meta.decimals);
      }
      s = group(s);
      // social mode: never a $ / € sign. A replay link in social mode that names no currency shows bare
      // figures: no symbol, no stray space (trim).
      if (social && !CURRENCY_SOCIAL.has(currency || state.currency)) return `${s} ${currency || state.currency}`.trim();
      return (meta.after ? `${s} ${meta.symbol}` : `${meta.symbol}${s}`).trim();
    },

    /** Bet must sit within min/max and land on a step boundary. */
    validBet(amount) {
      const c = state.config;
      if (!c) return true;
      if (c.minBet && amount < c.minBet) return false;
      if (c.maxBet && amount > c.maxBet) return false;
      if (c.stepBet && amount % c.stepBet !== 0) return false;
      return true;
    },

    /** The bet ladder, all from /authenticate: config.betLevels, keeping only the levels inside
     *  minBet..maxBet on a stepBet boundary (validBet). Should that leave nothing, the RGS's own list
     *  as sent; with no list at all, minBet. */
    betLevels() {
      const c = state.config;
      if (c && Array.isArray(c.betLevels) && c.betLevels.length) {
        const all = c.betLevels.map(Number).filter(v => Number.isFinite(v) && v > 0);
        const ok = all.filter(v => this.validBet(v));
        return (ok.length ? ok : all).sort((a, b) => a - b);
      }
      if (c && c.minBet) return [c.minBet];
      return [UNIT];
    },

    /** The level a session opens on: config.defaultBetLevel, else minBet, else the lowest level. */
    defaultBet() {
      const c = state.config || {};
      return Number(c.defaultBetLevel) || Number(c.minBet) || 0;
    },

    jurisdiction() { return (state.config && state.config.jurisdiction) || {}; },
  };
})();
