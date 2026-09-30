"""SPDX-License-Identifier: MIT. Atomic integer-credit reservations for agent workloads."""
import sqlite3


def units(value):
    if type(value) is not int or not 0 <= value <= 10**12:
        raise ValueError("Units must be an integer from zero to 10^12")
    return value


class Ledger:
    def __init__(self, path):
        self.path = str(path)
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS budgets(account TEXT, window TEXT, cap INTEGER, spent INTEGER, held INTEGER, PRIMARY KEY(account,window))")
            db.execute("CREATE TABLE IF NOT EXISTS reservations(account TEXT, window TEXT, id TEXT, amount INTEGER, state TEXT, actual INTEGER, PRIMARY KEY(account,window,id))")

    def configure(self, account, window, cap):
        units(cap)
        if any(not isinstance(s, str) or not 1 <= len(s) <= 100 for s in (account, window)):
            raise ValueError("Account and window must be bounded strings")
        with sqlite3.connect(self.path, timeout=10) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT spent,held FROM budgets WHERE account=? AND window=?", (account, window)).fetchone()
            if row and cap < sum(row):
                raise ValueError("Cap cannot be below spent plus held units")
            db.execute("INSERT INTO budgets VALUES(?,?,?,0,0) ON CONFLICT(account,window) DO UPDATE SET cap=excluded.cap", (account, window, cap))

    def reserve(self, account, window, key, amount):
        units(amount)
        if amount == 0 or not isinstance(key, str) or not 1 <= len(key) <= 100:
            raise ValueError("A positive reservation and nonempty request key are required")
        with sqlite3.connect(self.path, timeout=10) as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT amount,state FROM reservations WHERE account=? AND window=? AND id=?", (account, window, key)).fetchone()
            if old:
                if old[0] != amount:
                    raise ValueError("Reservation key amount conflict")
                if old[1] != "held":
                    raise ValueError("Reservation is already " + old[1] + "; use a new key")
                return {"id": key, "state": "held", "duplicate": True}
            updated = db.execute("UPDATE budgets SET held=held+? WHERE account=? AND window=? AND cap-spent-held>=?", (amount, account, window, amount))
            if updated.rowcount != 1:
                raise ValueError("Budget missing or insufficient capacity")
            db.execute("INSERT INTO reservations VALUES(?,?,?,?,'held',NULL)", (account, window, key, amount))
        return {"id": key, "state": "held", "duplicate": False}

    def settle(self, account, window, key, actual=None):
        if actual is not None:
            units(actual)
        desired = "cancelled" if actual is None else "settled"
        with sqlite3.connect(self.path, timeout=10) as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT amount,state,actual FROM reservations WHERE account=? AND window=? AND id=?", (account, window, key)).fetchone()
            if not old:
                raise ValueError("Unknown reservation")
            if old[1] != "held":
                if old[1:] == (desired, actual):
                    return {"state": desired, "duplicate": True}
                raise ValueError("Reservation is already finalized differently")
            if actual is not None and actual > old[0]:
                raise ValueError("Actual exceeds reserved ceiling; reconcile before finalizing")
            db.execute("UPDATE budgets SET held=held-?,spent=spent+? WHERE account=? AND window=?", (old[0], actual or 0, account, window))
            db.execute("UPDATE reservations SET state=?,actual=? WHERE account=? AND window=? AND id=?", (desired, actual, account, window, key))
        return {"state": desired, "duplicate": False}

    def balance(self, account, window):
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT cap,spent,held FROM budgets WHERE account=? AND window=?", (account, window)).fetchone()
        if not row:
            raise ValueError("Unknown budget")
        return dict(zip(("cap", "spent", "held", "available"), (*row, row[0] - row[1] - row[2])))
