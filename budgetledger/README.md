# BudgetLedger Kit core

Reserve integer credits before work and settle measured usage afterward.

MIT-licensed Python 3.11+ library and tests, no runtime package dependencies. Run `python3 -m unittest discover -p 'test_*.py' -v` from this directory. Import directly from core. test_core.py contains complete working invocations.

Credits are application-defined units, not verified provider billing. Your application authenticates accounts, selects windows and computes conservative reservations. Work that bypasses the ledger is unbounded. There is no payment processing, invoicing or automatic expiration of ambiguous reservations. Reserving again with a key that is already cancelled or settled returns that state with duplicate=true instead of raising, so check the returned state before doing work. Settling with no measured amount cancels the whole reservation.

Trusted in-process use only. Add authentication and application authorization at the host boundary. No independent security audit. The configured example and supporting material are part of the separate commercial starter bundle.
