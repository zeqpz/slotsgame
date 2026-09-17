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
    XGC: { symbol: "GC", decimals: 2 },           XSC: { symbol: "SC", decimals: 2 },
  };

  const q = new URLSearchParams(location.search);
  const sessionID = q.get("sessionID") || "";
  const lang = q.get("lang") || "en";
  const device = q.get("device") || "desktop";
  const raw = (q.get("rgs_url") || "").trim().replace(/\/+$/, "");
  const root = raw ? (/^https?:\/\//i.test(raw) ? raw : "https://" + raw) : "";
  // social=true means the game is loaded on a social casino (Stake.us): restricted gambling
  // vocabulary must not appear anywhere in the UI. The jurisdiction flag says the same
  // thing after authenticate; the URL param is there before it.
  const social = q.get("social") === "true";
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
    UNIT, sessionID, lang, device, rgsUrl: root, social, urlCurrency,
    get state() { return state; },
    RgsError,

    /** Must succeed before any other wallet call, or the rest return ERR_IS. */
    async authenticate() {
      const d = absorb(await call("/wallet/authenticate", {}));
      if (d.config) state.config = d.config;
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

    /** Optional progress marker so a disconnect can resume mid-round. */
    async event(name) {
      try { return await call("/bet/event", { event: name }); }
      catch (e) { return null; }   // never let bookkeeping break a round
    },

    /** What the player is actually staking — the social-casino currencies get real names. */
    currencyName(code) {
      const c = code || state.currency;
      if (c === "XSC") return "Stake Cash";
      if (c === "XGC") return "Gold Coins";
      return c;
    },

    /** extra = how many digits past the currency's usual precision may show when the
     *  amount needs them. Reviewers' current rule (May–Jun 2026): the balance is capped
     *  at the usual 2, bets and wins may carry up to 4 when a sub-cent value needs it. */
    money(amount, currency, extra = 2) {
      const meta = CURRENCY[currency || state.currency] ||
                   { symbol: currency || state.currency, decimals: 2, after: true };
      const a = amount || 0;
      const v = a / UNIT;
      const maxDec = Math.min(6, meta.decimals + Math.max(0, extra));
      const unit = Math.pow(10, 6 - meta.decimals);
      let s = v.toFixed(meta.decimals);
      if (extra > 0 && unit > 1 && a % unit !== 0) {
        s = v.toFixed(maxDec).replace(/0+$/, "");
        if (s.split(".")[1] && s.split(".")[1].length < meta.decimals) s = v.toFixed(meta.decimals);
      }
      return meta.after ? `${s} ${meta.symbol}` : `${meta.symbol}${s}`;
    },

    /** Bet must sit within min/max and land on a step boundary. */
    validBet(amount) {
      const c = state.config;
      if (!c) return true;
      if (amount < c.minBet || amount > c.maxBet) return false;
      if (c.stepBet && amount % c.stepBet !== 0) return false;
      return true;
    },

    betLevels() {
      const c = state.config;
      if (c && Array.isArray(c.betLevels) && c.betLevels.length) return c.betLevels.slice();
      if (c && c.minBet) return [c.minBet];
      return [UNIT];
    },

    jurisdiction() { return (state.config && state.config.jurisdiction) || {}; },
  };
})();
