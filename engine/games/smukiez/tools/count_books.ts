// Count the books of each mode's published books file (all zstd frames).
import { bookLines } from "../src/books"
import { args, modeFiles } from "./lib"
;(async () => {
  const a = args()
  for (const m of (a.mode ?? "base,bonus,extremebonus").split(",")) {
    let n = 0
    for await (const _ of bookLines(modeFiles((a.which ?? "native") as any, m).books)) n++
    console.log(m, n)
  }
})()
