// One simulated round of Smukiez's City (math v5): a direct port of math-sdk/games/smukiez_tag_run (gamestate.py,
// game_executables.py, game_calculations.py, game_override.py, game_events.py) and of the Math SDK paths it runs
// through (src/calculations/board.py + tumble.py, src/events/events.py, src/wins/win_manager.py), so the books carry
// the same events, field for field, as the published v5 books.
//
// The round knows nothing about Slot Engine's simulation loop: randomness, symbols, reel strips, the cluster
// evaluator and the sinks for the wallet, tags and book events are handed in (src/gameFlow.ts wires them to the
// GameContext). That also lets tools/replay_v5.ts drive the same code with the decisions recorded in a v5 book.
import { ClusterWinType, GameSymbol, Reels } from "@slot-engine/core"
import {
  ANTICIPATION_TRIGGER,
  COVER_MULT_VALUES,
  EXTREME_DIRECT_BS,
  EXTREME_DIRECT_COUNT,
  EXTREME_DIRECT_SPINS,
  FREESPIN_TRIGGERS,
  GameType,
  LINE_DROP_PER,
  LINE_DROP_VALUES,
  MAX_TRIGGER,
  MAX_TUMBLES_PER_SPIN,
  MIN_TRIGGER,
  NUM_REELS,
  NUM_ROWS,
  SETTLE_TUMBLE_CAP,
  Table,
  WALL_LINE_CHANCE,
  WALL_LINE_LENGTHS,
  WINCAP,
  winLevel,
} from "./config"
import type { Conditions } from "./conditions"

/** Python's round(x, 2) for the values this game produces (multiples of 0.01 within float error). */
export const round2 = (x: number) => Math.round(x * 100) / 100
/** Python's int(round(x, 0)) for near-integers. */
const cents = (x: number) => Math.round(x * 100)
const mod = (a: number, n: number) => ((a % n) + n) % n

export type Cell = [reel: number, row: number]
export type Trigger = "standard" | "extreme" | null

export interface RoundIO {
  /** Uniform float in [0, 1). */
  uniform(): number
  /** The game's symbols by id (Slot Engine GameSymbols, the same objects the reel strips hold). */
  symbols: Map<string, GameSymbol>
  /** Reel strips by id, as Slot Engine parsed them from the CSVs. */
  strips: Record<string, Reels>
  /** Context handed to Slot Engine's ClusterWinType (it tags every paying cluster through it). */
  clusterCtx: any
  /** Book events are appended here (null = dry run: nothing is recorded). */
  events: any[] | null
  /** Python's record(): force-record keys -> Slot Engine tags. */
  record?(rec: Record<string, string | number>): void
  /** Wallet sinks: a paid board's win, and the end of a (free) spin. */
  addWin?(amount: number): void
  confirmSpin?(gametype: GameType): void
  /** Free spins awarded (Slot Engine's state.triggeredFreespins / freespin counters). */
  awardFreespins?(amount: number): void
  /** Spin type switch (Slot Engine's state.currentSpinType). */
  setGameType?(gametype: GameType): void
}

interface Win {
  symbol: string
  kind: number
  base: number
  win: number
  cells: Cell[]
  cellMults: number[]
  mult: number
}

const SYM_JSON: Record<string, any> = {}
/** json_ready_sym for this game's special_symbols {wild, scatter, scatter_extreme, booster, multiplier}. */
export function symJson(s: GameSymbol): any {
  if (s.id === "M") return { name: "M", booster: true, multiplier: s.properties.get("multiplier") }
  return (SYM_JSON[s.id] ??=
    s.id === "BS" ? { name: "BS", scatter: true } : s.id === "ES" ? { name: "ES", scatter_extreme: true } : { name: s.id })
}
const isScatter = (s: GameSymbol) => s.id === "BS" || s.id === "ES"

/** Python's Cluster.get_neighbours on the 7x7 board: left, right, up, down. */
function neighbours(r: number, c: number): Cell[] {
  const out: Cell[] = []
  if (r > 0) out.push([r - 1, c])
  if (r < NUM_REELS - 1) out.push([r + 1, c])
  if (c > 0) out.push([r, c - 1])
  if (c < NUM_ROWS - 1) out.push([r, c + 1])
  return out
}

/** A cluster's cells in the order the SDK's recursive Cluster.get_clusters visits them (root = first cell
 *  reel-major; every listed neighbour is claimed by the cell that listed it). */
function sdkClusterOrder(cells: Cell[]): Cell[] {
  const key = (r: number, c: number) => r * 8 + c
  const inCluster = new Set(cells.map(([r, c]) => key(r, c)))
  let root = cells[0]!
  for (const cell of cells) if (cell[0] * 8 + cell[1] < root[0] * 8 + root[1]) root = cell
  const out: Cell[] = [root]
  const listed = new Set([key(root[0], root[1])])
  const visit = (r: number, c: number) => {
    const fresh: Cell[] = []
    for (const [rr, cc] of neighbours(r, c)) {
      const k = key(rr, cc)
      if (!listed.has(k)) {
        listed.add(k)
        fresh.push([rr, cc])
      }
    }
    for (const [rr, cc] of fresh) {
      if (inCluster.has(key(rr, cc))) {
        out.push([rr, cc])
        visit(rr, cc)
      }
    }
  }
  visit(root[0], root[1])
  return out
}

export class SmukiezRound {
  // ---------------------------------------------------------------- inputs
  readonly io: RoundIO
  readonly conds: Conditions
  readonly criteria: string

  // ---------------------------------------------------------------- board state (SDK Board / Tumble)
  gametype: GameType = "basegame"
  board: GameSymbol[][] = []
  explode: boolean[][] = []
  top: GameSymbol[] = []
  bottom: GameSymbol[] = []
  reelPositions: number[] = []
  stripId = ""
  strip: Reels = []
  anticipation: number[] = []
  /** The multipliers the Multis and line drops leave: they belong to the CELL (reel-major, visible rows). */
  gridMults: number[][] = []
  wallEvent: { kind: "line" | "cover"; cells: Cell[] } | null = null

  // ---------------------------------------------------------------- win manager (SDK WinManager)
  spinWin = 0
  runningBetWin = 0
  basegameWins = 0
  freegameWins = 0
  finalWin = 0
  wincapTriggered = false
  winData: { totalWin: number; wins: Win[] } = { totalWin: 0, wins: [] }

  // ---------------------------------------------------------------- feature state
  totFs = 0
  fs = 0
  triggeredFreegame = false
  triggeredExtreme = false
  bonusType = ""
  /** Python's self.repeat: the outcome cannot satisfy the criteria (an unwanted trigger) - resimulate. */
  repeat = false
  /** check_repeat's verdict once the round is over. */
  accepted = false

  constructor(io: RoundIO, conds: Conditions, criteria: string) {
    this.io = io
    this.conds = conds
    this.criteria = criteria
  }

  // ================================================================ randomness (Python statistics/random)
  /** get_random_outcome: a value drawn from a {value: weight} table. */
  pick<T>(table: Table<T>): T {
    let total = 0
    for (const [, w] of table) total += w
    const roll = this.io.uniform() * total
    let cum = 0
    for (const [v, w] of table) {
      cum += w
      if (cum >= roll) return v
    }
    return table[table.length - 1]![0]
  }
  /** random.randrange(0, n) */
  randInt(n: number): number {
    return Math.min(n - 1, Math.floor(this.io.uniform() * n))
  }
  /** random.choice */
  choice<T>(arr: readonly T[]): T {
    return arr[this.randInt(arr.length)]!
  }
  /** random.sample(arr, k): k distinct items, uniformly, in selection order. */
  sample<T>(arr: readonly T[], k: number): T[] {
    const a = arr.slice()
    for (let i = 0; i < k; i++) {
      const j = i + this.randInt(a.length - i)
      ;[a[i], a[j]] = [a[j]!, a[i]!]
    }
    return a.slice(0, k)
  }

  // ================================================================ events
  emit(event: Record<string, any>) {
    const events = this.io.events
    if (!events) return
    events.push({ index: events.length, ...event })
  }
  gridSnapshot() {
    return this.gridMults.map((col) => col.slice())
  }

  // ================================================================ symbols
  /** create_symbol: a Multi rolls its value from the criteria's table for the current game type. */
  makeSymbol(name: string): GameSymbol {
    const def = this.io.symbols.get(name)
    if (!def) throw new Error(`unknown symbol ${name}`)
    if (name !== "M") return def
    const m = def.clone()
    m.properties.set("multiplier", this.rollBoosterMult())
    return m
  }
  rollBoosterMult(): number {
    return this.pick(this.conds.boosterMults[this.gametype]!)
  }
  countOnBoard(id: string): number {
    let n = 0
    for (const col of this.board) for (const s of col) if (s.id === id) n++
    return n
  }
  positionsOf(id: string): Cell[] {
    const out: Cell[] = []
    this.board.forEach((col, r) => col.forEach((s, c) => s.id === id && out.push([r, c])))
    return out
  }

  // ================================================================ board (SDK Board)
  /** Lay the board out from reel stops (create_board_reelstrips / force_board_from_reelstrips). */
  fillBoard(stripId: string, positions: number[]) {
    this.stripId = stripId
    this.strip = this.io.strips[stripId]!
    if (!this.strip) throw new Error(`unknown strip ${stripId}`)
    this.reelPositions = positions
    this.board = []
    this.explode = []
    this.top = []
    this.bottom = []
    let first = -1
    let scatters = 0
    for (let r = 0; r < NUM_REELS; r++) {
      const reel = this.strip[r]!
      const L = reel.length
      const p = positions[r]!
      this.top.push(this.makeSymbol(reel[mod(p - 1, L)]!.id))
      this.bottom.push(this.makeSymbol(reel[mod(p + NUM_ROWS, L)]!.id))
      const col: GameSymbol[] = []
      for (let row = 0; row < NUM_ROWS; row++) {
        const s = this.makeSymbol(reel[mod(p + row, L)]!.id)
        col.push(s)
        if (s.id === "BS") {
          scatters++
          if (scatters >= ANTICIPATION_TRIGGER && first === -1) first = r + 1
        }
      }
      this.board.push(col)
      this.explode.push(new Array(NUM_ROWS).fill(false))
    }
    this.anticipation = new Array(NUM_REELS).fill(0)
    if (first > -1 && first !== NUM_REELS) for (let r = first, n = 1; r < NUM_REELS; r++, n++) this.anticipation[r] = n
  }
  selectStrip(): string {
    return this.pick(this.conds.reelWeights[this.gametype]!)
  }
  createBoardReelstrips() {
    const id = this.selectStrip()
    const strip = this.io.strips[id]!
    this.fillBoard(id, strip.map((reel) => this.randInt(reel.length)))
  }
  /** force_board_from_reelstrips: each forced stop lands on a random row (the stop can come out negative,
   *  exactly as the SDK reports it in paddingPositions). */
  forceBoardFromReelstrips(stripId: string, forced: Map<number, number>) {
    const strip = this.io.strips[stripId]!
    const positions: number[] = new Array(NUM_REELS)
    for (const r of [...forced.keys()].sort((a, b) => a - b)) positions[r] = forced.get(r)! - this.randInt(NUM_ROWS)
    for (let r = 0; r < NUM_REELS; r++) if (positions[r] === undefined) positions[r] = this.randInt(strip[r]!.length)
    this.fillBoard(stripId, positions)
  }
  stopsOf(strip: Reels, id: string): number[][] {
    return strip.map((reel) => reel.flatMap((s, i) => (s.id === id ? [i] : [])))
  }
  /** force_special_board("scatter", n): exactly n Crew Leaders on the first board (SDK Board). */
  forceSpecialBoard(id: string, n: number) {
    for (;;) {
      const stripId = this.selectStrip()
      const strip = this.io.strips[stripId]!
      const stops = this.stopsOf(strip, id)
      const probs = stops.map((s, r) => s.length / strip[r]!.length)
      const forced = new Map<number, number>()
      let possible = probs.flatMap((p, r) => (p > 0 ? [r] : []))
      while (forced.size !== n && possible.length > 0) {
        const chosen = this.pick(possible.map((r) => [r, probs[r]!] as const))
        forced.set(chosen, this.choice(stops[chosen]!))
        probs[chosen] = 0
        possible = probs.flatMap((p, r) => (p > 0 ? [r] : []))
      }
      this.forceBoardFromReelstrips(stripId, forced)
      if (this.countOnBoard(id) === n) return
    }
  }
  /** force_smukiez_board: a base board with exactly nBs Crew Leaders and nEs Phantoms. */
  forceSmukiezBoard(nBs: number, nEs: number) {
    const stripId = this.selectStrip()
    const strip = this.io.strips[stripId]!
    const bsStops = this.stopsOf(strip, "BS")
    const esStops = this.stopsOf(strip, "ES")
    const esReels = esStops.flatMap((s, r) => (s.length ? [r] : []))
    if (esReels.length < nEs) throw new Error(`strip ${stripId} does not hold ES on ${nEs} reels`)
    for (let attempt = 0; attempt < 100; attempt++) {
      const forced = new Map<number, number>()
      for (const r of this.sample(esReels, nEs)) forced.set(r, this.choice(esStops[r]!))
      const bsReels = bsStops.flatMap((s, r) => (s.length && !forced.has(r) ? [r] : []))
      if (bsReels.length < nBs) continue
      for (const r of this.sample(bsReels, nBs)) forced.set(r, this.choice(bsStops[r]!))
      this.forceBoardFromReelstrips(stripId, forced)
      if (this.countOnBoard("BS") === nBs && this.countOnBoard("ES") === nEs) return
    }
    throw new Error(`could not force extreme board (${nBs} BS, ${nEs} ES) on ${stripId}`)
  }
  /** draw_board: the game's override (forced Extreme boards) over the SDK's (forced triggers / no triggers). */
  drawBoard() {
    const c = this.conds
    if (this.gametype === "basegame" && c.forceExtreme) {
      if (this.pick(c.extremeTriggerStyle!) === "direct") this.forceSmukiezBoard(this.pick(EXTREME_DIRECT_BS), EXTREME_DIRECT_COUNT)
      else this.forceSmukiezBoard(this.pick(c.scatterTriggers!), 1)
    } else if (this.gametype === "basegame" && c.forceFreegame) {
      this.forceSpecialBoard("BS", this.pick(c.scatterTriggers!))
    } else if (this.gametype === "basegame") {
      this.createBoardReelstrips()
      while (this.countOnBoard("BS") >= MIN_TRIGGER) this.createBoardReelstrips()
    } else {
      this.createBoardReelstrips()
    }
  }

  // ================================================================ wall events
  applyWallEvents() {
    if (this.gametype === "basegame" && this.conds.forceCover) this.coverBoard()
    else if (this.io.uniform() < WALL_LINE_CHANCE[this.gametype]) this.dropWallLine()
  }
  /** A straight run of 3 or 4 walls along a row or down a column, never over a scatter. */
  dropWallLine(): boolean {
    const n = this.pick(WALL_LINE_LENGTHS)
    const options: Cell[][] = []
    for (let r = 0; r < NUM_REELS; r++)
      for (let c = 0; c < NUM_ROWS; c++) {
        if (r + n <= NUM_REELS) options.push(Array.from({ length: n }, (_, i) => [r + i, c] as Cell))
        if (c + n <= NUM_ROWS) options.push(Array.from({ length: n }, (_, i) => [r, c + i] as Cell))
      }
    const ok = options.filter((o) => !o.some(([r, c]) => isScatter(this.board[r]![c]!)))
    if (!ok.length) return false
    const cells = this.choice(ok)
    for (const [r, c] of cells) this.board[r]![c] = this.makeSymbol("M")
    this.wallEvent = { kind: "line", cells }
    return true
  }
  /** Every cell but a scatter becomes a wall valued from cover_mult_values. */
  coverBoard() {
    const cells: Cell[] = []
    for (let r = 0; r < NUM_REELS; r++) for (let c = 0; c < NUM_ROWS; c++) if (!isScatter(this.board[r]![c]!)) cells.push([r, c])
    for (const [r, c] of cells) {
      const m = this.makeSymbol("M") // rolls the mode's own table first, as the SDK's create_symbol does
      m.properties.set("multiplier", this.pick(COVER_MULT_VALUES))
      this.board[r]![c] = m
    }
    this.wallEvent = { kind: "cover", cells }
    this.io.record?.({ kind: cells.length, symbol: "wallcover", gametype: this.gametype })
  }
  emitWallEvent() {
    if (!this.wallEvent) return
    const { kind, cells } = this.wallEvent
    this.emit({ type: "wallDrop", kind, positions: cells.map(([r, c]) => ({ reel: r, row: c + 1 })) })
    this.wallEvent = null
  }

  revealEvent() {
    const board = this.board.map((col, r) => [symJson(this.top[r]!), ...col.map(symJson), symJson(this.bottom[r]!)])
    this.emit({
      type: "reveal",
      board,
      paddingPositions: this.reelPositions.slice(),
      gameType: this.gametype,
      anticipation: this.anticipation.slice(),
    })
  }

  // ================================================================ wins (game_calculations.py)
  /** Every cluster of 5+ (Slot Engine's ClusterWinType + the symbols' pays), scaled by the SUM of the values
   *  on its cells; listed in the SDK's order (by symbol in first-seen order, cells in its visiting order). */
  evaluateWins() {
    const { winCombinations } = new ClusterWinType({ ctx: this.io.clusterCtx }).evaluateWins(this.board).getWins()
    const firstSeen = new Map<string, number>()
    this.board.forEach((col, r) => col.forEach((s, c) => firstSeen.has(s.id) || firstSeen.set(s.id, r * NUM_ROWS + c)))
    const ordered = winCombinations
      .map((wc, i) => ({ wc, i }))
      .sort((a, b) => firstSeen.get(a.wc.baseSymbol.id)! - firstSeen.get(b.wc.baseSymbol.id)! || a.i - b.i)
    const wins: Win[] = []
    let total = 0
    for (const { wc } of ordered) {
      const cells = sdkClusterOrder(wc.symbols.map((s) => [s.reelIndex, s.posIndex] as Cell))
      const cellMults = cells.map(([r, c]) => this.gridMults[r]![c]!)
      const mult = round2(cellMults.reduce((a, b) => a + b, 0))
      const base = wc.payout
      const win = mult > 0 ? round2(base * mult) : base
      wins.push({ symbol: wc.baseSymbol.id, kind: wc.kind, base, win, cells, cellMults, mult })
      total += win
    }
    this.winData = { totalWin: round2(total), wins }
  }
  winInfoEvent() {
    const wins = this.winData.wins.map((w) => {
      const meta: any = { clusterSize: w.kind, winWithoutMult: Math.trunc(Math.min(w.base * 100, WINCAP * 100)), multiplier: w.mult > 0 ? w.mult : 1 }
      if (w.mult > 0) meta.cellMults = w.cellMults.map(round2)
      return {
        symbol: w.symbol,
        kind: w.kind,
        win: cents(Math.min(w.win, WINCAP)),
        positions: w.cells.map(([r, c]) => ({ reel: r, row: c + 1 })),
        meta,
      }
    })
    this.emit({ type: "winInfo", totalWin: cents(Math.min(this.winData.totalWin, WINCAP)), wins })
  }
  updateSpinWin(amount: number) {
    this.spinWin += amount
    this.runningBetWin += amount
    this.io.addWin?.(amount)
  }
  evaluateWincap() {
    if (this.runningBetWin >= WINCAP && !this.wincapTriggered) {
      this.wincapTriggered = true
      this.emit({ type: "wincap", amount: cents(Math.min(this.runningBetWin, WINCAP)) })
    }
  }
  /** Pay this board's clusters, drop their line multipliers, flag their symbols. True if any symbol is flagged. */
  payAndMarkTumble(): boolean {
    if (this.winData.totalWin <= 0) return false
    this.updateSpinWin(this.winData.totalWin)
    this.winInfoEvent()
    this.emit({ type: "updateTumbleWin", amount: cents(Math.min(this.spinWin, WINCAP)) })
    this.evaluateWincap()
    if (!this.wincapTriggered) this.dropLineMults()
    let any = false
    for (const w of this.winData.wins)
      for (const [r, c] of w.cells) {
        this.explode[r]![c] = true
        any = true
      }
    return any
  }
  /** Line drops: chosen cells + values for one paid cluster (one per line_drop_per symbols it held). */
  lineDrops(cells: Cell[], _winIndex: number): Array<[number, number, number]> {
    const n = Math.max(1, Math.floor(cells.length / LINE_DROP_PER))
    return this.sample(cells, Math.min(n, cells.length)).map(([r, c]) => [r, c, this.pick(LINE_DROP_VALUES)])
  }
  dropLineMults() {
    const drops: Array<[number, number, number]> = []
    this.winData.wins.forEach((w, i) => {
      for (const [r, c, v] of this.lineDrops(w.cells, i)) {
        this.gridMults[r]![c] = round2(this.gridMults[r]![c]! + v)
        drops.push([r, c, v])
      }
    })
    if (drops.length)
      this.emit({
        type: "lineMults",
        drops: drops.map(([r, c, v]) => ({ reel: r, row: c + 1, mult: v })),
        gridMults: this.gridSnapshot(),
      })
  }

  // ================================================================ the Multi
  /** Blow out every Multi on the board: itself + its edge neighbours (scatters immune) take its value. */
  markBoosters(): boolean {
    const boosters: Cell[] = []
    this.board.forEach((col, r) => col.forEach((s, c) => s.id === "M" && boosters.push([r, c])))
    if (!boosters.length) return false
    const details = []
    for (const [r, c] of boosters) {
      const value: number = this.board[r]![c]!.properties.get("multiplier")
      const hit: Array<{ reel: number; row: number }> = []
      for (const [rr, cc] of [[r, c] as Cell, ...neighbours(r, c)]) {
        if ((rr !== r || cc !== c) && isScatter(this.board[rr]![cc]!)) continue
        this.gridMults[rr]![cc] = round2(this.gridMults[rr]![cc]! + value)
        this.explode[rr]![cc] = true
        hit.push({ reel: rr, row: cc + 1 })
      }
      details.push({ reel: r, row: c + 1, mult: value, cells: hit })
    }
    this.emit({ type: "booster", boosters: details, gridMults: this.gridSnapshot() })
    return true
  }
  /** A symbol entering the board in a tumble: k-th of the reel's refill (i = 1..k-1), or its new top padding. */
  tumbleSymbol(_reel: number, stripPos: number, _i: number, _k: number, _padding: boolean): GameSymbol {
    return this.makeSymbol(this.strip[_reel]![stripPos]!.id)
  }
  /** tumble_flagged: every flagged symbol leaves in ONE tumble (SDK Tumble.tumble_board, with padding). */
  tumbleFlagged() {
    const exploding: Array<{ reel: number; row: number }> = []
    this.explode.forEach((col, r) => col.forEach((f, c) => f && exploding.push({ reel: r, row: c + 1 })))
    const newSymbols: any[][] = []
    for (let r = 0; r < NUM_REELS; r++) {
      const reel = this.strip[r]!
      const L = reel.length
      const flags = this.explode[r]!
      const k = flags.reduce((n, f) => n + (f ? 1 : 0), 0)
      const fresh: GameSymbol[] = []
      const inserted: GameSymbol[] = []
      for (let i = 0; i < k; i++) {
        this.reelPositions[r] = mod(this.reelPositions[r]! - 1, L)
        let s: GameSymbol
        if (i === 0) s = this.top[r]!
        else {
          s = this.tumbleSymbol(r, this.reelPositions[r]!, i, k, false)
          fresh.unshift(s)
        }
        inserted.unshift(s)
      }
      this.board[r] = [...inserted, ...this.board[r]!.filter((_, c) => !flags[c])]
      this.explode[r] = new Array(NUM_ROWS).fill(false)
      if (k > 0) {
        this.top[r] = this.tumbleSymbol(r, mod(this.reelPositions[r]! - 1, L), k, k, true)
        fresh.unshift(this.top[r]!)
      }
      newSymbols.push(fresh.map(symJson))
    }
    this.emit({ type: "tumbleBoard", newSymbols, explodingSymbols: exploding })
  }
  resolveBoosters(): boolean {
    if (!this.markBoosters()) return false
    this.tumbleFlagged()
    return true
  }
  settleBoosters(tumbles: number, cap: number) {
    while (tumbles < cap && this.resolveBoosters()) tumbles++
    return tumbles
  }

  /** The cascade of one spin: clusters paid first, then the Multis, then one tumble; up to 12 board changes. */
  evaluateAndEmitWins() {
    let tumbles = 0
    for (;;) {
      this.evaluateWins()
      const exploded = this.payAndMarkTumble()
      if (this.wincapTriggered) break
      if (tumbles >= MAX_TUMBLES_PER_SPIN) break
      const boosted = this.markBoosters()
      if (!exploded && !boosted) break
      this.tumbleFlagged()
      tumbles++
    }
    if (!this.wincapTriggered) this.settleBoosters(tumbles, SETTLE_TUMBLE_CAP)
    // set_end_tumble_event
    if (this.spinWin > 0 && !this.wincapTriggered)
      this.emit({ type: "setWin", amount: Math.min(Math.round(this.spinWin * 100), WINCAP * 100), winLevel: winLevel(this.spinWin, "standard") })
    this.emit({ type: "setTotalWin", amount: cents(Math.min(this.runningBetWin, WINCAP)) })
  }
  updateGametypeWins() {
    if (this.gametype === "basegame") this.basegameWins += this.spinWin
    else this.freegameWins += this.spinWin
    this.io.confirmSpin?.(this.gametype)
  }

  /** One reveal: draw, wall event, reveal, cascade. */
  playSpin() {
    this.drawBoard()
    this.applyWallEvents()
    this.revealEvent()
    this.emitWallEvent()
    this.evaluateAndEmitWins()
    this.updateGametypeWins()
  }

  // ================================================================ bonus triggers
  checkTriggers(): Trigger {
    const nBs = this.countOnBoard("BS")
    const nEs = this.countOnBoard("ES")
    const bsKey = Math.min(nBs, MAX_TRIGGER)
    let trigger: Trigger = null
    if (nEs >= EXTREME_DIRECT_COUNT) {
      trigger = "extreme"
      this.bonusType = "extreme_direct"
      this.totFs = EXTREME_DIRECT_SPINS
    } else if (nBs >= MIN_TRIGGER && nEs >= 1) {
      trigger = "extreme"
      this.bonusType = "extreme_upgrade"
      this.totFs = FREESPIN_TRIGGERS[bsKey]!
    } else if (nBs >= MIN_TRIGGER) {
      trigger = "standard"
      this.bonusType = "standard"
      this.totFs = FREESPIN_TRIGGERS[bsKey]!
    }
    if (trigger === null) return null
    const c = this.conds
    if (trigger === "extreme" && !c.forceExtreme) {
      this.repeat = true
      return null
    }
    if (trigger === "standard" && (!c.forceFreegame || c.forceExtreme)) {
      this.repeat = true
      return null
    }
    this.triggeredExtreme = trigger === "extreme"
    if (nEs > 0) this.io.record?.({ kind: nEs, symbol: "scatter_extreme", gametype: this.gametype })
    if (nBs >= MIN_TRIGGER) this.io.record?.({ kind: nBs, symbol: "scatter", gametype: this.gametype })
    return trigger
  }
  freespinEntry(trigger: Trigger) {
    const bs = this.positionsOf("BS").map(([r, c]) => ({ reel: r, row: c + 1 }))
    this.emit({ type: "freeSpinTrigger", totalFs: this.totFs, positions: bs })
    if (trigger === "extreme") {
      const es = this.positionsOf("ES").map(([r, c]) => ({ reel: r, row: c + 1 }))
      this.emit({ type: "extremeTrigger", positions: es, reason: this.bonusType })
    }
    this.emit({ type: "enterBonus", reason: this.bonusType })
    this.io.awardFreespins?.(this.totFs)
    this.runFreespins()
  }
  /** The Standard / Extreme Bonus: exactly the spins the trigger awarded; multipliers persist across them. */
  runFreespins() {
    this.triggeredFreegame = true
    this.fs = 0
    this.gametype = "freegame"
    this.io.setGameType?.("freegame")
    this.spinWin = 0
    this.resetGrid()
    while (this.fs < this.totFs && !this.wincapTriggered) {
      this.emit({ type: "updateFreeSpin", amount: this.fs, total: this.totFs })
      this.fs++
      this.spinWin = 0
      this.playSpin()
    }
    this.emit({
      type: "freeSpinEnd",
      amount: cents(Math.min(this.freegameWins, WINCAP)),
      winLevel: winLevel(this.freegameWins, "endFeature"),
    })
  }
  resetGrid() {
    this.gridMults = Array.from({ length: NUM_REELS }, () => new Array(NUM_ROWS).fill(0))
  }

  // ================================================================ the round (gamestate.run_spin)
  run(): this {
    this.gametype = "basegame"
    this.io.setGameType?.("basegame")
    this.resetGrid()
    this.playSpin()
    const trigger = this.repeat ? null : this.checkTriggers()
    if (this.repeat) return this // an unwanted trigger: the criteria can no longer be met
    if (trigger !== null) this.freespinEntry(trigger)
    // evaluate_finalwin
    this.finalWin = round2(Math.min(this.runningBetWin, WINCAP))
    const base = round2(Math.min(this.basegameWins, WINCAP))
    const free = round2(Math.min(this.freegameWins, WINCAP))
    if (Math.min(round2(base + free), WINCAP) !== this.finalWin) throw new Error("Base + Free game payout mismatch!")
    this.emit({ type: "finalWin", amount: cents(Math.min(this.finalWin, WINCAP)) })
    this.accepted = this.checkRepeat()
    return this
  }
  /** game_override.check_repeat: does the outcome satisfy the criteria it was simulated for? */
  checkRepeat(): boolean {
    const c = this.conds
    if (this.repeat) return false
    if (c.winCriteria !== undefined && this.finalWin !== c.winCriteria) return false
    if (c.forceFreegame && !this.triggeredFreegame) return false
    if (c.forceExtreme && !this.triggeredExtreme) return false
    if (this.triggeredExtreme && !c.forceExtreme) return false
    if (this.runningBetWin === 0 && this.criteria !== "0") return false
    return true
  }
  /** The book's baseGameWins / freeGameWins (as the Math SDK writes them). */
  get bookWins() {
    return { base: round2(Math.min(this.basegameWins, WINCAP)), free: round2(Math.min(this.freegameWins, WINCAP)) }
  }
}
