# How the game goes up to engine.io (Stake Engine)

This is how Smukiezs Mural is uploaded to engine.io, and the code that does it.

| File | What it is |
|---|---|
| `github_upload_tab.js` | **Route A** (the usual one): run it in the logged-in dashboard tab. It uploads a pushed commit straight from GitHub, only the files that changed. |
| `stake_upload.py` | **Route B**: upload from your own disk (files not pushed yet). Same script as `tools/stake_upload.py`. |

## What goes where

engine.io keeps two **bundles** per game, each in a *scratch* area:

| Bundle | Comes from | Contents |
|---|---|---|
| `front` | `frontend/` (everything except `mock_rgs.py`, the local dev server) | `index.html`, the scripts, `assets/...` |
| `math` | `math-sdk/games/smukiez_tag_run/library/publish_files/` | `books_*.jsonl.zst`, `lookUpTable_*.csv`, `index.json` |

* **Uploading** puts files into scratch. Nothing changes for players.
* **Publishing** turns scratch into a new version (front vN, math vN) that the game launcher serves.
* Team `smukiez`, game `smukiezs-mural`. Files page:
  https://studio.engine.io/teams/smukiez/games/smukiezs-mural/files

## There is no API key

engine.io only trusts a logged-in browser session. Every upload is therefore minted **inside the
logged-in dashboard tab**: open the Files page above, open DevTools (F12) and use the Console. You
can also run the scripts with any tool that executes JavaScript in that tab.

Use the plain `/files` page. On the `...files?launch=true...` URL the upload API answers
`Forbidden`.

## Route A: from GitHub (recommended)

The repo is public with no Git LFS, so the tab can read any commit itself. It downloads each file
from `raw.githubusercontent.com` and MD5s it, then compares that with the scratch listing (the
listing's etags are plain MD5s). Only files that differ are uploaded: it mints a presigned URL for
each and PUTs the bytes from the tab. No URL or token ever leaves the tab, and nothing runs on your
machine.

1. Commit and push what you want live:
   ```bash
   git push origin main
   git rev-parse HEAD
   ```
   Copy the full 40-character SHA.
2. Open the Files page (logged in), then the DevTools Console.
3. Open `github_upload_tab.js`, set `CFG.commit` to the SHA, and paste the whole file into the
   Console. It starts a background job and returns at once.
   * `CFG.dryRun = true` shows what would go up without uploading anything. Try it first.
   * `CFG.partsToDo = ["front"]` limits the run to the front end, and `CFG.only = ["front/index.html"]`
     to named files.
   * Text files whose scratch copy differs only by Windows line endings count as unchanged
     (`crlfSame`), so a CRLF upload from a Windows checkout is not sent again for nothing.
4. Poll until it finishes:
   ```js
   __upStatus()
   ```
   Keep polling while `phase` is `"checking and uploading"` or `"verifying"`. It ends as `"done"` or
   `"failed"`. A front-end change takes about a minute; the math books (60-90 MB each) take a few
   more.
5. Check the result. `uploaded` lists the files sent, and `verified` counts the ones whose scratch
   etag now equals the MD5 of what was sent. `errors` should be empty.
6. Publish (below).

## Route B: from your own disk

Use this for files that are not on GitHub yet. The dashboard tab cannot read your disk: a browser
on an https page cannot fetch `http://localhost`. So Python writes a checksummed manifest, the tab
mints the URLs, and Python PUTs the files. The checksums make a copy-paste slip impossible to miss.

```bash
python howtotuploadonengine/stake_upload.py manifest ../engine_upload
```

This writes `../engine_upload/upload_manifest.txt` (every local file: bundle path, MD5, size) and
`../engine_upload/upload_tab.js`. Keep this folder **outside the repo**, so the minted URLs in it
can never be committed.

1. Run `upload_tab.js` in the dashboard tab. It verifies the manifest's SHA-256, diffs it against
   scratch, and mints one URL per changed file. It returns `{upload, sha, json}`.
2. Save `json` exactly as returned to `../engine_upload/mint.json`, then:
   ```bash
   python howtotuploadonengine/stake_upload.py build ../engine_upload/mint.json <sha>
   ```
   It refuses a table whose SHA-256 is not the tab's. It writes `urls_front.txt` and one
   `urls_math_<n>.txt` per math file.
3. Upload:
   ```bash
   python howtotuploadonengine/stake_upload.py put front ../engine_upload/urls_front.txt
   ```
   For math, run `put math ../engine_upload/urls_math_<n>.txt`, one per book, in parallel terminals. One
   connection can crawl while another runs fast. Uploads stream in 1 MB pieces, print progress,
   and retry 4 times.

The minted URLs carry short-lived AWS credentials. Mint, upload, then delete the folder.
Never commit them.

## Publish

Press **Publish Game** on the dashboard, or run this in the tab:

```js
const pub = kind => fetch(`/api/file/publish/${kind}`, { method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ team: "smukiez", game: "smukiezs-mural" }) }).then(r => r.json());
await pub("front");   // and/or await pub("math")
```

It answers `{ version, changed }`. `changed: false` means scratch had nothing new for that bundle.

Check what is live (the list is newest first):

```js
await (await fetch("/api/teams/smukiez/games/smukiezs-mural/versions")).json()
```

The first request to a freshly published version can answer **404** for assets the CDN edge has not
warmed yet. The same request answers 200 moments later; the file is not missing.

The approval review is separate. It rates a version, and you resubmit from the game's Approval
page once it unlocks.

## The dashboard API the scripts use

All calls are same-origin `fetch` from the logged-in tab.

| Call | Does |
|---|---|
| `GET /api/file/game/<team>/<game>/scratch/front` (or `/math`) | Lists scratch: `[{ key: "front/…", etag: "\"<md5>\"", size }]`. The etag is the plain MD5 (single-part PUT), so comparisons are exact. |
| `POST /api/file/upload` `{ team, game, path, size }` | Mints one presigned S3 PUT URL: `{ key, url }`. **One file per call**: a batched `files: [...]` array returns 500. `path` must carry the `front/` or `math/` prefix. `size` is the real byte count; a placeholder is refused. |
| `PUT <url>` with the raw bytes | Uploads the file. Every realistic asset fits one PUT (the chunk size is 100 MB). |
| `POST /api/file/publish/front` (or `/math`) `{ team, game }` | Publishes scratch as a new version: `{ version, changed }`. |
| `GET /api/teams/<team>/games/<game>/versions` | `[{ type: "front" or "math", version, created }]`, newest first. |
| `POST /api/file/delete` `{ team, game, paths: [...] }` | Deletes from scratch. It needs a **`paths` array**: a singular `path` silently answers `{"deleted":0}`. This cannot be undone. |

## Gotchas (all hit for real)

* **Drop the `front/` or `math/` prefix and nothing fails, but the files land in the wrong place.**
  The mint and the PUT both answer 200, but the file lands beside the bundle instead of in it. The
  tell: publishing answers `changed: false`, and the Files page still shows the old size.
* **Never call `/api/file/complete`.** It is for multipart uploads only and answers 500 otherwise.
* **Presigned URLs expire early.** Their STS credentials die well before the advertised
  `X-Amz-Expires=21600` (6 h). Mint fresh URLs for every upload and never reuse a saved table.
* **Line endings.** A Windows checkout (`core.autocrlf=true`) has CRLF text files while git stores
  LF, so the same `index.html` has two different MD5s. Route A uploads the git (LF) version, and its
  `crlfSame` option treats a CRLF copy already in scratch as the same file. Browsers do not care
  which one is served.
* **Big uploads from this PC can stall for minutes.** Route B streams with a stall timeout and
  retries; run books in parallel.
* **The Claude app's browser pane cannot reach `localhost` from the https dashboard**
  (`ERR_BLOCKED_BY_CLIENT`). That is why Route B moves the manifest and the URL table by copy, with
  checksums.
* **Only the 16:9 cover and 3:4 tile go on the Media page.** Fonts, sounds, video and images the
  game loads belong in the front bundle.
* **Use the right Files page URL:** `/teams/<team>/games/<slug>/files`. The shorter
  `/games/<slug>/files` renders "Something went wrong".
