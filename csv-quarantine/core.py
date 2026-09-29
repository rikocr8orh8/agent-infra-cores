"""SPDX-License-Identifier: MIT. Deterministic supplier catalog ingestion."""
import csv
import hashlib
import io
import json
import re
import sqlite3

FIELDS = ["sku", "name", "price_minor", "currency"]


def inspect_csv(raw):
    if not isinstance(raw, bytes) or len(raw) > 5 * 1024 * 1024:
        raise ValueError("CSV must be bytes, at most 5 MiB")
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
    if reader.fieldnames != FIELDS:
        raise ValueError("CSV header must be exactly: " + ",".join(FIELDS))
    accepted, rejected, seen = [], [], set()
    for index, row in enumerate(reader, 2):
        if index > 10001:
            raise ValueError("CSV exceeds 10000 records")
        errors = []
        if set(row) != set(FIELDS) or any(v is None for v in row.values()):
            errors.append("Incorrect column count")
        else:
            if any(v.lstrip().startswith(("=", "+", "-", "@")) for v in row.values()):
                errors.append("Spreadsheet formula prefix is not allowed")
            if any(any(ord(c) < 32 and c not in "\n\r\t" for c in v) for v in row.values()):
                errors.append("Control characters are not allowed")
            if not re.fullmatch(r"[A-Z0-9_-]{1,40}", row["sku"]):
                errors.append("Invalid SKU")
            if not 1 <= len(row["name"].strip()) <= 200:
                errors.append("Name must contain 1–200 characters")
            if not re.fullmatch(r"[0-9]{1,9}", row["price_minor"]):
                errors.append("Price must be a nonnegative integer, maximum 9 digits")
            if row["currency"] not in ("USD", "EUR", "GBP"):
                errors.append("Unsupported currency")
            if row["sku"] in seen:
                errors.append("Duplicate SKU within batch")
            seen.add(row["sku"])
        if errors:
            rejected.append({"record": index, "errors": errors, "row": row})
        else:
            accepted.append(row | {"price_minor": int(row["price_minor"])})
    return {"source_sha256": hashlib.sha256(raw).hexdigest(), "accepted": accepted, "rejected": rejected}


def import_catalog(path, supplier, raw, expected_sha256):
    if not isinstance(supplier, str) or not 1 <= len(supplier) <= 100:
        raise ValueError("Trusted supplier identity is required")
    report = inspect_csv(raw)  # Revalidate original bytes at commit time.
    if report["source_sha256"] != expected_sha256:
        raise ValueError("CSV changed since inspection")
    if report["rejected"]:
        raise ValueError("Batch contains quarantined records; correct the source and inspect again")
    with sqlite3.connect(path, timeout=10) as db:
        db.execute("CREATE TABLE IF NOT EXISTS imports(supplier TEXT, digest TEXT, PRIMARY KEY(supplier,digest))")
        db.execute("CREATE TABLE IF NOT EXISTS catalog(supplier TEXT, sku TEXT, name TEXT, price_minor INTEGER, currency TEXT, PRIMARY KEY(supplier,sku))")
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT 1 FROM imports WHERE supplier=? AND digest=?", (supplier, expected_sha256)).fetchone():
            return {"duplicate": True, "rows": 0}
        for row in report["accepted"]:
            db.execute("INSERT INTO catalog VALUES(?,?,?,?,?) ON CONFLICT(supplier,sku) DO UPDATE SET name=excluded.name,price_minor=excluded.price_minor,currency=excluded.currency",
                       (supplier, row["sku"], row["name"], row["price_minor"], row["currency"]))
        db.execute("INSERT INTO imports VALUES(?,?)", (supplier, expected_sha256))
    return {"duplicate": False, "rows": len(report["accepted"])}


def quarantine_json(report):
    # JSON output avoids generating an executable spreadsheet from rejected cells.
    return json.dumps({"source_sha256": report["source_sha256"], "rejected": report["rejected"]}, indent=2)
