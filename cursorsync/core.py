"""SPDX-License-Identifier: MIT. Atomic paginated synchronization checkpoints."""
import hashlib
import json
import sqlite3


class SyncStore:
    def __init__(self, path):
        self.path = str(path)
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS streams(name TEXT PRIMARY KEY, cursor TEXT, done INTEGER NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS records(stream TEXT, id TEXT, body TEXT, PRIMARY KEY(stream,id))")
            db.execute("CREATE TABLE IF NOT EXISTS pages(stream TEXT, cursor_key TEXT, digest TEXT, PRIMARY KEY(stream,cursor_key))")

    def checkpoint(self, stream):
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT cursor,done FROM streams WHERE name=?", (stream,)).fetchone()
        return {"cursor": row[0], "done": bool(row[1])} if row else {"cursor": None, "done": False}

    def apply_page(self, stream, expected_cursor, next_cursor, records):
        if not isinstance(stream, str) or not 1 <= len(stream) <= 200:
            raise ValueError("Trusted stream namespace required")
        if any(c is not None and (not isinstance(c, str) or not 1 <= len(c) <= 1000) for c in (expected_cursor, next_cursor)):
            raise ValueError("Cursors must be null or bounded nonempty strings")
        if next_cursor is not None and next_cursor == expected_cursor:
            raise ValueError("Cursor must advance")
        if not isinstance(records, list) or len(records) > 1000:
            raise ValueError("A page must contain at most 1000 records")
        ids = set()
        for row in records:
            if type(row) is not dict or set(row) != {"id", "deleted", "data"}:
                raise ValueError("Each record requires exactly id, deleted, data")
            if not isinstance(row["id"], str) or not 1 <= len(row["id"]) <= 200 or type(row["deleted"]) is not bool:
                raise ValueError("Invalid record ID or tombstone")
            if row["id"] in ids:
                raise ValueError("Duplicate record ID within page")
            ids.add(row["id"])
        encoded = json.dumps({"next": next_cursor, "records": records}, sort_keys=True, separators=(",", ":"), allow_nan=False)
        if len(encoded.encode()) > 1048576:
            raise ValueError("Page exceeds 1 MiB")
        digest = hashlib.sha256(encoded.encode()).hexdigest()
        cursor_key = json.dumps(expected_cursor)
        with sqlite3.connect(self.path, timeout=10) as db:
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute("SELECT digest FROM pages WHERE stream=? AND cursor_key=?", (stream, cursor_key)).fetchone()
            if prior:
                if prior[0] != digest:
                    raise ValueError("Cursor replay has different contents")
                return {"duplicate": True}
            db.execute("INSERT OR IGNORE INTO streams VALUES(?,NULL,0)", (stream,))
            current = db.execute("SELECT cursor,done FROM streams WHERE name=?", (stream,)).fetchone()
            if current[1] or current[0] != expected_cursor:
                raise ValueError("Stale cursor or completed stream")
            if next_cursor is not None and db.execute("SELECT 1 FROM pages WHERE stream=? AND cursor_key=?", (stream, json.dumps(next_cursor))).fetchone():
                raise ValueError("Cursor cycle detected")
            for row in records:
                if row["deleted"]:
                    db.execute("DELETE FROM records WHERE stream=? AND id=?", (stream, row["id"]))
                else:
                    db.execute("INSERT INTO records VALUES(?,?,?) ON CONFLICT(stream,id) DO UPDATE SET body=excluded.body", (stream, row["id"], json.dumps(row["data"], sort_keys=True, allow_nan=False)))
            db.execute("INSERT INTO pages VALUES(?,?,?)", (stream, cursor_key, digest))
            db.execute("UPDATE streams SET cursor=?,done=? WHERE name=?", (next_cursor, int(next_cursor is None), stream))
        return {"duplicate": False, "count": len(records), "done": next_cursor is None}

    def records(self, stream):
        with sqlite3.connect(self.path) as db:
            return {r[0]: json.loads(r[1]) for r in db.execute("SELECT id,body FROM records WHERE stream=? ORDER BY id", (stream,))}
