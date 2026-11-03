// Side-by-side tables (markdown) from the stats files of tools/book_stats.ts: v5 vs the native build (and the
// tilt-only variant if checks/stats_native_tail_<mode>.json exists), plus the event-schema parity check.
//   npx tsx games/smukiez/tools/compare.ts  -> checks/parity_report.md
import fs from "fs"
import path from "path"
import { GAME_DIR, MODES } from "./lib"

const C = path.join(GAME_DIR, "checks")
const load = (f: string) => (fs.existsSync(path.join(C, f)) ? JSON.parse(fs.readFileSync(path.join(C, f), "utf8")) : null)
const fmt = (x: number, d = 4) => (Math.abs(x) >= 1000 ? Math.round(x).toLocaleString("en-US") : (+x.toPrecision(d)).toString())
const one = (p: number) => (p > 0 ? "1 in " + fmt(1 / p, 4) : "-")
const out: string[] = []
const table = (head: string[], rows: string[][]) => {
  out.push("| " + head.join(" | ") + " |", "|" + head.map(() => "---").join("|") + "|")
  for (const r of rows) out.push("| " + r.join(" | ") + " |")
  out.push("")
}

out.push("# Smukiez native port vs v5 - parity tables", "", `Generated ${new Date().toISOString()} by tools/compare.ts.`, "")
out.push("## Optimised statistics (weighted by the published lookup tables)", "")
for (const m of MODES) {
  const v = load(`stats_v5_${m}.json`), n = load(`stats_native_${m}.json`), t = load(`stats_native_tail_${m}.json`)
  if (!v || !n) continue
  out.push(`### ${m}`, "")
  const rows: Array<[string, (w: any) => string]> = [
    ["RTP", (w) => w.rtp.toFixed(6)],
    ["hit rate (non-zero)", (w) => "1 in " + w.hitRate.toFixed(3)],
    ["P(win < cost)", (w) => (w.pLessBet * 100).toFixed(2) + "%"],
    ["volatility (std, x bet)", (w) => fmt(w.std)],
    ["max win (10,000x) frequency", (w) => one(w.maxWinRate)],
    ["free-spin trigger frequency", (w) => one(w.triggerRate)],
    ["  standard / direct / upgrade", (w) => [w.standardRate, w.directRate, w.upgradeRate].map(one).join(" / ")],
    ["average bonus win (freeSpinEnd)", (w) => fmt(w.avgBonusWin) + "x"],
    ["average payout of a bonus round", (w) => fmt(w.avgPayoutGivenTrigger) + "x"],
    ["RTP from free spins / base", (w) => w.bonusRtpShare.toFixed(4) + " / " + w.baseRtpShare.toFixed(4)],
    ["full-wall cover frequency", (w) => one(w.coverRate)],
    ["base 1000x-wall rounds", (w) => one(w.wall1000Rate)],
    ["base wall-line rounds", (w) => one(w.baseWallLineRate)],
  ]
  table(["statistic", "v5 (published)", "native (default, v5 shape)", ...(t ? ["native (tilt only)"] : [])], rows.map(([k, f]) => [k, f(v.weighted), f(n.weighted), ...(t ? [f(t.weighted)] : [])]))
}

out.push("## Raw simulated pools per criteria (unweighted: the math itself, before any optimiser)", "")
const prow: string[][] = []
for (const m of MODES) {
  const v = load(`stats_v5_${m}.json`), n = load(`stats_native_${m}.json`)
  if (!v || !n) continue
  for (const c of Object.keys(v.pool)) {
    const a = v.pool[c], b = n.pool[c]
    if (!b) continue
    const se = Math.sqrt((a.std ** 2) / a.n + (b.std ** 2) / b.n)
    prow.push([m, c, `${a.n} / ${b.n}`, `${fmt(a.mean)} / ${fmt(b.mean)}`, se > 0 ? ((b.mean - a.mean) / se).toFixed(2) : "-", `${fmt(a.std)} / ${fmt(b.std)}`, `${fmt(a.max)} / ${fmt(b.max)}`, `${a.cap} / ${b.cap}`])
  }
}
table(["mode", "criteria", "books v5 / native", "mean payout v5 / native", "z (diff / SE)", "std v5 / native", "max", "10,000x books"], prow)

out.push("## Mechanic distributions (unweighted, per criteria / game type)", "")
const mrow: string[][] = []
const share = (c: Record<string, number>, k: string) => {
  const t = Object.values(c ?? {}).reduce((s, x) => s + x, 0)
  return t ? ((c[k] ?? 0) / t * 100).toFixed(1) + "%" : "-"
}
const mean = (c: Record<string, number>) => {
  let s = 0, t = 0
  for (const [k, n] of Object.entries(c ?? {})) (s += Number(k) * n), (t += n)
  return t ? s / t : 0
}
for (const m of MODES) {
  const v = load(`stats_v5_${m}.json`), n = load(`stats_native_${m}.json`)
  if (!v || !n) continue
  for (const key of Object.keys(v.mech)) {
    const a = v.mech[key], b = n.mech[key]
    if (!b || a.reveals < 100) continue
    const lines = (x: any) => Object.values(x.wallLine as Record<string, number>).reduce((s, y) => s + y, 0) / x.reveals
    const pairs: Array<[string, (x: any) => string]> = [
      ["reveals", (x) => String(x.reveals)],
      ["Multis per board", (x) => (x.multsOnBoard / x.reveals).toFixed(3)],
      ["mean Multi value (blow-outs)", (x) => mean(x.boosterValues).toFixed(2)],
      ["Multi 1000x share", (x) => share(x.boosterValues, "1000")],
      ["wall line per reveal", (x) => lines(x).toFixed(4)],
      ["wall line 3 / 4", (x) => `${share(x.wallLine, "3")} / ${share(x.wallLine, "4")}`],
      ["line drop 1.25/1.5/2", (x) => ["1.25", "1.5", "2"].map((k) => share(x.lineDropValues, k)).join(" / ")],
      ["tumbles per spin", (x) => mean(x.tumblesPerSpin).toFixed(3)],
      ["spins with a win", (x) => (x.spinsWithWin / x.spins * 100).toFixed(2) + "%"],
      ["5-clusters share", (x) => share(x.clusterKinds, "5")],
    ]
    for (const [k, f] of pairs) mrow.push([`${m} ${key}`, k, f(a), f(b)])
  }
}
table(["mode criteria/gametype", "measure", "v5", "native"], mrow)

out.push("## Triggers (unweighted counts in the pools: reason | spins | Crew Leaders | Phantoms)", "")
for (const m of MODES) {
  const v = load(`stats_v5_${m}.json`), n = load(`stats_native_${m}.json`)
  if (!v || !n) continue
  const keys = [...new Set([...Object.keys(v.triggers), ...Object.keys(n.triggers)])].sort()
  table([`${m} trigger`, "v5", "native"], keys.map((k) => [k, String(v.triggers[k] ?? 0), String(n.triggers[k] ?? 0)]))
}

out.push("## Event-schema parity", "", "Per event type, every field path with its key order(s) and value types (int = integral number, frac = fractional), over all books of both builds.", "")
const srow: string[][] = []
let schemaDiffs = 0
const allV: any = {}, allN: any = {}
for (const m of MODES) {
  const v = load(`stats_v5_${m}.json`), n = load(`stats_native_${m}.json`)
  for (const [src, dst] of [[v, allV], [n, allN]]) {
    if (!src) continue
    for (const [t, paths] of Object.entries(src.schema as Record<string, any>))
      for (const [p, s] of Object.entries(paths as Record<string, any>)) {
        const d = ((dst[t] ??= {})[p] ??= { types: new Set(), keys: new Set() })
        s.types.forEach((x: string) => d.types.add(x))
        s.keys.forEach((x: string) => d.keys.add(x))
      }
  }
}
for (const t of [...new Set([...Object.keys(allV), ...Object.keys(allN)])].sort()) {
  const pv = allV[t] ?? {}, pn = allN[t] ?? {}
  const paths = [...new Set([...Object.keys(pv), ...Object.keys(pn)])]
  const diffs: string[] = []
  for (const p of paths) {
    const a = pv[p], b = pn[p]
    if (!a || !b) diffs.push(`${p || "(event)"} only in ${a ? "v5" : "native"}`)
    else {
      const ta = [...a.types].sort().join("|"), tb = [...b.types].sort().join("|")
      const ka = [...a.keys].sort().join(" ; "), kb = [...b.keys].sort().join(" ; ")
      if (ta !== tb) diffs.push(`${p}: types ${ta} vs ${tb}`)
      if (ka !== kb) diffs.push(`${p}: key orders {${ka}} vs {${kb}}`)
    }
  }
  schemaDiffs += diffs.length
  srow.push([t, String(paths.length), [...(pv[""]?.keys ?? [])].join(" ; "), diffs.length ? diffs.join("<br>") : "identical"])
}
table(["event type", "field paths", "top-level keys (v5)", "differences (v5 vs native)"], srow)
out.push(`Schema differences: ${schemaDiffs}.`, "")

fs.writeFileSync(path.join(C, "parity_report.md"), out.join("\n"))
console.log(out.join("\n"))
