# Golden Tee: Private Online Emulation & Player Login

An ongoing engineering journal for bringing a privately operated Golden Tee cabinet onto a locally controlled replacement service.

**Latest documented milestone:** November 13, 2026, approximately 23:20 UTC.
**Log created:** November 13, 2026.  
**Project status:** Experimental card login, gameplay and local persistence demonstrated; protocol coverage remains incomplete.

This initial log reconstructs the recorded work from research notes, test evidence, and recovery records. It is not a claim that every earlier command or hardware action was recorded. Future changes should be appended using the template at the end.

## 1. What we are building

The goal is a private replacement service that the cabinet can communicate with, followed by card-based player identification, local player profiles, and persistent progress.

This is not a connection to an official online account system. Recovering official player history, operating official tournaments or prizes, and reproducing every vendor feature are outside the demonstrated scope.

### Initial result (historical; superseded by the evening updates)

- Private registration and an encrypted, signed session exchange were accepted by the original cabinet software during an isolated test.
- Follow-up synchronization replies and acknowledgments were accepted.
- A remote screenshot showed a **green LIVE indicator**.
- The Online menu, card swipe, player login, profile retrieval, and profile saving have **not** been verified end to end.
- Testing ended with the original registration state restored and independently compared against backups. Temporary WAN isolation was removed, normal game startup was verified, and remote management remained available.
- No persistent private online service is installed on the cabinet.

The green indicator is a meaningful protocol milestone, not proof that the player-facing project is finished. There is no defensible percentage-complete or completion date yet: the remaining player workflow can expose additional protocol requirements.

## 2. Environment and architecture

The cabinet presents as Golden Tee 2021 HD; the observed running software version is `16.04.15`. The environment includes 32-bit i686 Linux, kernel `5.0.10-PRD.1.5`, PostgreSQL 7.3, and the bundled NVIDIA 390.116 driver used for the GTX 1080 work.

These details describe this cabinet, not a universal compatibility guide.

```text
Original cabinet game
  |  Registration, session establishment, encrypted follow-up requests
  v
Cabinet-specific test routing / SSH bridge
  |
  v
Private responder on a separate host
  |-- Container framing, checksums, compression and encryption
  |-- Private registration and session responses
  |-- Bounded synchronization / file / banner / settings responses
  `-- Player identity and persistent profile service: future work

Separate recovery path:
  management SSH + boot gate + registration snapshots + verified restoration
```

The private session currently depends on an explicit **RAM-only public trust selection** in the game process. The unmodified cabinet has not been shown to trust arbitrary replacement servers. Original trust objects are retained during the test; reboot clears the temporary selection. No vendor private signing keys were recovered, and cabinet private identity keys were not read for this work.

## 3. Milestone ledger

| Milestone | Evidence / status |
| --- | --- |
| Keep management SSH alive through game startup | Startup-script fixes and subsequent successful access |
| GTX 1080 driver, display and game startup | Native driver and 1080p startup observed; long-term gameplay stability not established |
| Capture and understand basic vendor traffic | PING/PONG, check-in, registration and follow-up traffic decoded |
| Reproduce container framing | Offline fixtures plus bounded live exchanges |
| Restore targeted registration state | Hardware-backed storage and SQL restoration independently compared |
| Positive private registration | Accepted live under cabinet-only isolation |
| Native cryptographic compatibility | Original routines exercised offline; valid and invalid response cases checked |
| Encrypted private registration/session | Accepted live under temporary public trust selection |
| Follow-up synchronization and ACKs | Specific replies accepted by the native game |
| Green LIVE indicator | Observed in a remote screenshot during the isolated test |
| Latest mixed-request bundle handling | Offline-tested only; resumed live window received no requests |
| Online menu and card swipe | Awaiting physical cabinet test |
| Player login and persistent profiles | Local persistence implemented/offline-tested; cabinet login and profile reload remain unverified |
| Unattended installation and reboot persistence | Not implemented as a finished service |

## 4. Historical change log

All times below are UTC. Entries distinguish observations from hypotheses and record unsuccessful approaches where they affected the design.

### 2026-11-03 — Remote access and initial hardware compatibility

**Remote management recovery**

- An offline SSD copy was available for analysis. A user-supplied Clonezilla report said all eight partitions were restorable, with an approximately 23 GiB backup. A physical restore was not performed as part of this verification.
- Found that the Samba stop script explicitly terminated `sshd`, while BootAgent stopped Samba during startup. The early SSH hook also ran in inappropriate stop/prepare-master paths.
- Made a two-file fix: stop terminating SSH in the Samba shutdown path, and restrict the early SSH hook to startup.
- Preserved pre-change copies; checked shell syntax, ownership, modes, and unchanged Ethernet configuration. The user reported the game and SSH working, and independent SSH access succeeded.
- This established recovery access, not a guarantee of indefinite uptime or repeated-boot stability.

**Motherboard identity and display**

- Distinguished motherboard classification from the displayed SMBIOS label; these were separate paths.
- Tested a temporary RAM-only display-label correction with the original buffer preserved. This was not a BIOS, kernel, or on-disk executable change and did not survive reboot.
- Physical DIP-switch changes produced an observed `1920x1080 @ 60 Hz` display mode.

**GTX 1080, first attempt**

- The bundled native driver supported the card, but the driver selector lacked the matching case. Added a narrowly scoped selector branch for the existing 390.116 driver.
- Six mocked PCI-selection tests passed, retaining other GPU and fallback behavior.
- Driver and X startup succeeded, but the game rejected the card at 1080p.
- A game-only PCI-reporting experiment presenting a GTX 1650 selected an incompatible X layout and produced a black screen. It was rolled back, and the original GTX 750 Ti was restored.
- Later analysis identified the missing `layout_1280x720` X configuration as part of that failure. The black screen alone was not evidence that the native GTX 1080 driver failed.

### 2026-11-04 — Recovery-first boot and revised GTX 1080 path

- Audited bundled driver archives. Only 304.137, 340.107 and 390.116 contained actual driver payloads; five other archives were manifests/empty entries, not usable installations.
- Corrected the earlier GTX 1650 assumption: its support was not present in this bundled 32-bit stack. Changing reported PCI names does not supply a missing driver.
- Introduced a boot gate separating management recovery from game launch: networking and SSH become available before the game is released for that boot.
- Revised the game-only compatibility profile to present the GTX 1080 as a GTX 750 Ti while retaining the real native GTX 1080 driver.
- Eight offline boundary checks passed. Recovery SSH was demonstrated with both the original card and the GTX 1080.
- The GTX 1080 reached 1080p at 60 Hz with sound/control/framework startup; the user confirmed the displayed resolution.
- One startup Xid 13 shader-exception cluster was observed, with no recurrence during the short observation window. Long-duration stability and full gameplay/audio coverage were not established.

### 2026-11-12 — Online diagnosis and transport reconstruction

**Why a successful network connection was insufficient**

- The Advanced/Online workflow was unavailable and registration was required; there was no usable UI path for the intended card test.
- Vendor PING/PONG and `SPAM_ME` traffic worked. A captured Force Call led from `SPAM_ME` message 3 version 4 to registration 14007 version 3, control 62 version 2, and file-list 258 version 2.
- The vendor response contained zero operator identifiers and disabled online/account availability. TCP connectivity and a successful check-in therefore did not establish registration.
- The reason for the vendor's disabled response remains unknown. Retirement, account state, and hardware restrictions were not independently established as the cause.
- Database metadata supplied approximately 239 distinct message IDs for the relevant product, with multiple versions. Metadata was treated as a lead, not evidence that every message was implemented or exercised live.

**Capture and packet framing**

- Corrected packet capture from `ETH_P_IP` to `ETH_P_ALL`, using narrow filters and bounded capture size/time.
- Established version and size-width handling in the first header byte, big-endian fields, header and container checksums, container identifiers, and echo behavior.
- Corrected an earlier interpretation: compression selection is in the top two bits of the first header byte, not the second byte.
- Implemented uncompressed traffic and compression method 1 (zlib). Method 2 includes an additional transform and remains unsupported.
- A loopback PING/PONG fixture initially matched exactly offline; later bounded live heartbeat exchanges supplied separate live evidence.
- Re-encoded an official negative registration response with identical fields as a transport control. That was not a positive registration result.
- Normal startup revealed encrypted registration message 14009, showing that plaintext check-in support was only part of the required implementation.

### 2026-11-12 — Registration state, native emulation and rollback

Positive registration can modify both hardware-backed storage and PostgreSQL state. Restoration was developed before relying on positive tests.

- Took six 512-byte reads: selectors 1, 2 and 3, each read twice, with valid checksums.
- Corrected the active registration mapping: format 1 uses mirrored physical blocks **2 and 3**, not the earlier 1-and-3 hypothesis.
- Native writes occur to block 3 and then block 2. A failure on the second write can leave different copies; there is no automatic undo.
- Native reads prefer block 2 and fall back to block 3 on failure. A valid block 2 can conceal a divergent block 3.
- Exercised original x86 routines under Unicorn using synthetic RAM-backed device calls: three write cases and seven read cases covered failure/fallback and integrity behavior. This did not emulate complete firmware or prove power-loss behavior.
- An authorized identical-byte hardware rewrite was followed by six independent reads that matched exactly, around 20:44–20:47.
- Tested PostgreSQL 7.3 restoration against temporary tables and native constraints with transaction rollback, then developed atomic snapshots and guarded restoration of three registration objects and fifteen attributes, including four equality checks.
- Observed that native handler memory identifiers can change before a save failure and that the tested caller prefix did not check certain database-helper return values. A success-looking UI is not sufficient restoration evidence.
- Recovery therefore compares storage and SQL independently and restarts the process to clear transient state.

**Backup scope:** these storage snapshots cover the selected registration blocks, not the entire device. The targeted SQL snapshots are not a full database backup. A separately saved full database dump is also not proof of a tested full-system restore.

### 2026-11-12 — Isolated positive registration experiments

- Early cabinet-local routing/isolation attempts interfered with management or game progress. No positive responses were sent in the early failed cases. Recovery paths were exercised, including one physical reboot.
- The claim that the game deleted routes was not established and is not treated as a finding.
- Moved WAN isolation to a gateway-owned, cabinet-specific block while preserving management access and a local bridge to the replacement responder. Other devices and default routes were left unchanged.
- Kept the isolation block until registration restoration was independently verified. A pending-test boot gate prevented a reboot from releasing altered registration state back to the vendor.
- Used bounded responders and return-to-maintenance timers.
- Around 23:06, a positive local registration response was accepted live, followed by verified rollback.
- Around 23:40, the physical UI still showed Online unavailable with a technical connection failure. Investigation identified encrypted `NEW_SESSION` message 14000 as the next missing exchange.
- From approximately 23:46, original storage and SQL were restored and compared, isolation was removed, and normal game operation resumed.
- Added handling for observed boot, clock, and software-update exchanges. Unsupported/error cases were not converted into fictitious success.

### 2026-11-13 — Native crypto and complete session acceptance

**Offline compatibility**

- Built native-routine tests for RSA private decryption/padding, SHA-1, DSA signature verification, Diffie–Hellman key agreement, and complete session response acceptance.
- Used synthetic keys, controlled time, cached provisioning, and modeled allocation/library behavior. This was an original-code harness, not a full game emulator.
- Investigated slow RSA setup. The modeled allocator failed to reclaim memory; implementing reuse/free allowed original modulus/exponent/private-exponent initialization to pass without the earlier factor-injection workaround.
- A valid complete reply established native session state 2 and the expected shared key. A modified reply was rejected with status 256 and empty output.
- Added a PyCryptodome-backed private-service adapter using independently generated server keys.

**Bounded live trust and encrypted transport**

- Drilled restoration before selecting separate public encryption/verification contexts in RAM. Original objects and cached public identity were retained; checks tied the operation to the expected executable and boot.
- By approximately 13:03, encrypted registration `14009 -> 14003` and signed session establishment `14000 -> 14001` were accepted live under this temporary trust selection, without upstream vendor connections during the isolated test.
- Confirmed legacy transport behavior against original routines: a 32-byte derived key, per-container RC4, a key-seeded container CRC, an unkeyed header CRC, and two key slots selected by a container flag.
- This describes compatibility with an existing legacy protocol, not a recommended modern security design.

**Clock and follow-up findings**

- The native clock setter sometimes shifted system time through its RTC path. Root cause remains unresolved; accurate time was observed again after recovery.
- Independently checked accurate time before a bounded RAM last-check marker suppressed only a redundant RTC update. Native decision tests showed that it did not override a genuinely incorrect clock. This is not a permanent clock repair.
- Diagnostic message 141 was durably recorded before acknowledgment; software-update message 146 received similar receipt handling. The guard rejects acknowledgment when persistence is unavailable.
- A successful `ReconnectITNetNow` wrapper call did not produce an observed idle, unregistered check-in. It is not treated as a proven Force Call replacement.
- Early follow-up failures included unsupported synchronization and mixed banner/settings bundles, dropped connections, and a pipelined heartbeat.
- For one same-boot responder restart, only the ephemeral transport key was retained privately, not cabinet identity keys.

### 2026-11-13 — Correct ACKs, synchronization and green LIVE

- Fixed a misleading acknowledgment test: a native response-policy allowlist accepted the intended message type, but the actual normal-form wire encoding was rejected.
- The correct compact ACK is byte `04`; the original parser expands it to the internal ACK representation. Added an independent native wire-parser regression rather than relying on a local encoder/decoder round trip.
- Decoded synchronization message 274 version 1: short name/value pairs in field 36 and timestamps in field 34, with count and group validation. Native cursor checks independently confirmed the boundaries for observed lists of 20 and 585 pairs.
- Replied with message 261 version 1 in the same transformation group and an empty name list, meaning no updates requested. Two such replies were accepted around 13:39:44; the corrected ACK was accepted around 13:39:48.
- Added handling for an observed mixed `274 / 274 / 257 / 188` bundle with `261 / 261 / 258 / 189` replies. The latest mixed-bundle implementation passed offline tests, but the restarted live responder received no requests in its bounded window. **That final change is not live-verified.**
- Enabled the private test's online/account availability fields while leaving unsupported prize, tournament, and optional integrations disabled. No player profiles were fabricated.
- Eleven focused regression tests passed. This is a focused test result, not a claim that every project test or protocol path passed.
- Around 13:41–13:42, an XWD-based remote screenshot showed a **green LIVE indicator**. FFmpeg lacked the required X11 capture support, so XWD plus a locally validated conversion was used.
- No physical Online-menu or card-swipe confirmation was available because the operator was away from the cabinet.

### 2026-11-13 — Cooling warning and final recovery

**Separate hardware observation**

- The screen showed a cooling-system warning. Observed readings were approximately CPU 35°C, GPU 46°C, and GPU fan 29%, while motherboard fan-speed readings were zero.
- CPU-fan STOPPED messages were already present in logs from November 12. These observations do not establish newly damaged motherboard hardware or overheating.
- Normal temperatures do not prove the CPU fan is spinning. A physical fan/header check remains outstanding; no thermal or fan-control settings were changed for this warning.

**Return to normal operation, verified by 13:46:36**

- Ended the bounded private-server experiment.
- Compared six storage reads and the three-object/fifteen-attribute SQL snapshot against their pre-test originals: exact matches.
- Reboot cleared the RAM-only trust selection. Restored the pre-test boot gate and archived active test/pending markers.
- Removed the owned cabinet-only WAN block and verified its absence.
- Verified normal game process startup and the mode-tree startup log, healthy SSH, accurate UTC, and ordinary vendor routing/TCP connectivity.
- These checks establish restored registration and normal startup, not a fresh end-to-end gameplay test or official online registration.

### 2026-11-13 — Public documentation established

- Created this consolidated journal in a separate public-documentation directory rather than exposing the research workspace.
- Established a convention to append meaningful future changes, verification results, failures, and recovery outcomes here.
- This is a documentation export only. No GitHub repository was created or published as part of this step.

### 2026-11-13 — GitHub documentation publication

- At the owner's request, prepared the sanitized journal and a short README for `mrgrosser/gtonline-project`.
- Publication scope is documentation only; no private research files, test secrets, captures, or cabinet dumps are included.
- The cabinet was not modified by this documentation step.

### 2026-11-13 — Sanitized source publication

- At the owner's explicit request, prepared 101 source/dependency files from the protocol/session research and earlier SSH/GPU work for publication. Preserved superseded experiments as history.
- Replaced identifying deployment values with example placeholders; decoded and sanitized embedded shell payloads. Exported vendor-script modifications as minimal patches, not full vendor scripts.
- Added a source manifest, publication exclusions, runtime/dependency notes, and explicit offline test commands in `SOURCE_GUIDE.md`.
- On the sanitized export: 33 mocked checks passed; 65 Python files parsed as Python 3 and 19 shell files passed syntax checks. Fourteen Python 2-only files were not syntax/runtime-validated. Native/private-fixture tests were not rerun.
- This publication made no cabinet changes. Player login remains unverified; no new live-online milestone is claimed.

### 2026-11-13 — Offline compression decoder and login research

- Corrected the compression selector to four bits spanning the first two header bytes. Original-code execution matched all16 values; extended selectors are now rejected rather than mistaken for modes0/1/2.
- Implemented bounded method2 decoding: zlib followed by an inverse byte-sort transform with a sentinel and two trailer indices. Seven synthetic vectors matched the original transform routine.
- Added eight standard-library-only synthetic compression tests, runnable without private captures or executables. The focused private-fixture/native suite passed20 tests, including plaintext/encrypted method2 settings bundles and refusal when the isolation guard fails.
- No real method2 capture was available in the surveyed saved containers, and no live retest occurred. This is offline compatibility evidence, not a new player-facing milestone. Selectors>=3 remain unsupported.
- Mapped candidate player-info, stats, hole-data, name and cardless-login messages from metadata; drafted a SQLite-backed profile design and physical validation sequence in `PLAYER_LOGIN_PLAN.md`. These handlers/storage are not implemented or accepted live. An uninitialized native player-policy probe failed with an unmapped read, so no acceptance claim is made.
- Cabinet unchanged; final restored state remains the13:46UTC record. Physical fan, Online-menu, card swipe and profile reload checks remain outstanding.

### 2026-11-13 — Offline player identity/profile store

- Implemented `player_store.py` using standard-library SQLite: explicit enrollment, source-scoped HMAC identity lookup, profile revisions, atomic saves and per-player retry receipts. No raw card identity or key is stored; profile payloads themselves are not encrypted at rest.
- Fifteen offline tests pass, including concurrent identical retries (one commit/one replay), stale updates, conflicting retries, receipt-write rollback, read-only refusal, reopen persistence, wrong-key refusal and forced process exit within the actual save transaction.
- Profile format is a local version1 JSON object, not a claimed cabinet wire schema. Round/hole semantics, normalization and the player-login adapter remain unimplemented. No responder/player success messages were added.
- Static follow-up explains the native player-policy probe's missing runtime context: it depends on a message registry and association logic. Those branches are not yet acceptance-verified.
- Added `PLAYER_STORE.md` with API, runnable synthetic example, tested behavior and limitations. Cabinet and gateway remain untouched.

### 2026-11-13 — Native player reply policy harness

- Added `test_player_reply_policy.py` and [native-policy notes](PLAYER_REPLY_POLICY.md). Six offline test methods pass against the privately supplied original executable.
- Initialized a synthetic in-memory lookup table instead of passing a null context. Original matching routines accept configured pairs and reject crossed/empty associations; a deliberately changed table changes the outcome. Repeated calls and multi-entry vectors also pass.
- The tested general policy branch does not validate payload version; its accepting a version argument is not proof of a supported player schema. Generic ACK is rejected for the tested player request IDs.
- Scope limitation: actual product registry initialization, real pairings, payload parsing and cabinet login remain unverified. No original code or real account/capture data is published.
- No cabinet or gateway changes. Physical fan, Online-menu, card and profile-reload checks still await the operator.

## 5. Protocol coverage snapshot

Message numbers are research references, not a complete protocol specification. Versions and field layouts matter; supporting one version does not establish all versions.

| Exchange / feature | Current coverage |
| --- | --- |
| PING/PONG and basic check-in | Captured, reproduced and exercised in bounded tests |
| Plain registration 14007 v3 | Observed official negative response; private positive registration subsequently accepted |
| Encrypted registration 14009 → 14003 | Accepted live under temporary private trust |
| Session 14000 → 14001 | Native offline validation and isolated live acceptance |
| Diagnostic 141 / update 146 | Receipt persistence handling; not full reproduction of vendor processing |
| Compact ACK / internal 32767 | Native wire regression and live acceptance |
| Synchronization 274 v1 → 261 v1 | Specific no-update responses accepted live |
| File list 257 → 258 | Empty-list handling; latest combined bundle is offline-only |
| Banner 188 → 189 | Empty response handling; not a content service |
| Settings 235 v2 → 236 v2 | Empty response handling; not full settings synchronization |
| Compression 0 / 1 | Uncompressed and zlib paths implemented |
| Compression 2 | Decoder implemented; synthetic/native comparisons pass; no live proof |
| Player lookup, profile loading/saving | Local store tested offline; cabinet wire adapter/end-to-end behavior not demonstrated |

## 6. Implementation inventory

The following filenames identify research components now included as sanitized source under `research/`. They are not a promise of standalone execution: see `SOURCE_GUIDE.md` for excluded inputs and validation limits. Captures, secrets, generated fixtures, and future source changes require their own review before publication.

| Area | Representative local components |
| --- | --- |
| Capture and framing | `inspect_capture.py`, `heartbeat_probe.py`, `reencoding_relay.py`, `decode_force_call.py` |
| Registration and follow-ups | `registration_fixture.py`, `local_followups.py` |
| Session transport | `session_transport.py`, `private_session_crypto.py` |
| Original-code harnesses | `native_crypto_machine.py`, `emulate_complete_session_reply.py`, `emulate_outgoing_session.py`, `emulate_session_signature.py`, `emulate_trust_swap.py` |
| Private server | `private_session_responder.py`, `run_private_host.py` |
| Temporary trust | `gdb_public_trust_drill.py`, `refresh_public_context.py`, `apply_trust_when_ready.py` |
| Isolated test routing | `gateway_registration_guard.py`, `cabinet_relay_bridge.py`, `run-relay-window.sh` |
| Snapshot and recovery | `snapshot_registration_db.py`, `build_registration_db_restore.py`, `registration_storage_drill.py`, `restore_original_registration.py` |
| Focused regressions | `test_followup_wire.py`, `test_private_session_responder.py`, `test_session_transport.py`, `test_session_clock_guard.py` |

The local emulation environment uses Unicorn, pyelftools, and PyCryptodome. No installation recipe or dependency-version guarantee is implied by this inventory.

## 7. Persistent versus temporary changes

- **Earlier compatibility/recovery work:** SSH startup fixes, the GPU selector/compatibility setup, and boot-gate infrastructure are separate from the online experiment. Ending the online test does not mean the cabinet is entirely factory stock.
- **Temporary online experiment:** private public-trust selection, test routing/bridge, cabinet WAN block, bounded responder, and pending-test state. The latest recorded recovery removed or cleared their active test effects.
- **Registration data:** positive tests could write real storage and SQL. Targeted original values were restored and independently checked after testing.
- **Retained privately:** source, test evidence, snapshots, logs, recovery artifacts, and necessary test secrets. They are not part of this document export.

## 8. Open work and next validation gates

1. **Physical checks:** inspect the CPU fan and relevant header; observe Start → Online during an authorized isolated retest. Record the actual screen result rather than infer it from the LIVE lamp.
2. **Follow-up coverage:** live-test the latest mixed-bundle handler and method2 decoder; investigate selectors>=3 and newly observed required exchanges without guessing successful replies.
3. **Card input:** when the menu is available, capture a controlled test swipe and establish how the cabinet represents and submits player identity. Keep real card data out of public logs.
4. **Player lifecycle:** implement and verify lookup, unknown-player behavior, profile creation/loading, save updates, and persistence across sessions. Do not claim success until the cabinet displays and subsequently reloads the expected data.
5. **Stability:** exercise reconnects, process restarts, reboots, clock behavior, incomplete replies, and server unavailability. Confirm recovery independently.
6. **Installation:** only after functional verification, design a maintainable persistent service with reproducible setup and recovery. Current live success depended on a supervised, temporary test arrangement.

## 9. Evidence and publication boundaries

This journal summarizes private evidence retained in the research workspace, including:

- `FINDINGS.md` in the earlier hardware review.
- `registration-investigation.md`, `wire-notes.md`, and `connection-test-plan.md`.
- `storage-analysis.md`, `registration-handler-analysis.md`, and `hardware-drill-plan.md`.
- `positive-test-plan.md`, `maintenance-plan.md`, and `session-handshake-analysis.md`.
- `FOLLOWUP-TEST-RUNBOOK.md` and `followup-regression-20261113.txt`.
- Native logs, offline test outputs, state comparisons, and the remote screenshot.

Those artifacts are not bundled here. Older research notes contain chronological states that were later superseded; the current-status section in this journal reflects the final recorded recovery.

This public document deliberately omits credentials, private keys, card data, cabinet/network identifiers, raw packet captures, database/device dumps, and proprietary executable/assets. Screenshots also need review before sharing. The research directory itself is **not** a publish-ready repository.

## 10. Ongoing logging convention

For every meaningful code, configuration, hardware, protocol, or recovery change:

- Append a dated entry; preserve failed approaches and corrections rather than rewriting them into an uninterrupted success story.
- Record what changed, why, what actually ran, and what was observed.
- Label evidence as offline, native-harness, live cabinet, or physical-user confirmation.
- Separate a planned test from an executed test, and startup from gameplay success.
- Record rollback and the resulting cabinet state. Update the top-level status after a meaningful milestone or recovery.
- Keep sensitive operational details in private notes; use a sanitized summary here.
- If a change cannot be reconstructed confidently, mark it unknown instead of inventing a date or result.

### Entry template

```markdown
### YYYY-MM-DD HH:MM UTC — Short change title

- Purpose:
- Changed: components/files and behavior (no secrets or identifiers)
- Scope: offline / temporary cabinet test / persistent change
- Verification performed:
- Observed result:
- Failed attempts or corrections:
- Recovery/rollback and final state:
- Remaining unknowns / next validation:
- Evidence reference: sanitized filename or future public commit link
```

### 2026-11-13 — Original player registry, payload loop and read-only bridge

- Scope: offline only; cabinet, gateway and account settings unchanged.
- Executed original product association/version initializers with modeled map storage. Actual selected associations:8→9,14/166→15,220→221. Tested1,792 byte-version combinations across seven IDs.
- Added a strict payload codec for14/v7,15/v7 and221/v0 and read-only local identity lookup. No network login response, implicit player creation or entitlement defaults.
- Compared the complete18-field player-info payload with the original field-reading loop, stopping before its database/application callback. Tested string/integer boundaries and identity conversion.
- Correction: high-bit UINT32 wire values become signed decimal intermediate text in this native path; expectations now reflect that. Harness bounds on truncated native reads are not evidence of native length validation.
- Verification:49 methods pass in the existing private research environment:30 standalone wire/store/compression and19 native registry/payload/synthetic-policy methods. An initial system-Python run failed three native imports because emulation dependencies were absent; rerunning with the existing research virtual environment passed.
- Public export adds six source files;113 source/dependency files total. No private executable, capture, full metadata, account data or database is included.
- Remaining: full application-handler semantics, actual physical swipe path, screen identity and save/reload. Green LIVE still does not establish login.
- Details: [PLAYER_WIRE.md](PLAYER_WIRE.md), [PLAYER_REPLY_POLICY.md](PLAYER_REPLY_POLICY.md).

### 2026-11-13 — Player dispatch, persistence errors and V2 login correction

- Continued offline after Bob requested all work that does not need physical presence. No cabinet, gateway or account changes.
- Traced generic attribute persistence and added five native handoff tests with explicitly modeled DB outcomes: initialization failure skips saving; save failures propagate. This is not real SQL/transaction or UI verification.
- Added five native dispatch methods.9/15/221 use the generic parser;184 uses dedicated handler0x089c3170. Caller supplies object/context; actual login key not yet established.
- Corrected incomplete login map: actual184 associations are183,166,203. Max versions183/184:3,203:0. Added registry assertions and768 version subcases, bringing selected version checks to2,560. The earlier15/v7 codec is not a universal player-login decoder.
- First184 probe hit an unmodeled C++ operation; tracing identified its special branch. Tests now stop explicitly at the dedicated handler entry rather than claiming complete decoding.
- Combined60 methods pass;116 exported source/dependency files. Private SQL/procedures, full metadata, binaries and account details remain excluded.
- Next offline target: dedicated184 decoder and request/object correlation. Physical login/save/reload still unverified. See [PLAYER_HANDOFF.md](PLAYER_HANDOFF.md).

### 2026-11-13 — Dedicated V2 player decoder through first save

- Continued into the original dedicated184 handler, rather than stopping after discovering its entry point. Versions0–3 now reach the first-save boundary with modeled strings, typed attributes, identity container and DB initialization; no database save is executed.
- Ten new tests cover basic and extended fields, binary/string/integer edges, course/count list values and native mismatch rejection0x482. Truncated reads are still harness-enforced checks, not claimed native validation.
- Correction: this typed path preserves unsigned32-bit values, unlike the older generic parser's intermediate signed text. Three legacy social fields are skipped before the first save.
- Nonempty-list testing initially stopped at an unmodeled indexed-key format; added only the two observed formatting variants. Actual reader/control-flow instructions remain unchanged.
- Total70 offline methods pass (40 native/private-input,30 standalone);118 source/dependency files. Full login, transaction effects, later saves and UI consumption remain unverified. Cabinet untouched.
- Details and reproduction: [PLAYER_HANDOFF.md](PLAYER_HANDOFF.md).

## 2026-11-13 — V2 codec, completion errors and request correlation

Added strict183/184 versions0–3 payload codecs, with exact field/range/length checks and conservative19-course bounds. Native comparisons cover all four versions and a19-course payload. Five completion tests continue through modeled save/cleanup to the original final status write: initialization failures skip saving, injected save errors survive, and native list mismatch returns0x482. No real database transaction is claimed.

Static tracing connects container ID/offset to outgoing request context, object name and storage category. Three response-builder regression methods preserve correlation headers, supported bundle order and encryption-key slot, while confirming unsupported player requests remain refused. No responder behavior was weakened.

Selected suite:87 methods passed (37 standalone,47 native/private-executable,3 private-metadata correlation). The37 standalone methods also passed in the reviewed public export. Duplicate test discovery and an unsupported synthetic request fixture were corrected during development; see [full contract, commands and limits](PLAYER_V2_CODEC.md). Public archive now has121 source/dependency files. Cabinet, gateway and account unchanged. Live swipe/login/save-reload remain unproven.

### Same-day follow-up — execute base request-queue correlation

Six additional native methods pass using synthetic database boundaries: absent backend0x433, missing outgoing queue0x461, missing container-map diagnostic branch, successful context population and binding/value width checks. The missing-map path stops before logging and does not establish its return status. No SQL, account or cabinet access occurred. See [queue follow-up](PLAYER_V2_CODEC.md#native-queue-follow-up-six-additional-methods). Selected coverage totals93 methods; archive122 source files.

### Nighthawk queue errors and caller status gate

Continued Nighthawk work at the owner's direction; Titan remains a separate possible future evaluation, not an active conversion. Four additional methods check query execute/fetch errors, partial request context on failure, and the caller's immediate status branch. Second-query failures return0x432. First-query diagnostic continuations are still deliberately bounded before logging. Selected coverage97 methods; source inventory remains122. See [queue-error limits](PLAYER_V2_CODEC.md#nighthawk-queue-error-follow-up). Cabinet unchanged.

## 2026-11-13 — ITNet worker entry points

The supplied decrypted Nighthawk executable matches the existing research executable byte-for-byte. REA/Hopper CLI installation was repaired and verified by successful static decompilation of the known request-context function; private binaries/pseudocode remain excluded. Initial120-second startup timed out; a documented600-second allowance succeeded after roughly9minutes. No MCP registration or cabinet change was made.

Focused static analysis now maps ITNetNowThread through pthread entry0x088f009b to worker0x0893fe2e, and ITNetBackgroundThread through entry0x088f013e to worker0x0891161a. Thread creation sites0x088e805d/0x088e823c and direct worker calls establish the association; it is not inferred from strings alone. Function ranges are corroborated by ELF unwind entries.

Startup and worker diagnostics identify candidate CID/network-device and registration/session gates. Their complete conditions and player-request routing are not yet proven. Next investigation follows scheduling, thread_handler assignment and completion delivery toward game/UI consumers. No new runtime tests or live-login claims are made in this mapping step. The supplied game.bin remains unidentified data.

## 2026-11-13 — ITNet completion polling

Seven new native offline test methods exercise the original request-completion reader with a synthetic database. Missing database and execute/fetch errors return 0; missing request row returns 3; pending status -1 becomes 0. Other signed status values are preserved except on channels 1, 2, 3 and 6, where the original classifier and reader reduce them to the boolean `status == 1`. The integrated classifier test covers 13 channel values and four statuses (52 combinations). Full 64-bit request identity binding is also checked.

Static tracing connects handler success/failure to completion values 1/3 and a conditional completion-persistence call. Handler failure takes precedence over the persistence result; successful handlers return the persistence result. This is not proof of an actual database commit. The outgoing enqueue path binds `thread_handler` from request options, so message ID alone does not establish the sending worker.

The selected suite passes 104 methods (97 previous plus seven completion-reader methods). Source inventory:123 files. Run the new subset with `.venv/bin/python -m unittest test_native_itnet_completion` from research; it requires the private matching executable and the existing queue fixture. Database operations remain modeled; no SQL runs. A generic status helper is identified, but its player/UI caller and the swipe-specific scheduling options remain unresolved. No live login, cabinet change, or Titan conversion is claimed.

## 2026-11-13 — bounded ITNet polling tests

Three further methods execute the original polling slice with modeled initialization/status/timing boundaries. Positive statuses 1, 2 and 3 all exit; nonpositive statuses retry. Initialization failure skips reading and preserves the existing output. A helper exit therefore cannot be counted as successful login. The full loop and player-specific caller remain unproven; see [handoff boundaries](PLAYER_HANDOFF.md#itnet-completion-versus-player-login-success).

Selected combined suite:107 methods. Public source inventory:124 files. No cabinet, account or gateway actions.

## 2026-11-13 — player-specific request routing

Identified concrete player-info183v3 and alternate-checkin166v7 configuration paths, both initializing handler1. Three new native methods verify bounded constructor initialization and48 generic enqueue-forwarding combinations. Cardless203v0 forwards the same options offset, but its configuration default and handler1's named-worker association are still unresolved. See [routing scope](PLAYER_HANDOFF.md#player-specific-scheduling-configuration).

Selected suite110 methods;125 exported source/dependency files. No cabinet, SQL, account or gateway operations; no live-login claim.

## 2026-11-13 — Now application queue range resolved (offline)

Reviewed the two pending native queue-selection tests and added three focused original-instruction methods. The previously found 13000–13999 selector is a separate queue category. The Now worker also calls an application selector with handler1 and an explicit message-ID range of1–9999, which includes player-info183 and alternate-checkin166. Generic enqueue binds the supplied message ID directly, without a12000/13000 offset. Other queue filters still apply.

The focused selection/routing/queue suite passes18 methods. Tests use synthetic receiver/caller state and stop before SQL; they do not establish live delivery, card login, or profile persistence. Cardless203's config default is still unresolved. No cabinet or network operations were performed by this offline investigation. These new files have not yet been published; earlier public test/source totals remain historical publication counts.

### Capture-only player request inspection

Added a strict offline inspector for183v3's20-byte player identity and166v7's8-byte check-in identity, with identifier-free summaries. Three standalone methods and one original-field-loop/private-metadata method pass; together with existing transport-correlation/player-refusal checks, seven methods pass. No response handler was enabled. A truthful player-not-found error code and its UI handling are not yet established; a zero-filled profile or unrelated captured error must not be substituted. New artifacts remain unpublished.

## 2026-11-13 — evening private card-test preparation

Fresh held-game registration SQL and repeated storage snapshots preserved before a new isolated test. The cabinet accepted private registration, encrypted session and follow-up synchronization; a fresh remote screenshot showed green LIVE. This does not prove player login. Existing cooling-system warning remains visible; CPU package measured37C, but motherboard fan tachometer readings were zero and physical inspection remains pending.

The arrival-time test extends the explicitly bounded host/bridge window up to two hours, with a reboot-to-recovery-gate timer and durable cabinet-only isolation. A captured update-diagnostic plus PING bundle exposed an unsupported combination; a narrow correction is being tested before service restart. No vendor traffic or fabricated player success is used. This is an active test, not a completed rollback or permanent deployment.

### Observed update-check and heartbeat bundle

A fresh controlled-test capture contained146v1 with its observed header flags followed by ordinary PING1v0. The prior single-message diagnostic decoder rejected it. Added only this exact bundle shape, returning an ordered durable-receipt ACK then PONG with the echoed byte; existing diagnostic singles remain supported. Unsupported tails/flags, truncation, missing/failed persistence and failed isolation guard produce no response. No player-login or update-success result is fabricated. The focused21-method suite passed, including native ACK acceptance/wire checks, encrypted correlation and unchanged player refusal. Deployment and live acceptance are separate parent-operated checks; this entry records the offline fix only.

Evening continuation: narrow diagnostic146+PING handling passed21 focused tests and was deployed during the isolated test. After same-boot service restart the cabinet sent another encrypted settings request, which was handled successfully. Card swipe/UI acceptance remains pending. The service is a bounded capture test; persistent registration recovery has not yet been performed.

## 2026-11-13 — physical card request reaches private service

A physical swipe displayed “Accessing Player Information.” The private service received and decrypted player-info183v3 flags0 with the expected20-byte opaque identifier, then observed a retry. Identifier/capture remain private. This proves the card-to-service path, not login: the player response handler remains unimplemented and emitted no reply, explaining the waiting screen. Work continues on native reply/error semantics.

### Bounded negative player reply prepared offline

Original common registry and version initializers now establish that ERROR6v0 is permitted for player-info183v3. Original decode maps wire20001 to client4c1, named “Data Not Found On Server”; the bounded original completion tail reports failure status3 with correlated request identifiers. C++ map storage, string-library operations and persistence callback are modeled; full SQL/network/UI execution is not proven. The explicit not-found UI branch located so far belongs to cardless ID/PIN, not the physical-card screen.

Added a disabled-by-default, exact-identity-pinned183v3 negative-response option. It emits only ERROR6v0/20001 after isolation guard and durable diagnostic capture; no profile, enrollment or success is fabricated. Unsupported identities/shapes remain refused. Twenty focused methods pass, covering actual private capture shape, encrypted correlation, negative cases, persistence/guard failures and native error semantics. This entry records offline readiness only; host integration, live acceptance and physical UI remain separate checks. New code/evidence is not published.

Player failure-response experiment: verified native ERROR6 code20001 maps to Data Not Found and failure completion. Added an opt-in exact-card diagnostic response; default player refusal remains.25 focused tests passed before controlled deployment. This creates no player profile and claims no successful login; awaiting physical screen result.

## Live player failure response,2026-11-13 21:42UTC
Bob reports “Player stats will not be available.” Private responder emitted pinned ERROR6/20001 for183v3; native log shows product-policy INVALID MSG RESPONSE183->6 then common message error20001 “Data Not Found On Server” and completed processing. Full card→service→failure UI path witnessed; not profile/login success and no official stats retrieval/loss claim. Child continues separate offline local-test-profile adapter investigation; running responder unchanged. Additional mixed235-headed bundle rejected (unsupported header shape), preserved privately for follow-up.

### Separate local profile adapter, not deployed

Prepared an explicit new local-only profile adapter using the existing durable store and strict184v3 codec. Enrollment is an explicit separate operation; request lookup never creates an account. Initial nickname, stable local check-in token, empty histories and zero monetary/registration claims are distinguished from official account data. Exact pin/version/shape checks and unchanged-initial-profile restrictions remain. No actual player was enrolled and the running service was not changed by this work.

Five new methods plus existing store/codec/native-completion coverage pass32 methods. Original product registry accepts183→184 and original dedicated184v3 handler reaches its modeled save/completion for this candidate. This is not actual cabinet persistence or login proof. Mandatory zero rating/bracket/country/quota values have unproven UI meaning; they must not be described as unlimited privileges or verified official values. Website provenance can be retained separately, but numeric display values are not silently converted into wire statistics without units/semantics evidence.

## 2026-11-13 — authorized statistics import
Authenticated read-only website inspection captured distinct All Courses bests, totals and averages with source/time provenance. Stored a private local profile linked to the observed card through a keyed digest; persistence verified after reopening the database. No account modifications. Personal values, credentials and cookies excluded from public artifacts. Website records are not yet mapped to cabinet protocol fields or deployed as a successful login response.

### Website counters separated from player-info fields

A separate read-only mapping adapter now extracts15 exact integral lifetime event counters from the provenance-bearing All Courses/Totals snapshot;14 other source labels remain unmapped. It preserves source column/time, rejects ambiguous values and never zero-fills missing fields. Four focused methods pass, including original native field-loop checks. High-bit UINT32 fields were rendered as signed decimal by that loop, so supported imported counters are conservatively limited to nonnegative signed31-bit range.

Native9v2 statistics contain66 fields and separate18-/9-hole best records;184v3 player-info has no lifetime best-score/GSP/distance totals. Website bests and averages are not substituted for rating or handicap. Raw distance units, handicap scale, round-count format, averaging window and full response completeness remain unproven. No store, key or running service was changed by this mapping work.

## Local profile response experiment
Prepared an explicit store-backed player-info184v3 response for the pinned card, retaining real website history separately rather than guessing numeric conversions. Local display name, stable local check-in token and explicit free-play policy are not official balances/ranks/entitlements. Native modeled handler and encrypted guarded response tests pass. Full cabinet database snapshot/catalog preserved before enabling the profile response. Awaiting physical name/menu result; round saving remains unimplemented.

## First physical local check-in
User confirmed “BOB is checked in” after the private184v3 profile response. Server then received8v1 statistics request, currently unsupported. Course entry did not automatically follow; fresh screen showed attract mode. Check-in is now physically confirmed; course entry, statistics delivery and round persistence remain separate unproven steps.

Correction to screen interpretation: user identified Course Records as the pre-course screen, not attract. Native game log confirmed repeated statistics requests while stalled. Added exact pinned stats8v1 unavailable response (ERROR6/20001), rather than fabricated statistics success;20 tests pass. Awaiting automatic retry and physical course-entry result.

Observed course entry followed retry exhaustion, not acceptance of the stats-unavailable patch: actual startup bundled stats, avatar, consumables and custom-bag requests; later retry bundled stats and game-start. Narrow adapter rejected those bundles. Game began the course with live features disabled and displayed communication/refund wording; no official wallet charge/refund was performed by the private server. Complete post-login bundle handling remains required.

### Post-checkin resource contracts verified offline

The extra startup requests are avatar, consumable inventory and custom golf bags—not contest status or refund operations. Three new methods pass: actual bundle shape/identity consistency, original resource reply/version policy plus common-error fallback, and the native consumable count gate. In particular, an all-empty consumable reply is invalid: native code requires at least two current selections (ball and tee), returning0x482 otherwise. Passing that first gate does not establish valid selection IDs or full reply behavior.

Website-selected appearance IDs are not yet proven equivalent to native IDs/ownership bitmaps. No guessed ownership, empty-inventory success, contest result or refund response was emitted. Exact bundled failure handling needs per-message correlation verification; successful resource delivery still needs actual inventory semantics. Running responder, host and private player store were unchanged by this offline work.

### Bundled resource correlation verified offline

The original incoming message loop passes zero-based positions, not byte offsets,
through its wrapper; native queue lookup uses those positions with the container
ID. Two new original-code tests cover this with modeled handler/database boundaries.
Added a strict ordered four-resource setup adapter and a failure reply per position.
Mixed identities, reordered messages, malformed tails and game-start retries remain
refused. Encrypted transport retains guard, durable capture and correlation checks.
27 focused tests pass. Changes are staged only: the running responder is unchanged,
and failure handling is not successful online play or score saving.

### Native custom-bag and consumable decoders exercised offline

Twelve focused methods pass (nine new, three existing). Original consumable decoder additionally requires at least31 ball inventory values and one tee inventory value. Native code supplies empty custom-slot defaults itself, but valid selected equipment IDs and quantity provenance remain unresolved; no consumable success response was enabled.

Original custom-bag decoder accepts16 empty lists through modeled save/completion, generating zero valid bags, empty names/descriptions and club sentinel9999. Added an explicit opt-in LOCAL empty-bag response builder; this does not claim the official account has no custom bags. Database/container boundaries are modeled, not actual persistence. Running responder and player store unchanged by this offline work.

Parent reviewed and tested the explicit local-empty custom-bag builder in an
ordered resource bundle: its218 reply stays in fourth position while unavailable
resources retain failure responses.16 focused tests pass. This opt-in helper is
not deployed and does not yet make the complete online setup successful.

### Complete statistics schema handoff checked offline

Four new tests exercise all66 statistics response fields through the original
field parser and attribute/save handoff with modeled database callbacks. The
complete-only encoder refuses missing fields and does not silently fill unknown
website statistics. Initialization/save failures propagate; truncation is stopped
by the harness. This is not SQL persistence or game UI verification.

Existing private source-table comparison resolves a prior uncertainty: the saved
Bests table is explicitly18-hole data. Native distance/score interpretation and
full historical-statistics coverage remain unverified; imported records and the
running server were not changed by this investigation.

### Native starter-avatar baseline recovered offline

Seven new tests exercise the complete avatar reply parser through modeled save,
all55 field mappings,64-bit masks, error propagation and native default writes.
A crucial distinction is now verified: custom-bag selection minus-one preserves
ordinary clubs; zero selects custom bag zero. The native handler itself grants
the base body-suit bit. Native normal-reset code supplies basic selections and
base availability, independently of website inventory IDs.

An explicit local starter-avatar policy and exact-field encoder are available
for review. They are not imported official equipment, do not copy unlock/demo
ownership, and have not been deployed or verified on the cabinet. Runtime,
private store, keys and official account were unchanged by this work.

### Native new-local statistics baseline

Recovered and tested the game's initial statistics values: both best-round fields
start at200 and handicap at100, while counters and opportunities start at0.
An explicit new-local-history policy now emits the complete statistics response,
with caller-supplied name/time. It does not overlay incomplete website history or
claim these are official records. Eight focused tests pass, including original
model binding, constructor writes and parser-to-modeled-save handoff. No live
runtime, database, or imported records were changed; cabinet/UI verification
remains separate.

### Local game-start receipt contract, offline

Five focused tests pass for strict game-start decoding, original native ACK/error
admission policy, guarded filesystem persistence, replay/conflict handling and
failure propagation. A private immutable journal must fsync before any ACK is
returned. This records a local start event only—not scores, a completed round,
charges or refunds. Mixed stats/start requires a separate explicit stats reply.

A later captured packet previously described as a standalone start is actually
start plus refund request plus game end. The new receipt helper rejects that whole
bundle; it does not acknowledge unimplemented wallet or end-of-round operations.
No running server, player store or cabinet changes were made by this work.

### Complete local starter setup integrated for controlled cabinet test

35 focused tests pass for encrypted setup, original-code starter resources and
statistics, guarded persistence, and idempotent durable game-start receipt.
The new statistics response uses actual native new-player defaults, not a partial
or fabricated historical import. Official website records remain preserved
separately; starter equipment is explicitly local and grants no paid inventory.
The responder was recovered after its earlier process/management tunnel ended,
with current boot/session/isolation verified, and relaunched as a bounded service.
Fresh screen shows PRESS START and green LIVE. User asked for one new login/course
entry test, stopping before a shot. Full setup acceptance and round saving remain
unverified. Refund/game-end bundles are not acknowledged as completed scores.

### Historical distance units resolved offline

Original incoming-statistics checks equate18000 raw units with500 yards for both
longest drive and putt, establishing inch-scale storage. Four tests pass, including
original compare branches and diagnostic text. Added a strict partial mapper for
18-hole lifetime website distances, preserving source and explicitly marking the
result as display-quantized—not recovered original sub-unit measurements. Score
interpretation and ambiguous best-count labels remain unmapped. No store/runtime
changes or mixing with the fresh-local statistics policy.

### Offline round-event persistence boundary

Identified separate hole-score, game-end and opaque session-data message schemas.
An end marker contains no score and also occurs after failed/refunded starts, so
it is not treated as a completed round. Original registry tests accept receipt
ACKs for these events, but no new network ACK route was enabled.

Added strict pinned raw-event inspection and private fsynced immutable receipts;
five tests pass. Score is signed16; session data remains opaque. Hole/session
header flags still require first live capture, and score aggregation, complete
round detection, historical-stat projection and reload remain unimplemented.
No runtime, wallet, player store or cabinet modifications were made by this work.

### Additional custom-club reply resolved

After the four-resource setup, the cabinet requested custom-club details for
slot-1. A new strict local baseline reply uses the original game's no-custom
component tuple0/0/0, traced through model binding, successful-load consumer,
setters and normal reset. Six tests pass including the original234 handler,
registry policy, exact request pinning, failure propagation and truncation.
This is local baseline equipment, not imported official ownership. The child
made no runtime changes; parent owns guarded deployment and live verification.

### Cabinet accepted initial setup; additional custom-club request discovered

Cabinet queue confirms successful statistics, avatar, consumables, custom bags,
and game-start receipt. It then requested custom-club detail for no-custom slot.
Native reset and consumer mapping verify the three-zero default tuple; six native
and18 focused integration tests pass. Exact pinned response deployed with guards.
The preceding attempt exhausted retries before this fix, then reached first tee;
that is not evidence of clean online setup. Awaiting physical error confirmation
and actual acceptance of the additional reply. No scores saved yet.

User then confirmed visible course and equipment, and explicitly reported no
Communication Error. This establishes clean user-visible course entry, correcting
the inference that the pending/refund-marker traffic necessarily meant an error
was shown. Additional233 reply acceptance is still not witnessed; score
persistence and reload remain the next milestones.

### Next test and private pro-shop scope

Local display name corrected to the user's requested name, verified after reopen
and in both profile/statistics projections. Existing round retains its loaded
name until next check-in. Durable capture-only round-event handling is staged
in the bounded test service;14 focused tests pass. User asked to complete one
hole and pause so actual score traffic can be verified before receipt ACKs or
aggregation are enabled.

User requested a private digital store. Existing cabinet Equipment UI already
provides selection and purchase entries; investigation targets its catalog,
local purchase/unlock ledger and equipment persistence—not a separate storefront
or real-money charges. Score saving remains the immediate priority.

### Private pro-shop investigation and actual equipment uploads

The existing cabinet has shop/pricing/selection UI; grey purchase controls also
have native home-edition, offline and before-first-shot gates, so missing backend
catalog is not yet established as their cause. Documented a local-only backend
sequence: validated catalog, separate ownership/selection/quantities, retry-safe
transaction ledger, receipt ACK after commit and reload verification.

Actual menu traffic contains avatar+consumable updates. Added a strict pinned
capture-only decoder; four tests pass including signed quantity deltas and native
ACK admission. Observed selected IDs do not directly match mask-bit assumptions,
so no entitlement grants, update ACKs, real charges or runtime changes were made.

### Native round-score semantics and session-block structure

Three offline original-instruction checks passed: ordinary score generation uses
cumulative strokes relative to accumulated par, another branch adjusts out the
current-hole par, and the session-data copy preserves all 444 bytes unchanged.
The native hole index is zero-based. Session data structurally contains a 12-byte
header and 18 24-byte hole slots; individual field meanings remain unfinished.
Do not sum repeated cumulative scores or treat an end notification as completed
round proof. The nearby leaderboard request is not the hole-report response;
actual transport receipt behavior remains a separate live verification.

### Partial session scorecard decoder

Original producer and independent aggregate-consumer evidence now identifies
per-hole strokes, par and Great Shot Points inside session blobs. Added a pure
partial decoder retaining unknown bytes; six combined checks pass, including
original native writes into a non-first player's final-hole slot. It does not
mark rounds complete or mutate lifetime history. Proposed local completion
cross-check requires a matching terminal hole report and full 18-slot scorecard
whose strokes-minus-par total agrees; an end notification alone remains invalid.

### Live cumulative scores acknowledged; bounded play window extended

Live reports after holes5 and6 were durably saved with cumulative scores−2 and−3;
original native code verifies relative-to-par semantics and zero-based hole
indices. Cabinet queue confirms receipt ACK acceptance. No report summation or
historical-source mutation. User continuing the round for end-record verification.
The owned bounded test bridge/server/recovery timer were renewed after inspecting
current state, keeping the same boot and isolation. Recovery remains owned and
required; the new window is not permanent WAN access.

### 2026-11-13 — isolated native home locker persistence

Traced the shipped home-edition equipment provisioning path and verified the
local cabinet catalog bounds through a narrowly scoped read. Added an opt-in
private selection journal with atomic receipts, replay deduplication, stale
update suppression, and explicit conflict handling. It stores selected club,
ball, and tee only; uploaded masks and purchase/consumption deltas do not grant
ownership. Separate native-home projections preserve the existing home policy,
without modifying imported website records or official accounts. Twelve offline
checks pass, including original inventory decoder and original home/consumption
routines with a documented modeled database-transfer boundary. Cabinet reload
integration remains unverified; no deployment was performed by this work.

### Best-round representation verified

Two additional original-native aggregate tests prove that the 18-hole best-round
field is signed relative-to-par (not stroke count), including retaining a better
negative score across subsequent rounds. Verified native hole-score category
counts and overlapping holes-in-one. A complete statistics reply must not turn
unmapped putts/distances/penalties into asserted zeros; documented the proven
partial-local aggregates and kept imported history separate. Also identified a
previously ambiguous session-header byte as player-outcome bits, not completion.

Added an offline full native replay alternative to partial statistic overlays:
original constructor and aggregate routines populate every bound numeric field
from complete raw session blobs, including putts, with executable provenance and
strict wire validation. Five focused tests pass. Fractional values unsupported
by the verified integer wire encoding refuse rather than silently truncate.
Actual completed-session projection and next-login rendering remain unverified.

### Local contest-results reply verified offline (2026-11-13)

Corrected a protocol interpretation: the pending request is for contest results,
not a numeric rating or handicap. Added an explicitly scoped local-no-contests
reply; it does not fabricate official rankings or prizes. Six focused checks
pass, including original native handler execution with modeled database save,
error propagation, pinned identity/version enforcement and bounded truncation.
The native empty reply saves a zero valid-contest count and returns success.
No cabinet deployment or UI result is claimed by this offline work.

### 2026-11-13 — First completed local round verified

The player completed an eighteen-hole round. Cross-checked its terminal report
against all eighteen session scorecard slots: 75 strokes on par 72, +3. Saved and
reopened the private local history database. Original-code aggregation produced
one completed round, eighteen holes and eighteen putts; the complete statistics
projection is persisted separately from the untouched imported website history.
Next-check-in rendering is not yet verified. Nine focused adapter/regression
checks pass for serving the completed projection with the corrected display name.
An additional original-code investigation identified message 35 as contest-results
retrieval, not numeric rating. An explicit no-local-contests reply passes six
focused tests; no official rankings or prizes are asserted.

### End-of-round equipment receipt scope (2026-11-13)

Inspected the completed round's equipment upload: selected clubs/balls remain
unchanged and every consumption delta is zero. Added a separate fail-closed,
matched-session end-receipt helper with durable deduplication, without changing
inventory balances or the selection journal. Five offline checks pass; the
successful storage case uses an explicit synthetic appearance authority.
The real upload changes the avatar body relative to both earlier uploads and the
existing baseline, so it remains rejected pending independent appearance-policy
resolution. Tests do not constitute authority to accept that real change.

Deployed the completed-local-statistics reload and exact witnessed pre-round
bundle response. Local contest results are empty by explicit policy; game-start
receipt is persisted before ACK. Extended durable raw-event receipts to the
observed terminal-score and end/session-data shapes, without treating an ACK as
proof of score aggregation or official upload. Seventeen focused round/start
checks passed; the actual stored profile and pre-round request also verified.
Asked for one new physical check-in to verify name/equipment/history reload.
Final combined appearance/consumables upload remains deliberately unacknowledged:
it contains an appearance change not yet supported by the selection-only ledger.

### Native cosmetic body policy clarified (2026-11-13)

Further original-code analysis shows the normal player reset grants every body
in the installed cosmetic catalog, not merely the minimal baseline's first body.
Three native tests prove catalog-bounded selection and rejection outside that
range. Body availability is not supplied in this network avatar message, so this
rule need not trust uploaded unlock masks. The observed end-of-round change is
only body selection; actual installed catalog count still needs independent
verification before accepting it under this local policy. The tests do not prove
why the user's selection changed, and no runtime policy was relaxed.

### Offline completion collector

Added a dry-run-first helper/CLI that extracts validated completed rounds from
explicit mixed plain captures, retains original evidence, and atomically stores
round summaries plus a native projection of every verified local round. Replays
are idempotent; conflicting or missing earlier history refuses. Four tests pass,
including close/reopen, source adoption and preservation of previous rounds.
No private runtime or profile store was changed by this implementation.

### Partial setup request correction
A subsequent course selection stalled because the cabinet requested only statistics and avatar equipment, then retried avatar alone. Existing handling accepted only the complete setup or statistics alone. Extended the pinned read-only setup path for those two observed shapes without course-specific rules. Nineteen focused tests pass; captured requests replay to the expected ordered replies. Bounded local service reloaded and readiness verified; physical course entry remains unverified.

Follow-up: the next attempt requested three resources, exposing that the initial exact-shape correction was too narrow. Shared read-only resource handling now supports all 15 nonempty ordered subsets of the four established resource types, retaining identity checks and rejecting duplicate/reordered requests. Twenty focused tests pass, including every subset. Bounded service reloaded; cabinet recovery still unverified.

### Latest physical outcome and remaining gaps

After the cached-resource fix, the user confirmed course entry. Fresh profile, setup and custom-club requests succeeded. This does not prove complete protocol coverage: standalone contest-results requests remain unsupported, and the final equipment-upload variant still needs integration. Score reports are durably captured; the offline completed-history collector is not an automatic runtime collector yet.

The user also reported missing Great Shot Points. Three received score reports had zero Great Shot Points while ordinary Golden Tee Points increased. Qualification rules versus game-setup effects remain unresolved; no points were fabricated or scoring rules patched.

This publication updates source and documentation only. It does not deploy a permanent service or change the cabinet's current test lifecycle.
