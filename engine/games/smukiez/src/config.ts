// Smukiez's City (math v5) - every constant of math-sdk/games/smukiez_tag_run/game_config.py, unchanged.
// Weight tables are [value, weight] lists in the Python dicts' order (a weighted pick is order-independent anyway).

export type Table<T> = ReadonlyArray<readonly [T, number]>
export type GameType = "basegame" | "freegame"

export const GAME_ID = "smukiez"
export const NUM_REELS = 7
export const NUM_ROWS = 7
export const WINCAP = 10000
export const RTP = 0.967

/** Max board changes (cascades) within one spin; a board's paid clusters and its Multi blow-outs are one. */
export const MAX_TUMBLES_PER_SPIN = 12
/** After the budget is spent, Multis still on the board blow out (no pays) up to this many board changes. */
export const SETTLE_TUMBLE_CAP = MAX_TUMBLES_PER_SPIN + 4

/** Paytable size tiers: 5 | 6 | 7-8 | 9-11 | 12-15 | 16+ (up to the whole 49-cell board). Lower bounds: */
export const TIER_SIZES = [5, 6, 7, 9, 12, 16] as const
export const CLUSTER_PAYS: Record<string, readonly number[]> = {
  H1: [4.0, 8.0, 16.0, 40.0, 100.0, 400.0],
  H2: [3.2, 6.0, 12.0, 30.0, 80.0, 300.0],
  H3: [2.4, 4.8, 10.0, 24.0, 60.0, 200.0],
  H4: [2.0, 4.0, 8.0, 20.0, 48.0, 160.0],
  H5: [1.6, 3.2, 6.4, 16.0, 40.0, 120.0],
  H6: [1.6, 3.2, 6.4, 16.0, 40.0, 120.0],
  H7: [1.2, 2.4, 4.8, 12.0, 32.0, 100.0],
  L1: [0.8, 1.6, 3.2, 8.0, 20.0, 60.0],
  L2: [0.8, 1.6, 3.2, 8.0, 20.0, 60.0],
  L3: [0.8, 1.2, 2.4, 6.0, 16.0, 48.0],
  L4: [0.4, 1.2, 2.4, 6.0, 16.0, 48.0],
  L5: [0.4, 0.8, 2.0, 4.8, 12.0, 40.0],
  L6: [0.4, 0.8, 2.0, 4.8, 12.0, 40.0],
  L7: [0.4, 0.8, 1.6, 4.0, 10.0, 32.0],
  L8: [0.4, 0.8, 1.6, 4.0, 10.0, 32.0],
  L9: [0.4, 0.8, 1.2, 3.2, 8.0, 24.0],
  L10: [0.4, 0.8, 1.2, 3.2, 8.0, 24.0],
}
export const PAYING_SYMBOLS = Object.keys(CLUSTER_PAYS)
/** M = the Multi (booster), BS = Crew Leader (bonus scatter), ES = The Phantom (extreme scatter). */
export const SPECIAL_SYMBOLS = ["M", "BS", "ES"] as const

/** Crew Leaders on the base board -> free spins (the game_config docstring's 8/10/12 is stale: the code
 *  and the published v5 books award 10/12/15). */
export const FREESPIN_TRIGGERS: Record<number, number> = { 3: 10, 4: 12, 5: 15 }
export const MIN_TRIGGER = 3
export const MAX_TRIGGER = 5
/** anticipation_triggers: min trigger - 1 Crew Leaders before the following reels anticipate. */
export const ANTICIPATION_TRIGGER = MIN_TRIGGER - 1
export const EXTREME_DIRECT_COUNT = 2
export const EXTREME_DIRECT_SPINS = 17
/** Crew Leaders forced next to the two Phantoms of a direct Extreme entry. */
export const EXTREME_DIRECT_BS: Table<number> = [[0, 60], [1, 25], [2, 15]]

/** Wall events: a straight line of 3-4 walls on a reveal, and the full-board cover (forced by criteria). */
export const WALL_LINE_CHANCE: Record<GameType, number> = { basegame: 1 / 40, freegame: 1 / 6 }
export const WALL_LINE_LENGTHS: Table<number> = [[3, 70], [4, 30]]
export const COVER_MULT_VALUES: Table<number> = [[5, 30], [10, 30], [20, 25], [50, 12], [100, 3]]
/** Line drops: each paid cluster drops one small multiplier per five symbols it held on its own cells. */
export const LINE_DROP_PER = 5
export const LINE_DROP_VALUES: Table<number> = [[1.25, 60], [1.5, 25], [2, 15]]

/** The Multi's value, rolled the moment it lands. */
export const BOOSTER_MULTS_BASE: Table<number> = [
  [1.25, 480], [1.5, 280], [2, 150], [3, 60], [5, 22], [10, 7], [20, 3],
  [50, 1.2], [100, 0.5], [250, 0.22], [500, 0.12], [1000, 0.55],
]
export const BOOSTER_MULTS_FREE: Table<number> = [
  [1.25, 300], [1.5, 240], [2, 220], [3, 150], [5, 80], [10, 35], [20, 14],
  [50, 5], [100, 2], [250, 0.7], [500, 0.3], [1000, 0.15],
]
export const BOOSTER_MULTS_EXTREME: Table<number> = [
  [2, 320], [3, 260], [5, 160], [10, 70], [20, 25], [50, 8],
  [100, 3], [250, 1], [500, 0.45], [1000, 0.22],
]
/** Wincap simulations only: a Multi-dense strip where every Multi is 1000x. */
export const BOOSTER_MULTS_RICH: Table<number> = [[1000, 100]]

/** Reel strips (copied unchanged from math-sdk/games/smukiez_tag_run/reels). */
export const STRIP_IDS = ["BR0", "BRE", "FR0", "FRE", "FRWCAP"] as const
export type StripId = (typeof STRIP_IDS)[number]

/** Python's get_win_level, "standard" (setWin) and "endFeature" (freeSpinEnd) level tables. */
export function winLevel(win: number, key: "standard" | "endFeature"): number {
  const levels =
    key === "standard"
      ? [[0, 0.1], [0.1, 1], [1, 2], [2, 5], [5, 15], [15, 30], [30, 50], [50, 100], [100, WINCAP], [WINCAP, Infinity]]
      : [[0, 1], [1, 5], [5, 10], [10, 20], [20, 50], [50, 100], [100, 500], [500, 2000], [2000, WINCAP], [WINCAP, Infinity]]
  for (let i = 0; i < levels.length; i++) if (win >= levels[i]![0]! && win < levels[i]![1]!) return i + 1
  throw new Error(`winLevel not found: ${win}`)
}
