# Offline player/profile persistence

Implemented November 13, 2026. This is a tested **local storage component**, not a cabinet login implementation or public authentication service. It is not connected to `PrivateResponder`, and it sends no game-protocol success replies.

## Implemented

`research/player_store.py` uses Python's standard-library SQLite, HMAC and JSON support. No new service, paid dependency or custom storage engine is needed.

- Explicit player enrollment with an opaque local UUID and display name.
- Opaque identity lookup. Unknown identities return `None` and do not create accounts.
- Additional identities can be attached to a player; an existing identity cannot be reassigned to another player through this API.
- Identity records store a source-scoped HMAC-SHA256 digest, not raw card bytes. The caller must supply the same private32-byte key when reopening the database; a wrong key is rejected. No normalization is guessed.
- Version1 local JSON profiles, a64KiB payload limit, and monotonically increasing revisions.
- Optimistic revision checks prevent stale saves. SQLite immediate transactions serialize competing writers; busy/write errors propagate rather than pretending success.
- Durable per-player request receipts make exact retries idempotent. Reusing a request ID for different content/revision fails. Retrying an older successful request returns its original result, not a later profile version.
- Profile update and receipt commit together. No successful result is returned before commit.
- Newly created database files use mode0600. Existing database permissions are the operator's responsibility. Stored profile content is ordinary SQLite data, **not encrypted at rest**; HMAC protects only the stored identity representation.
- Unknown schema versions and unrelated nonempty databases are refused; no automatic destructive migration.

## API

| Operation | Result |
| --- | --- |
| `PlayerStore(path, identity_key)` | Open/create the local store; enforce schema and key consistency |
| `create_player(source, identity_bytes, display_name, profile=None)` | Explicit enrollment; return local player ID |
| `lookup_identity(source, identity_bytes)` | Local player ID or `None`; never implicit enrollment |
| `bind_identity(player_id, source, identity_bytes)` | Attach another identity without transferring existing ownership |
| `get_profile(player_id)` | Name, local profile format, revision, payload and update time |
| `save_profile(player_id, request_id, expected_revision, profile, format_version=1)` | Committed result, with `replayed` indicating an exact retry |
| `close()` / context manager | Close the database connection |

`StoreError` subclasses distinguish unknown players, identity conflicts, stale revisions, conflicting retries and key mismatch. SQLite errors are not swallowed. Instances use SQLite's ordinary same-thread connection rule; independent workers need separate instances.

## Synthetic example

Run from `research/`, using only a temporary database and fictional data:

```python
import secrets
import tempfile
from pathlib import Path
from player_store import PlayerStore

with tempfile.TemporaryDirectory() as directory:
    database = Path(directory) / 'players.sqlite3'
    key = secrets.token_bytes(32)  # Keep the same key for this database's lifetime.
    with PlayerStore(database, key) as store:
        player = store.create_player('synthetic', b'demo-card', 'Demo Player')
        saved = store.save_profile(player, 'demo-save-1', 0, {'test_color': 'blue'})
        assert saved['revision'] == 1
    with PlayerStore(database, key) as store:
        assert store.lookup_identity('synthetic', b'demo-card') == player
        assert store.get_profile(player)['profile'] == {'test_color': 'blue'}
```

For a real deployment, provision/preserve the identity key separately from the database and session/signing keys; never use the public unit-test key. This release does not implement key rotation, identity enrollment authorization, a network API, or game-specific field validation.

## Verification

```sh
python3 research/test_player_store.py
```

**15 offline tests pass**, using temporary databases and synthetic identities. Coverage includes:

- Enrollment/unknown-player behavior, identity namespace separation, and ownership conflicts.
- Raw-identity/key absence from the newly created test database; mode0600 creation.
- Save/reopen persistence and wrong-key rejection.
- Exact retry behavior, canonical JSON key ordering, request-ID conflicts and player-scoped receipts.
- Stale saves across separate connections.
- Two concurrent subprocesses submitting the same save: one commit, one replay, one revision increment and one receipt.
- Injected receipt-write failure: profile revision/payload roll back together.
- Read-only write refusal: no success result and no revision increment.
- Forced process exit inside the actual save transaction, immediately before inserting its receipt: reopening preserves the prior profile.
- Malformed/oversized JSON, non-finite values, invalid revisions/formats, and unrelated/future-schema database refusal.

These are application/SQLite process-level tests, not proof against all storage hardware failures, power loss or filesystem corruption. They do not prove the cabinet accepts a profile response or has saved/reloaded a real player.

## Not yet implemented

- A verified card normalization rule and actual cabinet login wire adapter.
- Native player-info/stat response validation and complete game-specific field semantics.
- Rounds/hole-update modeling and deduplication from observed real message identifiers.
- Account administration, authentication, key rotation, schema migrations, automated backup/retention or multi-cabinet synchronization.
- Official balances, purchases, entitlements, player history or tournament integration.

The storage format is deliberately local and versioned. It must not be confused with a game message version. The next integration step is an evidence-backed mapping from actual card/player traffic to these operations, with no fabricated success response for unsupported requests.
