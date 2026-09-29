"""SPDX-License-Identifier: MIT. Signed inbound-event persistence."""
import hashlib
import hmac
import json
import re
import sqlite3
import time


def signature(secret, timestamp, event_id, body):
    if not isinstance(secret, bytes) or len(secret) < 32:
        raise ValueError("Use a signing key of at least 32 bytes")
    if type(timestamp) is not int or not isinstance(event_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", event_id):
        raise ValueError("Invalid event ID or timestamp")
    return hmac.new(secret, f"{timestamp}.{event_id}.".encode() + body, hashlib.sha256).hexdigest()


class Inbox:
    def __init__(self, path, secret, clock=time.time, tolerance=300):
        signature(secret, 0, "init", b"")
        if type(tolerance) is not int or tolerance < 1:
            raise ValueError("Tolerance must be positive seconds")
        self.path, self.secret, self.clock, self.tolerance = str(path), secret, clock, tolerance
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS inbox(id TEXT PRIMARY KEY, digest TEXT NOT NULL, body BLOB NOT NULL, received INTEGER NOT NULL, processed INTEGER)")

    def accept(self, event_id, timestamp, body, supplied_signature):
        if not isinstance(body, bytes) or len(body) > 1048576:
            raise ValueError("Body must be bytes, maximum 1 MiB")
        expected = signature(self.secret, timestamp, event_id, body)
        if abs(self.clock() - timestamp) > self.tolerance:
            raise ValueError("Signature timestamp outside accepted window")
        if not isinstance(supplied_signature, str) or not re.fullmatch(r"[0-9a-f]{64}", supplied_signature) or not hmac.compare_digest(expected, supplied_signature):
            raise ValueError("Invalid signature")
        # Parse only after authenticating the original bytes.
        payload = json.loads(body)
        if not isinstance(payload, dict):
            raise ValueError("Event body must be a JSON object")
        checksum = hashlib.sha256(body).hexdigest()
        with sqlite3.connect(self.path, timeout=10) as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT digest FROM inbox WHERE id=?", (event_id,)).fetchone()
            if old:
                if old[0] != checksum:
                    raise ValueError("Event ID reused with different bytes")
                return {"id": event_id, "duplicate": True}
            db.execute("INSERT INTO inbox VALUES(?,?,?,?,NULL)", (event_id, checksum, body, int(self.clock())))
        return {"id": event_id, "duplicate": False}

    def pending(self, limit=100):
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("Limit must be 1–1000")
        with sqlite3.connect(self.path) as db:
            return [{"id": r[0], "payload": json.loads(r[1]), "received": r[2]} for r in db.execute("SELECT id,body,received FROM inbox WHERE processed IS NULL ORDER BY received,id LIMIT ?", (limit,))]

    def mark_processed(self, event_id):
        # Call after successful work. This is not an atomic remote-effect boundary.
        with sqlite3.connect(self.path) as db:
            result = db.execute("UPDATE inbox SET processed=? WHERE id=? AND processed IS NULL", (int(self.clock()), event_id))
            return result.rowcount == 1
