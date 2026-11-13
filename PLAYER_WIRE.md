# Player payload codec and native field-loop checks

## Implemented scope

`research/player_wire.py` is a standalone, strict payload-only codec for request14/version7 (20-byte player identity), reply15/version7 (18 fields), and reply221/version0 (one availability byte). Field order/types were checked against the private metadata and the original field-reading loop. No metadata dump or real account data is included.

It rejects unsupported formats, missing/extra fields, out-of-range values, truncation and trailing bytes. Byte strings remain opaque; fixed identities retain their exact size. No card normalization, implicit enrollment, money/entitlement defaults, transport authentication or network reply is supplied.

`lookup_info_request` performs only a namespaced local lookup (`gt.player_id.v7`) and returns a stored snapshot or None. It never creates a player, changes a profile, authorizes login or emits a success response. The network responder is not wired to it. Alternate request166, stats reply9, cardless login203 and hole updates are not implemented by this codec.

## Native comparison, not a complete login

`emulate_player_payload.py` executes original field loop `0x08961bf0`, with explicitly supplied metadata vectors and modeled C++ string/libc operations. It stops before the database-dependent callback at `0x08961d97`. It does not execute database schema lookup, application state transitions or rendering.

Six native test methods cover the complete18-field payload, empty/maximum/binary strings, signed-byte and32-bit boundaries, raw20-byte identity conversion, availability values and truncated reads. The original identity path emits uppercase hexadecimal intermediate text. Although metadata calls certain fields unsigned32-bit, this loop formats high-bit values as signed decimal text:0xffffffff becomes -1. The wire codec preserves unsigned bits; downstream interpretation is still unknown. Initial comparison expectations were corrected after inspecting that formatting behavior.

**Truncated reads are stopped by a harness memory-read bound, not by demonstrated native validation.** These tests must not be cited as evidence that the game safely rejects malformed packets. The standalone codec independently rejects malformed input.

## Reproduction

Standalone tests, no private inputs:

```sh
cd research
python3 -m unittest test_player_wire test_player_store test_container_compression
```

Observed:30 methods pass (7 wire,15 store,8 compression).

Native tests additionally require the exact privately held analyzed executable at `research/evidence/game-executable` and the emulation dependencies:

```sh
python3 -m unittest test_native_player_registry test_native_player_payload test_player_reply_policy
```

Observed:19 methods pass (7 registry,6 payload,6 earlier synthetic policy). Combined:49 methods pass in the existing research virtual environment. The system Python lacks Unicorn/pyelftools: an initial combined invocation there failed imports, not protocol assertions. No dependency installation or clean-environment native reproduction is claimed.

## Remaining evidence needed

- Actual swipe/request sequence, selected version and flags; no assumption that14 rather than166 is used.
- Full database/application handler behavior and unknown-player handling.
- Correct meaning of money, bans, ratings and other fields; no invented values to manufacture success.
- On-screen identity, save, reconnect and reload under controlled isolation.

Physical preflight: inspect the reported CPU fan/header condition first. Then use the established cabinet-only isolation, management access and registration rollback procedure. Record menu state before a single controlled swipe. Keep raw card/account data private; publish only sanitized structural observations. Stop on unexpected behavior and verify restoration afterward. This document does not schedule or execute a cabinet test.

## Subsequent dispatch/handoff correction

The selected earlier map is not exhaustive: actual reply184 pairs with183,166 and203 and uses a dedicated native handler, unlike9/15/221. The18-field generic-loop evidence remains specific to15/v7. New tests cover dispatcher selection and modeled database-error propagation; see [PLAYER_HANDOFF.md](PLAYER_HANDOFF.md). The public wire codec still rejects184.
