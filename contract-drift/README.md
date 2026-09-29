# Contract Drift Kit core

Flag potentially breaking request-schema changes before updating a connector.

MIT-licensed Python 3.11+ library and tests, no runtime package dependencies. Run `python3 -m unittest discover -p 'test_*.py' -v` from this directory. Import directly from core. test_core.py contains complete working invocations.

Only the documented JSON Schema subset is supported (type, properties, required, additionalProperties, items, enum and description). Unsupported keywords fail closed. This is not a complete OpenAPI or JSON Schema implementation, response compatibility checker, or proof of all semantic compatibility. Conservative checks can flag changes that need human review.

Trusted in-process use only. Add authentication and application authorization at the host boundary. No independent security audit. The configured example and supporting material are part of the separate commercial starter bundle.
