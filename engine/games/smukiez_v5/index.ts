// Smukiez's City, math v5 AS PUBLISHED - the Stake Math SDK build (math-sdk/games/smukiez_tag_run), brought into
// Slot Engine's layout by engine/tools/import_math_sdk.py so the panel and its local gaming server serve those
// exact books (same ids, weights and events). It declares the modes and symbols only: it is never simulated here
// (the native Slot Engine port of the game is its own game). Re-import after the Math SDK math changes:
//   python engine/tools/import_math_sdk.py math-sdk/games/smukiez_tag_run/library/publish_files engine/games/smukiez_v5
import path from "path"
import {
  GameMode,
  GameSymbol,
  InferGameType,
  ResultSet,
  SPIN_TYPE,
  StaticReelSet,
  createSlotGame,
  defineGameModes,
  defineSymbols,
  defineUserState,
} from "@slot-engine/core"

const REELS_DIR = path.join(__dirname, "../../../math-sdk/games/smukiez_tag_run/reels")
const reelSets = [
  new StaticReelSet({ id: "base", csvPath: path.join(REELS_DIR, "BR0.csv") }),
  new StaticReelSet({ id: "bonus", csvPath: path.join(REELS_DIR, "FR0.csv") }),
]
const reelWeights = { [SPIN_TYPE.BASE_GAME]: { base: 1 }, [SPIN_TYPE.FREE_SPINS]: { bonus: 1 } }

export const userState = defineUserState({})
export type UserStateType = typeof userState

const ids = ["M", "BS", "ES", "H1", "H2", "H3", "H4", "H5", "H6", "H7", "L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9", "L10"] as const
export const symbols = defineSymbols(Object.fromEntries(ids.map((id) => [id, new GameSymbol({ id })])) as Record<(typeof ids)[number], GameSymbol>)
export type SymbolsType = typeof symbols

function mode(name: string, cost: number, isBonusBuy: boolean) {
  return new GameMode({
    name,
    cost,
    rtp: 0.967,
    reelsAmount: 7,
    symbolsPerReel: [7, 7, 7, 7, 7, 7, 7],
    isBonusBuy,
    reelSets,
    resultSets: [new ResultSet({ criteria: "published", quota: 1, reelWeights })],
  })
}

export const gameModes = defineGameModes({
  base: mode("base", 1, false),
  bonus: mode("bonus", 100, true),
  extremebonus: mode("extremebonus", 400, true),
  // Bonus Boost: a base spin at 1.25x the bet with the free spins 1.6x as likely (not a buy)
  boost: mode("boost", 1.25, false),
})
export type GameModesType = typeof gameModes
export type GameType = InferGameType<GameModesType, SymbolsType, UserStateType>

export const game = createSlotGame<GameType>({
  id: "smukiez_tag_run",
  name: "Smukiez's City (math v5, published)",
  maxWinX: 10000,
  gameModes,
  symbols,
  userState,
  hooks: {
    onHandleGameFlow() {
      throw new Error("smukiez_v5 serves the Math SDK's published books; simulate the native port instead")
    },
  },
  rootDir: __dirname,
})
