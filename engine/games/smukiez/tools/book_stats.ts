// Statistics of one mode's books, the same way for the published v5 (Math SDK) books and for the native Slot Engine
// build, so the two can be compared side by side (tools/compare.ts):
//   * weighted (by the published lookup table): RTP, hit rate, volatility, max-win and bonus-trigger frequency, ...
//   * the raw simulated pool per criteria (unweighted: what the math produces before the optimiser weighs it)
//   * mechanic distributions (unweighted): Multi values, wall lines, line drops, tumbles, clusters, triggers
//   * the event schema: per event type, every field path with its key orders and value types
//
//   npx tsx games/smukiez/tools/book_stats.ts --which=v5|native --mode=base [--limit=N] [--out=file.json]
import fs from "fs"
import path from "path"
import { args, bookLines, modeFiles, MODE_COST, readLut, readSegmented, BUILD_DIR } from "./lib"

type Counter = Record<string, number>
const inc = (c: Counter, k: string | number, by = 1) => {
  c[k] = (c[k] ?? 0) + by
}

/** Path-based schema: path -> { types, keyOrders } (arrays add "[]" to the path). */
type Schema = Record<string, { types: Counter; keys: Counter }>
function walk(v: any, p: string, s: Schema) {
  const node = (s[p] ??= { types: {}, keys: {} })
  if (v === null) return inc(node.types, "null")
  if (Array.isArray(v)) {
    inc(node.types, "array")
    for (const x of v) walk(x, p + "[]", s)
    return
  }
  if (typeof v === "object") {
    inc(node.types, "object")
    inc(node.keys, Object.keys(v).join(","))
    for (const k of Object.keys(v)) walk(v[k], p + "." + k, s)
    return
  }
  if (typeof v === "number") return inc(node.types, Number.isInteger(v) ? "int" : "frac")
  inc(node.types, typeof v)
}

const lines = bookLines

async function main() {
  const a = args()
  const which = (a.which ?? "native") as "v5" | "native"
  const mode = a.mode ?? "base"
  const limit = a.limit ? Number(a.limit) : Infinity
  const schemaBooks = Number(a.schemaBooks ?? 3000)
  const files = modeFiles(which, mode, a.build ?? BUILD_DIR)
  const lut = readLut(files.lut)
  const seg = files.segmented && fs.existsSync(files.segmented) ? readSegmented(files.segmented) : undefined
  const cost = MODE_COST[mode]!

  const W = { total: 0, payout: 0, payout2: 0, zero: 0, lessBet: 0, cap: 0, trig: 0, std: 0, direct: 0, upgrade: 0,
    trigPayout: 0, trigFree: 0, cover: 0, wall1000: 0, wallLine: 0, baseWin: 0, freeWin: 0 }
  const pool: Record<string, { n: number; sum: number; sum2: number; max: number; zero: number; cap: number }> = {}
  const mech: Record<string, any> = {}
  const triggers: Counter = {}
  const eventTypes: Counter = {}
  const schema: Record<string, Schema> = {}
  const schemaSeen: Counter = {}
  const bookKeys: Counter = {}
  const checks = { books: 0, payoutMismatch: 0, badIndex: 0, negPadding: 0, maxEvents: 0, maxBytes: 0, over512k: 0,
    lutMissing: 0, firstIndex: {} as Counter }
  const sizes: number[] = []

  const M = (key: string) =>
    (mech[key] ??= {
      reveals: 0, spins: 0, multBoard: {}, multPad: {}, multsOnBoard: 0, wallLine: {}, wallOrient: {}, cover: 0,
      boosterEvents: 0, boosters: 0, boosterValues: {}, boosterCells: {}, lineDropValues: {}, lineDropEvents: 0,
      drops: 0, tumblesPerSpin: {}, winBoardsPerSpin: {}, clusterKinds: {}, clusterSyms: {}, wins: 0, winCents: 0,
      spinWinCents: 0, spinsWithWin: 0,
    })

  for await (const line of lines(files.books)) {
    if (checks.books >= limit) break
    const book = JSON.parse(line)
    checks.books++
    const bytes = Buffer.byteLength(line)
    sizes.push(bytes)
    checks.maxBytes = Math.max(checks.maxBytes, bytes)
    if (bytes > 524288) checks.over512k++
    inc(bookKeys, Object.keys(book).join(","))
    const row = lut.get(book.id)
    if (!row) {
      checks.lutMissing++
      continue
    }
    const [w, payout] = row
    if (payout !== book.payoutMultiplier) checks.payoutMismatch++
    const criteria: string = book.criteria ?? seg?.get(book.id)?.criteria ?? "?"
    const x = payout / 100
    W.total += w
    W.payout += w * x
    W.payout2 += w * x * x
    if (payout === 0) W.zero += w
    if (x < cost) W.lessBet += w
    if (payout >= 1_000_000) W.cap += w
    const pc = (pool[criteria] ??= { n: 0, sum: 0, sum2: 0, max: 0, zero: 0, cap: 0 })
    pc.n++
    pc.sum += x
    pc.sum2 += x * x
    pc.max = Math.max(pc.max, x)
    if (payout === 0) pc.zero++
    if (payout >= 1_000_000) pc.cap++

    const ev: any[] = book.events
    checks.maxEvents = Math.max(checks.maxEvents, ev.length)
    if (ev.length) inc(checks.firstIndex, ev[0].index)
    if (ev.some((e, i) => e.index !== i)) checks.badIndex++
    let gametype = "basegame"
    let key = `${criteria}/basegame`
    let tumbles = 0, winBoards = 0, spinWin = 0
    let reason = "", totalFs = 0, nBS = 0, nES = 0, freeEnd = 0
    let hasCover = false, has1000 = false, hasLine = false
    const closeSpin = () => {
      const m = M(key)
      m.spins++
      inc(m.tumblesPerSpin, tumbles)
      inc(m.winBoardsPerSpin, winBoards)
      if (spinWin > 0) {
        m.spinsWithWin++
        m.spinWinCents += spinWin
      }
    }
    let open = false
    const doSchema = checks.books <= schemaBooks
    for (const e of ev) {
      inc(eventTypes, e.type)
      if (doSchema || (schemaSeen[e.type] ?? 0) < 200) {
        inc(schemaSeen, e.type)
        walk(e, "", (schema[e.type] ??= {}))
      }
      switch (e.type) {
        case "reveal": {
          if (open) closeSpin()
          open = true
          tumbles = winBoards = spinWin = 0
          gametype = e.gameType
          key = `${criteria}/${gametype}`
          const m = M(key)
          m.reveals++
          for (const p of e.paddingPositions) if (p < 0) checks.negPadding++
          for (const col of e.board)
            col.forEach((s: any, row: number) => {
              if (s.name !== "M") return
              if (row === 0 || row === col.length - 1) inc(m.multPad, s.multiplier)
              else {
                inc(m.multBoard, s.multiplier)
                m.multsOnBoard++
              }
            })
          break
        }
        case "wallDrop": {
          const m = M(key)
          if (e.kind === "cover") {
            m.cover++
            hasCover = true
          } else {
            inc(m.wallLine, e.positions.length)
            const sameReel = e.positions.every((p: any) => p.reel === e.positions[0].reel)
            inc(m.wallOrient, sameReel ? "column" : "row")
            if (gametype === "basegame") hasLine = true
          }
          break
        }
        case "booster": {
          const m = M(key)
          m.boosterEvents++
          for (const b of e.boosters) {
            m.boosters++
            inc(m.boosterValues, b.mult)
            inc(m.boosterCells, b.cells.length)
            if (gametype === "basegame" && b.mult >= 1000) has1000 = true
          }
          break
        }
        case "lineMults": {
          const m = M(key)
          m.lineDropEvents++
          for (const d of e.drops) {
            m.drops++
            inc(m.lineDropValues, d.mult)
          }
          break
        }
        case "winInfo": {
          const m = M(key)
          winBoards++
          for (const wn of e.wins) {
            const kind = Array.isArray(wn) ? wn[1] : wn.kind
            const sym = Array.isArray(wn) ? wn[0] : wn.symbol
            m.wins++
            m.winCents += Array.isArray(wn) ? wn[2] : wn.win
            inc(m.clusterKinds, kind >= 16 ? "16+" : kind)
            inc(m.clusterSyms, sym)
          }
          spinWin += e.totalWin
          break
        }
        case "tumbleBoard":
          tumbles++
          break
        case "freeSpinTrigger":
          totalFs = e.totalFs
          nBS = e.positions.length
          break
        case "extremeTrigger":
          nES = e.positions.length
          break
        case "enterBonus":
          reason = e.reason
          break
        case "freeSpinEnd":
          freeEnd = e.amount / 100
          break
      }
    }
    if (open) closeSpin()
    if (reason) {
      inc(triggers, `${reason}|fs${totalFs}|bs${nBS}|es${nES}`)
      W.trig += w
      W.trigPayout += w * x
      W.trigFree += w * freeEnd
      if (reason === "standard") W.std += w
      if (reason === "extreme_direct") W.direct += w
      if (reason === "extreme_upgrade") W.upgrade += w
    }
    if (hasCover) W.cover += w
    if (has1000) W.wall1000 += w
    if (hasLine) W.wallLine += w
    const s = seg?.get(book.id)
    W.baseWin += w * (book.baseGameWins ?? s?.base ?? 0)
    W.freeWin += w * (book.freeGameWins ?? s?.free ?? 0)
  }

  sizes.sort((p, q) => p - q)
  const mean = W.payout / W.total
  const out = {
    which, mode, files, cost,
    weighted: {
      totalWeight: W.total,
      rtp: mean / cost,
      avgWin: mean,
      std: Math.sqrt(W.payout2 / W.total - mean * mean),
      hitRate: W.total / (W.total - W.zero),
      pZero: W.zero / W.total,
      pLessBet: W.lessBet / W.total,
      maxWinRate: W.cap / W.total,
      triggerRate: W.trig / W.total,
      standardRate: W.std / W.total,
      directRate: W.direct / W.total,
      upgradeRate: W.upgrade / W.total,
      avgPayoutGivenTrigger: W.trig ? W.trigPayout / W.trig : 0,
      avgBonusWin: W.trig ? W.trigFree / W.trig : 0,
      bonusRtpShare: W.freeWin / W.total / cost,
      baseRtpShare: W.baseWin / W.total / cost,
      coverRate: W.cover / W.total,
      wall1000Rate: W.wall1000 / W.total,
      baseWallLineRate: W.wallLine / W.total,
    },
    pool: Object.fromEntries(
      Object.entries(pool).map(([c, p]) => {
        const m = p.sum / p.n
        return [c, { n: p.n, mean: m, std: Math.sqrt(Math.max(0, p.sum2 / p.n - m * m)), max: p.max, zero: p.zero, cap: p.cap }]
      }),
    ),
    mech,
    triggers,
    eventTypes,
    bookKeys,
    checks: { ...checks, medianBytes: sizes[Math.floor(sizes.length / 2)] ?? 0, p99Bytes: sizes[Math.floor(sizes.length * 0.99)] ?? 0 },
    schema: Object.fromEntries(
      Object.entries(schema).map(([t, s]) => [
        t,
        Object.fromEntries(Object.entries(s).map(([p, n]) => [p, { types: Object.keys(n.types).sort(), keys: Object.keys(n.keys) }])),
      ]),
    ),
  }
  const outFile = a.out ?? path.join(__dirname, "..", "checks", `stats_${which}_${mode}.json`)
  fs.mkdirSync(path.dirname(outFile), { recursive: true })
  fs.writeFileSync(outFile, JSON.stringify(out, null, 1))
  console.log(`${which} ${mode}: ${checks.books} books, rtp ${(mean / cost).toFixed(6)}, hit 1 in ${out.weighted.hitRate.toFixed(3)}, std ${out.weighted.std.toFixed(2)} -> ${outFile}`)
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
