// The LGS's in-memory storage, kept on disk: the panel runs under `tsx watch`, and every restart used to drop
// every session, so a game left open answered each spin with "unknown session" (ERR_VAL). Sessions, wallets and
// bets are loaded from the file at start and written back after every change.
import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs"
import { dirname } from "node:path"
import { InMemoryStorage } from "@slot-engine/lgs"

type Repo = { items: Map<string | number, any>; nextId: () => string | number; create: Function; update: Function; delete: Function }

export class FileStorage extends InMemoryStorage {
  constructor(private readonly path: string) {
    super()
    const repos = this.repos()
    if (existsSync(path)) {
      try {
        const saved = JSON.parse(readFileSync(path, "utf8"))
        for (const [name, repo] of Object.entries(repos)) for (const item of saved[name] || []) repo.items.set(item.id, item)
      } catch (e) {
        console.warn(`LGS storage ${path} unreadable, starting empty:`, e)
      }
    }
    // bet ids count up from the last one kept, never reusing an id a round history already shows
    let last = Math.max(0, ...[...repos.bets.items.keys()].map(Number))
    repos.bets.nextId = () => ++last
    for (const repo of Object.values(repos)) {
      for (const op of ["create", "update", "delete"] as const) {
        const inner = repo[op].bind(repo)
        repo[op] = async (...args: unknown[]) => {
          const out = await inner(...args)
          this.save()
          return out
        }
      }
    }
  }

  private repos(): Record<"wallets" | "sessions" | "bets", Repo> {
    return { wallets: this.wallets as unknown as Repo, sessions: this.sessions as unknown as Repo, bets: this.bets as unknown as Repo }
  }

  private save() {
    const data = Object.fromEntries(Object.entries(this.repos()).map(([name, repo]) => [name, [...repo.items.values()]]))
    mkdirSync(dirname(this.path), { recursive: true })
    writeFileSync(this.path + ".tmp", JSON.stringify(data))
    renameSync(this.path + ".tmp", this.path)
  }
}
