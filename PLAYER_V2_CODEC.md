# V2 player codec, completion and correlation

## Verified offline — November 13, 2026

The standalone payload codec now supports request183 and reply184 versions0–3. This is not a network login implementation. Requests14,183,166 and203 remain rejected by the network responder. No cabinet, gateway or account changes were made.

### Strict wire contract

- Request183: exactly 20 opaque identity bytes. Its schema is metadata-backed, not a tested native request serializer.
- Reply184 version0: the existing 18-field player-info prefix plus current monthly ranking.
- Version1 adds daily/per-course limits, course IDs, corresponding games-played counts and weekly limits/counts.
- Version2 adds COTW daily limits/counts.
- Version3 adds registered email, grace-period expiration and registration flag.
- Exact version-specific field sets, integer ranges/types, byte-string lengths, complete reads and no trailing bytes are enforced. No guessed entitlement defaults or identity normalization are supplied.
- Course/count list lengths must agree. The adapter supports zero through19 entries. **19 is a conservative tested adapter ceiling, not a claimed protocol maximum.** The original handler takes a separate diagnostic path above19; that path remains unverified.

Seven standalone methods compare all four versions with independently assembled extension bytes, check every truncation and trailing data, exact fields, list consistency/limits, numeric types/ranges and opaque request identities. Two added native methods compare public-encoder output with original decoder attributes and exercise19 courses.

### Native completion boundary

Five new methods continue original handler control flow past a **modeled** database save to the final result write, before the function epilogue. All four tested versions attempt one modeled save on success. Initialization failure skips decoding and saving; injected save errors and details propagate to the final status. Native mismatched course/count rejection returns0x482 before saving. Zero-code status details also survive.

Database initialization/save, attribute containers, strings and destructors are models. This proves neither an actual SQL transaction nor real cleanup. Harness read bounds remain separate from demonstrated native validation. No native branch was patched to manufacture acceptance.

### Request correlation: static evidence and builder regressions

Static inspection of the base request-context routine at0x08967488 shows two lookups: container ID plus container offset resolve message ID/version and request ID in `container_map`; request ID then resolves object name, storage category and completion status in `itnet_message_out_q`. The outer reply path passes that resolved context into reply-policy checking and product dispatch.

This is a static trace, not an executed database-query test or proof for every derived implementation. It explains why decoding a valid player identity does not alone establish its destination object. The precise runtime meaning of every container-offset value is not independently established.

Three regression methods verify that existing response builders preserve container ID, selected header bytes, encryption-key slot and supported bundle reply order. A mixed supported bundle retains its order both plaintext and encrypted with either synthetic key slot. Unsupported player requests still fail closed. These tests require private metadata at import, but no cabinet connection, capture or game executable.

### Reproduction and counts

Selected combined result: **87 methods passed**:

- 37 standalone:7 old wire,7 V2 wire,15 store,8 compression.
- 47 native/private-executable methods:6 payload,8 registry,6 synthetic policy,5 handoff,5 dispatch,12 V2 decoder,5 completion.
- 3 correlation methods requiring private metadata.

Standalone:

```sh
cd research
python3 -m unittest test_player_wire test_player_wire_v2 test_player_store test_container_compression
```

Combined, only with independently supplied private research inputs:

```sh
python3 -m unittest test_player_wire test_player_wire_v2 test_native_player_payload test_native_player_registry test_player_reply_policy test_player_store test_container_compression test_native_player_handoff test_native_player_dispatch test_native_player_v2 test_native_player_v2_completion test_player_response_correlation
```

During development, importing a TestCase class into the completion module caused duplicate discovery; switching to a module import removed the duplicates. An initial correlation fixture used unsupported235 versions and was correctly refused; the fixture was corrected to supported235/version2 rather than weakening the responder.

Remaining gaps include real queue/database behavior, identity-to-SQL mapping, application/UI consumption, actual swipe request selection, end-to-end login and save/reload. Neither the website account nor the cabinet was used to fabricate missing wire evidence.
