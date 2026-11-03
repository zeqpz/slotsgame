// The result sets: math-sdk/games/smukiez_tag_run/game_config.py's bet-mode Distributions (criteria, quota,
// win_criteria and conditions) as Slot Engine ResultSets.
import { GameContext, ResultSet, SPIN_TYPE } from "@slot-engine/core"
import {
  BOOSTER_MULTS_BASE,
  BOOSTER_MULTS_EXTREME,
  BOOSTER_MULTS_FREE,
  BOOSTER_MULTS_RICH,
  GameType,
  Table,
  WINCAP,
} from "./config"

/** A Distribution's conditions (game_config.py), keyed by game type like the Python dicts. */
export interface Conditions {
  reelWeights: Partial<Record<GameType, Table<string>>>
  boosterMults: Partial<Record<GameType, Table<number>>>
  scatterTriggers?: Table<number>
  extremeTriggerStyle?: Table<string>
  forceWincap: boolean
  forceFreegame: boolean
  forceExtreme: boolean
  forceCover: boolean
  /** Distribution.win_criteria: the exact final win the round must end on. */
  winCriteria?: number
}

/**
 * A ResultSet carrying its Distribution's conditions. Acceptance is the Python game's `check_repeat`, which the round
 * evaluates and leaves in `state.userData.accepted`. Slot Engine's own check would also reject a natural 10,000x in
 * any criteria but "wincap" (it requires the win to stay under maxWinX there); the Math SDK keeps those (v5 holds
 * 2 in the base pool and 9 in the extreme pool), so the check is the Python one, unchanged.
 */
export class SmukiezResultSet extends ResultSet<any> {
  conditions: Conditions
  constructor(opts: ConstructorParameters<typeof ResultSet<any>>[0] & { conditions: Conditions }) {
    super(opts)
    this.conditions = opts.conditions
  }
  meetsCriteria(ctx: GameContext): boolean {
    const ok = ctx.state.userData.accepted === true
    if (ok && this.forceMaxWin) ctx.services.data.tag({ maxwin: true })
    return ok
  }
}

const SE_SPIN: Record<GameType, string> = { basegame: SPIN_TYPE.BASE_GAME, freegame: SPIN_TYPE.FREE_SPINS }

function resultSet(criteria: string, quota: number, c: Omit<Conditions, "forceWincap" | "forceFreegame" | "forceExtreme" | "forceCover"> & Partial<Conditions>) {
  const conditions: Conditions = { forceWincap: false, forceFreegame: false, forceExtreme: false, forceCover: false, ...c }
  // Slot Engine wants weights for both spin types; criteria that never reach free spins get the standard strip
  const weights = (t: GameType) => Object.fromEntries(conditions.reelWeights[t] ?? conditions.reelWeights.basegame ?? [])
  return new SmukiezResultSet({
    criteria,
    quota,
    conditions,
    reelWeights: { [SE_SPIN.basegame]: weights("basegame"), [SE_SPIN.freegame]: conditions.reelWeights.freegame ? weights("freegame") : { FR0: 1 } } as any,
    forceMaxWin: conditions.forceWincap || undefined,
    forceFreespins: conditions.forceFreegame || undefined,
    multiplier: conditions.winCriteria === 0 ? 0 : undefined,
    userData: { forceExtreme: conditions.forceExtreme, forceCover: conditions.forceCover },
  })
}

export const RESULT_SETS = {
  base: [
    resultSet("wincap", 0.0002, {
      winCriteria: WINCAP,
      reelWeights: { basegame: [["BRE", 1]], freegame: [["FRWCAP", 1]] },
      boosterMults: { basegame: BOOSTER_MULTS_BASE, freegame: BOOSTER_MULTS_RICH },
      scatterTriggers: [[3, 1], [4, 2]],
      extremeTriggerStyle: [["direct", 50], ["upgrade", 50]],
      forceWincap: true,
      forceFreegame: true,
      forceExtreme: true,
    }),
    resultSet("extremegame", 0.02, {
      reelWeights: { basegame: [["BRE", 1]], freegame: [["FRE", 1]] },
      boosterMults: { basegame: BOOSTER_MULTS_BASE, freegame: BOOSTER_MULTS_EXTREME },
      scatterTriggers: [[3, 75], [4, 25]],
      extremeTriggerStyle: [["direct", 60], ["upgrade", 40]],
      forceFreegame: true,
      forceExtreme: true,
    }),
    resultSet("freegame", 0.07, {
      reelWeights: { basegame: [["BR0", 1]], freegame: [["FR0", 1]] },
      boosterMults: { basegame: BOOSTER_MULTS_BASE, freegame: BOOSTER_MULTS_FREE },
      scatterTriggers: [[3, 80], [4, 15], [5, 5]],
      forceFreegame: true,
    }),
    // the board cover: forced on the reveal, so how often a player sees one is the optimiser's call
    resultSet("wallcover", 0.002, {
      reelWeights: { basegame: [["BR0", 1]] },
      boosterMults: { basegame: BOOSTER_MULTS_BASE },
      forceCover: true,
    }),
    resultSet("0", 0.35, {
      winCriteria: 0,
      reelWeights: { basegame: [["BR0", 1]] },
      boosterMults: { basegame: BOOSTER_MULTS_BASE },
    }),
    resultSet("basegame", 0.5578, {
      reelWeights: { basegame: [["BR0", 1]] },
      boosterMults: { basegame: BOOSTER_MULTS_BASE },
    }),
  ],
  bonus: [
    resultSet("wincap", 0.0005, {
      winCriteria: WINCAP,
      reelWeights: { basegame: [["BR0", 1]], freegame: [["FRWCAP", 1]] },
      boosterMults: { basegame: BOOSTER_MULTS_BASE, freegame: BOOSTER_MULTS_RICH },
      scatterTriggers: [[3, 1], [4, 2], [5, 1]],
      forceWincap: true,
      forceFreegame: true,
    }),
    resultSet("freegame", 0.998, {
      reelWeights: { basegame: [["BR0", 1]], freegame: [["FR0", 1]] },
      boosterMults: { basegame: BOOSTER_MULTS_BASE, freegame: BOOSTER_MULTS_FREE },
      scatterTriggers: [[3, 70], [4, 20], [5, 10]],
      forceFreegame: true,
    }),
  ],
  extremebonus: [
    resultSet("wincap", 0.001, {
      winCriteria: WINCAP,
      reelWeights: { basegame: [["BRE", 1]], freegame: [["FRWCAP", 1]] },
      boosterMults: { basegame: BOOSTER_MULTS_BASE, freegame: BOOSTER_MULTS_RICH },
      scatterTriggers: [[3, 1], [4, 2]],
      extremeTriggerStyle: [["direct", 50], ["upgrade", 50]],
      forceWincap: true,
      forceFreegame: true,
      forceExtreme: true,
    }),
    resultSet("extremegame", 0.995, {
      reelWeights: { basegame: [["BRE", 1]], freegame: [["FRE", 1]] },
      boosterMults: { basegame: BOOSTER_MULTS_BASE, freegame: BOOSTER_MULTS_EXTREME },
      scatterTriggers: [[3, 75], [4, 25]],
      extremeTriggerStyle: [["direct", 60], ["upgrade", 40]],
      forceFreegame: true,
      forceExtreme: true,
    }),
  ],
}
