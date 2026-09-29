"""SPDX-License-Identifier: MIT. Explicitly projected API fixtures with offline replay."""
import hashlib
import json
import sqlite3
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode


class Tape:
    def __init__(self, path, request_fields, response_fields, query_fields=()):
        self.path = str(path)
        self.request_fields, self.response_fields, self.query_fields = tuple(request_fields), tuple(response_fields), tuple(query_fields)
        for fields in (self.request_fields, self.response_fields, self.query_fields):
            if any(not isinstance(k, str) or not k for k in fields) or len(set(fields)) != len(fields):
                raise ValueError("Projection fields must be unique nonempty strings")
        self.policy = json.dumps([self.request_fields, self.response_fields, self.query_fields])
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS metadata(id INTEGER PRIMARY KEY CHECK(id=1), policy TEXT)")
            db.execute("CREATE TABLE IF NOT EXISTS fixtures(key TEXT PRIMARY KEY, request TEXT, response TEXT)")
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT policy FROM metadata WHERE id=1").fetchone()
            if old and old[0] != self.policy:
                raise ValueError("Projection policy differs from this tape; create a new tape")
            db.execute("INSERT OR IGNORE INTO metadata VALUES(1,?)", (self.policy,))

    def project(self, value, fields):
        if type(value) is not dict:
            raise ValueError("Body must be a JSON object")
        result = {}
        for key in fields:
            if key in value:
                if type(value[key]) not in (str, int, float, bool, type(None)):
                    raise ValueError("Only explicitly selected scalar values may be recorded")
                result[key] = value[key]
        return result

    def request(self, method, url, body):
        parsed = urlsplit(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
            raise ValueError("URL must be HTTP(S), with no credentials or fragment")
        if method not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            raise ValueError("Unsupported method")
        query = urlencode(sorted((k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k in self.query_fields))
        safe_url = urlunsplit((parsed.scheme, parsed.netloc.lower(), parsed.path, query, ""))
        value = {"method": method, "url": safe_url, "body": self.project(body, self.request_fields)}
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(encoded.encode()).hexdigest(), encoded

    def record(self, method, url, body, status, response):
        if type(status) is not int or not 100 <= status <= 599:
            raise ValueError("Invalid HTTP status")
        key, request = self.request(method, url, body)
        result = json.dumps({"status": status, "body": self.project(response, self.response_fields)}, sort_keys=True, allow_nan=False)
        if len(request.encode()) + len(result.encode()) > 1048576:
            raise ValueError("Fixture exceeds 1 MiB")
        with sqlite3.connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT response FROM fixtures WHERE key=?", (key,)).fetchone()
            if old and old[0] != result:
                raise ValueError("Projected request is ambiguous; use a distinct tape or more match fields")
            db.execute("INSERT OR IGNORE INTO fixtures VALUES(?,?,?)", (key, request, result))
        return key

    def replay(self, method, url, body):
        key, _ = self.request(method, url, body)
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT response FROM fixtures WHERE key=?", (key,)).fetchone()
        if not row:
            raise ValueError("Fixture miss; network fallback is forbidden")
        return json.loads(row[0])

    def export(self):
        with sqlite3.connect(self.path) as db:
            return [{"request": json.loads(r[0]), "response": json.loads(r[1])} for r in db.execute("SELECT request,response FROM fixtures ORDER BY key")]
