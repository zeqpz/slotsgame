/* Game rules, paytable and UI guide — the content behind the (i) button.
 *
 * Every number here mirrors math-sdk/games/smukiez_tag_run/game_config.py; the reviewer
 * checks wins against this page, so it must never drift from the paytable the books were
 * generated with. Pays are multiples of the TOTAL bet, per line, left to right.
 *
 * Social mode (Stake.us) forbids a list of gambling terms. Copy is written once in the
 * normal vocabulary and passed through T() which swaps the restricted words when the game
 * is loaded with social=true — see the jurisdiction-requirements guideline.
 */
const RULES = (() => {
  const PAYS = {   // symbol: [5-of-a-kind, 4, 3]
    W:  [25, 10, 4],
    C3: [25, 10, 4],  C2: [20, 8, 3],   C1: [15, 6, 2.5],
    H1: [12, 5, 2],   H2: [10, 4, 1.5], H3: [8, 3, 1.2],  H4: [6, 2.5, 1],
    H5: [5, 2, 0.8],  H6: [4.5, 1.8, 0.7], H7: [4, 1.6, 0.6],
    L1: [2.5, 1, 0.4], L2: [2, 0.8, 0.3], L3: [1.5, 0.7, 0.3], L4: [1.2, 0.6, 0.2],
    L5: [1, 0.5, 0.2], L6: [1, 0.5, 0.2], L7: [1, 0.4, 0.2], L8: [0.8, 0.4, 0.2],
    L9: [0.8, 0.4, 0.1], L10: [0.6, 0.3, 0.1],
  };
  const NAMES = {
    W: "Paint Drip", BS: "Crew Leader", ES: "The Phantom",
    C1: "Smukiez Character 1", C2: "Smukiez Character 2", C3: "Smukiez Character 3",
    H1: "Bag of Cash", H2: "Cartoon Glock", H3: "Gold Chain", H4: "Fresh Kicks", H5: "Boombox",
    H6: "Skateboard", H7: "Limited Drop Box",
    L1: "Spray Can", L2: "Graffiti Markers", L3: "Smukiez Beanie", L4: "Custom Hangtag", L5: "Dice",
    L6: "Smukiez Shirt", L7: "Hoodie", L8: "Bag of Weed", L9: "Freight Train", L10: "Brick Wall Chunk",
  };
  const ORDER = ["W", "C3", "C2", "C1", "H1", "H2", "H3", "H4", "H5", "H6", "H7",
                 "L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9", "L10"];
  const CHAR_VALUES = {   // value drawn when the symbol lands
    C1: { base: "x2 (70%) or x3 (30%)", free: "x2 (55%) or x3 (45%)" },
    C2: { base: "x5", free: "x5" },
    C3: { base: "x8 (75%) or x10 (25%)", free: "x8 (60%) or x10 (40%)" },
  };
  const PAYLINES = [
    [0,0,0,0,0],[1,1,1,1,1],[2,2,2,2,2],[3,3,3,3,3],[0,1,0,1,0],[1,0,1,0,1],[1,2,1,2,1],
    [2,1,2,1,2],[2,3,2,3,2],[3,2,3,2,3],[0,1,2,1,0],[3,2,1,2,3],[1,2,3,2,1],[2,1,0,1,2],
    [0,0,1,0,0],[3,3,2,3,3],[1,1,0,1,1],[2,2,3,2,2],[0,1,2,3,3],[3,2,1,0,0],[1,0,0,0,1],
    [2,3,3,3,2],[0,1,1,1,0],[3,2,2,2,3],[1,1,2,3,3],[2,2,1,0,0],[0,2,0,2,0],[3,1,3,1,3],
    [1,3,1,3,1],[2,0,2,0,2],
  ];
  const RTP = "96.50%", MAX_WIN = 5000;

  // Restricted phrase -> replacement, from Stake's jurisdiction-requirements table. Longer
  // phrases first so "buy bonus" is swapped before "buy" gets a chance at it.
  const SWEEPS = [
    ["buy bonus", "get bonus"], ["bonus buy", "bonus"], ["total bet", "total play"],
    ["at the cost of", "for"], ["cost of", "can be played for"], ["pays out", "wins"],
    ["paid out", "won"], ["pay out", "win"], ["win feature", "play feature"],
    ["place your bets", "come and play"], ["betting", "playing"], ["bets", "plays"], ["bet", "play"],
    ["bought", "instantly triggered"], ["buy", "get"], ["purchase", "play"],
    ["cash", "coins"], ["money", "coins"], ["currency", "token"], ["credit", "balance"],
    ["wager", "play"], ["gamble", "play"], ["stake", "play amount"],
    ["pays", "wins"], ["paid", "won"], ["pay", "win"], ["cost", "amount"],
  ];
  // Each replacement word borrows the case of the word it replaces ("Buy Bonus" -> "Get
  // Bonus", "BET" -> "PLAY"), so headings and buttons keep their look.
  function recase(from, to) {
    const src = from.split(" "), out = to.split(" ");
    return out.map((w, i) => {
      const s = src[Math.min(i, src.length - 1)];
      if (s === s.toUpperCase() && /[A-Z]/.test(s)) return w.toUpperCase();
      if (s[0] === s[0].toUpperCase()) return w[0].toUpperCase() + w.slice(1);
      return w;
    }).join(" ");
  }
  function T(text, social) {
    if (!social) return text;
    let out = text;
    for (const [from, to] of SWEEPS) {
      out = out.replace(new RegExp("\\b" + from + "\\b", "gi"), m => recase(m, to));
    }
    return out;
  }

  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const x = v => "x" + (Number.isInteger(v) ? v : String(v));

  function tile(sym) {
    if (sym === "W") return `<div class="ptile wild"><span>DRIP</span><small>WILD</small></div>`;
    if (/^C\d$/.test(sym)) return `<div class="ptile char"><span>${sym === "C1" ? "x2" : sym === "C2" ? "x5" : "x10"}</span><small>MULT</small></div>`;
    return `<img class="ptile" src="assets/${sym}.png" alt="${esc(NAMES[sym])}" draggable="false">`;
  }

  function lineSvg(rows, n) {
    const w = 50, h = 40, cx = i => 5 + i * 10, cy = r => 5 + r * 10;
    let cells = "";
    for (let r = 0; r < 5; r++) for (let c = 0; c < 4; c++)
      cells += `<rect x="${r * 10 + 0.5}" y="${c * 10 + 0.5}" width="9" height="9" rx="1" class="${rows[r] === c ? "on" : ""}"/>`;
    const pts = rows.map((r, i) => `${cx(i)},${cy(r)}`).join(" ");
    return `<figure class="pline"><svg viewBox="0 0 ${w} ${h}" aria-label="Payline ${n}">${cells}<polyline points="${pts}"/></svg><figcaption>${n}</figcaption></figure>`;
  }

  /**
   * opts: { bet: integer 6dp, fmt(amount) -> string, social: bool, modeCost: {bonus, extremebonus} }
   */
  function render(opts) {
    const { bet, fmt, social } = opts;
    const cost = opts.modeCost || { bonus: 100, extremebonus: 400 };
    const t = s => T(s, social);
    const money = mult => fmt(Math.round(mult * bet));

    const payRows = ORDER.map(sym => {
      const p = PAYS[sym];
      return `<div class="prow">
        ${tile(sym)}
        <div class="pname">${esc(t(NAMES[sym]))}<small>${sym}</small></div>
        <div class="pvals">
          <div><b>5</b> ${x(p[0])} <em>${money(p[0])}</em></div>
          <div><b>4</b> ${x(p[1])} <em>${money(p[1])}</em></div>
          <div><b>3</b> ${x(p[2])} <em>${money(p[2])}</em></div>
        </div>
      </div>`;
    }).join("");

    const html = `
<section>
  <h4>${t("About the game")}</h4>
  <p>${t(`Smukiez Tag Run is a 5-reel, 4-row video slot with 30 fixed paylines. Wins form left to right on adjacent reels starting from reel 1, and only the highest win per line counts. The values below are multiples of the total bet, shown at your current bet of ${fmt(bet)}.`)}</p>
  <div class="kvgrid">
    <div><span>RTP</span><b>${RTP}</b><small>${t("every mode")}</small></div>
    <div><span>${t("Max win")}</span><b>${x(MAX_WIN)}</b><small>${t("of the total bet")} · ${money(MAX_WIN)}</small></div>
    <div><span>${t("Volatility")}</span><b>${t("Medium–High")}</b><small>${t("bonus and Extreme carry the big wins")}</small></div>
  </div>
  <p class="fine">${t("The expected return is calculated over many plays. A round's total win is capped at the max win; once the cap is reached the round ends and any remaining feature is void.")}</p>
</section>

<section>
  <h4>${t("Game modes")}</h4>
  <table class="modes">
    <tr><th>${t("Mode")}</th><th>${t("Cost")}</th><th>${t("What you get")}</th></tr>
    <tr><td>${t("Base game")}</td><td>${x(1)} <em>${money(1)}</em></td><td>${t("One spin. Free spins trigger naturally from Crew Leader and Phantom symbols.")}</td></tr>
    <tr><td>${t("Buy Bonus")}</td><td>${x(cost.bonus)} <em>${money(cost.bonus)}</em></td><td>${t("A spin guaranteed to trigger the Standard Bonus (8, 10 or 12 free spins). RTP ")}${RTP}.</td></tr>
    <tr><td>${t("Buy Extreme")}</td><td>${x(cost.extremebonus)} <em>${money(cost.extremebonus)}</em></td><td>${t("A spin guaranteed to trigger the Extreme Bonus. RTP ")}${RTP}.</td></tr>
  </table>
  <p class="fine">${t("Both are chosen from the Bonus panel, which shows the exact total before you press Play. The max win applies to every mode.")}</p>
</section>

<section>
  <h4>${t("Paytable")}</h4>
  <p class="fine">${t("5 / 4 / 3 of a kind on a payline, multiples of the total bet and the amount at your current bet.")}</p>
  <div class="paytable">${payRows}</div>
</section>

<section>
  <h4>${t("Special symbols")}</h4>
  <div class="prow">${tile("W")}<div class="pname">${t("Paint Drip — Wild")}<small>W</small></div>
    <div class="ptext">${t("Substitutes for every paying symbol, including the characters, but not for Crew Leader or The Phantom. A drip that lands expands to paint its whole reel wild (it paints around scatters and characters, which stay in play). Every winning line gets +1x for each painted reel it crosses (paint level +1x in the base game and Standard Bonus, +2x at the start of the Extreme Bonus, upgradeable by the Tag Meter to +2x / +3x). Painted reels stack. Paint Drip also has its own line value: ")}${x(25)} / ${x(10)} / ${x(4)}.</div></div>
  <div class="prow"><img class="ptile" src="assets/BS.png" alt="Crew Leader" draggable="false"><div class="pname">${t("Crew Leader — Bonus Scatter")}<small>BS</small></div>
    <div class="ptext">${t("Appears anywhere. 3, 4 or 5 Crew Leaders on one spin award 8, 10 or 12 free spins (the Standard Bonus). Crew Leader has no line value of its own.")}</div></div>
  <div class="prow"><img class="ptile" src="assets/ES.png" alt="The Phantom" draggable="false"><div class="pname">${t("The Phantom — Extreme Scatter")}<small>ES</small></div>
    <div class="ptext">${t("2 Phantoms anywhere on one spin award 10 free spins in the Extreme Bonus directly. 1 Phantom on the same spin as a Crew Leader trigger upgrades that trigger to the Extreme Bonus, keeping its spin count. The Phantom has no line value of its own.")}</div></div>
  <div class="prow">${tile("C1")}<div class="pname">${t("Smukiez Characters — Multipliers")}<small>C1 · C2 · C3</small></div>
    <div class="ptext">${t("Characters count as premium symbols on paylines and also multiply the whole spin. Each one that lands shows its value: ")}
      <b>${t("Character 1")}</b> ${CHAR_VALUES.C1.base} (${t("free spins")} ${CHAR_VALUES.C1.free}),
      <b>${t("Character 2")}</b> ${CHAR_VALUES.C2.base},
      <b>${t("Character 3")}</b> ${CHAR_VALUES.C3.base} (${t("free spins")} ${CHAR_VALUES.C3.free}).
      ${t("If the spin has any line win, values of the same character add together and different characters multiply each other (x3 and x5 become x15), up to a combined cap of x128, applied to every line win of that spin.")}</div></div>
</section>

<section>
  <h4>${t("Free spins")}</h4>
  <p><b>${t("Standard Bonus")}</b> — ${t("3 / 4 / 5 Crew Leaders award 8 / 10 / 12 free spins. Painted reels stay painted for the whole bonus; new Paint Drips can fall on any spin. Paint level +1x per painted reel. Tag Meter target: 4.")}</p>
  <p><b>${t("Extreme Bonus")}</b> — ${t("2 Phantoms award 10 free spins; a Crew Leader trigger with a Phantom on the same spin is upgraded to Extreme with its own spin count. Reels painted on the triggering spin carry over, paint starts at +2x per painted reel, character values are richer, Tag Meter target: 3.")}</p>
  <p><b>${t("Tag Meter")}</b> — ${t("every winning free spin adds one tag. When the meter fills it awards +2 free spins (at most +6 per bonus) and raises the paint level by +1x (up to +2x in the Standard Bonus, +3x in Extreme), then resets. Free spins are not re-triggered by scatters; extra spins come only from the Tag Meter.")}</p>
  <p><b>${t("Full Wall")}</b> — ${t("painting all 5 reels during free spins completes the mural. The Full Wall awards the max win of")} ${x(MAX_WIN)} ${t("the total bet and ends the bonus.")}</p>
  <p class="fine">${t("Free spins are played at the bet and mode of the triggering spin. If the connection drops, reload the game to finish the round.")}</p>
</section>

<section>
  <h4>${t("Paylines")}</h4>
  <p class="fine">${t("30 fixed lines, always active. Wins form left to right from reel 1.")}</p>
  <div class="plines">${PAYLINES.map((r, i) => lineSvg(r, i + 1)).join("")}</div>
</section>

<section>
  <h4>${t("How to play")}</h4>
  <table class="guide">
    <tr><td><b>${t("Spin")}</b></td><td>${t("Plays one round at the current bet. The spacebar does the same. While a round is running the same button reads Skip and fast-forwards the animation (clicking the board also skips).")}</td></tr>
    <tr><td><b>− / +</b></td><td>${t("Lowers or raises the bet through every level offered by the server.")}</td></tr>
    <tr><td><b>${t("Bonus")}</b></td><td>${t("Opens the bonus chooser: pick Standard or Extreme, set the bet, and the total charge is shown before you press Play.")}</td></tr>
    <tr><td><b>${t("Auto")}</b></td><td>${t("Plays a chosen number of rounds one after another at the current bet. You confirm the number before it starts; press it again to stop. It also stops when the balance can't cover the next round.")}</td></tr>
    <tr><td><b>${t("Turbo")}</b></td><td>${t("Shortens the reel spin and win animations. Results are unaffected.")}</td></tr>
    <tr><td><b>♪</b></td><td>${t("Sound on / off. Remembered on this device.")}</td></tr>
    <tr><td><b>i</b></td><td>${t("Opens this information page.")}</td></tr>
    <tr><td><b>${t("Win / Balance")}</b></td><td>${t("The header shows the current round's win and your balance in the token you are playing with. The balance is always the amount the server reports.")}</td></tr>
  </table>
</section>

<section>
  <p class="legal">${t("Malfunction voids all wins and plays. A consistent internet connection is required. In the event of a disconnection, reload the game to finish any uncompleted rounds. The expected return is calculated over many plays. The game display is not representative of any physical device and is for illustrative purposes only. Winnings are settled according to the amount received from the Remote Game Server and not from events within the web browser. TM and © 2026 Engine.")}</p>
</section>`;
    return html;
  }

  return { render, T, PAYS, NAMES, PAYLINES, RTP, MAX_WIN };
})();
