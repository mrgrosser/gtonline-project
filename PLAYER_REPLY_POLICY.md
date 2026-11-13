# Native player reply policy: offline harness

## Verified scope — November 13, 2026

Six test methods execute the original general reply policy and lookup routines with an explicitly synthetic in-memory registry. No policy instructions or return values are patched. The existing runner models allocation/libc and forbids guest syscalls. There is no cabinet or network access.

The registry fixture supplies a balanced search-tree shape and uint16 association vectors. It does not execute the game's registry constructor, reproduce red-black insertion, or load real registry contents. Missing-node insertion and zero-valued association diagnostic paths are outside this test.

## Observations

- With synthetic associations 9:[8], 15:[14], 221:[220], matching request IDs pass and crossed IDs fail.
- Deliberately changing the entry for reply15 to request60000 makes14 fail and60000 pass. This control establishes table-driven behavior, not correctness of our candidate pairings.
- Empty association vectors reject replies.
- Multi-entry vectors find later entries, reject absent requests, and work across repeated calls. The policy's lookup resets its iteration cursor.
- The tested general branch accepts a matching table entry for version arguments0,1,7,8,254,255. **This is not payload-version support:** version validation must be established elsewhere.
- Generic ACK32767 is rejected for the tested player requests8,14,220.

## Reproduction

Requires the exact privately supplied analyzed ELF at `research/evidence/game-executable` and the existing emulation dependencies; executable not redistributed.

```sh
cd research
python3 -m unittest -v test_player_reply_policy
```

Six methods passed against the private ELF. These are not six live login tests. They do not establish real default registry contents, player field decoding, authentication, card behavior, profile rendering or persistence.

## Next offline work

1. Trace the actual product-specific registry initialization and its inputs; do not fill it from guessed metadata pairings and label that native proof.
2. Identify player reply deserializers, supported versions and minimum required fields, with malformed-input controls.
3. Build a fail-closed adapter to local storage only for evidence-backed formats. Website profile structure can inform local design but cannot establish cabinet wire format.

Physical checks remain fan/header inspection, Online menu state, controlled swipe, displayed identity and profile save/reload under the established isolation/recovery procedure. Cabinet state is unchanged.

## Follow-up: original product initialization and field parsing

The earlier synthetic-registry limitations above are historical. The original product association initializer (`0x089ad620`) and version initializer (`0x089ac86e`) now execute in an offline harness. They construct164 association entries. C++ map insertion/storage and diagnostic strings are modeled; original association-vector construction, lookup, matching, and version comparison execute unchanged. This is not a complete original C++ runtime or live application test.

Selected actual associations are8→9,14→15,166→15 and220→221. Alternate check-in166 shares reply15; its identity must not automatically be equated with a raw player/card identity. The separate version policy accepts unsigned byte versions up to the initialized maximum:8:1,9:2,14:7,15:7,166:7,220:0,221:0. All256 version values for each of these seven messages were checked (1,792 subcases). A permitted version is not proof of its payload schema.

Seven registry test methods pass, including crossed pairs, generic ACK rejection and repeated lookups. Missing-node insertion and zero-association diagnostic paths remain outside scope. The complete wrapper's generic-registry fallback is not exercised.

The metadata-driven player field loop is now tested separately; see [wire codec and limits](PLAYER_WIRE.md). This advances offline compatibility evidence, not authentication, UI or profile persistence on the cabinet.

## Subsequent dispatch/handoff correction

The selected earlier map is not exhaustive: actual reply184 pairs with183,166 and203 and uses a dedicated native handler, unlike9/15/221. The18-field generic-loop evidence remains specific to15/v7. New tests cover dispatcher selection and modeled database-error propagation; see [PLAYER_HANDOFF.md](PLAYER_HANDOFF.md). The public wire codec still rejects184.
