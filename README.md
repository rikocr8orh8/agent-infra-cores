# Agent Infrastructure Cores

Ten small, standard-library Python 3.11+ building blocks for agent and service infrastructure. MIT-licensed. **57 tests across ten kits**, each kit runnable and testable on its own with no package install.

Run every kit's tests:

```sh
for d in */; do (cd "$d" && python3 -m unittest discover -p 'test_*.py' -v); done
```

## What these are not

- Not a hosted service, provider connector, security audit or production certification. No independent audit has been done.
- Local SQLite transaction guarantees do not imply exactly-once effects on remote systems.
- HMAC here uses shared secrets. It is not public-key signing.
- Trusted in-process callers supply tenant identity; add authentication and authorization at your own boundary.
- These are reusable, tested patterns, not proprietary technology. An AI assistant can write a version of most of these quickly; what is offered here is the tests, the documented failure modes and the stated limits.

## The ten cores

### Webhook Inbox (`webhook-inbox/`)

Authenticate incoming event bytes and persist one inbox record per event ID.

**Stated limits:** This is a custom signing protocol, not a drop-in Polar, Stripe or Lemon Squeezy webhook verifier. The pending reader does not lease events to concurrent workers. Use one consumer or add transactional leasing. Remote effects are not atomic with mark_processed.

Tests: 5 (`cd webhook-inbox && python3 -m unittest discover -p 'test_*.py' -v`).

### Durable Outbox (`durable-outbox/`)

Queue work with leases, exponential backoff and dead-letter states.

**Stated limits:** Use enqueue_in with the caller's active transaction on the same SQLite database for atomic business-state publishing; ordinary enqueue owns a separate transaction. Delivery is at least once, not exactly once. The kit supplies no real network sender, heartbeat, admin requeue or distributed database.

Tests: 6 (`cd durable-outbox && python3 -m unittest discover -p 'test_*.py' -v`).

### ToolScope (`toolscope/`)

Issue one-use capabilities bound to an agent, tool, resource and expiry.

**Stated limits:** The host application authenticates the subject and decides when to issue a capability. Signing keys remain trusted. The capability binds a resource, not arbitrary additional payload fields. Consumption occurs before the handler; a crash may consume it without an effect. Each of subject, tool and resource is limited to 200 characters and the whole capability to 4096, so use short ASCII identifiers. This is not a sandbox or MCP transport.

Tests: 6 (`cd toolscope && python3 -m unittest discover -p 'test_*.py' -v`).

### Readonly SQL (`readonly-sql/`)

Expose named, parameterized queries with read-only enforcement and resource limits.

**Stated limits:** SQLite only; no Oracle, SAP or PostgreSQL connector is included. Query authors must enforce tenant predicates correctly: presence of a parameter alone does not prove row isolation. The gateway only rejects a registered query that does not reference the exact parameter :tenant_id outside comments, quoted text and quoted identifiers, which catches mistakes and is not proof of isolation. Runtime callers must authenticate access to the named query and tenant. OS-level CPU and memory isolation are not supplied.

Tests: 8 (`cd readonly-sql && python3 -m unittest discover -p 'test_*.py' -v`).

### CSV Quarantine (`csv-quarantine/`)

Inspect supplier CSVs, quarantine invalid rows and commit a clean batch transactionally.

**Stated limits:** The supplied schema is sku,name,price_minor,currency. A batch with any rejected row is not imported. Formula checks are conservative heuristics, not a general spreadsheet sanitizer. Schema mapping, tax logic, exchange rates and database authentication are not included.

Tests: 5 (`cd csv-quarantine && python3 -m unittest discover -p 'test_*.py' -v`).

### Contract Drift (`contract-drift/`)

Flag potentially breaking request-schema changes before updating a connector.

**Stated limits:** Only the documented JSON Schema subset is supported (type, properties, required, additionalProperties, items, enum and description). Unsupported keywords fail closed. This is not a complete OpenAPI or JSON Schema implementation, response compatibility checker, or proof of all semantic compatibility. Conservative checks can flag changes that need human review.

Tests: 6 (`cd contract-drift && python3 -m unittest discover -p 'test_*.py' -v`).

### Fixture Replay (`fixture-replay/`)

Record explicitly selected request and response fields, then replay offline.

**Stated limits:** Projection is not automatic PII detection. Secrets in allowed fields, URL paths or identifiers remain visible. Omitted match fields can hide meaningful request differences. Supply synthetic or reviewed data and include every field required to distinguish cases. No HTTP proxy is included.

Tests: 4 (`cd fixture-replay && python3 -m unittest discover -p 'test_*.py' -v`).

### CursorSync (`cursorsync/`)

Commit imported records and the next cursor in the same transaction.

**Stated limits:** A local page-application engine is included, not a provider HTTP client. Stream identity is trusted caller input. A completed snapshot uses a new stream namespace for the next run. Provider ordering, changing-page semantics and snapshot consistency remain adapter responsibilities.

Tests: 5 (`cd cursorsync && python3 -m unittest discover -p 'test_*.py' -v`).

### BudgetLedger (`budgetledger/`)

Reserve integer credits before work and settle measured usage afterward.

**Stated limits:** Credits are application-defined units, not verified provider billing. Your application authenticates accounts, selects windows and computes conservative reservations. Work that bypasses the ledger is unbounded. There is no payment processing, invoicing or automatic expiration of ambiguous reservations. Reserving a key that is already cancelled or settled raises; reserving a key that is still held returns duplicate=true. Settling with no measured amount cancels the whole reservation.

Tests: 6 (`cd budgetledger && python3 -m unittest discover -p 'test_*.py' -v`).

### ArtifactSeal (`artifactseal/`)

Authenticate a file-tree manifest and detect added, removed or changed artifacts.

**Stated limits:** Shared-secret HMAC is not public-key signing or nonrepudiation. Freeze or snapshot the tree before sealing: this library does not eliminate filesystem races or bind later execution to the verified bytes. File permissions and executable modes are not included. Do not place the manifest inside the sealed root. Empty directories and hard links are not represented in the manifest, a directory the verifier cannot read is an error, and the limits are 1000 files, 16 MiB per file and 64 MiB in total.

Tests: 6 (`cd artifactseal && python3 -m unittest discover -p 'test_*.py' -v`).

The paid starter kits (configured examples, integration guides, supporting material) are planned but not on sale, and their catalog page is not live yet; a link will be added here when it is.

## Support

Open a [GitHub issue](../../issues). There is no hosted service, support subscription or update commitment.

## License

MIT, see `LICENSE` and each kit's own `LICENSE`. The paid starter bundles use a separate commercial end-product license and are not in this repository.
