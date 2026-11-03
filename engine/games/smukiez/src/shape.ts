// The published v5 distribution shape, carried over as Slot Engine scale rules.
//
// Stake's Rust optimiser does not just tilt a target to its mean: it builds thousands of candidate distributions
// per fence and keeps the one that scores best on simulated short sessions (test_spins 10-200), which favours a
// tight, low-variance shape. Slot Engine has no such search - one (1+x)^-mu tilt per target - so on the same pool
// and targets it lands every mean exactly but with roughly twice the v5 volatility. To reproduce the shape the
// v5 search settled on, src/v5_profile.json holds each v5 fence's published payout distribution (made by
// tools/v5_profile.ts from math-sdk/.../publish_files) and shapeRules() turns it into per-band scale factors for
// the native pool: band by band the native books get v5's probability mass, and the tilt only closes what is left.
import fs from "fs"
import path from "path"
import type { ScaleRule } from "@slot-engine/core"
import { WINCAP } from "./config"
import { bookLines } from "./books"

/** The Math SDK fence a book falls in (game_optimization.py conditions, in order). */
export function fenceOf(book: { payoutMultiplier: number; events: any[] }, mode: string): string {
  if (book.payoutMultiplier === WINCAP * 100) return "wincap"
  if (mode === "bonus") return "freegame"
  if (mode === "extremebonus") return "extremegame"
  if (book.payoutMultiplier === 0) return "0"
  let bs = 0, es = 0, cover = false
  for (const e of book.events) {
    if (e.type === "freeSpinTrigger") bs = e.positions.length
    else if (e.type === "extremeTrigger") es = e.positions.length
    else if (e.type === "wallDrop" && e.kind === "cover") cover = true
  }
  if (bs >= 3) return "freegame" // {symbol: scatter} record
  if (es > 0) return "extremegame" // {symbol: scatter_extreme}
  if (cover) return "wallcover"
  return "basegame"
}

/** payout cents -> book count, per fence, of a books file. */
export async function fenceCounts(booksFile: string, mode: string) {
  const out: Record<string, Map<number, number>> = {}
  for await (const line of bookLines(booksFile)) {
    const b = JSON.parse(line)
    const m = (out[fenceOf(b, mode)] ??= new Map())
    m.set(b.payoutMultiplier, (m.get(b.payoutMultiplier) ?? 0) + 1)
  }
  return out
}

export type Profile = Record<string, Record<string, Array<[cents: number, share: number]>>>
const SRC = path.basename(__dirname) === "__build__" ? path.join(path.dirname(__dirname), "src") : __dirname
export const PROFILE_FILE = path.join(SRC, "v5_profile.json")
export const loadProfile = (): Profile | null =>
  fs.existsSync(PROFILE_FILE) ? JSON.parse(fs.readFileSync(PROFILE_FILE, "utf8")) : null

// Log-spaced band edges (x bet); bands are merged until each holds at least MIN_BOOKS native books.
const EDGES = [0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 1.05, 1.25, 1.5, 1.75, 2, 2.5, 3, 3.5, 4, 5, 6, 7.5, 10, 12.5, 15, 20, 25, 30, 40, 50, 60, 75, 100, 125, 150, 200, 250, 300, 400, 500, 750, 1000, 1500, 2000, 3000, 5000, 7500]
const MIN_BOOKS = 5

/** Scale rules giving the native pool `counts` (payout cents -> books) the v5 fence's band masses. */
export function shapeRules(counts: Map<number, number>, v5: Array<[number, number]>): ScaleRule[] {
  const x = (c: number) => c / 100
  let bands: Array<[number, number]> = []
  let lo = 0
  for (const e of [...EDGES, Infinity]) {
    bands.push([lo, e])
    lo = e
  }
  const nIn = ([a, b]: [number, number]) => [...counts].reduce((s, [c, n]) => (x(c) >= a && x(c) < b ? s + n : s), 0)
  // merge thin bands into their lower neighbour, from the top, then the bottom one upwards
  for (let i = bands.length - 1; i > 0; i--) if (nIn(bands[i]!) < MIN_BOOKS) bands.splice(i - 1, 2, [bands[i - 1]![0], bands[i]![1]])
  while (bands.length > 1 && nIn(bands[0]!) < MIN_BOOKS) bands.splice(0, 2, [bands[0]![0], bands[1]![1]])
  bands = bands.filter((b) => nIn(b) > 0)
  if (bands.length < 2) return []
  const total = [...counts.values()].reduce((s, n) => s + n, 0)
  const bandOf = (c: number) => {
    const i = bands.findIndex(([a, b]) => x(c) >= a && x(c) < b)
    return i >= 0 ? i : x(c) < bands[0]![0] ? 0 : bands.length - 1 // v5 mass outside the native range: nearest band
  }
  const mass = new Array(bands.length).fill(0)
  for (const [c, p] of v5) mass[bandOf(c)] += p
  return bands.map((b, i) => ({
    winRange: [b[0], b[1] === Infinity ? 1e9 : b[1] - 1e-6] as [number, number],
    factor: Math.max(mass[i] / (nIn(b) / total), 1e-9),
  }))
}
