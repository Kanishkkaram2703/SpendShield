# SpendShield Security and Architecture Repair Report

Date: 2026-09-11

Scope: existing Python/FastAPI backend and non-database architecture. The
MongoDB and Cassandra foundation was preserved. No frontend was present to
audit.

## Executive summary

The repository was a backend foundation rather than a complete financial,
analytics, ML, or forensic platform. The most important weaknesses were the
absence of an account domain, explicit financial invariants, transaction
lifecycle rules, idempotency semantics, production security configuration,
object-level account authorization, and a canonical event envelope.

This repair adds those boundaries and an implemented account API without
pretending that payment settlement, account-event routing, ML, or forensics
are complete. MongoDB remains current domain state and Cassandra remains
historical event data.

## Findings and repair status

### F-001 - Missing backend-owned account domain

- Severity: High
- Status: Fixed for the Phase 3 account/status API
- Location: `backend/app/domain/financial.py:138`, `backend/app/services/account_service.py:25`, `backend/app/api/v1/accounts.py:20`
- Evidence: Before this repair there was no account service, account API, or account domain model; only the MongoDB collection/index definition existed.
- Impact: A frontend or future route could have invented balance/account state without a central invariant boundary.
- Fix: Added `Account`, `AccountStatus`, explicit status transitions, server-side initial balance configuration, account service, MongoDB adapter, ownership checks, admin-only status management, optimistic version checks, and account API endpoints.
- Remaining risk: The payment operation is fictional and controlled; external settlement is intentionally not implemented.

### F-002 - Financial rules and transaction lifecycle were implicit

- Severity: High
- Status: Fixed at the domain and API boundaries
- Location: `backend/app/domain/financial.py:62`, `backend/app/domain/financial.py:194`, `backend/app/domain/financial.py:318`
- Evidence: The earlier code had no money normalization, account debit rule, transaction state machine, or transition validation.
- Impact: Invalid transitions, negative/ambiguous money values, inactive-account operations, and insufficient-funds errors could not be handled consistently.
- Fix: Added exact `Decimal` money normalization, account status checks, insufficient-funds checks, explicit transaction transitions, balance-before/after values, and negative tests.
- Remaining risk: The standalone MongoDB fallback remains non-atomic, but the configured development API uses the validated `rs0` transaction path.

### F-003 - Duplicate side effects had no idempotency contract

- Severity: High
- Status: Fixed through the transactional repository and API boundary
- Location: `backend/app/domain/financial.py:261`, `backend/app/domain/financial.py:298`, `backend/app/services/payment_service.py:21`
- Evidence: No previous idempotency key or request fingerprint existed.
- Impact: Retried payment requests could create duplicate financial effects.
- Fix: Added bounded idempotency keys, request fingerprints that exclude the key itself, conflict detection, and a thread-safe test repository proving replay safety.
- Remaining risk: Rate limiting and token revocation remain future controls; duplicate financial effects are covered by the MongoDB idempotency constraint and transaction path.

### F-004 - Production host/debug/docs controls were incomplete

- Severity: High in staging/production
- Status: Fixed in application configuration
- Location: `backend/app/core/config.py:112`, `backend/app/main.py:149`
- Evidence: The application previously accepted production debug/documentation defaults without enforcing a real secret or host allowlist.
- Impact: Misconfiguration could expose interactive API documentation, debug behavior, or arbitrary Host-header handling.
- Fix: Staging/production now reject debug mode, placeholder auth secrets, and missing trusted hosts; interactive docs are disabled outside development/tests; `TrustedHostMiddleware` is applied when configured.
- Mitigation: Reverse-proxy configuration still needs independent verification in deployment.

### F-005 - JWT validation lacked issuer/audience binding

- Severity: High for multi-service or environment-separated deployments
- Status: Fixed
- Location: `backend/app/core/security.py:40`
- Evidence: Tokens previously carried subject, timing, and token type but not issuer/audience constraints.
- Impact: A valid token from another issuer or audience could be accepted if the signing secret were shared.
- Fix: Added configured `iss` and `aud` claims and strict decode validation, with tests.

### F-006 - Object-level account authorization was absent

- Severity: High once account resources exist
- Status: Fixed for the account API
- Location: `backend/app/services/account_service.py:189`, `backend/app/api/v1/accounts.py:48`
- Evidence: The earlier repository had no account resource endpoint or ownership check.
- Impact: Future ID-based routes could expose another user's financial state.
- Fix: Account lookup returns a non-sensitive 404 for non-owners; only the owner or an admin may retrieve an account by ID. IDs are parsed as UUIDs at the API boundary.
- Remaining risk: Merchant, case, evidence, and report ownership policies still need implementation when those resources are added.

### F-007 - Request correlation and baseline response headers were absent

- Severity: Medium
- Status: Fixed
- Location: `backend/app/core/middleware.py:15`
- Evidence: Requests previously had no application-level request ID or centralized security headers.
- Impact: Production diagnosis would be harder and browser-facing responses lacked baseline hardening headers.
- Fix: Added bounded `X-Request-ID` propagation, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and `Permissions-Policy` headers.

### F-008 - Rate limiting and request-size controls are not implemented

- Severity: Medium
- Status: Open
- Location: No current rate-limit middleware or edge configuration exists.
- Impact: Login, account creation, and future expensive endpoints can be abused for brute force or resource exhaustion.
- Fix: Not added in this slice because the repository has no deployment edge and no new dependency was authorized.
- Mitigation: Add edge limits and a bounded application strategy before exposing the API publicly.

### F-009 - Historical event publication boundary was not durable

- Severity: High for financial operations
- Status: Fixed as a generic retryable boundary and wired into the controlled payment API
- Location: `backend/app/events/models.py:18`, `backend/app/events/publication.py:25`, `backend/app/services/event_delivery_service.py:31`, `backend/app/repositories/audit.py:67`
- Evidence: The prior adapter had no durable pending state, retry schedule, or delivery acknowledgement.
- Impact: A Cassandra outage could lose the historical publication or require an unsafe re-execution of the domain operation.
- Fix: Added target-aware MongoDB publication metadata, unique event identity, explicit pending/failed/published states, bounded backoff, exact-envelope replay, correlation/provenance preservation, and live MongoDB-to-Cassandra integration tests.
- Remaining risk: The standalone MongoDB fallback remains non-atomic across documents; optimistic compare-and-set recovery prevents duplicate debits in tested races but is not multi-document atomicity. The configured development environment uses the validated replica-set transaction path; Cassandra delivery remains a separate retryable step.

### F-011 - Account status had no secure state-changing path

- Severity: High for account integrity
- Status: Fixed for Phase 3
- Location: `backend/app/services/account_service.py`, `backend/app/api/v1/accounts.py`, `backend/app/repositories/accounts.py`
- Evidence: Account status existed as a field but had no API, transition table, authorization policy, or version-checked persistence update.
- Impact: A future caller could create impossible status changes or silently overwrite concurrent state.
- Fix: Added explicit transitions, administrator authorization, strict request validation, optimistic version checks, and negative tests.

### F-010 - ML and forensic claims are not implemented

- Severity: High for product scope honesty
- Status: Open and intentionally not fabricated
- Location: No production ML/forensic source directories or workflows exist.
- Impact: Claiming anomaly detection, fraud decisions, evidence integrity, correlation, or reports would be unsupported.
- Fix: No fake models, metrics, evidence, or correlations were added.
- Next boundary: Build transaction history first, then an evidence-based ML baseline and forensic provenance workflow.

## Security controls confirmed

- Passwords use Argon2 through `pwdlib`.
- JWTs use an explicit algorithm allowlist and now validate expiry, issuer, audience, and token type.
- Header bearer authentication is used; tokens are not accepted in URLs or cookies.
- Public registration cannot select privileged roles.
- Response models exclude password hashes.
- Account ownership is enforced server-side.
- Account status changes are administrator-only, version-checked, and audited.
- No CORS middleware, file serving, uploads, WebSockets, subprocess execution, SQL, or outbound URL fetching exists in the current backend.
- Production configuration rejects debug mode, placeholder secrets, and missing trusted hosts.
- Cassandra keyspace identifiers are constrained to safe, valid bounded names before they reach DDL construction.
- Publication failures store bounded error classifications rather than raw exception text or event payloads.
- Payment persistence enforces the account owner, active status, currency, exact
  amount, version, and balance in the repository; the client cannot supply
  authoritative balance or transaction status.
- Payment event payloads omit the idempotency key and credentials; actor,
  correlation, causation, and provenance are retained for traceability. The
  public payment route is fictional, authenticated, owner-scoped, and does not
  expose internal event/publication fields.
- Replica-set configuration is explicit and environment-backed; no MongoDB
  credentials are placed in source code or logs. The existing shared Windows
  data directory was not altered without administrator-level verification.
- MongoDB transaction sessions include only current-state and publication
  metadata writes. Cassandra is reached by the separate delivery service, so a
  Cassandra failure cannot cause a financial retry.

## Verification

- Full test suite before this boundary slice: **45 passed, 2 skipped, 0 failed** in `backend\.venv`.
- Current full test suite with live Cassandra, replica-set, and merchant/catalog tests: **76 passed, 0 skipped, 0 failed**.
- The dependency-health response reports only non-secret MongoDB identity fields (`endpoint`, `replica_set`, and `is_writable_primary`); it does not return the URI, credentials, tokens, or secrets.
- Cassandra validation observed version **4.0.21**, a reachable `127.0.0.1:9042`, and one `UN` node via `nodetool status`.
- `pip check`: **PASS**.
- Python bytecode compilation (`python -m compileall -q app tests`): **PASS**.
- Domain tests cover money normalization, account status transitions, insufficient funds, lifecycle transitions, idempotency replay, and idempotency conflict.
- Account API tests cover server-owned defaults, duplicate creation, authentication, cross-owner access denial, admin status changes, invalid transitions, stale versions, and audit emission.
- Security tests cover production configuration rejection, JWT issuer/audience, docs disabling, request IDs, and security headers.
- Payment API integration tests cover authentication, ownership, malformed and
  excessive-precision amounts, inactive users/accounts, idempotency, bounded
  history, concurrency, safe 404s, and live MongoDB/Cassandra publication.
- Merchant/catalog integration tests cover authentication, admin-only
  management, version conflicts, bounded listing/cursors, invalid category
  relationships, inactive merchants, reclassification, and historical payment
  category snapshots.

## Remaining risks

1. The standalone Windows MongoDB service remains non-transactional; the
   isolated rs0 validation instance is a development-only transaction target.
2. Account historical events are not routed to Cassandra because the current schema has no account-specific query model.
3. Merchant ownership and `MERCHANT`-role management semantics are not modeled;
   current management is deliberately restricted to `ADMIN`.
4. No rate limiting, refresh-token/revocation system, MFA, or password reset exists.
5. No frontend, ML pipeline, forensic processing, deployment manifests, CI/CD, or production observability stack exists.

## Merchant and Category Security Review - 2026-09-11

The catalog boundary adds the following verified controls:

- category definitions are system-controlled and cannot be mass-assigned by
  normal users;
- merchant IDs are backend-generated UUIDs;
- merchant creation and updates require server-side `ADMIN` role evaluation;
- the existing `MERCHANT` role is not treated as an administrator because no
  merchant ownership association exists;
- merchant updates use expected-version compare-and-set semantics;
- merchant status and category relationship are validated server-side;
- payment requests cannot provide category values or merchant status;
- unknown and inactive merchants are rejected before the financial repository;
- merchant listings are bounded and cursor-paged, and responses exclude MongoDB
  internals and audit/publication metadata;
- payment transactions preserve a category snapshot for history without making
  the snapshot a second current-state authority.

The remaining catalog limitation is that merchant ownership and merchant-role
management semantics are not modeled. Adding that capability requires an
explicit identity/domain decision; it was not inferred from the role name.
