# Fixture Replay Kit core

Record explicitly selected request and response fields, then replay offline.

MIT-licensed Python 3.11+ library and tests, no runtime package dependencies. Run `python3 -m unittest discover -p 'test_*.py' -v` from this directory. Import directly from core. test_core.py contains complete working invocations.

Projection is not automatic PII detection. Secrets in allowed fields, URL paths or identifiers remain visible. Omitted match fields can hide meaningful request differences. Supply synthetic or reviewed data and include every field required to distinguish cases. No HTTP proxy is included.

Trusted in-process use only. Add authentication and application authorization at the host boundary. No independent security audit. The configured example and supporting material are part of the separate commercial starter bundle.
