/* Game rules, paytable and UI guide — the content behind the (i) button.
 *
 * Every number here mirrors math-sdk/games/smukiez_tag_run/game_config.py; the reviewer
 * checks wins against this page, so it must never drift from the paytable the books were
 * generated with. Pays are multiples of the TOTAL bet, per cluster, stepped by cluster size.
 *
 * Social mode (Stake.us) forbids a list of gambling terms. Copy is written once in the
 * normal vocabulary and passed through T() which swaps the restricted words when the game
 * is loaded with social=true — see the jurisdiction-requirements guideline.
 */
const RULES = (() => {
  // Cluster size tiers: a cluster of 5, 6, 7-8, 9-11, 12-15 or 16+ matching symbols. One
  // entry per tier, in that order — verbatim from game_config.py.
  const TIERS = ["5", "6", "7-8", "9-11", "12-15", "16+"];
  const PAYS = {   // symbol: [t5, t6, t7_8, t9_11, t12_15, t16plus]
    H1: [4, 8, 16, 40, 100, 400],
    H2: [3.2, 6, 12, 30, 80, 300],
    H3: [2.4, 4.8, 10, 24, 60, 200],
    H4: [2, 4, 8, 20, 48, 160],
    H5: [1.6, 3.2, 6.4, 16, 40, 120],
    H6: [1.6, 3.2, 6.4, 16, 40, 120],
    H7: [1.2, 2.4, 4.8, 12, 32, 100],
    L1: [0.8, 1.6, 3.2, 8, 20, 60],
    L2: [0.8, 1.6, 3.2, 8, 20, 60],
    L3: [0.8, 1.2, 2.4, 6, 16, 48],
    L4: [0.4, 1.2, 2.4, 6, 16, 48],
    L5: [0.4, 0.8, 2, 4.8, 12, 40],
    L6: [0.4, 0.8, 2, 4.8, 12, 40],
    L7: [0.4, 0.8, 1.6, 4, 10, 32],
    L8: [0.4, 0.8, 1.6, 4, 10, 32],
    L9: [0.4, 0.8, 1.2, 3.2, 8, 24],
    L10: [0.4, 0.8, 1.2, 3.2, 8, 24],
  };
  const NAMES = {
    M: "Multi", BS: "Crew Leader", ES: "The Phantom",
    H1: "Bag of Cash", H2: "Cartoon Glock", H3: "Gold Chain", H4: "Fresh Kicks", H5: "Boombox",
    H6: "Skateboard", H7: "Limited Drop Box",
    L1: "Spray Can", L2: "Graffiti Markers", L3: "Smukiez Beanie", L4: "Custom Hangtag", L5: "Dice",
    L6: "Smukiez Shirt", L7: "Hoodie", L8: "Bag of Weed", L9: "Freight Train", L10: "Brick Wall Chunk",
  };
  const ORDER = ["H1", "H2", "H3", "H4", "H5", "H6", "H7",
                 "L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9", "L10"];
  const RTP = "96.50%", MAX_WIN = 5000;
  const MULTI_MIN = 1.25, MULTI_MAX = 1000;

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
    if (sym === "M") return `<div class="ptile multi"><span>x5</span><small>MULTI</small></div>`;
    return `<img class="ptile" src="assets/${sym}.png" alt="${esc(NAMES[sym])}" draggable="false">`;
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
          ${TIERS.map((tier, i) => `<div><b>${tier}</b> ${x(p[i])} <em>${money(p[i])}</em></div>`).join("")}
        </div>
      </div>`;
    }).join("");

    const html = `
<section>
  <h4>${t("About the game")}</h4>
  <p>${t(`Smukiez Tag Run is a 7-reel, 7-row video slot with cluster pays and tumbling reels. A cluster is 5 or more matching symbols touching horizontally or vertically, anywhere on the board; every cluster on the board pays, winning symbols are removed, new ones drop in, and the new board is paid again. The values below are multiples of the total bet, shown at your current bet of ${fmt(bet)}.`)}</p>
  <div class="kvgrid">
    <div><span>RTP</span><b>${RTP}</b><small>${t("every mode")}</small></div>
    <div><span>${t("Max win")}</span><b>${x(MAX_WIN)}</b><small>${t("of the total bet")} · ${money(MAX_WIN)}</small></div>
    <div><span>${t("Volatility")}</span><b>${t("High")}</b><small>${t("the Multi carries the big wins")}</small></div>
  </div>
  <p class="fine">${t("The expected return is calculated over many plays. A round's total win is capped at the max win; once the cap is reached the round ends and any remaining feature is void.")}</p>
</section>

<section>
  <h4>${t("Game modes")}</h4>
  <table class="modes">
    <tr><th>${t("Mode")}</th><th>${t("Cost")}</th><th>${t("What you get")}</th></tr>
    <tr><td>${t("Base game")}</td><td>${x(1)} <em>${money(1)}</em></td><td>${t("One spin. Free spins trigger naturally from Crew Leader and Phantom symbols.")}</td></tr>
    <tr><td>${t("Buy Bonus")}</td><td>${x(cost.bonus)} <em>${money(cost.bonus)}</em></td><td>${t("A spin guaranteed to trigger the Standard Bonus (10, 12 or 15 free spins). RTP ")}${RTP}.</td></tr>
    <tr><td>${t("Buy Extreme")}</td><td>${x(cost.extremebonus)} <em>${money(cost.extremebonus)}</em></td><td>${t("A spin guaranteed to trigger the Extreme Bonus. RTP ")}${RTP}.</td></tr>
  </table>
  <p class="fine">${t("Both are chosen from the Bonus panel, which shows the exact total before you press Play. The max win applies to every mode.")}</p>
</section>

<section>
  <h4>${t("Paytable")}</h4>
  <p class="fine">${t("Pays by cluster size: 5 / 6 / 7-8 / 9-11 / 12-15 / 16 or more matching symbols touching horizontally or vertically. Multiples of the total bet and the amount at your current bet. There is no wild symbol.")}</p>
  <div class="paytable">${payRows}</div>
</section>

<section>
  <h4>${t("Special symbols")}</h4>
  <div class="prow">${tile("M")}<div class="pname">${t("Multi — Multiplier")}<small>M</small></div>
    <div class="ptext">${t(`Lands with a value from ${x(MULTI_MIN)} to ${x(MULTI_MAX)}, shown on the symbol. Every winning cluster on the board is paid first; only then does it blow out: the Multi and the four symbols sharing an edge with it are removed, each of those five cells keeps the Multi's value, and new symbols drop in on top. A winning cluster that covers one or more of those cells is multiplied by the SUM of the values on the cells it covers. When two Multis reach the same cell their values add. In the base game the values last for the rest of the spin, including every tumble; in a bonus they stay on the board for the whole feature. Crew Leader and The Phantom are never removed by a Multi. The Multi does not form clusters and has no value of its own.`)}</div></div>
  <div class="prow"><img class="ptile" src="assets/BS.png" alt="Crew Leader" draggable="false"><div class="pname">${t("Crew Leader — Bonus Scatter")}<small>BS</small></div>
    <div class="ptext">${t("Appears anywhere. 3, 4 or 5 Crew Leaders on one spin award 10, 12 or 15 free spins (the Standard Bonus). Crew Leader does not form clusters and has no value of its own.")}</div></div>
  <div class="prow"><img class="ptile" src="assets/ES.png" alt="The Phantom" draggable="false"><div class="pname">${t("The Phantom — Extreme Scatter")}<small>ES</small></div>
    <div class="ptext">${t("2 Phantoms anywhere on one spin award 17 free spins in the Extreme Bonus directly. 1 Phantom on the same spin as a Crew Leader trigger upgrades that trigger to the Extreme Bonus, keeping its spin count. The Phantom does not form clusters and has no value of its own.")}</div></div>
</section>

<section>
  <h4>${t("Free spins")}</h4>
  <p><b>${t("Standard Bonus")}</b> — ${t("3 / 4 / 5 Crew Leaders award 10 / 12 / 15 free spins. Multis land more often than in the base game, and every value a Multi leaves on the board stays there for the whole bonus. Tag Meter target: 4.")}</p>
  <p><b>${t("Extreme Bonus")}</b> — ${t("2 Phantoms award 17 free spins; a Crew Leader trigger with a Phantom on the same spin is upgraded to Extreme with its own spin count. Multis land more often still and their values run richer. Tag Meter target: 3.")}</p>
  <p><b>${t("Tag Meter")}</b> — ${t("every winning free spin adds one tag. When the meter fills it awards +3 free spins (at most +9 per bonus), then resets. Free spins are not re-triggered by scatters; extra spins come only from the Tag Meter.")}</p>
  <p class="fine">${t("Free spins are played at the bet and mode of the triggering spin. If the connection drops, reload the game to finish the round.")}</p>
</section>

<section>
  <h4>${t("How to play")}</h4>
  <table class="guide">
    <tr><td><b>${t("Spin")}</b></td><td>${t("Plays one round at the current bet. The spacebar does the same. While the reels are turning the button reads Skip and lands them at once (clicking the board also skips); every winning cluster is always shown in full.")}</td></tr>
    <tr><td><b>− / +</b></td><td>${t("Lowers or raises the bet through every level offered by the server.")}</td></tr>
    <tr><td><b>${t("Bonus")}</b></td><td>${t("Opens the bonus chooser: pick Standard or Extreme, set the bet, and the total charge is shown before you press Play.")}</td></tr>
    <tr><td><b>${t("Auto")}</b></td><td>${t("Plays a chosen number of rounds one after another at the current bet. You confirm the number before it starts; press it again to stop. It also stops when the balance can't cover the next round.")}</td></tr>
    <tr><td><b>${t("Rapid")}</b></td><td>${t("Shortens the reel spin and win animations. Results are unaffected.")}</td></tr>
    <tr><td><b>☰</b></td><td>${t("Opens the sound, music and information controls. Sound and music each have their own level, remembered on this device.")}</td></tr>
    <tr><td><b>${t("Win / Balance")}</b></td><td>${t("The bar shows your balance in the token you are playing with, and the current round's win while there is one. The balance is always the amount the server reports.")}</td></tr>
  </table>
</section>

<section>
  <p class="legal">${t("Malfunction voids all wins and plays. A consistent internet connection is required. In the event of a disconnection, reload the game to finish any uncompleted rounds. The expected return is calculated over many plays. The game display is not representative of any physical device and is for illustrative purposes only. Winnings are settled according to the amount received from the Remote Game Server and not from events within the web browser. TM and © 2026 Engine.")}</p>
</section>`;
    return html;
  }

  return { render, T, PAYS, TIERS, NAMES, RTP, MAX_WIN };
})();
