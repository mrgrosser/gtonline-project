"""Offline local identity/profile store; not a cabinet protocol or auth service.

Caller must supply a private 32-byte identity HMAC key and explicitly enroll
players. Identity bytes are opaque: wire normalization is deliberately not
invented. No raw identity, key, official entitlement or payment data is stored.
"""
from contextlib import contextmanager
import hashlib
import hmac
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid


class StoreError(Exception): pass
class UnknownPlayer(StoreError): pass
class IdentityConflict(StoreError): pass
class RevisionConflict(StoreError): pass
class RetryConflict(StoreError): pass
class KeyMismatch(StoreError): pass


def text_value(value, name, maximum=128):
    if not isinstance(value, str) or not value or len(value.encode('utf-8')) > maximum or '\x00' in value:
        raise ValueError('Invalid '+name)
    return value


def canonical(value):
    if not isinstance(value, dict):
        raise ValueError('Profile must be a JSON object')
    # Reject non-string nested keys instead of JSON silently coercing them.
    def validate(item):
        if isinstance(item, dict):
            if any(not isinstance(k, str) for k in item):
                raise ValueError('JSON object keys must be strings')
            for child in item.values(): validate(child)
        elif isinstance(item, list):
            for child in item: validate(child)
        elif item is not None and type(item) not in (str, int, float, bool):
            raise ValueError('Unsupported JSON value')
    try:
        validate(value)
        result = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
        if len(result.encode('utf-8')) > 65536:
            raise ValueError('Profile exceeds 64 KiB')
        return result
    except (TypeError, RecursionError, UnicodeError) as error:
        raise ValueError('Invalid profile JSON') from error


class PlayerStore:
    def __init__(self, path, identity_key, clock=time.time):
        if not isinstance(identity_key, bytes) or len(identity_key) != 32:
            raise ValueError('A private 32-byte identity key is required')
        self._key = identity_key
        self._clock = clock
        path = Path(path)
        # Newly created database is private even with a permissive process umask.
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            if not path.is_file() or path.is_symlink():
                raise ValueError('Database must be a regular non-symlink file')
        else:
            os.close(fd)
        self.db = sqlite3.connect(str(path), isolation_level=None, timeout=5)
        self.db.row_factory = sqlite3.Row
        try:
            self.db.execute('PRAGMA foreign_keys=ON')
            self.db.execute('PRAGMA synchronous=FULL')
            check = hmac.new(identity_key, b'gtonline-player-store-key-check-v1', hashlib.sha256).hexdigest()
            with self._transaction():
                version = self.db.execute('PRAGMA user_version').fetchone()[0]
                if version == 0:
                    if self.db.execute("SELECT 1 FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' LIMIT 1").fetchone():
                        raise StoreError('Refusing an unrelated nonempty database')
                    for statement in (
                        'CREATE TABLE metadata (name TEXT PRIMARY KEY, value TEXT NOT NULL)',
                        'CREATE TABLE players (player_id TEXT PRIMARY KEY, display_name TEXT NOT NULL, created_at INTEGER NOT NULL)',
                        'CREATE TABLE identities (source TEXT NOT NULL, digest TEXT NOT NULL, player_id TEXT NOT NULL REFERENCES players(player_id), PRIMARY KEY(source,digest))',
                        'CREATE TABLE profiles (player_id TEXT PRIMARY KEY REFERENCES players(player_id), revision INTEGER NOT NULL CHECK(revision>=0), format_version INTEGER NOT NULL CHECK(format_version=1), payload TEXT NOT NULL, updated_at INTEGER NOT NULL)',
                        'CREATE TABLE receipts (player_id TEXT NOT NULL REFERENCES players(player_id), request_id TEXT NOT NULL, fingerprint TEXT NOT NULL, result TEXT NOT NULL, PRIMARY KEY(player_id,request_id))',
                    ):
                        self.db.execute(statement)
                    self.db.execute('INSERT INTO metadata VALUES (?,?)', ('identity_key_check', check))
                    self.db.execute('PRAGMA user_version=1')
                elif version != 1:
                    raise StoreError('Unsupported store schema; no automatic migration')
                stored = self.db.execute('SELECT value FROM metadata WHERE name=?', ('identity_key_check',)).fetchone()
                if stored is None or not hmac.compare_digest(stored[0], check):
                    raise KeyMismatch('Identity key does not match this database')
        except BaseException:
            self.db.close()
            raise

    @contextmanager
    def _transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _identity(self, source, identity):
        source = text_value(source, 'identity source', 64)
        if not isinstance(identity, bytes) or not 1 <= len(identity) <= 4096:
            raise ValueError('Identity must contain 1..4096 opaque bytes')
        tag = source.encode('utf-8')
        data = b'gtonline-identity-v1\0'+len(tag).to_bytes(2, 'big')+tag+identity
        return source, hmac.new(self._key, data, hashlib.sha256).hexdigest()

    def lookup_identity(self, source, identity):
        source, digest = self._identity(source, identity)
        row = self.db.execute('SELECT player_id FROM identities WHERE source=? AND digest=?', (source, digest)).fetchone()
        return row[0] if row else None

    def create_player(self, source, identity, display_name, profile=None):
        source, digest = self._identity(source, identity)
        display_name = text_value(display_name, 'display name')
        payload = canonical({} if profile is None else profile)
        player_id = uuid.uuid4().hex
        stamp = int(self._clock())
        with self._transaction():
            if self.db.execute('SELECT 1 FROM identities WHERE source=? AND digest=?', (source,digest)).fetchone():
                raise IdentityConflict('Identity already enrolled')
            self.db.execute('INSERT INTO players VALUES (?,?,?)', (player_id, display_name, stamp))
            self.db.execute('INSERT INTO identities VALUES (?,?,?)', (source, digest, player_id))
            self.db.execute('INSERT INTO profiles VALUES (?,0,1,?,?)', (player_id, payload, stamp))
        return player_id

    def bind_identity(self, player_id, source, identity):
        source, digest = self._identity(source, identity)
        with self._transaction():
            self._profile(player_id)
            row = self.db.execute('SELECT player_id FROM identities WHERE source=? AND digest=?', (source,digest)).fetchone()
            if row:
                if row[0] != player_id:
                    raise IdentityConflict('Identity belongs to another local player')
                return
            self.db.execute('INSERT INTO identities VALUES (?,?,?)', (source, digest, player_id))

    def _profile(self, player_id):
        text_value(player_id, 'player ID')
        row = self.db.execute('SELECT p.player_id,p.display_name,f.revision,f.format_version,f.payload,f.updated_at FROM players p JOIN profiles f USING(player_id) WHERE p.player_id=?', (player_id,)).fetchone()
        if row is None:
            raise UnknownPlayer('Unknown local player')
        return dict(player_id=row['player_id'], display_name=row['display_name'], revision=row['revision'],
                    format_version=row['format_version'], profile=json.loads(row['payload']), updated_at=row['updated_at'])

    def get_profile(self, player_id):
        return self._profile(player_id)

    def save_profile(self, player_id, request_id, expected_revision, profile, format_version=1):
        text_value(player_id, 'player ID')
        text_value(request_id, 'request ID')
        if type(expected_revision) is not int or not 0 <= expected_revision < 2**63-1:
            raise ValueError('Invalid expected revision')
        if type(format_version) is not int or format_version != 1:
            raise ValueError('Unsupported profile format')
        payload = canonical(profile)
        digest = hashlib.sha256((str(expected_revision)+':'+str(format_version)+':'+payload).encode('utf-8')).hexdigest()
        with self._transaction():
            prior = self.db.execute('SELECT fingerprint,result FROM receipts WHERE player_id=? AND request_id=?', (player_id,request_id)).fetchone()
            if prior:
                if not hmac.compare_digest(prior['fingerprint'], digest):
                    raise RetryConflict('Request ID reused for a different update')
                result = json.loads(prior['result'])
                result['replayed'] = True
            else:
                current = self._profile(player_id)
                if current['revision'] != expected_revision:
                    raise RevisionConflict('Profile revision changed')
                stamp = int(self._clock())
                self.db.execute('UPDATE profiles SET revision=revision+1,payload=?,updated_at=? WHERE player_id=?', (payload, stamp, player_id))
                result = self._profile(player_id)
                result['replayed'] = False
                self.db.execute('INSERT INTO receipts VALUES (?,?,?,?)', (player_id, request_id, digest, json.dumps(result, sort_keys=True)))
        # Return only after the transaction commits, including its retry receipt.
        return result
