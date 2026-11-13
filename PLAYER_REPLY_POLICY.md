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
