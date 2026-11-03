// Replay published v5 books through the native round (src/round.ts) and require every event to come out identical.
//
// A v5 book records every random decision the Python game made: the reveal shows the reel stops (paddingPositions),
// every symbol and every Multi value (walls included), wallDrop names the wall cells, lineMults the line-drop cells
// and values, tumbleBoard the value of every Multi that drops in. The replay feeds exactly those decisions into the
// native round - and nothing else: clusters, pays, multiplier sums, the Multi blow-outs, tumbles and refills from
// the strips, padding, the tumble budget, triggers, spin counts, wincap, all win events and totals are recomputed
// by the port and compared field by field (key order included) with what the Python game wrote.
//
//   npx tsx games/smukiez/tools/replay_v5.ts [--mode=base] [--limit=2000] [--skip=0] [--every=1] [--verbose]
import fs from "fs"
import path from "path"
import { GameSymbol, Reels } from "@slot-engine/core"
import { symbols } from "../index"
import { RESULT_SETS } from "../src/conditions"
import { NUM_REELS, NUM_ROWS, STRIP_IDS } from "../src/config"
import { Cell, SmukiezRound } from "../src/round"
import { args, GAME_DIR, modeFiles, readBooks, readLut } from "./lib"

const SYMBOLS = new Map<string, GameSymbol>(Object.entries(symbols))
const STRIPS: Record<string, Reels> = {}
for (const id of STRIP_IDS) {
  const rows = fs.readFileSync(path.join(GAME_DIR, "reels", `${id}.csv`), "utf8").split("\n").filter((l) => l.trim())
  const reels: Reels = Array.from({ length: NUM_REELS }, () => [])
  for (const row of rows) row.split(",").forEach((s, r) => reels[r]!.push(SYMBOLS.get(s.trim())!))
  STRIPS[id] = reels
}

class Mismatch extends Error {}

/** A SmukiezRound whose random decisions are read back from a v5 book. */
class ReplayRound extends SmukiezRound {
  reveals: any[] = []
  wallAfter = new Map<any, any>()
  lineMults: any[] = []
  tumbles: any[] = []
  curReveal: any = null
  curLine: any = null
  lineCursor = 0
  curTumble: any = null

  load(events: any[]) {
    events.forEach((e, i) => {
      if (e.type === "reveal") {
        this.reveals.push(e)
        if (events[i + 1]?.type === "wallDrop") this.wallAfter.set(e, events[i + 1])
      } else if (e.type === "lineMults") this.lineMults.push(e)
      else if (e.type === "tumbleBoard") this.tumbles.push(e)
    })
    return this
  }
  fromJson(j: any): GameSymbol {
    const def = SYMBOLS.get(j.name)
    if (!def) throw new Mismatch(`unknown symbol ${j.name}`)
    if (j.name !== "M") return def
    const m = def.clone()
    m.properties.set("multiplier", j.multiplier)
    return m
  }
  override rollBoosterMult(): number {
    return 0 // placeholder: every Multi's value is taken from the book below
  }
  override drawBoard() {
    const rev = (this.curReveal = this.reveals.shift())
    if (!rev) throw new Mismatch("the port draws more boards than the book reveals")
    const stripId = this.conds.reelWeights[this.gametype]![0]![0]
    this.fillBoard(stripId, rev.paddingPositions.slice()) // the stops, the strip and the anticipation
    const wall = this.wallAfter.get(rev)
    const wallCells = new Set<number>((wall?.positions ?? []).map((p: any) => p.reel * 8 + p.row - 1))
    for (let r = 0; r < NUM_REELS; r++) {
      const col = rev.board[r]
      const check = (want: string, got: GameSymbol, where: string) => {
        if (want !== got.id) throw new Mismatch(`reveal ${where} reel ${r}: book ${want}, strip ${stripId} gives ${got.id}`)
      }
      check(col[0].name, this.top[r]!, "top padding")
      check(col[NUM_ROWS + 1].name, this.bottom[r]!, "bottom padding")
      this.top[r] = this.fromJson(col[0])
      this.bottom[r] = this.fromJson(col[NUM_ROWS + 1])
      for (let c = 0; c < NUM_ROWS; c++) {
        if (!wallCells.has(r * 8 + c)) check(col[c + 1].name, this.board[r]![c]!, `row ${c}`)
        this.board[r]![c] = this.fromJson(col[c + 1])
      }
    }
  }
  override applyWallEvents() {
    const wall = this.wallAfter.get(this.curReveal)
    if (!wall) return
    const cells: Cell[] = wall.positions.map((p: any) => [p.reel, p.row - 1] as Cell)
    for (const [r, c] of cells) if (this.board[r]![c]!.id !== "M") throw new Mismatch("a wall cell is not a Multi")
    this.wallEvent = { kind: wall.kind, cells }
    if (wall.kind === "cover") this.io.record?.({ kind: cells.length, symbol: "wallcover", gametype: this.gametype })
  }
  override lineDrops(cells: Cell[], winIndex: number): Array<[number, number, number]> {
    if (winIndex === 0) {
      this.curLine = this.lineMults.shift()
      this.lineCursor = 0
      if (!this.curLine) throw new Mismatch("the port drops line multipliers the book does not have")
    }
    const n = Math.max(1, Math.floor(cells.length / 5))
    const drops = this.curLine.drops.slice(this.lineCursor, this.lineCursor + n)
    this.lineCursor += n
    if (drops.length !== n) throw new Mismatch(`line drops: the book has fewer than ${n} for win ${winIndex}`)
    const inCluster = new Set(cells.map(([r, c]) => r * 8 + c))
    return drops.map((d: any) => {
      if (!inCluster.has(d.reel * 8 + d.row - 1)) throw new Mismatch(`line drop at ${d.reel},${d.row} is not on win ${winIndex}'s cells`)
      return [d.reel, d.row - 1, d.mult] as [number, number, number]
    })
  }
  override tumbleFlagged() {
    this.curTumble = this.tumbles.shift()
    if (!this.curTumble) throw new Mismatch("the port tumbles more often than the book")
    super.tumbleFlagged()
  }
  override tumbleSymbol(reel: number, stripPos: number, i: number, k: number, padding: boolean): GameSymbol {
    const name = this.strip[reel]![stripPos]!.id
    const listed = this.curTumble.newSymbols[reel]?.[padding ? 0 : k - i]
    if (!listed || listed.name !== name) throw new Mismatch(`tumble reel ${reel}: strip gives ${name}, book lists ${listed?.name}`)
    return this.fromJson(listed)
  }
}

/** Deep equality with key order; returns the path of the first difference. */
function diff(a: any, b: any, p = ""): string | null {
  if (typeof a === "number" && typeof b === "number") return a === b ? null : `${p}: ${a} != ${b}`
  if (Array.isArray(a) || Array.isArray(b)) {
    if (!Array.isArray(a) || !Array.isArray(b) || a.length !== b.length) return `${p}: array ${JSON.stringify(a)?.slice(0, 120)} != ${JSON.stringify(b)?.slice(0, 120)}`
    for (let i = 0; i < a.length; i++) {
      const d = diff(a[i], b[i], `${p}[${i}]`)
      if (d) return d
    }
    return null
  }
  if (a && b && typeof a === "object" && typeof b === "object") {
    const ka = Object.keys(a), kb = Object.keys(b)
    if (ka.join(",") !== kb.join(",")) return `${p}: keys [${ka}] != [${kb}]`
    for (const k of ka) {
      const d = diff(a[k], b[k], `${p}.${k}`)
      if (d) return d
    }
    return null
  }
  return a === b ? null : `${p}: ${JSON.stringify(a)} != ${JSON.stringify(b)}`
}

async function main() {
  const a = args()
  const modes = (a.mode ?? "base,bonus,extremebonus").split(",")
  const limit = Number(a.limit ?? 2000)
  const skip = Number(a.skip ?? 0)
  const every = Number(a.every ?? 1)
  const summary: any = {}
  for (const mode of modes) {
    const files = modeFiles("v5", mode)
    const lut = readLut(files.lut)
    const res = { books: 0, identical: 0, events: 0, mismatches: [] as string[], criteria: {} as Record<string, number>, features: {} as Record<string, number> }
    let n = 0
    const only = a.criteria ? new Set(a.criteria.split(",")) : null
    const capOnly = a.caps === "true"
    for await (const book of readBooks(files.books, only || capOnly ? Infinity : skip + limit * every)) {
      if (only || capOnly) {
        // a filtered replay: every book of the given criteria (or every 10,000x book), up to --limit
        if ((only && !only.has(book.criteria)) || (capOnly && book.payoutMultiplier !== 1_000_000)) continue
        if (res.books >= limit) break
      } else if (n++ < skip || (n - skip - 1) % every) continue
      res.books++
      res.criteria[book.criteria] = (res.criteria[book.criteria] ?? 0) + 1
      const rs = (RESULT_SETS as any)[mode].find((x: any) => x.criteria === book.criteria)
      const events: any[] = []
      const records: any[] = []
      const ctx = { services: { data: { tagSymbolOccurrence() {} } }, state: { currentSpinType: "basegame" } }
      const round = new ReplayRound(
        { uniform: () => 0.5, symbols: SYMBOLS, strips: STRIPS, clusterCtx: ctx, events, record: (r) => records.push(r) },
        rs.conditions,
        book.criteria,
      ).load(book.events)
      let problem: string | null = null
      try {
        round.run()
        const mine = JSON.parse(JSON.stringify(events))
        if (mine.length !== book.events.length) {
          const types = (es: any[]) => es.map((e) => e.type).join(" ")
          let i = 0
          while (i < mine.length && i < book.events.length && mine[i].type === book.events[i].type) i++
          problem = `event count ${mine.length} != ${book.events.length}; first type difference at #${i}: ${mine[i]?.type} vs ${book.events[i]?.type}` + (a.verbose ? `\n mine ${types(mine)}\n book ${types(book.events)}` : "")
        } else {
          for (let i = 0; i < mine.length && !problem; i++) {
            const d = diff(mine[i], book.events[i])
            if (d) problem = `event #${i} (${book.events[i].type})${d}`
          }
        }
        if (!problem) {
          const { base, free } = round.bookWins
          const payout = Math.round(round.finalWin * 100)
          if (payout !== book.payoutMultiplier || payout !== lut.get(book.id)?.[1]) problem = `payout ${payout} != ${book.payoutMultiplier}`
          else if (base !== book.baseGameWins || free !== book.freeGameWins) problem = `base/free ${base}/${free} != ${book.baseGameWins}/${book.freeGameWins}`
          else if (!round.accepted) problem = `the port would not accept this outcome for criteria ${book.criteria}`
        }
      } catch (e) {
        problem = e instanceof Mismatch ? e.message : String((e as Error).stack ?? e)
      }
      res.events += book.events.length
      if (problem) {
        if (res.mismatches.length < 20) res.mismatches.push(`book ${book.id} (${book.criteria}): ${problem}`)
      } else {
        res.identical++
        const types = new Set(book.events.map((e: any) => e.type))
        for (const t of types) res.features[t as string] = (res.features[t as string] ?? 0) + 1
        for (const e of book.events) {
          if (e.type === "wallDrop") res.features[`wallDrop:${e.kind}`] = (res.features[`wallDrop:${e.kind}`] ?? 0) + 1
          if (e.type === "enterBonus") res.features[`bonus:${e.reason}`] = (res.features[`bonus:${e.reason}`] ?? 0) + 1
        }
      }
    }
    summary[mode] = res
    console.log(`${mode}: ${res.identical}/${res.books} books replayed identically (${res.events} events)`)
    for (const m of res.mismatches.slice(0, 8)) console.log("   " + m)
  }
  if (a.out) fs.writeFileSync(a.out, JSON.stringify(summary, null, 1))
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
