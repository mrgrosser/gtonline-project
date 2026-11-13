# Container compression investigation — 2026-11-13

Offline only. No cabinet changes, sockets, routing, or live registration tests.

## Findings

The native selector extraction at `0x08958dc7` reads byte1 then byte0, shifts the combined little-endian word by6 and masks15. Correct selector: `((byte1 << 8 | byte0) >> 6) & 15`. The previous two-bit inspector aliased extended selectors onto methods0–3. Original-code execution matched all16 selectors.

Native receive dispatch normalizes selectors greater than2 to a separate mode3 path with an additional selector argument. That path remains unsupported; do not interpret selectors4/5/6 as plain/zlib/method2.

For modes1/2, `0x088f4884` inflates through `0x08a35d02`. Mode2 then invokes setup `0x08a58dba` and inverse transform `0x08a58e44`. Inflated data has n+1 column bytes followed by two big-endian uint32 indices (start and sentinel row); output has n bytes. The sentinel is treated as symbol256, after byte255. A stable frequency/prefix mapping builds the traversal table; starting at the recorded index, the routine emits n bytes.

`container_compression.py` independently implements this inverse mapping with bounds, index checks, traversal-cycle/terminal checks, strict zlib EOF/trailing-data checks and unsupported-selector rejection. The checks are intentionally stricter than blindly following native out-of-bounds behavior. `reencoding_relay.body` now delegates to this shared decoder, including the private responder's path. The older direct registration fixture remains scoped to methods0/1.

## Verification

- `test_container_compression.py`: 8 synthetic-only unittest methods pass, including independently generated forward-transform vectors, all selector values, malformed/truncated/trailing input, bounds and container integrity. Requires standard Python3 only; no private inputs.
- `emulate_container_compression.py`: 7 inverse-transform vectors matched the original routine; all16 selector cases matched the original instruction fragment. Original executable required privately. C++ zero-length allocation was modeled as a one-byte allocation after the initial allocator rejected the empty-vector case. No transform arithmetic is mocked.
- Focused combined suite:20 unittest methods pass (compression, private responder, follow-up wire, session transport, clock guard). Includes plaintext and encrypted method2 two-message settings bundles, unsupported extended selector rejection, and isolation-guard denial.
- These are synthetic/native-harness and saved-fixture checks, not a new live result. Existing parseable saved containers surveyed were modes0/1; no real method2 capture was available for validating this decoder's output in this pass.

## Remaining

Live method2 compatibility and mixed sync/file/banner retest remain unverified. Selectors>=3 need separate investigation. Player menu/card/profile validation still requires physical interaction. Keep fresh snapshots, isolation, and normal recovery requirements for any later live test.
