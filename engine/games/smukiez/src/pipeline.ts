// The run.py pipeline on Slot Engine: simulate -> (base_book_scaling from the pool) -> optimise -> finish_luts ->
// analyse. Main thread only; started by index.ts when run with --slot-engine-run.
import os from "os"
import type { SlotGame } from "@slot-engine/core"
import { baseBookScaling, optimizationConfig } from "./optimization"
import { finishLuts } from "./finish"
import { fenceCounts, loadProfile, shapeRules } from "./shape"

function flags() {
  const out: Record<string, string> = {}
  for (const a of process.argv.slice(2)) {
    const m = /^--([^=]+)(?:=(.*))?$/.exec(a)
    if (m) out[m[1]!] = m[2] ?? "true"
  }
  return out
}

export async function runPipeline(game: SlotGame, defaults = { base: 100_000, bonus: 20_000, extremebonus: 20_000 }) {
  const f = flags()
  const modes = (f.modes ?? "base,bonus,extremebonus").split(",")
  const sims: Record<string, number> = {}
  for (const m of modes) sims[m] = Number(f[m] ?? f[m === "extremebonus" ? "extreme" : m] ?? defaults[m as keyof typeof defaults])
  const threads = Number(f.threads ?? Math.max(2, Math.min(6, os.cpus().length - 2)))
  const t0 = Date.now()

  if (!f["no-sim"]) {
    console.log(`Simulating ${JSON.stringify(sims)} on ${threads} workers`)
    game.configureSimulation({ simRunsAmount: sims, concurrency: threads, maxPendingSims: 25, maxDiskBuffer: 150 })
    await game.runTasks({ _internal_ignore_args: true, doSimulation: true })
    console.log(`simulation done in ${((Date.now() - t0) / 1000).toFixed(0)} s`)
  }
  if (!f["no-opt"]) {
    // --shape=v5 (default): every fence gets the published v5 distribution shape (src/shape.ts);
    // --shape=tail: game_optimization.py alone - its targets + base_book_scaling, shaped only by Slot Engine's tilt
    const shape = f.shape ?? "v5"
    const profile = shape === "v5" ? loadProfile() : null
    if (shape === "v5" && !profile) throw new Error("src/v5_profile.json missing: run tools/v5_profile.ts or use --shape=tail")
    const scale = modes.includes("base") && !profile ? baseBookScaling(game) : []
    const config = optimizationConfig(scale)
    if (profile) {
      for (const m of modes) {
        const counts = await fenceCounts(game.getMetadata().paths.booksCompressed(m), m)
        for (const [target, t] of Object.entries((config as any)[m].targets as Record<string, any>)) {
          const rules = counts[target] && profile[m]?.[target] ? shapeRules(counts[target]!, profile[m]![target]!) : []
          if (rules.length) t.scale = rules
          console.log(`  v5 shape: ${m}/${target}: ${rules.length} bands`)
        }
      }
    }
    game.configureOptimization(config)
    await game.runTasks({ _internal_ignore_args: true, doOptimization: true, optimizationOpts: { gameModes: modes } })
  }
  if (!f["no-finish"]) await finishLuts(game, { modes })
  if (!f["no-analysis"])
    await game.runTasks({
      _internal_ignore_args: true,
      doAnalysis: true,
      analysisOpts: {
        gameModes: modes,
        tagStats: [{ groupBy: ["symbolId", "kind", "spinType"] }, { groupBy: ["criteria"] }, { groupBy: ["symbol", "kind"] }],
      },
    })
  console.log(`pipeline done in ${((Date.now() - t0) / 1000).toFixed(0)} s`)
}
