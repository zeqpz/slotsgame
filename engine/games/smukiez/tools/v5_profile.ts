// Write src/v5_profile.json: each v5 fence's published payout distribution (probability of every payout within
// the fence, from the published lookup tables). Re-run only if the v5 publish files change.
//   npx tsx games/smukiez/tools/v5_profile.ts
import fs from "fs"
import { fenceOf, PROFILE_FILE, Profile } from "../src/shape"
import { MODES, modeFiles, readBooks, readLut } from "./lib"
;(async () => {
  const profile: Profile = {}
  for (const mode of MODES) {
    const f = modeFiles("v5", mode)
    const lut = readLut(f.lut)
    const acc: Record<string, Map<number, number>> = {}
    for await (const b of readBooks(f.books)) {
      const m = (acc[fenceOf(b, mode)] ??= new Map())
      m.set(b.payoutMultiplier, (m.get(b.payoutMultiplier) ?? 0) + lut.get(b.id)![0])
    }
    profile[mode] = {}
    for (const [fence, m] of Object.entries(acc)) {
      const tot = [...m.values()].reduce((s, w) => s + w, 0)
      profile[mode]![fence] = [...m].sort((a, b) => a[0] - b[0]).map(([c, w]) => [c, w / tot])
      console.log(mode, fence, m.size, "payouts")
    }
  }
  fs.writeFileSync(PROFILE_FILE, JSON.stringify(profile))
  console.log("->", PROFILE_FILE)
})()
