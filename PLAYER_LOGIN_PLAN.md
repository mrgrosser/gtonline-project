# Player login: offline map and validation plan

Prepared November 13, 2026; updated after the offline storage implementation. **The local identity/profile store now exists and passes15 offline tests; cabinet login remains unimplemented/unverified.** See [storage API and tests](PLAYER_STORE.md).

## Candidate message families

These names/versions were found in local protocol metadata. They are leads, not proof that a physical card swipe will use a particular version or that a guessed response will be accepted.

| ID | Metadata name | Listed versions |
| --- | --- | --- |
| 14 | GOLF_PLAYER_INFO_REQUEST | 0–7 |
| 15 | GOLF_PLAYER_INFO_RESPONSE | 0–7 |
| 8 | GOLF_PLAYER_STATS_REQUEST / V1 | 0–1 |
| 9 | GOLF_PLAYER_STATS_RESPONSE | 0–2 |
| 22 | GOLF_PLAYER_HOLE_DATA | 0–2 |
| 25 | GOLF_SET_PLAYER_NAME | 0 |
| 203 | GOLF_CARDLESS_LOGIN | 0 |
| 220 | GOLF_CHECK_CARDLESS_ID_REQUEST | 0 |
| 221 | GOLF_CHECK_CARDLESS_ID_RESP | 0 |

No complete metadata dump or actual card/profile data is included. A trial native response-policy probe for the player messages encountered an unmapped memory read with an uninitialized object; unlike some earlier message checks, it needs more object setup. It supplies **no response-acceptance evidence**. We must distinguish a listed request/response family from a verified wire contract.

## Proposed minimal persistence model

Use a local SQLite database through Python's standard library for the first single-cabinet prototype, instead of creating a custom storage engine. This local component is now implemented in `research/player_store.py`; it has not been deployed or connected to cabinet login. No performance claim is made.

- `players`/`profiles`: implemented opaque local player ID, display name, timestamps, local JSON profile and revision.
- `identities`: source/type plus a keyed digest of normalized card identity, mapped to a local player. The normalization rule awaits captured wire evidence. The digest key must be separate from session/signing keys; real card values must not enter public logs.
- `profiles`: explicit versioned fields supported by the observed cabinet request, linked to player ID. Do not invent official account balances, entitlements or history.
- `rounds` and `hole_updates`: local game/session ID, revision/order information, and a supported deduplication key. Determine retry identity from actual traffic before selecting uniqueness constraints.
- Transactions must commit accepted updates before acknowledging persistence. Conflicting, malformed and unknown versions must fail explicitly rather than silently becoming empty success responses.

Keep a bounded diagnostic record of message type/version and validation outcome, not raw identity. Back up the database before schema changes. Test duplicate saves, interrupted commits, server restarts and profile reload before treating persistence as working.

## Next hands-on test

1. Physically inspect the CPU fan/header and resolve any actual cooling fault.
2. Under the existing isolated test/recovery procedure, observe Start → Online and record the exact menu/error state.
3. When the menu permits it, perform one controlled swipe using an operator-selected test identity. Keep its data private.
4. Record the actual message ID, version, flags, field boundaries, request order and response-policy requirements. Establish unknown-player behavior before building profile success responses.
5. Implement one evidence-backed identity/profile path, then verify displayed identity, a saved change, a reconnect and subsequent reload.
6. Restore/verify cabinet registration state and remove test isolation as usual.

Offline decoding can proceed without the operator present. The screen, swipe and persistence results cannot be inferred from a green LIVE indicator.

## Native player-policy investigation update

Static inspection explains the prior uninitialized-object failure: general replies pass through a per-context message registry (`0x0897a758`) and request/reply association logic (`0x0897a088`). Earlier special-case ACK/control policy checks do not establish these general player paths. This pass did not initialize or validate that registry, so14→15 and8→9 remain metadata-derived candidates, not native acceptance results.

## Follow-up: initialized synthetic registry

Six native-policy test methods now pass with a deliberately synthetic registry. This resolves the harness's uninitialized-context obstacle and demonstrates table-driven matching, negative cases, and cursor reset, but **does not establish the game's actual registry contents or candidate player pairings**. See [scope and results](PLAYER_REPLY_POLICY.md).

## Follow-up: original product initialization and field parsing

The earlier synthetic-registry limitations above are historical. The original product association initializer (`0x089ad620`) and version initializer (`0x089ac86e`) now execute in an offline harness. They construct164 association entries. C++ map insertion/storage and diagnostic strings are modeled; original association-vector construction, lookup, matching, and version comparison execute unchanged. This is not a complete original C++ runtime or live application test.

Selected actual associations are8→9,14→15,166→15 and220→221. Alternate check-in166 shares reply15; its identity must not automatically be equated with a raw player/card identity. The separate version policy accepts unsigned byte versions up to the initialized maximum:8:1,9:2,14:7,15:7,166:7,220:0,221:0. All256 version values for each of these seven messages were checked (1,792 subcases). A permitted version is not proof of its payload schema.

Seven registry test methods pass, including crossed pairs, generic ACK rejection and repeated lookups. Missing-node insertion and zero-association diagnostic paths remain outside scope. The complete wrapper's generic-registry fallback is not exercised.

The metadata-driven player field loop is now tested separately; see [wire codec and limits](PLAYER_WIRE.md). This advances offline compatibility evidence, not authentication, UI or profile persistence on the cabinet.
