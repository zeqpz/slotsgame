/* Game rules, paytable and UI guide — the content behind the (i) button.
 *
 * Every number here mirrors math-sdk/games/smukiez_tag_run/game_config.py; the reviewer
 * checks wins against this page, so it must never drift from the paytable the books were
 * generated with. Pays are multiples of the TOTAL bet, per cluster, stepped by cluster size.
 *
 * Social mode (Stake.us) forbids a list of gambling terms. Copy is written once in the
 * normal vocabulary and passed through T() which swaps the restricted words when the game
 * is loaded with social=true — see the jurisdiction-requirements guideline
 * (studio.engine.io/docs/approval-guidelines/jurisdiction-requirements). Where a word swap would
 * change a sentence's meaning or read badly, the sentence carries both wordings inline as
 * {real|social}: T() keeps the first outside social mode and the second in it.
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
    L6: "Smukiez Shirt", L7: "Hoodie", L8: "Bag of Weed", L9: "Freight Train", L10: "Lowrider",
  };
  const ORDER = ["H1", "H2", "H3", "H4", "H5", "H6", "H7",
                 "L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9", "L10"];
  const RTP = "96.70%", MAX_WIN = 10000;
  const MULTI_MIN = 1.25, MULTI_MAX = 1000;

  // One display name per math mode (index.json ids: base, bonus, extremebonus, boost), used by the bonus
  // shop, this page, the recent rounds and the replay window alike, in the real and the social build. The
  // guideline: a mode's name carries no restricted term ("buy", "bet", "pay"...) and is the same in the game,
  // the replay window and the math files.
  const MODE_NAMES = { base: "Base", bonus: "Bonus", extremebonus: "Extreme Bonus", boost: "Bonus Boost" };

  // Restricted word or phrase -> replacement: the jurisdiction-requirements table (2026-11-16), plus the
  // inflections it leaves to common sense ("costs", "buying", "payouts", "wagered"...). All of it is matched
  // in ONE pass, longest phrase first, on word boundaries - so "buy bonus" wins over "buy" and a replacement
  // is never swapped a second time.
  const SWEEPS = [
    ["be awarded to player's accounts", "appear in player's accounts"],
    ["place your bets", "come and play"], ["at the cost of", "for"], ["cost of", "can be played for"],
    ["buy bonus", "get bonus"], ["bonus buy", "bonus"], ["bonus buys", "bonuses"], ["total bet", "total play"],
    ["pays out", "wins"], ["paid out", "won"], ["pay out", "win"], ["paying out", "winning"],
    ["win feature", "play feature"], ["cash out", "redeem"], ["cashout", "redeem"],
    ["pay table", "win table"], ["paytable", "win table"], ["paytables", "win tables"],
    ["payouts", "wins"], ["payout", "win"], ["paylines", "win lines"], ["payline", "win line"],
    ["payments", "wins"], ["payment", "win"],
    ["betting", "playing"], ["bets", "plays"], ["bet", "play"], ["bettor", "player"], ["bettors", "players"],
    ["rebet", "respin"], ["rebets", "respins"], ["autobet", "autoplay"],
    ["bought", "instantly triggered"], ["buying", "playing"], ["buys", "plays"], ["buy", "play"],
    ["buyer", "player"], ["buyers", "players"],
    ["purchasing", "playing"], ["purchased", "played"], ["purchases", "plays"], ["purchase", "play"],
    ["cash", "coins"], ["money", "coins"], ["currencies", "tokens"], ["currency", "token"],
    ["credited", "added"], ["credits", "balance"], ["credit", "balance"],
    ["deposited", "got coins"], ["depositing", "getting coins"], ["deposits", "gets coins"], ["deposit", "get coins"],
    ["funded", "topped up"], ["funding", "balance"], ["funds", "balance"], ["fund", "balance"],
    ["gambling", "playing"], ["gamblers", "players"], ["gambler", "player"], ["gambled", "played"],
    ["gambles", "plays"], ["gamble", "play"],
    ["wagering", "playing"], ["wagered", "played"], ["wagers", "plays"], ["wager", "play"],
    ["staking", "playing"], ["staked", "played"], ["stakes", "play amounts"], ["stake", "play amount"],
    ["paying", "winning"], ["payers", "winners"], ["payer", "winner"], ["pays", "wins"], ["paid", "won"], ["pay", "win"],
    ["withdrawals", "redemptions"], ["withdrawal", "redemption"], ["withdrawing", "redeeming"],
    ["withdrawn", "redeemed"], ["withdrew", "redeemed"], ["withdraws", "redeems"], ["withdraw", "redeem"],
    ["costing", "playing for"], ["costs", "plays for"], ["cost", "amount"],
  ];
  const SWEEP_MAP = new Map(SWEEPS);
  const SWEEP_RX = new RegExp("\\b(" + SWEEPS.map(p => p[0]).sort((x, y) => y.length - x.length)
    .map(k => k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/ /g, "\\s+")).join("|") + ")\\b", "gi");
  // Each replacement word borrows the case of the word it replaces ("Buy Bonus" -> "Get
  // Bonus", "BET" -> "PLAY"), so headings and buttons keep their look.
  function recase(from, to) {
    const src = from.split(/\s+/), out = to.split(" ");
    return out.map((w, i) => {
      const s = src[Math.min(i, src.length - 1)];
      if (s === s.toUpperCase() && /[A-Z]/.test(s) && s.length > 1) return w.toUpperCase();
      if (s[0] === s[0].toUpperCase() && s[0] !== s[0].toLowerCase()) return w[0].toUpperCase() + w.slice(1);
      return w;
    }).join(" ");
  }
  // {real|social}: a sentence that needs more than a word swap carries both wordings.
  const PAIR_RX = /\{([^{}|]*)\|([^{}|]*)\}/g;
  function T(text, social) {
    if (typeof text !== "string" || !text) return text;
    const out = text.indexOf("{") < 0 ? text : text.replace(PAIR_RX, social ? "$2" : "$1");
    if (!social) return out;
    return out.replace(SWEEP_RX, m => recase(m, SWEEP_MAP.get(m.toLowerCase().replace(/\s+/g, " ")) || m));
  }
  const modeName = (mode, social) => T(MODE_NAMES[mode] || String(mode || ""), social);

  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const x = v => "x" + (Number.isInteger(v) ? v : String(v));

  function tile(sym, social) {
    if (sym === "M") return `<div class="ptile multi"><span>x5</span><small>MULTI</small></div>`;
    return `<img class="ptile" src="assets/flat/${sym}.webp" alt="${esc(T(NAMES[sym], social))}" draggable="false">`;
  }

  /**
   * opts: { bet: integer 6dp, fmt(amount) -> string, social: bool, modeCost: {bonus, extremebonus, boost} }
   */
  function render(opts) {
    const { bet, fmt, social } = opts;
    const cost = opts.modeCost || { bonus: 100, extremebonus: 400 };
    const t = s => T(s, social);
    const mode = m => esc(modeName(m, social));
    const money = mult => fmt(Math.round(mult * bet));

    const payRows = ORDER.map(sym => {
      const p = PAYS[sym];
      return `<div class="prow">
        ${tile(sym, social)}
        <div class="pname">${esc(t(NAMES[sym]))}<small>${sym}</small></div>
        <div class="pvals">
          ${TIERS.map((tier, i) => `<div><b>${tier}</b> ${x(p[i])} <em>${money(p[i])}</em></div>`).join("")}
        </div>
      </div>`;
    }).join("");

    const html = `
<section>
  <h4>${t("About the game")}</h4>
  <p>${t(`Smukiez &amp; Skelly is a 7-reel, 7-row video slot with cluster {pays|wins} and tumbling reels. A cluster is 5 or more matching symbols touching horizontally or vertically, anywhere on the board; every cluster on the board {pays|wins}, winning symbols are removed, new ones drop in, and the new board is {paid|checked for wins} again. The values below are multiples of the total bet, shown at your current {bet|play amount} of ${fmt(bet)}.`)}</p>
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
    <tr><th>${t("Mode")}</th><th>${t("{Cost|Plays for}")}</th><th>${t("What you get")}</th></tr>
    <tr><td>${mode("base")}</td><td>${x(1)} <em>${money(1)}</em></td><td>${t("One spin. Free spins trigger naturally from Crew Leader and Phantom symbols.")}</td></tr>
    <tr><td>${mode("bonus")}</td><td>${x(cost.bonus)} <em>${money(cost.bonus)}</em></td><td>${t("A spin guaranteed to trigger the Standard Bonus (10, 12 or 15 free spins). RTP ")}${RTP}.</td></tr>
    <tr><td>${mode("extremebonus")}</td><td>${x(cost.extremebonus)} <em>${money(cost.extremebonus)}</em></td><td>${t("A spin guaranteed to trigger the Extreme Bonus. RTP ")}${RTP}.</td></tr>
    ${cost.boost ? `<tr><td>${mode("boost")}</td><td>${x(cost.boost)} <em>${money(cost.boost)}</em></td><td>${t("A switch, not a {buy|one-off feature}: while it is on, every spin (autoplay included) {costs|plays for} ")}${x(cost.boost)}${t(" the {bet|play amount} and is 1.6 times as likely to trigger free spins. Everything else plays as in the base game. RTP ")}${RTP}.</td></tr>` : ""}
  </table>
  <p class="fine">${t("All are chosen from the Bonus panel, which shows the exact {price at your bet before anything is charged; a buy|amount at your current play amount before anything is taken from your balance; a bonus} asks you to confirm. While Bonus Boost is on, the {bet in the bar shows the boosted cost|play amount in the bar shows the boosted amount} of a spin. The max win applies to every mode.")}</p>
</section>

<section>
  <h4>${t("Paytable")}</h4>
  <p class="fine">${t("{Pays|Wins} by cluster size: 5 / 6 / 7-8 / 9-11 / 12-15 / 16 or more matching symbols touching horizontally or vertically. Multiples of the total bet and the amount at your current {bet|play amount}. There is no wild symbol.")}</p>
  <div class="paytable">${payRows}</div>
</section>

<section>
  <h4>${t("Special symbols")}</h4>
  <div class="prow">${tile("M")}<div class="pname">${t("Multi — Multiplier")}<small>M</small></div>
    <div class="ptext">${t(`Lands with a value from ${x(MULTI_MIN)} to ${x(MULTI_MAX)}, shown on the symbol. Every winning cluster on the board is {paid|counted} first; only then does it blow out: the Multi and the four symbols sharing an edge with it are removed, each of those five cells keeps the Multi's value, and new symbols drop in on top. A winning cluster that covers one or more of those cells is multiplied by the SUM of the values on the cells it covers. When two Multis reach the same cell their values add. In the base game the values last for the rest of the spin, including every tumble; in a bonus they stay on the board for the whole feature. Crew Leader and The Phantom are never removed by a Multi. The Multi does not form clusters and has no value of its own.`)}</div></div>
  <div class="prow">${tile("M")}<div class="pname">${t("Wall Line and Full Wall")}<small>M</small></div>
    <div class="ptext">${t("Wall Line: a straight line of 3 or 4 Multis can land together, along a row or down a column; their blasts overlap, so the cells between them collect more than one value. It can land on any spin, and far more often in a bonus. Full Wall: very rarely, in the base game, every cell of the board except a Crew Leader or Phantom becomes a Multi at once; they all blow out together and the whole board drops in on top of their values.")}</div></div>
  <div class="prow"><div class="ptile multi"><span>x1.25</span><small>DROP</small></div><div class="pname">${t("Line Drops")}</div>
    <div class="ptext">${t("Every winning cluster, once {paid|counted}, leaves a small multiplier (x1.25, x1.5 or x2) on one of its own cells for every five symbols it held, chosen at random. A line drop adds to whatever value that cell already holds and lasts exactly as a Multi's value does: for the rest of the spin in the base game, for the whole feature in a bonus. It never changes the win of the cluster that left it.")}</div></div>
  <div class="prow"><img class="ptile" src="assets/flat/BS.webp" alt="Crew Leader" draggable="false"><div class="pname">${t("Crew Leader — Bonus Scatter")}<small>BS</small></div>
    <div class="ptext">${t("Appears anywhere. 3, 4 or 5 Crew Leaders on one spin award 10, 12 or 15 free spins (the Standard Bonus). Crew Leader does not form clusters and has no value of its own.")}</div></div>
  <div class="prow"><img class="ptile" src="assets/flat/ES.webp" alt="The Phantom" draggable="false"><div class="pname">${t("The Phantom — Extreme Scatter")}<small>ES</small></div>
    <div class="ptext">${t("2 Phantoms anywhere on one spin award 17 free spins in the Extreme Bonus directly. 1 Phantom on the same spin as a Crew Leader trigger upgrades that trigger to the Extreme Bonus, keeping its spin count. The Phantom does not form clusters and has no value of its own.")}</div></div>
</section>

<section>
  <h4>${t("Free spins")}</h4>
  <p><b>${t("Standard Bonus")}</b> — ${t("3 / 4 / 5 Crew Leaders award 10 / 12 / 15 free spins. Multis land more often than in the base game and Wall Lines far more often, and every value on the board - a Multi's or a line drop's - stays there for the whole bonus.")}</p>
  <p><b>${t("Extreme Bonus")}</b> — ${t("2 Phantoms award 17 free spins; a Crew Leader trigger with a Phantom on the same spin is upgraded to Extreme with its own spin count. Multis land more often still, every Multi is worth x2 or more, and Wall Lines land far more often than in the base game.")}</p>
  <p><b>${t("Spins")}</b> — ${t("a bonus plays exactly the free spins its trigger awarded. Free spins are not re-triggered and no spins are added during the feature.")}</p>
  <p class="fine">${t("Free spins are played at the {bet|play amount} and mode of the triggering spin. If the connection drops, reload the game to finish the round.")}</p>
</section>

<section>
  <h4>${t("How to play")}</h4>
  <table class="guide">
    <tr><td><b>${t("Spin")}</b></td><td>${t("Plays one round at the current {bet|play amount}. The spacebar does the same. While the reels are turning the button reads Skip and lands them at once (clicking the board also skips); every winning cluster is always shown in full.")}</td></tr>
    <tr><td><b>− / +</b></td><td>${t("Lowers or raises the {bet|play amount} through every level offered by the server.")}</td></tr>
    <tr><td><b>${t("Bonus")}</b></td><td>${t("Opens the bonus panel: Bonus, Extreme Bonus and Bonus Boost, each with its {price|amount} at the current {bet|play amount}, which can be changed there. Bonus and Extreme Bonus take two presses - Get, then Confirm - and {nothing is charged|nothing is taken from your balance} before the second; Bonus Boost is switched on and off.")}</td></tr>
    <tr><td><b>${t("Auto")}</b></td><td>${t("Plays a chosen number of rounds one after another at the current {bet|play amount}. You confirm the number before it starts; press Auto again, or Spin between two rounds, to stop it. Only the next round has to be covered: it stops by itself when the balance can't cover it, and every {bet|play amount} level the balance covers can be played again at once.")}</td></tr>
    <tr><td><b>${t("Rapid")}</b></td><td>${t("Shortens the reel spin and win animations. Results are unaffected.")}</td></tr>
    <tr><td><b>${t("Info")}</b></td><td>${t("Opens this page: the rules, the paytable and your recent rounds.")}</td></tr>
    <tr><td><b>${t("Audio")}</b></td><td>${t("Opens the Sound and Music volume sliders. Slide one all the way left to silence it; with both at zero every sound in the game is off. Levels are remembered on this device.")}</td></tr>
    <tr><td><b>${t("Win / Balance")}</b></td><td>${t("The bar shows your balance in the token you are playing with, and the current round's win while there is one. The balance is always the amount the server reports.")}</td></tr>
  </table>
</section>

<section>
  <p class="legal">${t("Malfunction voids all wins and plays. A consistent internet connection is required. In the event of a disconnection, reload the game to finish any uncompleted rounds. The expected return is calculated over many plays. The game display is not representative of any physical device and is for illustrative purposes only. Winnings are settled according to the amount received from the Remote Game Server and not from events within the web browser. TM and © 2026 Engine.")}</p>
</section>`;
    return html;
  }

  return { render, T, modeName, MODE_NAMES, SWEEPS, PAYS, TIERS, NAMES, RTP, MAX_WIN };
})();
