# GTStats

A lightweight private Golden Tee clubhouse: lifetime totals, averages, bests, progression, completed-round scorecards, course filtering, and a clearly separated snapshot of imported account history. Original interface; no official website assets or login credentials are included.

## Architecture

- `export_snapshot.py` opens local player/history SQLite databases read-only and writes an explicit allowlist of display data. Card identities, signing keys, raw protocol blobs, payment information, and account credentials are never exported.
- `server.mjs` is a dependency-free Node HTTP service. It only serves three static assets, a read-only stats endpoint, and health status; no gameplay writes or remote code execution endpoints.
- `sync_snapshot.sh` publishes the export atomically over SSH. The deployed user timer refreshes it every minute; the UI polls every 30 seconds and flags snapshots older than three minutes.
- One non-root, read-only, capability-dropped container on an internal Swarm node. The data directory is mounted read-only. Pangolin/Newt routes the public hostname to the internal target and requires the owner's existing SSO access.
- Saved rounds and imported history remain distinct. A completed round requires matching start, final-score, and full scorecard evidence; aborted attempts never count.

## Run

Generate `stats.json` with `export_snapshot.py --data PRIVATE_DB_DIRECTORY --imports OPTIONAL_PRIVATE_IMPORT_DIRECTORY --courses courses.json --output DATA_DIRECTORY/stats.json`. The output contains personal playing statistics and must not be committed.

Build using `docker build -t gtstats:local .`, then run the image with a read-only `/data` bind mount, non-root user, dropped capabilities, and port 3000 routed through your authenticated proxy. The image health check verifies that a snapshot exists.

Customize the paths and destination in `sync_snapshot.sh` for your own host. Install it as a supervised oneshot timer, not an unowned background loop. Preserve existing proxy configuration and access policies.

## Verification

Browser checks cover desktop/mobile rendering, course filtering, expanding front/back-nine scorecards, imported-history tables, zero console errors, and no mobile horizontal overflow. Public checks cover DNS, trusted TLS, anonymous browser sign-in redirect, non-browser 401, and an authenticated scorecard workflow through Pangolin. Temporary verification access is revoked afterward.

The website never changes official account stats or the cabinet. Future additions could include multi-player leaderboards and richer shot breakdowns once the necessary source data is available; unsupported metrics are not invented.
