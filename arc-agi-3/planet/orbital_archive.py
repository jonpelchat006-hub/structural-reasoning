"""Immutable, content-addressed learning bundles in a dedicated SQLite store.

Objects are data, never executable commands. Retrieved bundles are candidates,
not current observations. This does not touch the legacy spiral-drive archive.
"""
import hashlib
import json
from pathlib import Path
import sqlite3
import zlib


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


class OrbitalArchive:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existed = self.path.exists()
        self.db = sqlite3.connect(str(self.path))
        self.db.execute('PRAGMA synchronous=FULL')
        if existed:
            version = self.db.execute('PRAGMA user_version').fetchone()[0]
            if version != 1:
                self.db.close()
                raise ValueError('not a supported orbital archive; existing file untouched')
        else:
            with self.db:
                self.db.executescript('''
                    CREATE TABLE objects(id TEXT PRIMARY KEY, payload BLOB NOT NULL);
                    CREATE TABLE bundles(id TEXT PRIMARY KEY, game_id TEXT NOT NULL,
                        instance_id TEXT NOT NULL, level INTEGER NOT NULL, attempt INTEGER NOT NULL,
                        reason TEXT NOT NULL);
                    CREATE TABLE observations(run_id TEXT NOT NULL, observation_id TEXT NOT NULL,
                        ordinal INTEGER NOT NULL, payload_id TEXT NOT NULL,
                        PRIMARY KEY(run_id, observation_id), UNIQUE(run_id, ordinal));
                    PRAGMA user_version=1;
                ''')

    def put(self, value):
        raw = encoded(value)
        if len(raw) > 64_000_000:
            raise ValueError('archive object exceeds 64 MB bound; nothing discarded')
        key = hashlib.sha256(raw).hexdigest()
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO objects VALUES (?,?)', (key, zlib.compress(raw)))
        return key

    def get(self, key):
        row = self.db.execute('SELECT payload FROM objects WHERE id=?', (key,)).fetchone()
        if row is None:
            raise KeyError(key)
        raw = zlib.decompress(row[0])
        if hashlib.sha256(raw).hexdigest() != key:
            raise ValueError('archive integrity mismatch')
        return json.loads(raw)

    def save_bundle(self, bundle):
        for field in ('game_id', 'instance_id', 'reason'):
            if not isinstance(bundle.get(field), str) or not bundle[field]:
                raise ValueError('bundle identity/reason required')
        for field in ('level', 'attempt'):
            if type(bundle.get(field)) is not int or bundle[field] < 0:
                raise ValueError('nonnegative bundle level/attempt required')
        key = self.put(bundle)
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO bundles VALUES (?,?,?,?,?,?)',
                            (key, bundle['game_id'], bundle['instance_id'], bundle['level'],
                             bundle['attempt'], bundle['reason']))
        return key

    def append_observation(self, run_id, observation_id, ordinal, payload):
        key = self.put(payload)
        previous = self.db.execute('SELECT ordinal,payload_id FROM observations WHERE run_id=? AND observation_id=?',
                                   (run_id, observation_id)).fetchone()
        if previous:
            if previous != (ordinal, key):
                raise ValueError('conflicting replay observation')
            return False
        with self.db:
            self.db.execute('INSERT INTO observations VALUES (?,?,?,?)', (run_id, observation_id, ordinal, key))
        return True

    def observations(self, run_id):
        return [self.get(row[0]) for row in self.db.execute(
            'SELECT payload_id FROM observations WHERE run_id=? ORDER BY ordinal', (run_id,))]

    def retrieve(self, *, game_id=None, limit=8):
        if type(limit) is not int or not 1 <= limit <= 64:
            raise ValueError('retrieval limit must be 1..64')
        if game_id is None:
            rows = self.db.execute('SELECT id FROM bundles ORDER BY rowid DESC LIMIT ?', (limit,))
        else:
            rows = self.db.execute('SELECT id FROM bundles WHERE game_id=? ORDER BY rowid DESC LIMIT ?', (game_id, limit))
        return [dict(bundle_id=row[0], bundle=self.get(row[0]), status='retrieved_candidate',
                     adds_observations=False, execution_authorized=False) for row in rows]

    def close(self):
        self.db.close()
