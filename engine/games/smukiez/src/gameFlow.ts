// Slot Engine's onHandleGameFlow hook: one SmukiezRound per simulation attempt, wired to the GameContext - its
// seeded RNG, the parsed reel strips, the wallet (per board win, per spin confirm), tags (the Python force records)
// and the book.
//
// Book events are written flat and 0-indexed straight into the book (`data._getBook().events`), the way the v5
// books and the front end have them. Slot Engine's own `data.addBookEvent` nests every payload under `data` and
// numbers events from 1 ({index: 1, type, data: {...}}), which the unmodified front end cannot read. Like
// addBookEvent, nothing is recorded during dry runs.
import { GameContext, GameSymbol, Reels, SPIN_TYPE } from "@slot-engine/core"
import { STRIP_IDS } from "./config"
import { SmukiezResultSet } from "./conditions"
import { SmukiezRound } from "./round"

const stripsByMode = new Map<string, Record<string, Reels>>()
function strips(ctx: GameContext<any, any, any>): Record<string, Reels> {
  const mode = ctx.state.currentGameMode
  let s = stripsByMode.get(mode)
  if (!s) {
    s = Object.fromEntries(STRIP_IDS.map((id) => [id, ctx.services.game.getReelsetById(mode, id)]))
    stripsByMode.set(mode, s)
  }
  return s
}

export function onHandleGameFlow(ctx: GameContext<any, any, any>) {
  const rs = ctx.state.currentResultSet as SmukiezResultSet
  const round = new SmukiezRound(
    {
      uniform: () => ctx.services.rng.randomFloat(0, 1),
      symbols: ctx.config.symbols as Map<string, GameSymbol>,
      strips: strips(ctx),
      clusterCtx: ctx,
      events: ctx.state.isDryRun ? null : ctx.services.data._getBook().events,
      record: (rec) => ctx.services.data.tag(rec),
      addWin: (amount) => ctx.services.wallet.addSpinWin(amount),
      confirmSpin: () => ctx.services.wallet.confirmSpinWin(),
      awardFreespins: (n) => ctx.services.game.awardFreespins(n),
      setGameType: (t) => {
        ctx.state.currentSpinType = t === "basegame" ? SPIN_TYPE.BASE_GAME : SPIN_TYPE.FREE_SPINS
      },
    },
    rs.conditions,
    rs.criteria,
  ).run()
  ctx.state.userData.accepted = round.accepted
  // an unwanted trigger (Python's self.repeat): this attempt can no longer meet its criteria
  if (round.repeat) ctx.state.skipAttempt = true
}
