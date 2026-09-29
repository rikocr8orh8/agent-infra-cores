# Durable Outbox Kit core

Queue work with leases, exponential backoff and dead-letter states.

MIT-licensed Python 3.11+ library and tests, no runtime package dependencies. Run `python3 -m unittest discover -p 'test_*.py' -v` from this directory. Import directly from core. test_core.py contains complete working invocations.

Use enqueue_in with the caller's active transaction on the same SQLite database for atomic business-state publishing; ordinary enqueue owns a separate transaction. Delivery is at least once, not exactly once. The kit supplies no real network sender, heartbeat, admin requeue or distributed database.

Trusted in-process use only. Add authentication and application authorization at the host boundary. No independent security audit. The configured example and supporting material are part of the separate commercial starter bundle.
