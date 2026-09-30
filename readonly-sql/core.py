"""SPDX-License-Identifier: MIT. Bounded named queries against a read-only SQLite database."""
from pathlib import Path
import re
import sqlite3

# Comments and quoted text can contain ":tenant_id" without binding anything; strip them before checking.
# Unterminated comments and strings run to the end of the statement, as SQLite treats them.
_NOT_CODE = re.compile(r"--[^\n]*|/\*.*?\*/|/\*.*|'(?:[^']|'')*'|'.*|\"(?:[^\"]|\"\")*\"|\".*|\[[^\]]*\]|`(?:[^`]|``)*`", re.S)


def _references_tenant(sql):
    # Not followed by a name character, ':' or '(': SQLite reads ':tenant_id::x' and ':tenant_id(x)' as other parameters.
    return re.search(r":tenant_id(?![\w:(])", _NOT_CODE.sub(" ", sql)) is not None


class ReadonlyGateway:
    def __init__(self, path, queries, max_rows=100, max_steps=100000):
        if type(max_rows) is not int or not 1 <= max_rows <= 1000:
            raise ValueError("max_rows must be 1–1000")
        if type(max_steps) is not int or not 1000 <= max_steps <= 1000000:
            raise ValueError("max_steps must be 1000–1000000")
        self.path = Path(path).resolve(strict=True)
        self.queries = dict(queries)
        self.max_rows, self.max_steps = max_rows, max_steps

    def query(self, name, tenant_id, parameters=None):
        if name not in self.queries:
            raise ValueError("Unknown named query")
        if not isinstance(tenant_id, str) or not tenant_id:
            raise ValueError("Trusted tenant identity is required")
        params = dict(parameters or {})
        if "tenant_id" in params:
            raise ValueError("Caller parameters cannot override tenant identity")
        params["tenant_id"] = tenant_id
        sql = self.queries[name]
        if not _references_tenant(sql):
            raise ValueError("Registered query must reference :tenant_id outside comments and quoted text")
        db = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True)
        try:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only=ON")
            db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 65536)
            db.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 65536)
            db.setlimit(sqlite3.SQLITE_LIMIT_COLUMN, 100)
            allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_RECURSIVE}
            functions = {"count", "sum", "min", "max", "avg", "lower", "upper", "length", "coalesce", "ifnull"}
            def authorize(action, arg1, arg2, _database, _trigger):
                if action in allowed or (action == sqlite3.SQLITE_FUNCTION and (arg2 or "").lower() in functions):
                    return sqlite3.SQLITE_OK
                return sqlite3.SQLITE_DENY
            db.set_authorizer(authorize)
            ticks = 0
            def progress():
                nonlocal ticks
                ticks += 1000
                return int(ticks >= self.max_steps)
            db.set_progress_handler(progress, 1000)
            cursor = db.execute(sql, params)
            result, truncated, total = [], False, 0
            for fetched in cursor:  # read row by row so the 1 MiB cap stops reading early
                if len(result) == self.max_rows:
                    truncated = True
                    break
                row = dict(fetched)
                for value in row.values():
                    if isinstance(value, bytes):
                        raise ValueError("Binary columns are not supported")
                    total += len(str(value).encode())
                if total > 1048576:
                    raise ValueError("Result exceeds 1 MiB")
                result.append(row)
            return {"rows": result, "truncated": truncated}
        except (sqlite3.Error, OverflowError) as exc:  # OverflowError: integer parameter above 2**63-1
            raise ValueError("Query denied, invalid, or exceeded its resource budget") from exc
        finally:
            db.close()
