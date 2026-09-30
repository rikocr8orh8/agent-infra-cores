# ToolScope Kit core

Issue one-use capabilities bound to an agent, tool, resource and expiry.

MIT-licensed Python 3.11+ library and tests, no runtime package dependencies. Run `python3 -m unittest discover -p 'test_*.py' -v` from this directory. Import directly from core. test_core.py contains complete working invocations.

The host application authenticates the subject and decides when to issue a capability. Signing keys remain trusted. The capability binds a resource, not arbitrary additional payload fields. Consumption occurs before the handler; a crash may consume it without an effect. Each of subject, tool and resource is limited to 200 characters and the whole capability to 4096, so use short ASCII identifiers. This is not a sandbox or MCP transport.

Trusted in-process use only. Add authentication and application authorization at the host boundary. No independent security audit. The configured example and supporting material are part of the separate commercial starter bundle.
