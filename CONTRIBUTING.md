# Helping stabilize the prototype

Start with README.md, then the latest entries in PROJECT_LOG.md and the exclusions in SOURCE_GUIDE.md. This is research source, not an installer. Do not run historical live-operation scripts on a cabinet without adapting and reviewing their guards and rollback.

## Code map

- `research/run_private_host.py`: bounded host listener, identity pinning, session resume and capture wiring.
- `research/private_session_responder.py`: encrypted request dispatch, reply correlation, durable receipt and isolation gates.
- `research/imported_profile_adapter.py` and `research/player_setup_bundle.py`: stored profile projection and partial/cached resource setup.
- `research/player_store.py`: SQLite identities and profiles.
- `research/local_home_selection_ledger.py`: local Home Edition equipment selections, not official entitlements.
- `research/round_event_journal.py`, `research/local_round_history.py`, `research/completed_round_collector.py`: raw receipts, validated completed rounds and offline collection.
- `research/native_local_stats_projection.py`: native statistics projection; requires private executable inputs.
- `research/local_contest_results_policy.py` and `research/local_pre_round_bundle.py`: implemented contest/pre-round contracts; standalone routing remains incomplete.

## Useful review targets

1. Request splitting, cached-resource subsets, retries and response ordering. See `test_player_setup_bundle.py`.
2. Standalone versus bundled contest/start requests without accidentally acknowledging unsupported writes.
3. End-of-round equipment-upload integration, identity/catalog validation and replay behavior.
4. Automatic completed-round collection without accepting aborted or conflicting rounds.
5. Great Shot Points qualification/setup behavior; zero values are observed, cause not established.

Preserve identity checks, durable-before-ACK ordering and isolation guards. Do not make unsupported messages succeed merely to hide a timeout. Separate native-harness evidence, offline tests, server observations and physical cabinet confirmation.

## Private dependencies

Captures, keys, player databases, protocol metadata, executable images and device/network identifiers are deliberately absent. Do not submit them in issues or pull requests. Synthetic fixtures and sanitized logs are preferred. The current system still depends on SSH and temporary test configuration; no turnkey boot path is claimed.
