# CSV Quarantine Kit core

Inspect supplier CSVs, quarantine invalid rows and commit a clean batch transactionally.

MIT-licensed Python 3.11+ library and tests, no runtime package dependencies. Run `python3 -m unittest discover -p 'test_*.py' -v` from this directory. Import directly from core. test_core.py contains complete working invocations.

The supplied schema is sku,name,price_minor,currency. A batch with any rejected row is not imported. Formula checks are conservative heuristics, not a general spreadsheet sanitizer. Schema mapping, tax logic, exchange rates and database authentication are not included.

Trusted in-process use only. Add authentication and application authorization at the host boundary. No independent security audit. The configured example and supporting material are part of the separate commercial starter bundle.
