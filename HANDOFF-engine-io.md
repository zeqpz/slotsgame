# How this project talks to engine.io (Stake Engine)

**There is no API key, token or CLI login stored anywhere.** Every upload so far went
through the **Claude desktop app's built-in browser pane**, which Cooper logged into
engine.io by hand. That browser profile holds the session cookie; the session that drives
the pane can make same-origin `fetch()` calls to engine.io's private dashboard API.

Game: team `smukiez`, game `smukiezs-mural`
Dashboard: https://studio.engine.io/teams/smukiez/games/smukiezs-mural/files
(moved from engine.io to **studio.engine.io** around 2026-09-18; the old host redirects
to marketing and its API returns the HTML shell, which reads like a broken session)
Game UUID (bucket prefix): `01a09492-cff1-7dee-98a7-3dc642d55cc2`
Test launcher: the **Play Game** button on that page → iframe at
`https://smukiez.live.engine.io/smukiezs-mural/v<front>/?sessionID=…&rgs_url=rgsd.engine.io&…`
(serves the *published* front version, not the scratch bucket).

## Upload = three steps

1. **Mint presigned URLs** — from a tab that is logged in and on the Files page:
   `POST /api/file/upload` with JSON `{team, game, path, size}` — **one file per call**,
   `path` carries the `front/` (or `math/`) prefix, no `type` field. Returns `{key, url}`,
   a presigned S3 PUT on `stake-engine-scratch.s3.eu-west-1.amazonaws.com`.
   `python tools/stake_upload.py mint index.html rgs.js assets/logo.png` prints the exact
   JS to paste; it outputs `rel|url` lines.
2. **PUT the bytes** from the PC: save the lines to `urls.txt`, run
   `python tools/stake_upload.py put urls.txt`. Expect `HTTP 200` per file.
   Do not reuse old URLs — the STS creds expire early (`ExpiredToken`).
   `/api/file/complete` is multipart-only; never call it (chunk size is 100 MB).
3. **Publish** — click **Publish Game** on the Files page (== `POST /api/file/publish/front
   {team, game}`). Front versions are numbered; Play Game picks up the new one.

Uploading only replaces the files you PUT; everything else in the bundle stays.

## Doing it from a new Claude session

Either:
- Open the app browser pane to the Files page, have Cooper log in, then use the pane's
  `javascript_tool` to run the minted snippet and read back the URLs; PUT with the script.
- Or install **stakecli** (github.com/mnemoo/cli, MIT): it authenticates with the browser's
  `sid` cookie from stake-engine.com/engine.io, has an upload wizard and a CI mode
  (`stakecli` upload → publish). Community-standard; not yet used on this project.

## Publishing math: the 512 KiB per-book limit

**Any single book (one line of the JSONL) over 512 KiB (524,288 bytes) is rejected.** The
publisher answers 400 with:

    {"code":"ERR_INVALID_FORMAT","mode":"bonus",
     "file":"failed to parse book file books_bonus.jsonl.zst:183074:0"}

`183074` is a **byte offset into the decompressed stream**, not a line number - which is why
it can exceed the file's line count. It lands inside the first offending book. In that case
it was 72,421 bytes into book #10, which is 527,367 bytes long.

Established by experiment against the live publisher (2026-09-18):

| uploaded | result |
| --- | --- |
| real bonus (largest book 1,739,634 B) | rejected at offset 183074 |
| byte-identical re-upload | same error - so it is not upload corruption |
| bonus with every book capped at 60 KB | bonus passes, publisher moves to extremebonus |
| extreme capped at exactly 524,288 B | extreme passes, publisher moves to base |
| real base (largest 1,523,170 B) | rejected at offset 1361560 |

So the ceiling is in [524288, 527367) - i.e. 512 KiB. Modes are checked in the order
**bonus -> extremebonus -> base** and it stops at the first failure, so an early pass does
not mean the later modes are clean.

Run `python tools/check_books.py <file>` before uploading; it flags oversized books and
names the line. Note the error is NOT about JSON validity - these files parse perfectly.
The fix is in the math: emit fewer/smaller events for long tumble chains (send only changed
cells on `tumbleBoard` rather than the whole board).

## Gotchas already hit
- Media page only accepts lobby artwork (16:9 cover, 3:4 tile); runtime assets go in the
  front bundle.
- Live RGS returns `round.state` (not `events`), plain `payoutMultiplier`, auto-settles
  zero-win rounds (`active:false`, and `end-round` then 400s), bare `{amount,currency}` from
  `end-round`. `frontend/rgs.js` handles all of it; `frontend/mock_rgs.py` mirrors it.
- Local test: `.venv/Scripts/python.exe frontend/mock_rgs.py` → `http://localhost:8733/index.html?sessionID=test&rgs_url=http://localhost:8733&lang=en&device=desktop`.

Full notes: `beta/README.md`, memory files `stake-engine-upload-api`, `stake-engine-rgs-wire-format`.
