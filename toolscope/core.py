"""SPDX-License-Identifier: MIT. One-use resource-scoped tool capabilities."""
import base64
import hashlib
import hmac
import json
import sqlite3
import time
import uuid


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


class Capabilities:
    def __init__(self, path, secret, clock=time.time):
        if not isinstance(secret, bytes) or len(secret) < 32:
            raise ValueError("Signing key must be at least 32 bytes")
        self.path, self.secret, self.clock = str(path), secret, clock
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS used(nonce TEXT PRIMARY KEY, consumed INTEGER NOT NULL)")

    def issue(self, subject, tool, resource, ttl=60):
        if any(not isinstance(v, str) or not 1 <= len(v) <= 200 for v in (subject, tool, resource)):
            raise ValueError("Subject, tool and resource must be nonempty bounded strings")
        if type(ttl) is not int or not 1 <= ttl <= 3600:
            raise ValueError("TTL must be 1–3600 seconds")
        payload = {"domain": "toolscope-v1", "subject": subject, "tool": tool, "resource": resource,
                   "expires": int(self.clock()) + ttl, "nonce": str(uuid.uuid4())}
        body = base64.urlsafe_b64encode(canonical(payload)).decode().rstrip("=")
        sig = hmac.new(self.secret, body.encode(), hashlib.sha256).hexdigest()
        return body + "." + sig

    def consume(self, token, subject, tool, resource):
        if not isinstance(token, str) or len(token) > 4096:
            raise ValueError("Invalid capability")
        try:
            body, sig = token.split(".")
            expected = hmac.new(self.secret, body.encode("ascii"), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected.encode(), sig.encode("ascii")):
                raise ValueError("Invalid capability signature")
            payload = json.loads(base64.b64decode(body + "=" * (-len(body) % 4), altchars=b"-_", validate=True))
        except (ValueError, UnicodeError) as exc:
            raise ValueError("Invalid capability") from exc
        if payload["domain"] != "toolscope-v1" or payload["expires"] <= self.clock():
            raise ValueError("Capability expired or wrong domain")
        if (payload["subject"], payload["tool"], payload["resource"]) != (subject, tool, resource):
            raise ValueError("Capability scope mismatch")
        try:
            with sqlite3.connect(self.path, timeout=10) as db:
                db.execute("INSERT INTO used VALUES(?,?)", (payload["nonce"], int(self.clock())))
        except sqlite3.IntegrityError as exc:
            raise ValueError("Capability already consumed") from exc
        return payload

    def dispatch(self, token, subject, tool, resource, handlers):
        if tool not in handlers:
            raise ValueError("Tool is not registered")
        self.consume(token, subject, tool, resource)
        # Fail closed: handler errors consume the capability. Reconcile before reissuing.
        return handlers[tool](resource)
