# Readonly SQL Kit core

Expose named, parameterized queries with read-only enforcement and resource limits.

MIT-licensed Python 3.11+ library and tests, no runtime package dependencies. Run `python3 -m unittest discover -p 'test_*.py' -v` from this directory. Import directly from core. test_core.py contains complete working invocations.

SQLite only; no Oracle, SAP or PostgreSQL connector is included. Query authors must enforce tenant predicates correctly: presence of a parameter alone does not prove row isolation. Runtime callers must authenticate access to the named query and tenant. OS-level CPU and memory isolation are not supplied.

Trusted in-process use only. Add authentication and application authorization at the host boundary. No independent security audit. The configured example and supporting material are part of the separate commercial starter bundle.
