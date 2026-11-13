# Source archive and validation guide

## What this release is

This is the recoverable project source used through November 13, 2026, exported from the working research directories. It includes successful approaches, superseded experiments, and historical cabinet-specific scripts. It is **not a turnkey emulator, installer, or complete reproducible cabinet environment**.

The original private working files were not changed. The public copies replace identifying deployment details with examples. `SOURCE_MANIFEST.json` lists all 121 exported source/dependency files, their relative origin, whether sanitization occurred, and the SHA-256 of the published copy. It does not contain hashes of private data.

## Layout

- `research/`: 102 protocol, crypto, capture, emulation, routing, recovery, test and dependency files.
- `hardware/`: 19 earlier SSH/GPU compatibility, deployment, recovery and verification files, including minimal patches rather than complete vendor scripts.
- `PROJECT_LOG.md`: chronological findings, verification limits and current cabinet state.
- `SOURCE_MANIFEST.json`: source inventory and public-file integrity hashes.

See the log's implementation inventory for the main entry points. Earlier prototypes are deliberately retained; their comments and behavior do not supersede the latest verified status in the log.

## Sanitization and intentional differences

- Cabinet, gateway and management addresses use documentation examples (`192.0.2.0/24`, `198.51.100.0/24`); the former upstream endpoint is replaced with an example in `203.0.113.0/24`.
- MAC addresses, site/zone/boot UUIDs, cabinet ID, SSH username, hostname and local workspace locations are replaced with examples. These are **not working settings**.
- The original SSD serial and registration-snapshot digest are replaced with explicit `REPLACE_WITH_...` markers. Digest/preimage guards remain present and will refuse unmatched inputs; they were not removed to make examples appear runnable.
- Embedded base64 shell payloads in the historical deployment script are decoded into readable heredocs and sanitized too.
- Hard-coded native function addresses, build fingerprints and protocol constants remain as research references. They are build-specific, not a stable API.
- Historical process IDs, dated temporary paths and pinned file hashes are not refreshed for a new machine. Copying the scripts is not sufficient to reproduce the original controlled test.
- `hardware/proposed/nvidia-selector.patch` represents the selector modification instead of redistributing the complete vendor selector. The SSH lifecycle changes are likewise supplied as a small patch.

## Excluded material and dependencies

The following are intentionally **not** published:

- Credentials, authentication configuration, private server/client keys, ephemeral session keys, and trust snapshots containing cabinet identity.
- Captures, decoded real request bodies, raw logs, screenshots, database exports, storage snapshots, generated restore SQL and operational policy journals.
- Game/BootAgent executables, kernel/device modules, disassembly dumps, driver payloads, copied vendor startup/configuration files, manuals and disk images.
- The complete extracted protocol database/metadata and historical fixture packets derived from the cabinet.
- Downloaded third-party project snapshots from the earlier comparison audit; those were not authored as part of this project.
- The pre-existing local UniFi API connector and its authentication setup. Gateway integration scripts depend on that external adapter (`unifi_api`); it is not a bundled module.
- Virtual environments, caches and generated outputs.

Private source-adjacent records are not assumed safe merely because they have a text extension. Interactive shell commands that were never saved as source are described in the project log where recorded; this archive does not invent scripts to fill those gaps.

### Consequences for running the code

Many modules expect files under `research/evidence/`, `research/backups/` or `research/private-server-keys/`. Some read these at import time. A fresh clone cannot run those paths without independently supplied, appropriate local inputs. For example:

- `decode_force_call.py` requires field metadata; `registration_fixture.py` also requires a capture.
- `emulate_storage_write.py` and dependent native harnesses require the exact analyzed executable.
- Signature/session tests depend on locally generated synthetic crypto inputs that are not bundled.
- Storage recovery tests require an approved snapshot and its matching digest.
- Hardware evidence verification requires the original local logs/configuration.

These dependencies are explicitly missing, not passing tests or silently supplied mock replacements. Do not substitute arbitrary files or remove preimage checks and then assume a historical compatibility result still applies.

## Runtime distinctions

Host-side code was developed with Python 3. Cabinet-side scripts include Python 2 and 32-bit ABI assumptions. `research/emulation-requirements.txt` records versions from the historical environment, not a newly validated installation lockfile. A clean dependency installation was not tested for this publication.

**Do not run blanket test discovery.** Some historical `test_*.py` files execute integration actions at import/top level: SSH, firewall policy changes, namespace/route operations, or database commands. The deployment, storage and recovery tools can also modify a cabinet. The four explicit commands below are the reviewed offline subset, not permission to run all other scripts on a live system.

## Publication validation — November 13, 2026

From the repository root, using Python 3 and Bash:

```sh
python3 research/test_gateway_registration_guard.py
python3 research/test_positive_gate.py
python3 research/test_gateway_gate.py
python3 hardware/retest-20261104/verify.py
```

Observed results on the sanitized export:

| Check | Result |
| --- | --- |
| Registration isolation guard | 9 cases passed |
| Original staged positive boot-gate loop with mocked routes | 8 cases passed |
| Staged gateway boot-gate loop with mocked routes | 8 cases passed |
| GPU shim and recovery gate with temporary mocked files/tools | 8 checks passed |
| Python 3 syntax parsing | 65 files parsed |
| Shell syntax (`bash -n`, including extensionless wrappers) | 19 files passed |
| Python 2-only syntax | 14 files not checked: Python 2 parser/runtime unavailable |

Total: **33 mocked/offline behavioral checks passed**. No live cabinet, gateway, vendor connection, storage write or game process was exercised by this publication validation. Python 3 parsing does not prove runtime compatibility for legacy code. Tests requiring omitted native executables or private fixtures were not rerun on the public export.

## Updating the public archive

Work on the private operational copy separately. Before publishing an update:

1. Inspect current remote changes and preserve other contributors' work.
2. Export only reviewed source; sanitize both ordinary text and any embedded payloads.
3. Keep the exclusion rules in `.gitignore`; inspect the exact staged file list and content.
4. Update public-file hashes in `SOURCE_MANIFEST.json` when source changes.
5. Run the appropriate explicit offline checks and record both results and unavailable coverage.
6. Append the change and final cabinet state to `PROJECT_LOG.md`.

Git ignore rules reduce accidental additions; they are not a replacement for reviewing publication content.

## Offline follow-up: compression and player-login planning

The archive now contains104 source/dependency files. See [compression notes](COMPRESSION_NOTES.md) and [player-login plan](PLAYER_LOGIN_PLAN.md).

An additional public test command needs only standard Python3:

```sh
python3 research/test_container_compression.py
```

Eight synthetic test methods pass without private data. The combined20-test private-fixture/native suite also passed in the working environment; it is not runnable solely from this export. Separately, seven synthetic inverse-transform comparisons and16 selector checks matched the original game code using `emulate_container_compression.py` and the privately held executable. No live test was performed. Prior publication checks above remain historical results, not a claim that missing private-input tests passed in a clean clone.

## Offline identity/profile storage follow-up

The archive now contains106 source/dependency files. [PLAYER_STORE.md](PLAYER_STORE.md) describes the local persistence API and limitations. Run `python3 research/test_player_store.py` for15 temporary-database/synthetic-identity tests. The store is not connected to cabinet login. Together with the compression module,23 explicit standalone tests run without private inputs; do not use blanket discovery of the historical integration scripts.

### Native player reply policy subset

`cd research && python3 -m unittest -v test_player_reply_policy` ran six methods successfully with the privately supplied original ELF. This is an offline synthetic-registry harness, not a standalone fresh-clone test or live login proof. See [limitations](PLAYER_REPLY_POLICY.md).

## Native registry and payload follow-up

The archive contains113 source/dependency files. Six new source files provide original-initializer tests, native field-loop comparisons and a narrow read-only wire/store bridge. See [PLAYER_WIRE.md](PLAYER_WIRE.md) for the explicit standalone30-method and private-input19-method commands, modeled runtime limits and remaining physical tests. No cabinet changes were made.

## Dispatcher and persistence-boundary follow-up

118 source/dependency files are now inventoried. Five new files and expanded registry tests distinguish generic and dedicated player paths. See [handoff evidence and explicit commands](PLAYER_HANDOFF.md). Combined70 offline methods pass in the private-input research environment;30 standalone methods still require no private files.

## V2 codec release validation

See [V2 codec and correlation](PLAYER_V2_CODEC.md) for the 87-method scope and limits. Safe standalone selection (37 methods):

```sh
cd research
python3 -m unittest test_player_wire test_player_wire_v2 test_player_store test_container_compression
```

Do not use blanket test discovery: historical modules can perform live operations. `test_player_response_correlation` requires private protocol metadata at import, despite not needing the game executable.
