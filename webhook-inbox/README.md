# Webhook Inbox Kit core

Authenticate incoming event bytes and persist one inbox record per event ID.

MIT-licensed Python 3.11+ library and tests, no runtime package dependencies. Run `python3 -m unittest discover -p 'test_*.py' -v` from this directory. Import directly from core. test_core.py contains complete working invocations.

This is a custom signing protocol, not a drop-in Polar, Stripe or Lemon Squeezy webhook verifier. The pending reader does not lease events to concurrent workers. Use one consumer or add transactional leasing. Remote effects are not atomic with mark_processed.

Trusted in-process use only. Add authentication and application authorization at the host boundary. No independent security audit. The configured example and supporting material are part of the separate commercial starter bundle.
