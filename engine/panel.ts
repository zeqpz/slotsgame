// Slot Engine panel (https://slot-engine.dev/docs/panel) with its local gaming server attached: run simulations,
// read the statistics, explore books and reel sets, and play the front end against the math on this machine.
//   npm run panel        -> http://localhost:7770 (the LGS answers on the same port: rgs_url=http://localhost:7770)
import path from "node:path"
import { EngineLgs } from "@slot-engine/lgs"
import { createPanel } from "@slot-engine/panel"
import { game as ClusterExample } from "./games/cluster_example/index"
import { game as SmukiezV5 } from "./games/smukiez_v5/index"
import { game as Smukiez } from "./games/smukiez/index"
import { FileStorage } from "./fileStorage"

const panel = createPanel({
  games: [SmukiezV5, Smukiez, ClusterExample],
  lgs: new EngineLgs({ storage: new FileStorage(path.join(__dirname, ".lgs/storage.json")) }),   // sessions outlive a restart
})

panel.start()
