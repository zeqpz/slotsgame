# How this project talks to engine.io (Stake Engine)

**There is no API key, token or CLI login stored anywhere.** Every upload so far went
through the **Claude desktop app's built-in browser pane**, which Cooper logged into
engine.io by hand. That browser profile holds the session cookie; the session that drives
the pane can make same-origin `fetch()` calls to engine.io's private dashboard API.

Game: team `smukiez`, game `smukiezs-mural`
Dashboard: https://engine.io/teams/smukiez/games/smukiezs-mural/files
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

## Gotchas already hit
- Media page only accepts lobby artwork (16:9 cover, 3:4 tile); runtime assets go in the
  front bundle.
- Live RGS returns `round.state` (not `events`), plain `payoutMultiplier`, auto-settles
  zero-win rounds (`active:false`, and `end-round` then 400s), bare `{amount,currency}` from
  `end-round`. `frontend/rgs.js` handles all of it; `frontend/mock_rgs.py` mirrors it.
- Local test: `.venv/Scripts/python.exe frontend/mock_rgs.py` → `http://localhost:8733/index.html?sessionID=test&rgs_url=http://localhost:8733&lang=en&device=desktop`.

Full notes: `beta/README.md`, memory files `stake-engine-upload-api`, `stake-engine-rgs-wire-format`.
