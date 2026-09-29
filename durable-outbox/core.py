"""SPDX-License-Identifier: MIT. Leased local work queue with dead letters."""
import json
import sqlite3
import time
import uuid


class Outbox:
    def __init__(self, path, clock=time.time, max_attempts=3):
        if type(max_attempts) is not int or not 1 <= max_attempts <= 20:
            raise ValueError("max_attempts must be 1–20")
        self.path, self.clock, self.max_attempts = str(path), clock, max_attempts
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, payload TEXT NOT NULL, state TEXT NOT NULL, available REAL NOT NULL, attempts INTEGER NOT NULL, lease TEXT, until REAL, error TEXT)")

    def enqueue(self, key, payload):
        with sqlite3.connect(self.path, timeout=10) as db:
            db.execute("BEGIN IMMEDIATE")
            return self.enqueue_in(db, key, payload)

    def enqueue_in(self, db, key, payload):
        """Insert in the caller's active transaction on this same database."""
        if not db.in_transaction:
            raise ValueError("Caller must begin a transaction before enqueue_in")
        if not isinstance(key, str) or not 1 <= len(key) <= 100:
            raise ValueError("Key must be a nonempty string, maximum 100 characters")
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        if len(encoded.encode()) > 1048576:
            raise ValueError("Payload exceeds 1 MiB")
        old = db.execute("SELECT payload FROM jobs WHERE id=?", (key,)).fetchone()
        if old and old[0] != encoded:
            raise ValueError("Idempotency key conflicts with existing payload")
        if not old:
            db.execute("INSERT INTO jobs VALUES(?,?,'queued',?,0,NULL,NULL,NULL)", (key, encoded, self.clock()))
        return key

    def claim(self, lease_seconds=60):
        if type(lease_seconds) is not int or not 1 <= lease_seconds <= 3600:
            raise ValueError("Lease must be 1–3600 seconds")
        now = self.clock()
        with sqlite3.connect(self.path, timeout=10) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("UPDATE jobs SET state='dead',lease=NULL,until=NULL,error='Lease expired at attempt limit' WHERE state='leased' AND until<=? AND attempts>=?", (now, self.max_attempts))
            row = db.execute("SELECT id,payload,attempts FROM jobs WHERE (state='queued' AND available<=?) OR (state='leased' AND until<=? AND attempts<?) ORDER BY available,id LIMIT 1", (now, now, self.max_attempts)).fetchone()
            if not row:
                return None
            lease = str(uuid.uuid4())
            db.execute("UPDATE jobs SET state='leased',lease=?,until=?,attempts=attempts+1 WHERE id=?", (lease, now + lease_seconds, row[0]))
        return {"id": row[0], "payload": json.loads(row[1]), "lease": lease, "attempt": row[2] + 1}

    def finish(self, key, lease, error=None):
        if error is not None and (not isinstance(error, str) or len(error) > 500):
            raise ValueError("Error must be a string of at most 500 characters")
        with sqlite3.connect(self.path, timeout=10) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT attempts FROM jobs WHERE id=? AND state='leased' AND lease=? AND until>?", (key, lease, self.clock())).fetchone()
            if not row:
                raise ValueError("Lease is missing, expired or owned by another worker")
            state = "done" if error is None else "dead" if row[0] >= self.max_attempts else "queued"
            db.execute("UPDATE jobs SET state=?,available=?,lease=NULL,until=NULL,error=? WHERE id=?", (state, self.clock() + min(2 ** row[0], 3600), error, key))
        return state

    def inspect(self):
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            return [dict(row) for row in db.execute("SELECT id,state,attempts,available,error FROM jobs ORDER BY id")]
