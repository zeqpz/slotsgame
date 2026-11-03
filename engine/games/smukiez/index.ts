// Smukiez's City, math v5 - native Slot Engine port of the Stake Math SDK game math-sdk/games/smukiez_tag_run.
// Same reel strips (reels/*.csv, copied unchanged), paytable, modes and costs; the result sets mirror the Python
// Distributions (src/conditions.ts), the round is a line-by-line port of the Python game (src/round.ts) and its books
// carry the same events as the published v5 books, so the unmodified front end plays them.
//
// Run from engine/:
//   npx tsx ./games/smukiez/index.ts --slot-engine-run                        simulate + optimise + finish + analyse
//   npx tsx ./games/smukiez/index.ts --slot-engine-run --base=100000 --bonus=20000 --extremebonus=20000 --threads=6
//   npx tsx ./games/smukiez/index.ts --slot-engine-run --no-sim               re-optimise the existing pool
//   flags: --no-sim --no-opt --no-finish --no-analysis --modes=base,bonus --threads=N
//          --shape=v5 (default: each fence takes the published v5 distribution shape, src/shape.ts)
//          --shape=tail (game_optimization.py alone: its targets + base_book_scaling, Slot Engine tilt only)
import path from "path"
import { isMainThread } from "worker_threads"
import {
  GameMode,
  GameSymbol,
  InferGameType,
  StaticReelSet,
  createSlotGame,
  defineGameModes,
  defineSymbols,
  defineUserState,
} from "@slot-engine/core"
import { CLUSTER_PAYS, GAME_ID, NUM_REELS, NUM_ROWS, RTP, STRIP_IDS, TIER_SIZES, WINCAP } from "./src/config"
import { RESULT_SETS } from "./src/conditions"
import { onHandleGameFlow } from "./src/gameFlow"

// Workers run a bundle of this file from __build__/, where __dirname is the build folder.
const ROOT = path.basename(__dirname) === "__build__" ? path.dirname(__dirname) : __dirname

export const userState = defineUserState({ accepted: false })
export type UserStateType = typeof userState

const pays = (id: string) => Object.fromEntries(TIER_SIZES.map((size, i) => [size, CLUSTER_PAYS[id]![i]!]))
export const symbols = defineSymbols({
  M: new GameSymbol({ id: "M", properties: { isBooster: true, isMultiplier: true } }), // the Multi (wall)
  BS: new GameSymbol({ id: "BS", properties: { isScatter: true } }), // Crew Leader
  ES: new GameSymbol({ id: "ES", properties: { isExtremeScatter: true } }), // The Phantom
  H1: new GameSymbol({ id: "H1", pays: pays("H1") }), // Bag of Cash
  H2: new GameSymbol({ id: "H2", pays: pays("H2") }), // Cartoon Glock
  H3: new GameSymbol({ id: "H3", pays: pays("H3") }), // Gold Chain
  H4: new GameSymbol({ id: "H4", pays: pays("H4") }), // Fresh Kicks
  H5: new GameSymbol({ id: "H5", pays: pays("H5") }), // Boombox
  H6: new GameSymbol({ id: "H6", pays: pays("H6") }), // Skateboard
  H7: new GameSymbol({ id: "H7", pays: pays("H7") }), // Limited Drop Box
  L1: new GameSymbol({ id: "L1", pays: pays("L1") }),
  L2: new GameSymbol({ id: "L2", pays: pays("L2") }),
  L3: new GameSymbol({ id: "L3", pays: pays("L3") }),
  L4: new GameSymbol({ id: "L4", pays: pays("L4") }),
  L5: new GameSymbol({ id: "L5", pays: pays("L5") }),
  L6: new GameSymbol({ id: "L6", pays: pays("L6") }),
  L7: new GameSymbol({ id: "L7", pays: pays("L7") }),
  L8: new GameSymbol({ id: "L8", pays: pays("L8") }),
  L9: new GameSymbol({ id: "L9", pays: pays("L9") }),
  L10: new GameSymbol({ id: "L10", pays: pays("L10") }),
})
export type SymbolsType = typeof symbols

const reelSets = STRIP_IDS.map((id) => new StaticReelSet({ id, csvPath: path.join(ROOT, "reels", `${id}.csv`) }))

function mode(name: keyof typeof RESULT_SETS, cost: number, opts: { isBonusBuy: boolean; isFeature: boolean }) {
  return new GameMode({
    name,
    cost,
    rtp: RTP,
    reelsAmount: NUM_REELS,
    symbolsPerReel: new Array(NUM_REELS).fill(NUM_ROWS),
    reelSets,
    resultSets: RESULT_SETS[name],
    ...opts,
  })
}

// base is a "feature" mode in the Python BetMode (is_feature=True; the published config.json says feature: true)
export const gameModes = defineGameModes({
  base: mode("base", 1, { isBonusBuy: false, isFeature: true }),
  bonus: mode("bonus", 100, { isBonusBuy: true, isFeature: false }),
  extremebonus: mode("extremebonus", 400, { isBonusBuy: true, isFeature: false }),
})
export type GameModesType = typeof gameModes
export type GameType = InferGameType<GameModesType, SymbolsType, UserStateType>

export const game = createSlotGame<GameType>({
  id: GAME_ID,
  name: "Smukiez's City (math v5, native Slot Engine)",
  maxWinX: WINCAP,
  gameModes,
  symbols,
  padSymbols: 1,
  userState,
  hooks: { onHandleGameFlow },
  rootDir: ROOT,
})

// The defaults finish in minutes on a busy 8-core machine; the published v5 pool was 100k / 20k / 20k.
export const DEFAULT_SIMS = { base: 100_000, bonus: 20_000, extremebonus: 20_000 }

if (!isMainThread) {
  // a simulation worker: it runs its share of the books configured by the main thread
  game.configureSimulation({ simRunsAmount: DEFAULT_SIMS, concurrency: 2 })
  game.runTasks({ doSimulation: true })
} else if (process.argv.includes("--slot-engine-run")) {
  import("./src/pipeline").then(({ runPipeline }) => runPipeline(game)).catch((e) => {
    console.error(e)
    process.exit(1)
  })
}
