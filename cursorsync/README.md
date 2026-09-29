# CursorSync Kit core

Commit imported records and the next cursor in the same transaction.

MIT-licensed Python 3.11+ library and tests, no runtime package dependencies. Run `python3 -m unittest discover -p 'test_*.py' -v` from this directory. Import directly from core. test_core.py contains complete working invocations.

A local page-application engine is included, not a provider HTTP client. Stream identity is trusted caller input. A completed snapshot uses a new stream namespace for the next run. Provider ordering, changing-page semantics and snapshot consistency remain adapter responsibilities.

Trusted in-process use only. Add authentication and application authorization at the host boundary. No independent security audit. The configured example and supporting material are part of the separate commercial starter bundle.
