// Optimisation targets mirroring math-sdk/games/smukiez_tag_run/game_optimization.py (v5).
//
// The Math SDK optimiser takes its "fences" in order and each one CLAIMS books: wincap = every book paying exactly
// 10,000x, "0" = every book paying 0, freegame = every remaining book with a {symbol: scatter} force record (the
// standard triggers AND the upgraded Extreme Bonuses, which also record their Crew Leaders), extremegame = the
// remaining {symbol: scatter_extreme} books (the direct Extreme entries), wallcover = the {symbol: wallcover} books,
// basegame = whatever is left. Slot Engine's `match` targets claim books the same way (first match wins, in the
// order defined), so the targets below reproduce the v5 fences book for book; the round tags exactly the records
// the Python game makes (src/round.ts: io.record).
//
// What cannot carry over is the Rust optimiser's search ("pig farm": candidate distributions scored on simulated
// sessions, num_show / num_per_fence / m2m / test_spins parameters). Slot Engine solves each target analytically:
// per-book priors (optionally scaled), tilted by (1+x)^-mu until the target's average win is met. The base game's
// win profile (base_book_scaling + BASE_TAIL) is therefore given to it as scale rules - the same per-book weights
// the Python function computes from the simulated pool.
import fs from "fs"
import type { OptimizationConfig, ScaleRule, SlotGame } from "@slot-engine/core"
import { WINCAP } from "./config"

export const BASE_TAIL: Array<[number, number | null, number]> = [
  [5, 20, 100],
  [20, 100, 250],
  [100, null, 15000],
]
export const BASE_TAIL_ASK = 0.8
export const BASE_TOP_LIFT = 3.0

/** The v5 conditions (game_optimization.py OptimizationSetup). */
export const TARGETS = {
  base: {
    wincap: { rtp: 0.002, avgWin: WINCAP },
    "0": { rtp: 0 },
    freegame: { rtp: 0.34, hr: 240 },
    extremegame: { rtp: 0.047, hr: 8000 },
    wallcover: { rtp: 0.012, hr: 80000 },
    basegame: { rtp: 0.566, hr: 2.5 },
  },
  bonus: { wincap: { rtp: 0.004, avgWin: WINCAP }, freegame: { rtp: 0.963 } },
  extremebonus: { wincap: { rtp: 0.0018, avgWin: WINCAP }, extremegame: { rtp: 0.9652 } },
}
const COST = { base: 1, bonus: 100, extremebonus: 400 }
/** hr of a fixed-payout fence: av_win / rtp / bet (the Rust optimiser's parse_fence_info). */
const capHitRate = (mode: keyof typeof COST) => WINCAP / TARGETS[mode].wincap.rtp / COST[mode]

export function optimizationConfig(baseScale: ScaleRule[]): OptimizationConfig {
  const t = TARGETS
  const cap = [WINCAP, WINCAP] as [number, number]
  return {
    base: {
      targets: {
        wincap: { match: { winRange: cap }, hitRate: capHitRate("base"), rtp: t.base.wincap.rtp },
        "0": { rtp: 0 }, // no hitRate: it absorbs the remaining probability, as the "0" fence does in the Math SDK
        freegame: { match: { tags: { symbol: "scatter" } }, hitRate: t.base.freegame.hr, rtp: t.base.freegame.rtp },
        extremegame: { match: { tags: { symbol: "scatter_extreme" } }, hitRate: t.base.extremegame.hr, rtp: t.base.extremegame.rtp },
        wallcover: { match: { tags: { symbol: "wallcover" } }, hitRate: t.base.wallcover.hr, rtp: t.base.wallcover.rtp },
        basegame: { hitRate: t.base.basegame.hr, rtp: t.base.basegame.rtp, ...(baseScale.length ? { scale: baseScale } : {}) },
      },
    },
    bonus: {
      targets: {
        wincap: { match: { winRange: cap }, hitRate: capHitRate("bonus"), rtp: t.bonus.wincap.rtp },
        freegame: { rtp: t.bonus.freegame.rtp },
      },
    },
    extremebonus: {
      targets: {
        wincap: { match: { winRange: cap }, hitRate: capHitRate("extremebonus"), rtp: t.extremebonus.wincap.rtp },
        extremegame: { rtp: t.extremebonus.extremegame.rtp },
      },
    },
  }
}

function readCsv(file: string): string[][] {
  return fs
    .readFileSync(file, "utf8")
    .split("\n")
    .filter((l) => l.trim())
    .map((l) => l.split(","))
}

/** Book ids carrying a tag with all of `filter`'s properties (Slot Engine's tags_<mode>.json). */
function taggedIds(tagsFile: string, filter: Record<string, string>): Set<number> {
  const out = new Set<number>()
  if (!fs.existsSync(tagsFile)) return out
  for (const tag of JSON.parse(fs.readFileSync(tagsFile, "utf8"))) {
    if (Object.entries(filter).every(([k, v]) => tag.search.some((s: any) => s.name === k && s.value === v)))
      for (const id of tag.bookIds) out.add(id)
  }
  return out
}

/**
 * game_optimization.base_book_scaling, for Slot Engine: one scale rule per payout of the base game's winning spins
 * up to 5x (a v^-a tilt, `a` solved so the small wins carry what BASE_TAIL leaves of the criteria's mean) and one
 * per BASE_TAIL band above it (each band asked for at 80%, the 100x+ band at three times that). The Python version
 * also multiplies by each payout's book count to turn the Rust optimiser's per-payout weights into per-book ones;
 * Slot Engine's priors are per book already, so the factor is the per-book weight alone.
 * Returns [] (no scaling) when there is no pool yet.
 */
export function baseBookScaling(game: SlotGame, log = console.log): ScaleRule[] {
  const paths = game.getMetadata().paths
  const lutFile = paths.lookupTable("base")
  const segFile = paths.lookupTableSegmented("base")
  if (!fs.existsSync(lutFile) || !fs.existsSync(segFile)) return []
  const criteriaOf = new Map(readCsv(segFile).map((r) => [Number(r[0]), r[1]!]))
  // the books the earlier fences take: exact payouts (0, the cap) and the tag searches
  const taken = new Set<number>()
  for (const symbol of ["scatter", "scatter_extreme", "wallcover"]) for (const id of taggedIds(paths.tags("base"), { symbol })) taken.add(id)
  const counts = new Map<number, number>()
  for (const [id, , p] of readCsv(lutFile)) {
    const payout = Number(p)
    if (taken.has(Number(id)) || payout === 0 || payout === WINCAP * 100 || criteriaOf.get(Number(id)) !== "basegame") continue
    counts.set(payout / 100, (counts.get(payout / 100) ?? 0) + 1)
  }
  if (counts.size === 0) return []
  const { rtp, hr } = TARGETS.base.basegame
  const share = 1 / hr
  const mean = rtp * hr
  const split = BASE_TAIL[0]![0]
  const bands: Array<{ lo: number; hi: number; m: number; size: number; avg: number }> = []
  for (const [lo, hi, oneIn] of BASE_TAIL) {
    let size = 0, sum = 0
    for (const [v, n] of counts) if (v > lo && v <= (hi ?? Infinity)) (size += n), (sum += v * n)
    if (size === 0) {
      log(`  base_book_scaling: no book in the ${lo}-${hi ?? "inf"}x band - the band is left unscaled`)
      continue
    }
    bands.push({ lo, hi: hi ?? Infinity, m: 1 / oneIn / share, size, avg: sum / size })
  }
  const tailMass = bands.reduce((s, b) => s + b.m, 0)
  const smallMean = (mean - bands.reduce((s, b) => s + b.m * b.avg, 0)) / (1 - tailMass)
  const small = [...counts].filter(([v]) => v <= split)
  let lo = -5, hi = 10, a = 0, tilted = 0
  for (let i = 0; i < 100; i++) {
    a = (lo + hi) / 2
    tilted = small.reduce((s, [v, n]) => s + n * v ** -a, 0)
    if (small.reduce((s, [v, n]) => s + n * v ** -a * v, 0) / tilted > smallMean) lo = a
    else hi = a
  }
  const got = small.reduce((s, [v, n]) => s + n * v ** -a * v, 0) / tilted
  if (Math.abs(got - smallMean) > 1e-6) {
    log(`  base_book_scaling: BASE_TAIL leaves the small wins a ${smallMean.toFixed(3)}x mean the pool cannot tilt to - no scaling`)
    return []
  }
  const total = tilted / (1 - tailMass)
  const rules: ScaleRule[] = small
    .sort(([x], [y]) => x - y)
    .map(([v]) => ({ winRange: [Math.round((v - 0.005) * 1000) / 1000, Math.round((v + 0.005) * 1000) / 1000], factor: v ** -a }))
  for (const b of bands) {
    const level = (BASE_TAIL_ASK * b.m * total) / b.size * (b.lo >= 100 ? BASE_TOP_LIFT : 1)
    rules.push({ winRange: [b.lo + 0.005, b.hi === Infinity ? 1e9 : b.hi + 0.005], factor: level })
  }
  log(`  base_book_scaling: ${counts.size} payouts over ${[...counts.values()].reduce((x, y) => x + y, 0)} books; small wins tilted v^-${a.toFixed(4)}; ` +
    bands.map((b) => `${b.lo}-${b.hi === Infinity ? "inf" : b.hi}x: ${b.size} books`).join(", "))
  return rules
}
