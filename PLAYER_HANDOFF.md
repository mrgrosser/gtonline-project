# Player dispatch and persistence handoff

## Evidence boundaries

This follow-up executes original dispatcher and field-handoff control flow offline. Database initialization, attribute collection and save calls are modeled boundaries with explicit injected results. No SQL is executed, no cabinet/database/account is contacted, and no successful login is manufactured.

## Corrected login map

The earlier selected map was incomplete, not an exhaustive list of player protocols. The actual original product initializer also defines:

| Reply | Allowed request associations | Maximum reply version |
| --- | --- | --- |
| 15 | 14,166 | 7 |
| 184 | 183,166,203 | 3 |
| 9 | 8 | 2 |
| 221 | 220 | 0 |

Request183 maximum version is3; cardless-login203 maximum is0. The expanded registry tests check all256 byte-version values across ten selected message IDs (2,560 subcases). Request166 can associate with either15 or184. This does not say which response a particular live request needs.

Metadata names183/184 as the V2 player-info family. Reply184 metadata lists19,25,27 and30 fields for versions0,1,2,3 respectively, adding ranking, course/game limits and registration-related fields over time. This is schema evidence, not handler execution or permission to invent values. The strict public codec deliberately still rejects184.

## Native dispatch results

Five methods in `test_native_player_dispatch.py` execute the original product dispatcher at `0x089a9b5c`:

- Replies9,15,221 reach the generic parser boundary `0x089629ec`.
- Reply184 versions0–3 reach the dedicated handler boundary `0x089c3170`, not the generic parser.
- Generic parser errors and dedicated-handler errors propagate through the dispatcher.
- The generic path forwards a caller-supplied object name and context. Synthetic fixtures demonstrate forwarding, not the actual login object's name/category.
- Dispatch itself forwards version255 for reply15; separate registry/version checks must not be omitted.

The first attempt to run184 through a generic-only harness reached an unmodeled C++ operation. Static tracing then identified the dedicated handler; the corrected test intercepts its entry rather than pretending it ran successfully. At that checkpoint its decoder was not executed; the follow-up below reaches its first save. Full application effects remain unverified.

## Native field-to-store results

Five methods in `test_native_player_handoff.py` extend the earlier field loop past its former stop:

- All18 decoded reply15/v7 fields are forwarded as name/value pairs.
- Injected initialization failures prevent attribute forwarding and saving.
- Injected save failure code/detail propagate unchanged.
- Zero-code results continue to save; the final save detail replaces the initialization detail.
- Availability reply221's byte is forwarded as named text, not as a login decision.

Original loop/branch instructions run; constructors, the attribute container and database functions are modeled. The harness stops before destructors. Earlier native payload bounds remain harness-enforced, not proof of native malformed-input rejection.

Static inspection identifies `0x08a20612` as a common attribute-store helper that builds `SAVE_ATTRIB_CATEGORY` SQL. An existing private database backup contains the corresponding category procedures; no restore or procedure execution was performed. The generic native persistence mechanism exists, but the real login object key, transaction behavior and downstream UI consumer are not established by these tests.

## Reproduction and result

Requires the exact privately held analyzed ELF and emulation dependencies. Do not use blanket discovery of the historical research directory.

```sh
cd research
python3 -m unittest test_native_player_handoff test_native_player_dispatch test_native_player_registry
```

18 methods in this subset; the expanded combined offline suite has70 methods, including the unchanged30 standalone wire/store/compression methods. Tests use synthetic data only. No vendor source, SQL procedure body, full metadata or account evidence is redistributed.

## Next evidence-backed target

Trace the dedicated184 decoder and its caller's request-context/object-name construction. Do not substitute the older15 payload or auto-enroll cardless identities. Keep the responder unsupported/fail-closed until an appropriate response contract is established. Actual menu/swipe/screen/save-reload evidence still requires the operator, but this dedicated-handler investigation remains useful offline work.

## Dedicated184 decoder follow-up: versions0–3

`emulate_player_v2.py` now executes the dedicated original decoder through its first database-save entry, where execution stops **before saving**. Ten additional methods pass in `test_native_player_v2.py`:

- Version0's19 wire fields produce16 first-save attributes; the handler reads/skips the three legacy Facebook fields without forwarding them to that save. Their use elsewhere is not established.
- High-bit UINT32 values remain unsigned in typed attributes, unlike the signed intermediate text in the older generic15 path. Country remains signed.
- Versions1–3 decode daily/per-course/weekly limits and course/count lists. Version2 adds COTW limits; version3 adds registered email, grace-period time and registration flag. These are synthetic compatibility fixtures, not fabricated official entitlements.
- Empty lists and two-element lists, including unsigned edge values, reach the save boundary with expected indexed attributes.
- **Original code rejects mismatched course/count list lengths with status0x482 before the first save.** The harness checks the status written by native instructions and stops before cleanup. This is a genuine specific native rejection, not a general malformed-input safety claim.
- Empty/maximum/binary strings, signed/unsigned edges and truncation are exercised. Truncation is stopped by harness bounds, including modeled string copies; original universal length validation is not proven.

C++ string allocation/formatting, typed attribute insertion, raw20-byte identity container and DB initialization are modeled. Native wire readers and handler branches run. This does not validate identity-to-SQL serialization, actual database transactions, later save calls, all possible list lengths, live acceptance or UI login. The public responder and standalone codec still do not implement184.

```sh
cd research
python3 -m unittest test_native_player_v2
```

Observed combined result:70 offline methods (40 native/private-input,30 standalone). The first nonempty-list attempt stopped at an unmodeled indexed-name formatting call; explicitly modeling the two observed integer format strings enabled the list tests. No native branch or return value was patched to manufacture acceptance.
