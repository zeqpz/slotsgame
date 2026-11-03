// tools/finish_luts.py, ported: the two corrections the v5 pipeline applies to the optimiser's tables before
// they are published, both leaving every payout's probability where the optimiser put it.
//   1. (base) A 1000x wall is a rare sight and never one board on repeat: no book showing a base-game wall of
//      1000x+ may weigh more than an ordinary losing round's book, and together such rounds come at most once in
//      1,500. The excess goes to the other books of the same payout, so each payout's total weight is unchanged.
//   2. (every mode) The exact RTP is brought 1e-10 under 0.967 by adding weight to the lowest-paying book.
// Integer arithmetic throughout (BigInt), like the Python Fractions. Rewrites the published lookup tables and the
// lookup-table index Slot Engine keeps next to them.
import fs from "fs"
import type { SlotGame } from "@slot-engine/core"
import { bookLines } from "./books"

type Row = [id: number, weight: bigint, payout: bigint]
const MARGIN_DEN = 10n ** 10n // MARGIN = 1/10^10

function readLut(file: string): Row[] {
  return fs
    .readFileSync(file, "utf8")
    .split("\n")
    .filter((l) => l.trim())
    .map((l) => {
      const [i, w, p] = l.split(",")
      return [Number(i), BigInt(w!), BigInt(p!)] as Row
    })
}
function writeLut(file: string, rows: Row[]) {
  fs.writeFileSync(file, rows.map(([i, w, p]) => `${i},${w},${p}\n`).join(""))
}
/** Slot Engine's lookUpTable_<mode>.index: the byte offset of every line of the published table, u64 LE. */
function writeLutIndex(lutFile: string, indexFile: string) {
  const lines = fs.readFileSync(lutFile, "utf8").split("\n").filter((l) => l.trim())
  const buf = Buffer.alloc(lines.length * 8)
  let offset = 0n
  lines.forEach((l, i) => {
    buf.writeBigUInt64LE(offset, i * 8)
    offset += BigInt(Buffer.byteLength(l + "\n"))
  })
  fs.writeFileSync(indexFile, buf)
}

/** Ids of the books where a wall worth `value` or more blows out in the base game. */
export async function rareWallBooks(booksFile: string, value: number): Promise<Set<number>> {
  const ids = new Set<number>()
  for await (const line of bookLines(booksFile)) {
    const book = JSON.parse(line)
    let gametype = "basegame"
    for (const ev of book.events) {
      if (ev.type === "reveal") gametype = ev.gameType ?? gametype
      else if (gametype === "basegame" && ev.type === "booster" && ev.boosters.some((b: any) => b.mult >= value)) {
        ids.add(book.id)
        break
      }
    }
  }
  return ids
}

const sum = (xs: bigint[]) => xs.reduce((a, b) => a + b, 0n)
const min = (a: bigint, b: bigint) => (a < b ? a : b)

/** Correction 1 (finish_luts.cap_rare), in place. */
export function capRare(rows: Row[], rare: Set<number>, oneIn?: number) {
  const zero = rows.filter((r) => r[2] === 0n).map((r) => r[1]).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0))
  if (!zero.length) return { capped: 0, before: 0n, after: 0n }
  let cap = zero[Math.floor(zero.length / 2)]!
  const before = sum(rows.filter((r) => rare.has(r[0])).map((r) => r[1]))
  const groups = new Map<bigint, Row[]>()
  for (const r of rows) {
    const g = groups.get(r[2])
    if (g) g.push(r)
    else groups.set(r[2], [r])
  }
  if (oneIn) {
    const movable: Row[] = []
    for (const g of groups.values()) if (g.some((x) => !rare.has(x[0]))) for (const r of g) if (rare.has(r[0])) movable.push(r)
    const allowed = sum(rows.map((r) => r[1])) / BigInt(oneIn) - (before - sum(movable.map((r) => r[1])))
    const load = (c: bigint) => sum(movable.map((r) => min(r[1], c)))
    if (load(cap) > allowed) {
      let lo = 1n, hi = cap
      while (lo < hi) {
        const mid = (lo + hi + 1n) / 2n
        if (load(mid) <= allowed) lo = mid
        else hi = mid - 1n
      }
      cap = lo
    }
  }
  let capped = 0
  for (const group of groups.values()) {
    const heavy = group.filter((r) => rare.has(r[0]) && r[1] > cap)
    const others = group.filter((r) => !rare.has(r[0]))
    if (!heavy.length || !others.length) continue
    const excess = sum(heavy.map((r) => r[1] - cap))
    for (const r of heavy) r[1] = cap
    const base = sum(others.map((r) => r[1]))
    let given = 0n
    for (const r of others) {
      const share = (excess * r[1]) / base
      r[1] += share
      given += share
    }
    let top = others[0]!
    for (const r of others) if (r[1] > top[1]) top = r
    top[1] += excess - given // the rounding remainder: the payout's total is exact
    capped += heavy.length
  }
  const after = sum(rows.filter((r) => rare.has(r[0])).map((r) => r[1]))
  return { capped, before, after }
}

/** Correction 2 (finish_luts.trim_rtp), in place: returns the weight added to the lowest-paying book. */
export function trimRtp(rows: Row[], cost: bigint, ceilingMilli = 967n): bigint {
  // ceiling = 0.967 - 1e-10 = n / d
  const d = MARGIN_DEN
  const n = ceilingMilli * (d / 1000n) - 1n
  const excess = sum(rows.map((r) => r[1] * r[2])) * d - n * 100n * cost * sum(rows.map((r) => r[1]))
  if (excess <= 0n) return 0n
  let low = rows[0]!
  for (const r of rows) if (r[2] < low[2]) low = r
  const k = n * 100n * cost - low[2] * d
  const add = (excess + k - 1n) / k
  low[1] += add
  return add
}

const rtpOf = (rows: Row[], cost: bigint) => Number(sum(rows.map((r) => r[1] * r[2])) * 10n ** 15n / (sum(rows.map((r) => r[1])) * 100n * cost)) / 1e15

export async function finishLuts(game: SlotGame, opts: { rareWall?: number; rareWallRate?: number; modes?: string[] } = {}) {
  const { rareWall = 1000, rareWallRate = 1500 } = opts
  const paths = game.getMetadata().paths
  const modes = game.getConfig().gameModes
  for (const name of opts.modes ?? Object.keys(modes)) {
    const lutFile = paths.lookupTablePublish(name)
    if (!fs.existsSync(lutFile)) continue
    const cost = BigInt(modes[name]!.cost)
    const rows = readLut(lutFile)
    const total = sum(rows.map((r) => r[1]))
    const payouts = new Map<bigint, bigint>()
    for (const r of rows) payouts.set(r[2], (payouts.get(r[2]) ?? 0n) + r[1])
    const r0 = rtpOf(rows, cost)
    let changed = false
    if (name === "base") {
      const rare = await rareWallBooks(paths.booksCompressed(name), rareWall)
      const { capped, before, after } = capRare(rows, rare, rareWallRate)
      let heaviest = 0n
      for (const r of rows) if (rare.has(r[0]) && r[1] > heaviest) heaviest = r[1]
      const one = (w: bigint) => (w > 0n ? Math.round(Number(total) / Number(w)).toLocaleString("en-US") : "never")
      console.log(`${name}: ${rare.size} books show a base-game wall of ${rareWall}x+; ${capped} capped; such a round comes 1 in ${one(before)} -> 1 in ${one(after)}` +
        (heaviest ? `, the most-drawn such board 1 in ${one(heaviest)}` : ""))
      changed ||= capped > 0
    }
    const added = trimRtp(rows, cost)
    changed ||= added > 0n
    const after = new Map<bigint, bigint>()
    for (const r of rows) after.set(r[2], (after.get(r[2]) ?? 0n) + r[1])
    let drift = 0
    for (const [p, w] of payouts) drift = Math.max(drift, Math.abs(Number(after.get(p)!) / Number(total + added) - Number(w) / Number(total)))
    console.log(`${name}: rtp ${r0.toFixed(12)} -> ${rtpOf(rows, cost).toFixed(12)}${added ? ` (+${added} weight on the lowest payout)` : ""}; largest payout-share drift ${drift.toExponential(1)}`)
    if (changed) {
      writeLut(lutFile, rows)
      writeLutIndex(lutFile, paths.lookupTableIndex(name))
      console.log(`  wrote ${lutFile}`)
    }
  }
}
