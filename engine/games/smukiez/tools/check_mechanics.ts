// Mechanic checks on books, independent of the round engine: the board is rebuilt from the events alone (reveal,
// tumbleBoard) and every rule of the game is re-derived and checked against what the book says. Runs the same way
// on the published v5 books and on the native build, so both can be held to the same rules.
//
//   npx tsx games/smukiez/tools/check_mechanics.ts --which=v5|native --mode=base [--limit=20000] [--every=1]
import fs from "fs"
import path from "path"
import {
  BOOSTER_MULTS_BASE, BOOSTER_MULTS_EXTREME, BOOSTER_MULTS_FREE, BOOSTER_MULTS_RICH, CLUSTER_PAYS, COVER_MULT_VALUES,
  EXTREME_DIRECT_SPINS, FREESPIN_TRIGGERS, LINE_DROP_VALUES, MAX_TUMBLES_PER_SPIN, SETTLE_TUMBLE_CAP, STRIP_IDS, TIER_SIZES, WINCAP,
  winLevel,
} from "../src/config"
import { args, BUILD_DIR, GAME_DIR, modeFiles, readBooks, readSegmented } from "./lib"

const R = 7, C = 7
const STRIPS: Record<string, string[][]> = {}
for (const id of STRIP_IDS) {
  const rows = fs.readFileSync(path.join(GAME_DIR, "reels", `${id}.csv`), "utf8").split("\n").filter((l) => l.trim())
  STRIPS[id] = Array.from({ length: R }, (_, r) => rows.map((row) => row.split(",")[r]!.trim()))
}
const MULT_VALUES = new Set([...BOOSTER_MULTS_BASE, ...BOOSTER_MULTS_FREE, ...BOOSTER_MULTS_EXTREME, ...BOOSTER_MULTS_RICH].map(([v]) => v))
const COVER_VALUES = new Set(COVER_MULT_VALUES.map(([v]) => v))
const DROP_VALUES = new Set(LINE_DROP_VALUES.map(([v]) => v))
const mod = (a: number, n: number) => ((a % n) + n) % n
const r2 = (x: number) => Math.round(x * 100) / 100
const pay = (sym: string, size: number) => {
  const p = CLUSTER_PAYS[sym]
  if (!p || size < 5) return 0
  let t = 0
  TIER_SIZES.forEach((s, i) => size >= s && (t = i))
  return p[t]!
}
const isScatter = (n: string) => n === "BS" || n === "ES"
type Sym = { name: string; multiplier?: number }

/** 4-connected same-name components of size >= 5 of paying symbols, as sets of r*8+c. */
function clusters(board: Sym[][]) {
  const seen = new Set<number>()
  const out: Array<{ sym: string; cells: number[] }> = []
  for (let r = 0; r < R; r++)
    for (let c = 0; c < C; c++) {
      if (seen.has(r * 8 + c)) continue
      const sym = board[r]![c]!.name
      const cells: number[] = []
      const stack = [[r, c]]
      seen.add(r * 8 + c)
      while (stack.length) {
        const [x, y] = stack.pop()!
        cells.push(x! * 8 + y!)
        for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1]]) {
          const nx = x! + dx!, ny = y! + dy!
          if (nx < 0 || ny < 0 || nx >= R || ny >= C || seen.has(nx * 8 + ny) || board[nx]![ny]!.name !== sym) continue
          seen.add(nx * 8 + ny)
          stack.push([nx, ny])
        }
      }
      if (cells.length >= 5 && pay(sym, cells.length) > 0) out.push({ sym, cells: cells.sort((a, b) => a - b) })
    }
  return out
}

async function main() {
  const a = args()
  const which = (a.which ?? "native") as "v5" | "native"
  const modes = (a.mode ?? "base,bonus,extremebonus").split(",")
  const limit = Number(a.limit ?? 20000)
  const every = Number(a.every ?? 1)
  const report: any = {}
  for (const mode of modes) {
    const files = modeFiles(which, mode, a.build ?? BUILD_DIR)
    const seg = files.segmented && fs.existsSync(files.segmented) ? readSegmented(files.segmented) : undefined
    const ok: Record<string, number> = {}
    const bad: Record<string, string[]> = {}
    const strips: Record<string, number> = {}
    const pass = (k: string) => (ok[k] = (ok[k] ?? 0) + 1)
    const fail = (k: string, msg: string) => {
      ;(bad[k] ??= []).length < 5 && bad[k]!.push(msg)
      ok[k] ??= 0
      ;(bad[k] as any).count = ((bad[k] as any).count ?? 0) + 1
    }
    const check = (k: string, cond: boolean, msg: () => string) => (cond ? pass(k) : fail(k, msg()))
    let books = 0, n = 0
    for await (const book of readBooks(files.books, limit * every)) {
      if (n++ % every) continue
      books++
      const crit = book.criteria ?? seg?.get(book.id)?.criteria ?? "?"
      const id = `${mode}#${book.id}(${crit})`
      let board: Sym[][] = [], top: Sym[] = [], pos: number[] = [], strip = ""
      let grid = Array.from({ length: R }, () => new Array(C).fill(0))
      let gametype = "basegame"
      let tumbles = 0, payBoards = 0, spinWin = 0, total = 0, freeWins = 0, baseWins = 0
      let flagged = new Set<number>(), lastWins: any[] = [], wincap = false, pendingWall: any = null, lastReveal: any = null
      let trigger: any = null, extreme: any = null, fsSeen = 0, afterWincap: string[] = []
      const ev: any[] = book.events
      const closeSpin = () => {
        if (!lastReveal) return
        // Multis must not be left on the board (unless the settle budget or the wincap stopped them)
        const left = board.flat().filter((s) => s.name === "M").length
        check("multis settle before the spin ends", left === 0 || wincap || tumbles >= SETTLE_TUMBLE_CAP, () => `${id}: ${left} Multis left after ${tumbles} tumbles`)
        check("tumble budget (<= 12 paid tumbles, <= 16 board changes)", tumbles <= SETTLE_TUMBLE_CAP && payBoards <= MAX_TUMBLES_PER_SPIN + 1, () => `${id}: ${tumbles} tumbles, ${payBoards} paid boards`)
        if (gametype === "basegame") baseWins += spinWin
        else freeWins += spinWin
      }
      const verifyStrip = (wallCells: Set<number>) => {
        const rev = lastReveal
        const fits = STRIP_IDS.filter((sid) =>
          rev.board.every((col: Sym[], r: number) => {
            const reel = STRIPS[sid]![r]!, L = reel.length, p = rev.paddingPositions[r]
            return col.every((s, row) => (row >= 1 && row <= C && wallCells.has(r * 8 + row - 1)) || reel[mod(p - 1 + row, L)] === s.name)
          }),
        )
        check("reveal = strip window at paddingPositions (incl. padding)", fits.length > 0, () => `${id}: no strip fits the reveal`)
        strip = fits[0] ?? ""
        const key = `${crit}/${gametype}:${fits.join("|")}`
        strips[key] = (strips[key] ?? 0) + 1
        pos = rev.paddingPositions.map((p: number, r: number) => mod(p, STRIPS[strip]?.[r]?.length ?? 100))
      }
      for (let i = 0; i < ev.length; i++) {
        const e = ev[i]
        if (pendingWall !== null && e.type !== "wallDrop") {
          verifyStrip(new Set())
          pendingWall = null
        }
        if (wincap) afterWincap.push(e.type)
        check("event index = position (0-based)", e.index === i, () => `${id}: event ${i} has index ${e.index}`)
        switch (e.type) {
          case "reveal": {
            closeSpin()
            lastReveal = e
            gametype = e.gameType
            check("reveal shape: 7 reels x (1+7+1) with padding", e.board.length === R && e.board.every((c: any[]) => c.length === C + 2), () => `${id}: bad board shape`)
            board = e.board.map((col: Sym[]) => col.slice(1, C + 1).map((s) => ({ ...s })))
            top = e.board.map((col: Sym[]) => ({ ...col[0]! }))
            for (const col of e.board)
              for (const s of col)
                if (s.name === "M") check("Multi values in the value tables", (s as any).booster === true && (MULT_VALUES.has(s.multiplier!) || COVER_VALUES.has(s.multiplier!)), () => `${id}: Multi ${JSON.stringify(s)}`)
            if (gametype === "basegame") grid = Array.from({ length: R }, () => new Array(C).fill(0))
            // anticipation: the reels after the one where the 2nd Crew Leader lands, counting 1, 2, ...
            let count = 0, first = -1
            board.forEach((col, r) => col.forEach((s) => s.name === "BS" && ++count >= 2 && first === -1 && (first = r + 1)))
            const want = Array.from({ length: R }, (_, r) => (first > -1 && first < R && r >= first ? r - first + 1 : 0))
            check("anticipation", JSON.stringify(want) === JSON.stringify(e.anticipation), () => `${id}: anticipation ${e.anticipation} vs ${want}`)
            tumbles = payBoards = spinWin = 0
            flagged = new Set()
            pendingWall = true
            break
          }
          case "wallDrop": {
            const cells = e.positions.map((p: any) => p.reel * 8 + p.row - 1)
            verifyStrip(new Set(cells))
            pendingWall = null
            const allM = e.positions.every((p: any) => board[p.reel]![p.row - 1]!.name === "M")
            check("wall cells are Multis on the revealed board", allM, () => `${id}: wall cell not a Multi`)
            if (e.kind === "line") {
              const ps = e.positions
              const sameReel = ps.every((p: any) => p.reel === ps[0].reel), sameRow = ps.every((p: any) => p.row === ps[0].row)
              const steps = ps.every((p: any, j: number) => (sameReel ? p.row === ps[0].row + j : p.reel === ps[0].reel + j))
              check("wall line: 3-4 walls in a straight run", (ps.length === 3 || ps.length === 4) && (sameReel || sameRow) && steps, () => `${id}: line ${JSON.stringify(ps)}`)
            } else {
              const want = []
              for (let r = 0; r < R; r++) for (let c = 0; c < C; c++) if (!isScatter(board[r]![c]!.name)) want.push(r * 8 + c)
              check("full wall covers every non-scatter cell, base game only", JSON.stringify(want) === JSON.stringify(cells) && gametype === "basegame", () => `${id}: cover cells`)
              check("full wall values from cover_mult_values", e.positions.every((p: any) => COVER_VALUES.has(board[p.reel]![p.row - 1]!.multiplier!)), () => `${id}: cover value`)
            }
            break
          }
          case "winInfo": {
            payBoards++
            check("no pays after the 12th tumble", tumbles <= MAX_TUMBLES_PER_SPIN, () => `${id}: pay at tumble ${tumbles}`)
            const want = clusters(board)
            const got = e.wins.map((w: any) => ({ ...w, cells: w.positions.map((p: any) => p.reel * 8 + p.row - 1).sort((x: number, y: number) => x - y) }))
            const key = (x: { sym?: string; symbol?: string; cells: number[] }) => `${x.sym ?? x.symbol}:${x.cells.join(".")}`
            check("every cluster of 5+ on the board is paid, nothing else", JSON.stringify(want.map(key).sort()) === JSON.stringify(got.map(key).sort()), () => `${id}: clusters ${want.map(key)} vs ${got.map(key)}`)
            let sum = 0
            for (const w of got) {
              const base = pay(w.symbol, w.cells.length)
              const cm = w.positions.map((p: any) => grid[p.reel]![p.row - 1]!)
              const mult = r2(cm.reduce((s: number, v: number) => s + v, 0))
              const win = mult > 0 ? r2(base * mult) : base
              check("cluster multiplier = SUM of its cells' values", (mult > 0 ? w.meta.multiplier === mult && JSON.stringify(w.meta.cellMults) === JSON.stringify(cm) : w.meta.multiplier === 1 && !w.meta.cellMults), () => `${id}: mult ${w.meta.multiplier} vs ${mult}`)
              check("cluster pay = paytable(size tier) x multiplier", w.kind === w.cells.length && w.meta.clusterSize === w.kind && w.win === Math.round(Math.min(win, WINCAP) * 100) && w.meta.winWithoutMult === Math.trunc(base * 100), () => `${id}: ${w.symbol}x${w.kind} win ${w.win} vs ${win}`)
              sum += win
            }
            check("winInfo totalWin = sum of the clusters", e.totalWin === Math.round(Math.min(r2(sum), WINCAP) * 100), () => `${id}: total ${e.totalWin} vs ${sum}`)
            spinWin += r2(sum)
            total += r2(sum)
            lastWins = got
            for (const w of got) for (const c of w.cells) flagged.add(c)
            const next = ev[i + 2]?.type
            if (total < WINCAP) check("every paid board drops line multipliers", next === "lineMults", () => `${id}: ${next} after winInfo`)
            break
          }
          case "updateTumbleWin":
            check("updateTumbleWin = the spin's win so far", e.amount === Math.round(Math.min(spinWin, WINCAP) * 100), () => `${id}: ${e.amount} vs ${spinWin}`)
            break
          case "lineMults": {
            const want = lastWins.reduce((s, w) => s + Math.max(1, Math.floor(w.cells.length / 5)), 0)
            check("line drops: one per 5 symbols of each paid cluster, on its own cells", e.drops.length === want && lastWins.every((w) => {
              const mine = e.drops.filter((d: any) => w.cells.includes(d.reel * 8 + d.row - 1))
              return mine.length === Math.max(1, Math.floor(w.cells.length / 5)) && new Set(mine.map((d: any) => d.reel * 8 + d.row)).size === mine.length
            }), () => `${id}: ${e.drops.length} drops, want ${want}`)
            for (const d of e.drops) {
              check("line drop values x1.25 / x1.5 / x2", DROP_VALUES.has(d.mult), () => `${id}: drop ${d.mult}`)
              grid[d.reel]![d.row - 1] = r2(grid[d.reel]![d.row - 1]! + d.mult)
            }
            check("lineMults gridMults = grid + drops", JSON.stringify(e.gridMults) === JSON.stringify(grid), () => `${id}: grid after drops`)
            break
          }
          case "booster": {
            const multis: Array<[number, number, number]> = []
            board.forEach((col, r) => col.forEach((s, c) => s.name === "M" && multis.push([r, c, s.multiplier!])))
            check("every Multi on the board blows out, in board order", JSON.stringify(multis.map(([r, c, v]) => [r, c + 1, v])) === JSON.stringify(e.boosters.map((b: any) => [b.reel, b.row, b.mult])), () => `${id}: boosters ${JSON.stringify(e.boosters.map((b: any) => [b.reel, b.row, b.mult]))} vs ${JSON.stringify(multis)}`)
            for (const b of e.boosters) {
              const r = b.reel, c = b.row - 1
              const want = [[r, c], [r - 1, c], [r + 1, c], [r, c - 1], [r, c + 1]].filter(([x, y], j) => x! >= 0 && y! >= 0 && x! < R && y! < C && (j === 0 || !isScatter(board[x!]![y!]!.name)))
              check("blast = the Multi + its edge neighbours, scatters immune", JSON.stringify(want.map(([x, y]) => ({ reel: x, row: y! + 1 }))) === JSON.stringify(b.cells), () => `${id}: cells ${JSON.stringify(b.cells)}`)
              for (const [x, y] of want) {
                grid[x!]![y!] = r2(grid[x!]![y!]! + b.mult)
                flagged.add(x! * 8 + y!)
              }
            }
            check("booster gridMults = grid + every blast's value (values add)", JSON.stringify(e.gridMults) === JSON.stringify(grid), () => `${id}: grid after boosters`)
            break
          }
          case "tumbleBoard": {
            tumbles++
            const want = [...flagged].sort((x, y) => x - y).map((k) => ({ reel: k >> 3, row: (k & 7) + 1 }))
            check("one tumble removes the paid clusters + the blast cells together", JSON.stringify(want) === JSON.stringify(e.explodingSymbols), () => `${id}: exploding ${JSON.stringify(e.explodingSymbols)} vs ${JSON.stringify(want)}`)
            for (let r = 0; r < R; r++) {
              const gone = [...flagged].filter((k) => k >> 3 === r).map((k) => k & 7)
              const k = gone.length
              const listed: Sym[] = e.newSymbols[r] ?? []
              check("newSymbols: one per removed cell (new top padding first)", listed.length === k, () => `${id}: reel ${r} lists ${listed.length} for ${k}`)
              if (strip && k > 0) {
                const reel = STRIPS[strip]![r]!, L = reel.length
                const names = Array.from({ length: k }, (_, j) => reel[mod(pos[r]! - k - 1 + j, L)])
                check("refills come off the strip above the stop (padding slides in)", JSON.stringify(names) === JSON.stringify(listed.map((s) => s.name)), () => `${id}: reel ${r} refill ${listed.map((s) => s.name)} vs ${names}`)
                pos[r] = mod(pos[r]! - k, L)
              }
              const survivors = board[r]!.filter((_, c) => !gone.includes(c))
              if (k > 0) {
                board[r] = [...listed.slice(1).map((s) => ({ ...s })), top[r]!, ...survivors]
                top[r] = { ...listed[0]! }
              }
              for (const s of listed) if (s.name === "M") check("Multi values in the value tables", MULT_VALUES.has(s.multiplier!), () => `${id}: refill Multi ${s.multiplier}`)
            }
            flagged = new Set()
            break
          }
          case "setWin":
            check("setWin = the spin's win, winLevel", e.amount === Math.min(Math.round(spinWin * 100), WINCAP * 100) && e.winLevel === winLevel(spinWin, "standard"), () => `${id}: setWin ${e.amount}/${e.winLevel} vs ${spinWin}`)
            break
          case "setTotalWin":
            check("setTotalWin = the round's win so far", e.amount === Math.round(Math.min(total, WINCAP) * 100), () => `${id}: total ${e.amount} vs ${total}`)
            break
          case "wincap":
            wincap = true
            check("wincap fires at 10,000x", total >= WINCAP && e.amount === WINCAP * 100, () => `${id}: wincap at ${total}`)
            break
          case "freeSpinTrigger": {
            closeSpin()
            lastReveal = null
            const bs: any[] = [], es: any[] = []
            board.forEach((col, r) => col.forEach((s, c) => (s.name === "BS" ? bs : s.name === "ES" ? es : []).push({ reel: r, row: c + 1 })))
            const fs = es.length >= 2 ? EXTREME_DIRECT_SPINS : FREESPIN_TRIGGERS[Math.min(bs.length, 5)]
            check("trigger: 3/4/5+ Crew Leaders -> 10/12/15 spins, 2+ Phantoms -> 17", gametype === "basegame" && e.totalFs === fs && JSON.stringify(e.positions) === JSON.stringify(bs) && (bs.length >= 3 || es.length >= 2), () => `${id}: totalFs ${e.totalFs} with ${bs.length} BS / ${es.length} ES`)
            trigger = { bs: bs.length, es, totalFs: e.totalFs }
            break
          }
          case "extremeTrigger": {
            const reason = trigger.es.length >= 2 ? "extreme_direct" : trigger.es.length === 1 && trigger.bs >= 3 ? "extreme_upgrade" : "?"
            check("extreme: 2 Phantoms = direct, 1 + a standard trigger = upgrade", e.reason === reason && JSON.stringify(e.positions) === JSON.stringify(trigger.es), () => `${id}: ${e.reason} with ${trigger.es.length} ES / ${trigger.bs} BS`)
            extreme = e.reason
            break
          }
          case "enterBonus":
            check("enterBonus reason", e.reason === (extreme ?? (trigger?.es.length ? "?" : "standard")), () => `${id}: enterBonus ${e.reason}`)
            grid = Array.from({ length: R }, () => new Array(C).fill(0))
            break
          case "updateFreeSpin":
            check("free spins count 0..totalFs-1", e.amount === fsSeen && e.total === trigger?.totalFs, () => `${id}: updateFreeSpin ${e.amount}/${e.total}`)
            fsSeen++
            break
          case "freeSpinEnd":
            closeSpin()
            lastReveal = null
            check("bonus plays exactly the awarded spins (or stops at the wincap)", fsSeen === trigger?.totalFs || wincap, () => `${id}: ${fsSeen} of ${trigger?.totalFs}`)
            check("freeSpinEnd = the bonus win", e.amount === Math.round(Math.min(freeWins, WINCAP) * 100) && e.winLevel === winLevel(freeWins, "endFeature"), () => `${id}: freeSpinEnd ${e.amount} vs ${freeWins}`)
            break
          case "finalWin":
            closeSpin()
            lastReveal = null
            check("finalWin = payout = min(total, 10,000x)", e.amount === book.payoutMultiplier && e.amount === Math.round(Math.min(r2(total), WINCAP) * 100), () => `${id}: final ${e.amount} vs ${book.payoutMultiplier} / ${total}`)
            break
        }
      }
      if (wincap) check("after the wincap only setTotalWin / freeSpinEnd / finalWin", afterWincap.every((t) => ["setTotalWin", "freeSpinEnd", "finalWin"].includes(t)), () => `${id}: after wincap ${afterWincap}`)
      check("the round ends on finalWin", ev[ev.length - 1]?.type === "finalWin", () => `${id}: ends on ${ev[ev.length - 1]?.type}`)
    }
    const failed = Object.fromEntries(Object.entries(bad).map(([k, v]) => [k, { count: (v as any).count, examples: v }]))
    report[mode] = { books, checks: Object.fromEntries(Object.keys(ok).sort().map((k) => [k, { passed: ok[k], failed: (bad[k] as any)?.count ?? 0 }])), failed, strips }
    const nFail = Object.values(failed).reduce((s: number, f: any) => s + f.count, 0)
    console.log(`${which} ${mode}: ${books} books, ${Object.keys(ok).length} rules, ${Object.values(ok).reduce((s, x) => s + x, 0)} checks passed, ${nFail} failed`)
    for (const [k, f] of Object.entries(failed)) console.log(`  FAIL ${k}: ${(f as any).count}x, e.g. ${(f as any).examples[0]}`)
  }
  const out = a.out ?? path.join(GAME_DIR, "checks", `mechanics_${which}.json`)
  fs.writeFileSync(out, JSON.stringify(report, null, 1))
  console.log("->", out)
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
