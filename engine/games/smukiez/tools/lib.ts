// Shared helpers for the smukiez check tools: stream books out of a .jsonl.zst file, read lookup tables, and
// locate the v5 (Math SDK) and native (Slot Engine) build files.
import fs from "fs"
import path from "path"
import { bookLines } from "../src/books"
export { bookLines }

export const ENGINE_DIR = path.resolve(__dirname, "../../..")
export const GAME_DIR = path.resolve(__dirname, "..")
export const BUILD_DIR = path.join(GAME_DIR, "__build__")
export const V5_DIR = path.resolve(ENGINE_DIR, "../math-sdk/games/smukiez_tag_run/library/publish_files")
export const MODES = ["base", "bonus", "extremebonus"] as const
export const MODE_COST: Record<string, number> = { base: 1, bonus: 100, extremebonus: 400 }

/** Every book of a books file (.jsonl.zst or .jsonl), parsed, in file order. */
export async function* readBooks(file: string, limit = Infinity): AsyncGenerator<any> {
  let n = 0
  for await (const line of bookLines(file)) {
    if (n++ >= limit) return
    yield JSON.parse(line)
  }
}

/** A lookup table `id,weight,payout` as a map id -> [weight, payoutCents]. */
export function readLut(file: string): Map<number, [number, number]> {
  const m = new Map<number, [number, number]>()
  for (const line of fs.readFileSync(file, "utf8").split("\n")) {
    if (!line.trim()) continue
    const [id, w, p] = line.split(",")
    m.set(Number(id), [Number(w), Number(p)])
  }
  return m
}

/** Slot Engine's segmented lookup table `id,criteria,basegameWins,freespinsWins`. */
export function readSegmented(file: string): Map<number, { criteria: string; base: number; free: number }> {
  const m = new Map<number, { criteria: string; base: number; free: number }>()
  for (const line of fs.readFileSync(file, "utf8").split("\n")) {
    if (!line.trim()) continue
    const [id, criteria, b, f] = line.split(",")
    m.set(Number(id), { criteria: criteria ?? "", base: Number(b), free: Number(f) })
  }
  return m
}

/** Paths of one mode's books + published table (+ criteria) for "v5" or for the native build. */
export function modeFiles(which: "v5" | "native", mode: string, buildDir = BUILD_DIR) {
  if (which === "v5") {
    return {
      books: path.join(V5_DIR, `books_${mode}.jsonl.zst`),
      lut: path.join(V5_DIR, `lookUpTable_${mode}_0.csv`),
      segmented: undefined as string | undefined,
    }
  }
  return {
    books: path.join(buildDir, "publish_files", `books_${mode}.jsonl.zst`),
    lut: path.join(buildDir, "publish_files", `lookUpTable_${mode}_0.csv`),
    segmented: path.join(buildDir, `lookUpTableSegmented_${mode}.csv`),
  }
}

/** Parse `--key=value` / `--flag` arguments. */
export function args(): Record<string, string> {
  const out: Record<string, string> = {}
  for (const a of process.argv.slice(2)) {
    const m = /^--([^=]+)(?:=(.*))?$/.exec(a)
    if (m) out[m[1]!] = m[2] ?? "true"
  }
  return out
}

export function pct(x: number, d = 2) {
  return (x * 100).toFixed(d) + "%"
}

export function oneIn(p: number) {
  return p > 0 ? "1 in " + Math.round(1 / p).toLocaleString("en-US") : "never"
}
