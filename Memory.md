# Memory

## Project
**SpendShield — Intelligent Payment, Financial Awareness & Digital Forensics Platform**

## Document Type
**Living Project Memory**

## Version
**0.1 — Initial Project Baseline**

## Purpose

`Memory.md` is the continuously updated memory of the SpendShield project.

It records what has actually happened during development.

This file is not a replacement for:

- `PRD.md` — what the product must do
- `Architecture.md` — how the system is structured
- `Phases.md` — how development is sequenced
- `Design.md` — how the product should look and behave
- `Rules.md` — what must and must not be done

Instead:

> **Memory.md records the current reality of the project.**

---

# 1. Current Project State

## Overall Status

**Implementation baseline active - Synthetic ML dataset foundation implemented**

The project concept, product requirements, architecture, development phases, design principles, and engineering rules have been defined. The backend foundation, authentication foundation, database foundation, account foundation, financial domain rules, payment engine, merchant/category foundation, analytics data foundation, and security hardening slices are implemented and validated.

ML model training/inference, notification, frontend, subscriptions, and forensic product features remain future work; the evidence-driven dataset audit and controlled synthetic dataset foundation are implemented.

---

# 2. Current Project Vision

SpendShield is a controlled fictional financial ecosystem that combines:

```text
Payment
+
Financial Intelligence
+
Machine Learning
+
Computer Forensics
+
Evidence Analysis
+
Database Engineering
```

The central investigation flow is:

```text
Financial Activity
        ↓
ML / Behavioural Analysis
        ↓
Suspicious Activity
        ↓
Forensic Case
        ↓
Digital Evidence
        ↓
Event Correlation
        ↓
Timeline
        ↓
Evidence Consistency
        ↓
Investigator Review
        ↓
Report
```

---

# 3. Current Technology Direction

## Frontend

Planned:

```text
Next.js
React
TypeScript
Tailwind CSS
```

## Backend

Planned:

```text
Python
FastAPI
Pydantic
```

## Databases

### MongoDB

Planned for flexible operational and investigation documents.

### Cassandra

Planned for high-volume chronological event workloads.

## Machine Learning

Planned:

```text
Python
pandas
numpy
scikit-learn
Jupyter
```

## Forensics

Planned capabilities:

```text
Evidence Ingestion
SHA-256 Hashing
Metadata
Artifact Processing
Event Normalization
Timeline Reconstruction
Correlation
Consistency Analysis
Chain of Custody
Investigator Findings
Reporting
```

---

# 4. Source-of-Truth Documents

The following files define the project:

```text
whole_project_idea_and_concept.md
PRD.md
Architecture.md
Phases.md
Design.md
Rules.md
Memory.md
```

When these documents conflict, do not silently choose one.

The conflict must be identified and resolved deliberately.

---

# 5. Current Architecture State

Current intended architecture:

```text
Next.js / React
        ↓
FastAPI
        ↓
Application Services
        ├── Financial Engine
        ├── ML Intelligence
        ├── Forensic Engine
        ├── Correlation Engine
        └── Reporting Engine
        ↓
Data Access Layer
        ├── MongoDB
        ├── Cassandra
        └── Evidence/Object Storage
```

---

# 6. Current Module State

| Module | Status | Notes |
|---|---|---|
| Project Foundation | Partially implemented | FastAPI/configuration/test baseline exists; frontend, Git hygiene, and deployment remain absent |
| Authentication | Implemented foundation | Argon2, JWT validation, roles, protected dependencies, and Mongo/in-memory repository contracts exist |
| Database Foundation | Implemented foundation | MongoDB current-state and Cassandra event adapters/schema exist; live Cassandra validation passed |
| Wallet / Account | Partially implemented | Backend-authoritative account creation/reads and Mongo persistence exist; account operations and full wallet lifecycle remain |
| QR Payment | Planned | Controlled fictional ecosystem |
| Transactions | Partially implemented | Domain lifecycle, money rules, and idempotency contracts exist; production persistence/API remain |
| Subscriptions | Planned | Fictional services |
| Analytics | Implemented | Read-only MongoDB current-state foundation |
| ML Pipeline | Partially implemented | Evidence audit, synthetic feature matrix, and research baseline; no production model or inference |
| Categorization | Planned | Model to be evaluated |
| Recurring Detection | Planned | Pattern-based/ML evaluation |
| Anomaly Detection | Planned | Must be evaluated |
| Forecasting | Planned | Requires sufficient data |
| Suspicious Activity | Planned | Decision-support only |
| Forensic Cases | Planned | Core module |
| Evidence Ingestion | Planned | Authorized evidence only |
| Evidence Hashing | Planned | SHA-256 baseline |
| Chain of Custody | Planned | Auditable application record |
| Artifact Processing | Planned | Supported formats only |
| Event Normalization | Planned | Common event schema |
| Cassandra Event Store | Implemented foundation | Query-first schema/repository and canonical publisher adapter exist; workflows are not fully wired |
| Correlation | Planned | Evidence-based |
| Timeline | Planned | Source timestamps preserved |
| Consistency Analysis | Planned | Conflicts surfaced |
| Investigation Graph | Planned | No invented relationships |
| Trace Back | Planned | Relevant predecessors |
| Trace Forward | Planned | Relevant successors |
| ML Explainability | Planned | Model-dependent |
| Investigator Findings | Planned | Human review |
| Reports | Planned | Evidence-backed |
| Security Hardening | Partially implemented | Baseline auth/config/request protections, account audit records, and retryable event delivery exist; rate limits, revocation, and MFA remain |
| Testing | Partially implemented | Unit/service/API/negative and live Cassandra integration tests exist; E2E is absent |
| Deployment | Planned | Reproducible deployment |

---

# 7. Decisions Already Made

## Decision 001 — Controlled Financial Ecosystem

The project will not process real money.

Reason:

```text
Educational safety
+
Simpler implementation
+
Full control over data
+
No real banking dependency
```

---

## Decision 002 — Computer Forensics Is Core

Computer forensics is not an optional add-on.

It begins when suspicious financial activity requires investigation.

---

## Decision 003 — MongoDB + Cassandra Have Different Responsibilities

MongoDB:

```text
Documents
Cases
Transactions
Evidence Metadata
Findings
Reports
```

Cassandra:

```text
High-volume chronological events
```

---

## Decision 004 — Jupyter Is the ML Laboratory

Model development and experimentation occur in notebooks.

Production inference should use exported/versioned model artifacts.

---

## Decision 005 — No Fake ML Accuracy

Model performance must be measured experimentally.

No arbitrary accuracy claims are permitted.

---

## Decision 006 — Anomaly Does Not Mean Fraud

The system may identify:

```text
Unusual
Potentially Suspicious
Requires Review
```

It must not automatically declare criminal activity.

---

## Decision 007 — Evidence Must Be Traceable

Important findings should have a path back to:

```text
Data
 ↓
Event
 ↓
Evidence
 ↓
Reasoning
 ↓
Decision
```

---

## Decision 008 — Original Evidence Must Be Preserved

Original evidence and derived artifacts are separate concepts.

---

## Decision 009 — Human Investigator Remains in Control

The system provides analytical support.

The investigator makes the final case decision.

---

# 8. Current ML Strategy

No final model should be considered selected until experimentation is completed.

Candidate approaches include:

```text
Transaction Classification
→ Logistic Regression / Tree-based baseline

Anomaly Detection
→ Isolation Forest / statistical methods

Forecasting
→ baseline time-series/statistical approach
```

Selection criteria:

```text
Performance
Interpretability
Data availability
Computational cost
Reproducibility
Suitability for the task
```

---

# 9. Current Forensic Strategy

The forensic subsystem should prioritize:

```text
Integrity
Provenance
Normalization
Correlation
Timeline Reconstruction
Consistency
Explainability
Human Review
```

The system should preserve uncertainty instead of manufacturing certainty.

---

# 10. Current Data Strategy

Potential data categories:

```text
Synthetic Financial Data
Controlled Investigation Data
Public Cybersecurity/Event Datasets
Authorized User-Provided Evidence
```

Every dataset must have documented provenance.

---

# 11. Current Demo Story

The primary demonstration should eventually follow a deterministic case:

```text
Normal User Activity
       ↓
Normal Payments
       ↓
New Device / Session
       ↓
Unusual Payment
       ↓
ML Risk Signal
       ↓
Investigation Case
       ↓
Evidence Ingestion
       ↓
Hash Verification
       ↓
Artifact Processing
       ↓
Event Normalization
       ↓
Timeline
       ↓
Correlation
       ↓
Potential Evidence Conflict
       ↓
Investigator Review
       ↓
Final Report
```

This demo story is a target design, not a claim that the workflow is already implemented.

---

# 12. Current Documentation Status

```text
whole_project_idea_and_concept.md → Created
PRD.md                            → Created
Project_idea.txt                  → Created
Architecture.md                   → Created
Phases.md                         → Created
Design.md                         → Created
Rules.md                          → Created
Memory.md                         → Initial version
```

---

# 13. Implementation Log

This section must be appended/updated during development.

## Entry Template

```text
### [YYYY-MM-DD] — [Change Title]

Status:
[Implemented / Partially Implemented / Reverted / Blocked]

What changed:
-

Why:
-

Files changed:
-

Database changes:
-

API changes:
-

Frontend changes:
-

ML changes:
-

Forensic changes:
-

Tests:
-

Result:
-

Known issues:
-

Next step:
-
```

Do not erase historical decisions unnecessarily.

If a previous decision is reversed, record the reversal and explain why.

---

# 14. Current Known Risks

## Risk 001 — Scope Creep

The project contains multiple academic domains.

Control:

```text
Follow Phases.md
Prioritize P0
Do not add technologies without justification
```

## Risk 002 — Overengineering

Control:

```text
Keep service boundaries meaningful.
Avoid unnecessary microservices.
```

## Risk 003 — ML Without Sufficient Data

Control:

```text
Allow rule/statistical baselines.
Report insufficient-data states.
```

## Risk 004 — Forensic Overclaiming

Control:

```text
Use evidence-backed language.
Preserve uncertainty.
Keep investigator review.
```

## Risk 005 — Database Misuse

Control:

```text
Document MongoDB workload.
Document Cassandra query patterns.
Measure actual behaviour.
```

## Risk 006 — UI-First Development

Control:

```text
Do not consider a feature complete because its UI exists.
```

---

# 15. Current Open Questions

These must be resolved during implementation rather than guessed.

```text
1. Final exact frontend component library.
2. Final MongoDB schema/index strategy.
3. Final Cassandra partition strategy after query analysis.
4. Final ML datasets.
5. Final model selection after experiments.
6. Exact supported forensic evidence formats.
7. Exact object-storage implementation.
8. Final deployment provider.
9. Final report-generation implementation.
10. Final authentication/session mechanism.
```

---

# 16. Change Impact Checklist

Whenever a major requirement changes, check:

```text
[ ] whole_project_idea_and_concept.md
[ ] PRD.md
[ ] Project_idea.txt
[ ] Architecture.md
[ ] Phases.md
[ ] Design.md
[ ] Rules.md
[ ] Memory.md
[ ] Source code
[ ] Tests
```

Not every change requires every document to change, but the impact must be considered.

---

# 17. Feature Completion Record

A feature should be recorded here only after:

```text
Implementation
+
Testing
+
Security Review
+
UI Integration
+
Documentation
```

Example:

```text
Feature:
Evidence SHA-256 Verification

Status:
Completed

Backend:
Implemented

Database:
Evidence metadata stored

Tests:
Match and mismatch cases passed

UI:
Integrity status displayed

Documentation:
Architecture/Rules updated

Known Issue:
None
```

---

# 18. Model Registry Record

Every production ML model should eventually be recorded here.

Template:

```text
Model:
Version:
Purpose:
Dataset:
Features:
Algorithm:
Training Date:
Evaluation Metrics:
Threshold:
Artifact:
Explainability:
Known Limitations:
Status:
```

---

# 19. Database Change Log

Template:

```text
### [YYYY-MM-DD]

Database:
MongoDB / Cassandra

Change:
-

Reason:
-

Collections/Tables:
-

Indexes/Keys:
-

Migration:
-

Tests:
-

Rollback Consideration:
-
```

---

# 20. Security Change Log

Template:

```text
### [YYYY-MM-DD]

Security Area:
-

Change:
-

Threat Addressed:
-

Implementation:
-

Test:
-

Result:
-
```

---

# 21. Current Next Step

The completed implementation sequence is:

```text
Phase 0 - Project Foundation
        v
Phase 1 - Authentication & Roles
        v
Phase 2 - Database Foundation
        v
Phase 3 - Wallet & Account System
```

No advanced ML or forensic implementation should begin before the foundational architecture is operational enough to support it.

---

# 22. Memory Update Protocol

After every meaningful development session:

1. Read the current `Memory.md`.
2. Record what actually changed.
3. Record important decisions.
4. Record tests/results.
5. Record unresolved issues.
6. Record the next concrete step.
7. Update affected project documents if requirements or architecture changed.
8. Do not claim unfinished work as completed.

---

# 23. Final Memory Principle

> **Memory.md must describe the project as it actually exists, not as we wish it existed.**

If the architecture changes, record it.

If a feature fails, record it.

If a model performs poorly, record it.

If a planned feature is removed, record why.

If a decision is reversed, preserve the history.

The purpose of this file is to ensure that any developer or AI coding agent can enter the project, understand its current state, and continue development without guessing.

---

# Current State Summary

**Project:** SpendShield

**Stage:** Phase 5 Payment Engine, Merchant/Category Foundation, and Analytics Data Foundation complete

**Primary Goal:** Build a unified fictional financial, machine-learning, and computer-forensics platform.

**Current Implementation:** FastAPI backend, authentication foundation, MongoDB persistence foundation, Cassandra event foundation, live dependency validation, backend-authoritative account APIs, admin-only account status management, optimistic version checks, MongoDB audit/publication records, retryable event delivery, exact money rules, transaction lifecycle rules, idempotency contracts, canonical event envelopes, transactional MongoDB payment persistence, authenticated owner-scoped payment API, controlled categories, versioned merchants, payment-time merchant/category validation, immutable merchant/category payment snapshots, owner-scoped read-only spending summary/category/merchant/trend/largest-payment analytics, the evidence-driven ML dataset audit notebook, the controlled synthetic ML dataset generator and validation notebooks, and production security defaults are implemented and tested. ML model training/inference and forensic features are not implemented.

**Next Phase:** Evidence-driven data science and ML foundation.

**Next Objective:** Prepare deterministic candidate features and evaluate a research-only baseline without turning a synthetic scenario label into a fraud fact or introducing a second source of financial truth.

---

# 24. Phase 01 Implementation Audit — 2026-09-08

## Repository State

The repository contains only the eight project source-of-truth documents and an empty `.qodo` directory structure. No application source, frontend, backend, tests, notebooks, datasets, dependencies, environment configuration, Docker/deployment configuration, or Git metadata is present.

## Audit Classification

- Completed: documentation baseline and intended architecture definition only.
- Partial: none in implementation; all product components remain planned.
- Missing: project foundation, FastAPI application, frontend, authentication, databases, payment/QR/subscription systems, analytics, ML pipeline/inference, forensic processing, evidence storage/integrity, correlation, timelines, findings, reports, tests, and deployment.

## Architectural Discoveries

- The later PRD, Architecture, Phases, Rules, Design, and existing Memory documents consistently define MongoDB for flexible operational/investigation documents and Cassandra for chronological event workloads.
- `Project_idea.txt` contains an older PostgreSQL plus Redis/Celery architecture. This remains an unresolved source-of-truth conflict and must not be silently discarded.
- The intended product boundary is a controlled fictional financial ecosystem; anomalies are decision-support signals, not fraud findings, and investigators retain final control.

## Risks Identified

- Technology-stack ambiguity before foundation work.
- Large scope with no executable baseline.
- No validated API/database contracts or test harness.
- Future ML leakage, unsupported model claims, evidence-integrity failures, and over-correlation are design risks requiring dependency-ordered implementation.

## Next Implementation Phase

Per the existing project sequence, the next implementation phase is **Phase 0 — Project Foundation**: establish the repository structure, FastAPI health endpoint, frontend shell, configuration, initial test structure, Git hygiene, and development documentation. This remains subject to human confirmation of the PostgreSQL/Redis/Celery versus MongoDB/Cassandra conflict.

---

# 25. Phase 02 — Python Backend Foundation — 2026-09-08

## Status

**Completed and validated.** This phase was intentionally limited to the Python/FastAPI backend foundation. The older PostgreSQL/SQLAlchemy/Redis/Celery direction was not introduced; MongoDB and Cassandra remain future integrations under the current architecture.

## What Changed

- Created the `backend/` Python package and extension-point directories.
- Added a FastAPI application factory and application metadata.
- Added unversioned `/health` and versioned `/api/v1/health` process health endpoints.
- Added typed environment-backed configuration using Pydantic Settings with the `SPENDSHIELD_` environment prefix.
- Added centralized standard-library logging with configurable levels.
- Added expected-application, validation, HTTP, and unexpected-error handlers with safe structured responses.
- Added common `HealthResponse` and `ErrorResponse` schemas only.
- Added a minimal pytest setup and real health/configuration/error-handling tests.
- Added dependency, environment-template, ignore-file, and backend setup documentation.

## Files Created

```text
.gitignore
backend/.env.example
backend/README.md
backend/requirements.txt
backend/app/__init__.py
backend/app/main.py
backend/app/api/__init__.py
backend/app/api/v1/__init__.py
backend/app/api/v1/router.py
backend/app/core/__init__.py
backend/app/core/config.py
backend/app/core/exceptions.py
backend/app/core/logging.py
backend/app/db/__init__.py
backend/app/repositories/__init__.py
backend/app/schemas/__init__.py
backend/app/schemas/common.py
backend/app/services/__init__.py
backend/app/utils/__init__.py
backend/tests/__init__.py
backend/tests/conftest.py
backend/tests/test_health.py
```

## Dependency and Runtime Details

- Python used for validation: 3.11.9.
- FastAPI installed during validation: 0.141.1.
- Uvicorn, Pydantic, Pydantic Settings, python-dotenv, pytest, and HTTPX were included.
- No MongoDB, Cassandra, PostgreSQL, Redis, Celery, ML, or forensic dependencies were added.
- A local `backend/.venv/` was used for validation and is excluded by `.gitignore`.

## API and Configuration

- API prefix: `/api/v1`.
- `GET /health` returns `{ "status": "ok", "service": "spendshield-backend" }`.
- `GET /api/v1/health` returns the same response.
- Configuration is loaded from environment variables prefixed with `SPENDSHIELD_` and optional local `.env` values.
- Database, authentication, and evidence-storage settings are placeholders only; no external systems are initialized.

## Validation

- Application startup: **PASS**.
- Root health endpoint: **PASS**, HTTP 200.
- Versioned health endpoint: **PASS**, HTTP 200.
- Pytest: **PASS**, 6 passed, 0 failed.
- Import validation: **PASS**.
- Python bytecode compilation: **PASS**.
- Dependency consistency (`pip check`): **PASS**.
- Prohibited Phase 02 dependencies: **none found**.
- Host environment isolation: **PASS**; unrelated generic environment variables do not override `SPENDSHIELD_` settings.

## Known Limitations

- No frontend was created, as explicitly required by the Phase 02 brief.
- No authentication, authorization, database connectivity, business logic, ML, or forensic processing exists yet.
- Health checks report process availability only and intentionally do not report dependency readiness.
- The repository has no Git metadata yet; `.gitignore` was created for the future repository.

## Next Step

Proceed only when explicitly instructed to Phase 1 — Authentication & Roles. Preserve the current API/configuration boundaries and do not begin MongoDB or Cassandra implementation during authentication work unless the next phase explicitly authorizes it.

---

# 26. Phase 03 — Authentication, Authorization & Role Foundation — 2026-09-08

## Status

**Completed and validated.** This phase implemented identity and protected API foundations only. MongoDB, Cassandra, wallets, payments, subscriptions, ML, frontend, and forensic functionality remain unimplemented.

## Authentication Architecture

- Authentication uses short-lived stateless HS256 JWT access tokens.
- Tokens contain a user ID, token ID, issued-at time, expiry, and access-token type only.
- Protected requests validate the token and then load the current active user through the repository abstraction.
- Role data is not trusted from the token, preventing stale token roles from becoming the authorization source of truth.
- There is no logout endpoint yet. Clients discard tokens locally; server-side revocation is reserved for persistence-backed session/token state in a later phase.

## Password and Role Security

- Passwords are hashed with Argon2 through `pwdlib`.
- Plaintext passwords and password hashes are excluded from all API response schemas and logs.
- Public registration always assigns `USER`.
- Controlled roles are `USER`, `INVESTIGATOR`, `MERCHANT`, and `ADMIN`.
- Role checks are reusable server-side FastAPI dependencies through `require_role(...)`.
- Inactive users cannot log in or access protected routes.

## Repository and Service Boundaries

- `UserRepository` is a persistence-neutral protocol for `get_by_email`, `get_by_id`, and `create`.
- `UnavailableUserRepository` is the default application adapter and returns a clear persistence-not-configured response rather than pretending users are permanently stored.
- `InMemoryUserRepository` exists only as an explicitly injected test fake.
- `AuthService` owns registration, password verification, active-user checks, and token issuance.
- Authentication routes remain thin and delegate to the service/dependencies.

## Endpoints Added

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/auth/me
```

## Files Added or Changed

Added authentication security, schemas, repository contract/fake, service, dependencies, router, and comprehensive tests under `backend/app/` and `backend/tests/`.

Updated:

- `backend/app/main.py`
- `backend/app/core/config.py`
- `backend/app/core/exceptions.py`
- `backend/app/api/v1/router.py`
- `backend/requirements.txt`
- `backend/.env.example`
- `backend/README.md`

## Validation

- Python: 3.11.9.
- Full pytest suite: **19 passed, 0 failed**.
- Manual registration: **PASS**.
- Manual login: **PASS**.
- Manual `/auth/me`: **PASS**.
- Manual unauthorized role denial: **PASS**.
- Manual authorized role access: **PASS**.
- Uvicorn startup: **PASS**.
- Existing `/health` and `/api/v1/health`: **PASS**, HTTP 200.
- Import validation: **PASS**.
- Bytecode compilation: **PASS**.
- `pip check`: **PASS**.
- Prohibited future-phase dependencies: **none found**.

The test stack emitted two non-blocking deprecation warnings from the installed Starlette/HTTPX/AnyIO versions.

## Known Limitations

- Users are not persistently stored until the MongoDB repository is implemented.
- No server-side logout/revocation store exists yet.
- Rate limiting and complete audit-event persistence remain future work.
- Authentication is not being claimed as a complete production security audit.

## Next Step

Proceed to **Phase 2 — Database Foundation** only after explicit instruction. Implement MongoDB and Cassandra with documented workload boundaries, then replace the unavailable user repository with a MongoDB adapter without changing the authentication service contract.

---

# 27. Phase 2 - Database Foundation - 2026-09-10

## Status

**Implemented and validated.** This phase established the MongoDB and Cassandra boundaries required by the architecture. It did not implement wallets, payments, subscriptions, ML, notifications, or forensic workflows.

## Database Responsibilities

- MongoDB is the operational and investigation-document store.
- Cassandra is the chronological event store.
- `DatabaseManager` owns connection lifecycle, safe dependency health checks, and schema initialization.
- Database driver details do not leak into API routes or authentication services.

## MongoDB Foundation

- Added configurable URI, database name, and connection timeouts.
- Added the nine initial collections from `Phases.md`.
- Added explicit uniqueness and workload indexes for users, accounts, merchants, transactions, subscriptions, cases, evidence, findings, and audit records.
- Added `MongoUserRepository`, which implements the existing Phase 03 `UserRepository` contract without changing `AuthService`.
- Duplicate email and database failures map to safe application errors.

## Cassandra Foundation

- Added configurable hosts, port, keyspace, credentials, timeout, and replication factor.
- Added query-first event tables partitioned by identifier and UTC event day: `authentication_events_by_user_day`, `session_events_by_user_day`, `device_events_by_device_day`, `transaction_events_by_account_day`, and `audit_events_by_case_day`.
- Added `CassandraEventRepository` for append and bounded partition/time-range queries.
- Event payloads are stored as JSON text; event timestamps are normalized to UTC.

## API and Configuration

- Added `GET /api/v1/health/dependencies` for safe MongoDB/Cassandra readiness status.
- Added database settings to `backend/.env.example` using the `SPENDSHIELD_` prefix.
- The application uses the MongoDB-backed user repository when a MongoDB URI is configured; otherwise it retains the explicit unavailable adapter.

## Validation

- Python: 3.11.9.
- Full pytest suite: **22 passed, 2 skipped, 0 failed**.
- Dependency health endpoint with unconfigured databases: **PASS**.
- MongoDB/Cassandra schema and CRUD/query integration tests are enabled with isolated namespaces.
- Local MongoDB was reachable during validation.
- Cassandra integration cases were skipped because no local Cassandra server was listening on `127.0.0.1:9042`; the skip is limited to external-service tests.
- `pip check`: **PASS** after installing `pymongo` and `cassandra-driver`.

## Known Limitations

- Cassandra service startup/configuration is not included in the repository; integration tests require an available Cassandra server.
- Schema initialization is exposed through `DatabaseManager`; automatic application startup migrations are intentionally not added yet.
- Seed/demo data strategy remains reserved for the appropriate domain phase.

## Next Step

Proceed to **Phase 3 - Wallet & Account System**. Use the existing repository and database boundaries, and keep authoritative account/balance state in the backend.

---

# 28. Non-Database Architecture and Financial Repair - 2026-09-11

## Status

**Implemented as a focused repair slice.** The existing MongoDB/Cassandra foundation was preserved. The work added backend/domain architecture around it without claiming that payment settlement, ML, or forensic workflows are complete.

## Repairs Implemented

- Added production/staging configuration guards for debug mode, placeholder authentication secrets, and trusted hosts.
- Added strict JWT issuer/audience claims and validation.
- Added request IDs and baseline security response headers.
- Added persistence-neutral `Account`, `Transaction`, `PaymentCommand`, and `PaymentExecution` domain objects.
- Added exact decimal money normalization, account status rules, insufficient-funds rules, explicit transaction transitions, balance-before/after values, and idempotency request fingerprints.
- Added backend-authoritative account creation and reads with UUID IDs and owner/admin object authorization.
- Added MongoDB account repository using the existing `accounts` collection and indexes.
- Added canonical `DomainEvent` envelope and Cassandra publisher adapter while preserving the existing Cassandra schema.
- Added a payment repository/service boundary and test-only atomic in-memory implementation. No public payment endpoint was added before production atomic persistence and event publication were available.

## Files Added or Changed

- Added `backend/app/domain/financial.py`.
- Added `backend/app/events/models.py` and `backend/app/events/publishers.py`.
- Added `backend/app/repositories/accounts.py` and `backend/app/repositories/payments.py`.
- Added `backend/app/services/account_service.py` and `backend/app/services/payment_service.py`.
- Added `backend/app/api/v1/accounts.py` and `backend/app/schemas/accounts.py`.
- Added `backend/app/core/middleware.py`.
- Updated application configuration, JWT handling, app wiring, dependencies, and tests.
- Added `security_best_practices_report.md`.

## Validation

- Domain/account/event/payment focused tests: **13 passed**.
- Existing authentication/health tests after security changes: **23 passed**.
- Full suite before the Phase 3 status/audit slice: **39 passed, 2 skipped, 0 failed**.
- The two skipped cases are Cassandra integration tests; Cassandra was unavailable at `127.0.0.1:9042`, so no Cassandra integration success is claimed.
- `pip check`: **PASS**. Python bytecode compilation: **PASS**.
- MongoDB account CRUD is covered when local MongoDB is reachable.

## Remaining Known Limitations

- No public payment route exists yet.
- No production MongoDB payment repository with atomic state-plus-transaction behavior exists yet.
- Account creation and status changes now write replay-safe canonical audit records to MongoDB; account-to-Cassandra historical publication remains intentionally unwired until an account-event query model is selected. A generic durable publication boundary was added in the later validation slice.
- State persistence and audit insertion are separate operations and are not yet an atomic outbox transaction.
- Rate limiting, refresh/revocation, MFA, frontend, ML, forensics, deployment, and CI/CD remain future work.

## Next Step

Make Cassandra available and run the blocked integration tests, then record the real result before advancing to the next phase.

---

# 29. Phase 3 Account Status and Audit Completion - 2026-09-11

## Status

**Implemented as a focused Phase 3 slice; phase remains partial.** Account
status transitions, admin authorization, optimistic version checks, replay-safe
MongoDB audit records, and the generic durable event-delivery boundary are
implemented. Balance history, account-to-Cassandra routing, and the frontend
wallet remain pending. Cassandra validation is now complete against the live
local service.

## API Changes

- Added `PATCH /api/v1/accounts/{account_id}/status`.
- Added `version` to the account response.
- Added a strict status-update request schema with optional expected version and
  bounded reason.

## Database Changes

- Added a justified unique `accounts.user_id` index to enforce one account per
  owner.
- Added the account audit-record adapter using the existing MongoDB
  `audit_records` collection.
- No Cassandra table, keyspace, or partition design was changed.

## Security and Audit Changes

- Only administrators may change account status.
- Allowed transitions are `ACTIVE ↔ SUSPENDED`, `ACTIVE → CLOSED`, and
  `SUSPENDED → CLOSED`; `CLOSED` is terminal.
- Account creation and status changes store actor, subject, request
  correlation, transition details, outcome, and provenance.

## Validation

- Focused Phase 3 tests remain a partial slice; the full boundary validation
  now covers live MongoDB/Cassandra integration.
- Final full suite after the boundary repair: **52 passed, 0 skipped, 0 failed**.
- Cassandra 4.0.21 was reachable at `127.0.0.1:9042` and reported `UN` via
  `nodetool status`.

---

# 30. Cassandra Validation and Durable Event Boundary - 2026-09-11

## Status

**Implemented and validated as a focused foundation slice.** The existing
MongoDB and Cassandra responsibilities were preserved. No public payment API,
new database, broker, or Cassandra table was added.

## Observed Environment

- Cassandra 4.0.21 is running in the prescribed WSL environment with Java 8.
- `nodetool status` reports one `UN` node at `127.0.0.1`.
- CQL is reachable on `127.0.0.1:9042`.
- The existing five-table schema initializes successfully after fixing the
  duplicate `device_id` declaration in the device table generator.

## Event Architecture

The pre-change account flow was:

```text
API → AccountService → domain rule → MongoDB account state → MongoDB audit
```

The Cassandra publisher existed but was not wired to that flow. The repair
adds a durable publication status to routed MongoDB audit records and an
explicit delivery service:

```text
MongoDB state → MongoDB audit/publication record → delivery retry → Cassandra
```

The exact event envelope is replayed using its event ID. A failed delivery can
be retried without rerunning the state-changing operation. Financial request
idempotency remains a separate concern from event-delivery idempotency.

## Consistency Guarantee and Limitation

The publication record is durable and retryable, but the current standalone
MongoDB deployment cannot atomically commit the account document and the audit
record. If the account write succeeds and the audit insert fails, the state
may exist without a publication record; the service reports the persistence
failure and the limitation is documented. Account events are intentionally
not sent to Cassandra until an existing query-specific Cassandra route is
selected.

## Validation

- Full suite: **52 passed, 0 failed, 0 skipped**.
- Real MongoDB→Cassandra publication test: passed.
- Retry and duplicate-event tests: passed.
- Correlation, causation, request provenance, and event identity assertions:
  passed.
- Python compilation and existing security/account/payment tests: passed.

## Next Step

Implement the atomic MongoDB payment state-plus-transaction repository and
enqueue a transaction event targeting the existing
`transaction_events_by_account_day` model; keep the public payment route
closed until that slice is tested.

# 31. Transaction and Payment Persistence Foundation - 2026-09-11

## Status

**Implemented as a closed, tested persistence foundation; public payment API
NOT READY.** No MongoDB or Cassandra redesign, broker, or payment route was
introduced.

## Current MongoDB Capability

Live validation observed MongoDB 8.3.4 as writable but standalone:
`setName=None`, with logical sessions available but no replica-set transaction
topology. The production adapter therefore reports
`standalone_optimistic_compare_and_set`; it does not claim multi-document
atomicity.

## Payment Persistence

`MongoPaymentRepository` uses the existing `accounts` and `transactions`
collections. It creates a unique owner/idempotency reservation, stores the
expected account version and balances, conditionally updates the account, and
finalizes the transaction. A retry can distinguish the expected post-debit
state from an unchanged reservation. Ambiguous concurrent changes are rejected
without applying another debit.

The current fictional payment contract retains the existing optional
`merchant_id`. No `destination_account_id` or peer-transfer behavior was
invented because the repository and product documents do not define that
contract.

## Event Boundary

On completion or rejection, the repository creates one canonical event with a
stable event ID and stores it through the existing MongoDB audit repository as
a pending publication targeting `transaction_events_by_account_day`. The
existing `EventDeliveryService` retries that exact envelope into Cassandra.
Request idempotency and event-delivery idempotency remain separate. Cassandra
stores history only; MongoDB remains authoritative for current balance and
transaction state.

## Validation

- Live Cassandra: 4.0.21, reachable on `127.0.0.1:9042`, one `UN` node.
- Live MongoDB: 8.3.4, standalone, writable.
- Payment-focused integration tests: **3 passed**.
- Full backend suite: **55 passed, 0 failed, 0 skipped**.
- Warnings: 3 dependency deprecation warnings.
- Tested: idempotent replay, conflicting key, audit failure recovery,
  Cassandra publication, correlation/causation propagation, and concurrent
  800/700 overspend prevention.

## Remaining Limitation and Next Step

The configured development environment now uses the validated `rs0` MongoDB
transaction path. The standalone deployment remains an explicit fallback: a
process crash can leave a recoverable reservation, but that fallback cannot
claim a true atomic outbox. The exact next step is the internal/public payment
API boundary, not a database redesign.

# 32. MongoDB Replica-Set and Atomic Payment Boundary - 2026-09-11

## Environment

The existing Windows MongoDB 8.3.4 service was inspected:

- service: `MongoDB`, automatic, running as `NetworkService`;
- config: `C:\Program Files\MongoDB\Server\8.3\bin\mongod.cfg`;
- data: `C:\Program Files\MongoDB\Server\8.3\data`;
- port: `127.0.0.1:27017`;
- topology: standalone, `setName=None`.

The data path contains `StudentDB` and `ghost_job_detector` databases from
other local work. No existing data, service configuration, or data directory
was changed.

For validation, an isolated single-node MongoDB 8.3.4 process was started on
`127.0.0.1:27018`, initialized as replica set `rs0`, and used only with
project-generated test databases. It reached a writable primary state. This
is not production high availability.

## Atomic implementation

`MongoPaymentRepository` now selects the actual mode from MongoDB topology:

- `replica_set_mongo_transaction`: one MongoDB session transaction inserts the
  transaction, updates account balance/version, and inserts the audit record
  with Cassandra publication metadata;
- `standalone_optimistic_compare_and_set`: the prior reservation/recovery
  fallback, explicitly non-atomic across MongoDB documents.

Transient transaction write conflicts are retried up to three times. A
duplicate-key race replays the committed winner. Cassandra remains outside
the MongoDB transaction; delivery is performed later by
`EventDeliveryService`.

## Validation

- Replica-set commit test: passed.
- Replica-set rollback test: passed.
- Atomic payment persistence with publication metadata: passed.
- Injected publication failure rolled back account and transaction: passed.
- Same-key concurrent retry created one financial effect: passed.
- Concurrent ₹800/₹700 against ₹1,000: passed.
- Cassandra publication after MongoDB commit: passed.
- One initial full-suite run recorded 57 passed, 2 skipped, and 1 failed due to
  a transient Cassandra connection timeout; the affected Cassandra test passed
  on retry.
- Final full backend suite: **70 passed, 0 failed, 0 skipped** with 3 dependency
  deprecation warnings.

## Configuration

`Settings.mongodb_replica_set` and `DatabaseManager` now support an explicit
replica-set connection without changing existing timeout or repository
abstractions. The ignored development `.env` and `.env.example` select the
validated `rs0` endpoint, while documenting that the unrelated standalone
service on `27017` remains untouched.

# 33. SpendShield Development Environment Configuration - 2026-09-11

The actual backend development configuration now uses:

- `mongodb://127.0.0.1:27018/?replicaSet=rs0`;
- database `spendshield`;
- explicit `SPENDSHIELD_MONGODB_REPLICA_SET=rs0`;
- Cassandra `127.0.0.1:9042` for historical events.

The running application health path reports MongoDB endpoint, replica-set name,
and writable-primary status without exposing credentials or the raw URI. The
replica integration test also exercises the FastAPI dependency-health path and
confirms the real repository selects `replica_set_mongo_transaction`.

The development rs0 is a single-node instance under
`.mongodb-rs-validation`; it is not production high availability. The
existing standalone `127.0.0.1:27017` Windows service and its unrelated data
were not changed. Cassandra remains outside the MongoDB transaction boundary;
its historical publication is still a separate retryable operation.

# 34. Controlled Payment API Boundary - 2026-09-11

The authenticated payment API is implemented over the existing payment service
and repository without duplicating financial logic:

- `POST /api/v1/payments` creates a fictional payment with a required
  `Idempotency-Key`;
- `GET /api/v1/payments/{transaction_id}` returns only the authenticated
  owner's current MongoDB transaction state;
- `GET /api/v1/payments` returns bounded, stable, cursor-paged owner history.

The request cannot set balance, owner, actor, transaction ID, event ID, status,
timestamps, or publication state. The route verifies ownership through the
account service, constructs a `PaymentCommand`, and delegates mutation to
`PaymentService` and `MongoPaymentRepository`. Amounts are Decimal values with
at most two decimal places, UUID identifiers are validated at the API boundary,
and unknown/foreign transactions are returned as safe 404 responses.

After a successful MongoDB transaction, the service attempts the existing
`EventDeliveryService` pass. Cassandra remains a historical sink outside the
MongoDB transaction; failure leaves the stored event retryable and cannot repeat
the financial effect. The merchant ID is currently an opaque bounded reference;
the Merchant System and category rules are the next domain phase.

Real HTTP integration tests pass against MongoDB `rs0` and Cassandra, including
authentication, ownership, validation, idempotency, history pagination,
rollback/business failures, same-key concurrency, and the ₹800/₹700 overspend
race.

# 35. Merchant and Category Domain Foundation - 2026-09-11

The Merchant and Category foundation is implemented and integrated with the
controlled payment API.

## Catalog model

- `CategoryRecord` represents a canonical category/subcategory pair with
  stable lowercase IDs, display names, active state, and timestamps.
- `MerchantRecord` represents current merchant state with a backend-generated
  UUID, normalized name, category/subcategory references, `ACTIVE`/`INACTIVE`
  status, timestamps, and an optimistic version.
- Categories are system-controlled. `app/seed/catalog.py` contains the small
  deterministic taxonomy and `backend/scripts/seed_catalog.py` is the explicit
  development command. Startup does not insert seed data.

## API and authorization

Implemented:

```text
GET    /api/v1/categories
GET    /api/v1/merchants
GET    /api/v1/merchants/{merchant_id}
POST   /api/v1/merchants              ADMIN only
PATCH  /api/v1/merchants/{merchant_id} ADMIN only
```

The existing `MERCHANT` role is read-only for this phase because no merchant
ownership relation exists in `UserRecord`. Deactivation is used instead of a
delete route. Listings are bounded, stably ordered, cursor-paged, and filtered
by status/category where requested.

## Payment integration and historical consistency

`PaymentService` now calls `MerchantService.resolve_for_payment` before the
existing repository transaction. Unknown, inactive, or invalidly categorized
merchants are rejected before any balance effect. The client supplies only a
merchant UUID; category data is derived server-side.

Transactions and canonical payment events store the resolved merchant ID plus
category/subcategory IDs and display-name snapshots. The snapshot is deliberate
historical denormalization: reclassifying a merchant changes future payments,
but does not rewrite completed transaction meaning. MongoDB remains authoritative
for current merchant/category state; Cassandra remains historical event data.

Merchant lifecycle audit facts are stored in MongoDB audit records. No merchant
Cassandra table, broker, new database, or analytics API was introduced.

## Validation

- Full backend suite after catalog integration: **76 passed, 0 failed, 0 skipped**.
- Live MongoDB `rs0` merchant/API integration: passed.
- Live MongoDB `rs0` payment integration with Cassandra delivery: passed.
- Merchant authorization, invalid-category, inactive-merchant, pagination,
  version-conflict, reclassification, and category-snapshot cases: passed.
- Python bytecode compilation: passed.
- `pip check`: passed.
# 36. Analytics Data Foundation and Read-Only Spending APIs - 2026-09-12
 
The first non-ML analytics slice is implemented over the existing Account, Payment, Merchant, and Category domains.
 
MongoAnalyticsRepository reads MongoDB transactions current state only; Cassandra is not used to calculate totals. AnalyticsService loads the authenticated owner's current account and keeps current balance separate from historical spending aggregates. Analytics use only COMPLETED transactions and a bounded half-open UTC period: 30-day default and 366-day maximum.
 
Implemented routes: GET /api/v1/analytics/spending/summary, /categories, /merchants, /trends, and /largest. Category and merchant grouping uses payment-time snapshots. New payments persist a merchant-name snapshot; legacy documents may have no merchant name.
 
All routes require bearer authentication; no user/account selector is accepted. Responses expose Decimal amounts, currency, UTC period, calculation basis, request ID, and safe spending projections only. Cassandra schema was not changed.
 
Known limitations: subscriptions, recurring commitments, balance history, upcoming commitments, spendable amount, currency conversion, anomaly scoring, forecasting, ML evaluation, and forensic analysis remain unimplemented. Reversal semantics are not yet defined; REVERSED records are excluded rather than guessed into a net total.

# 37. Evidence-Driven ML Dataset Audit and Notebook Foundation - 2026-09-12

The first ML phase is intentionally a dataset audit and baseline boundary, not
model training.

The live MongoDB rs0 development primary was available, but the
spendshield.transactions collection contained zero documents and zero
completed transactions. No fraud, human-review, or other verified target label
was present. The result is INSUFFICIENT_DATA with baseline status
BLOCKED_INSUFFICIENT_DATA.

Added:

- output/jupyter-notebook/01_dataset_audit.ipynb;
- output/jupyter-notebook/README.md;
- ML_DATASET_AUDIT.md.

The notebook is reproducible and read-only. It records application-operational
provenance, audits required fields and candidate labels, defines a
completed-transaction feature contract, excludes post-outcome/leaky fields,
and refuses to claim metrics when the dataset is empty or unlabelled.

No synthetic records were inserted. No model, model artifact, inference API,
ML dependency, Cassandra query model, or production risk decision was added.
MongoDB remains current operational state and Cassandra remains historical
event storage.
Final backend verification after the analytics implementation: **79 passed, 0 failed, 0 skipped**, with 3 dependency deprecation warnings. `pip check` and Python bytecode compilation passed.

# 38. Controlled Synthetic ML Dataset Generation and Validation - 2026-09-12

The operational dataset audit found zero current transaction documents and no
verified target labels. A separate research-only synthetic dataset was created
without reading or writing MongoDB or Cassandra.

Implemented:

- `ml/synthetic_dataset_generator.py` with a bounded fixed-seed generator and
  cross-file validator;
- `data/synthetic/` containing the full CSV, temporal train/validation/test
  CSVs, manifest, generation configuration, label dictionary, and limitations;
- generation notebook `output/jupyter-notebook/02_generate_synthetic_dataset.ipynb`;
- validation notebook `output/jupyter-notebook/03_validate_synthetic_dataset.ipynb`;
- generator tests covering schema, labels, leakage separation, temporal
  splits, writing, cross-file validation, and same-seed reproducibility.

Actual default artifact: 10,000 rows, 28 columns, 500 users, 500 accounts,
100 merchants, 12 categories, configured 90-day UTC coverage, and temporal
split counts of 7,061 train, 1,481 validation, and 1,458 test. Scenario counts
are 7,600 normal, 800 high amount, 600 rapid repeat, 600 unusual time, 300
behavior deviation, and 100 combined pattern.

Every record is marked `synthetic_research` with fictional `syn-*` identifiers.
Scenario labels are generator-rule labels, not fraud labels. Candidate
features exclude scenario metadata and future/post-event information. No model,
inference API, fraud classifier, blocking, notification, or production metric
was added.

Validation: generator tests **5 passed**; both notebooks executed
top-to-bottom successfully; the existing backend suite remains **79 passed,
0 failed, 0 skipped** with 3 dependency warnings; dependency checks passed.

The exact next step is deterministic candidate-feature preparation and a
research-only baseline evaluation using the generated dataset.

# 39. Deterministic Feature Matrix and First Research Baseline - 2026-09-12

The synthetic transaction files were converted into a separate candidate
feature artifact under `data/synthetic/features/`.

The matrix contains 28 model features: numeric transaction/history fields,
one missingness indicator, and one-hot categorical fields. Numeric imputation
and category vocabularies are fitted on training rows only. Identity,
timestamp, split, and `target_scenario_label` remain separate from the model
feature list. An independent audit confirmed that historical counts, averages,
category frequencies, and previous-transaction intervals use prior records
only, ordered by timestamp and then synthetic transaction ID.

The first baselines are a majority-class reference and a fixed
standard-library Gaussian Naive Bayes classifier. Final test metrics are:

- majority reference: accuracy `0.776406`, macro F1 `0.145688`;
- Gaussian Naive Bayes: accuracy `0.862826`, macro F1 `0.617953`, weighted F1
  `0.850388`.

These are synthetic scenario classification metrics, not fraud metrics. No
model artifact, inference route, fraud API, risk API, notification, blocking,
or production decision was added.

Added feature and baseline modules, tests, notebooks 04/05, manifests,
dictionaries, and research result JSON. ML tests: **9 passed**. The exact next
step is controlled error analysis and evaluation-protocol review before any
more complex model or model export.

## Controlled ML Error Analysis and Evaluation Review - 2026-09-12

Added `ml/error_analysis.py` and its regression tests, plus executed notebook
`output/jupyter-notebook/06_error_analysis.ipynb`. The module reproduces the
stored Gaussian Naive Bayes baseline before error analysis and writes reports
under `data/synthetic/error_analysis/`.

Observed final test metrics remain accuracy `0.862826`, macro F1 `0.617953`,
and weighted F1 `0.850388`. The review found 131 synthetic-pattern false
negatives, 53 false positives against normal, and 16 cross-scenario
confusions. Rapid-repeat test recall is `1.0`; unusual-time recall is
`0.285714`; behavior-deviation recall is `0.222222`; combined-pattern recall
is `0.368421` with 19 test rows.

The leakage review passed for prior-only history, deterministic tie-breaking,
training-only preprocessing, target/metadata exclusion, test isolation, and
temporal partitions. The validation-only shortcut review found exact or
near-exclusive generator rules for rapid-repeat and unusual-hour scenarios.
The generator and dataset were not modified. Current decision:
`DATASET_OR_GENERATOR_REVIEW_REQUIRED_FIRST`.

This remains synthetic scenario classification research. It is not a fraud
detector, production risk model, human decision, payment control, or
inference API. No backend, database, payment, frontend, or operational data
changed in this phase.

## Versioned Synthetic Generator Revision and Comparison - 2026-09-12

Preserved v1 and added v2 under `data/synthetic/v2/`. The revised artifact uses
generator `1.1.0`, feature version `1.1.0`, baseline version `1.1.0`, and seed
`20260913`. It contains 10,000 rows, 500 fictional users/accounts, 100
fictional merchants, 12 categories, INR-only values, and six synthetic
scenario classes with distribution 6,800 / 1,000 / 800 / 700 / 500 / 200.

The v2 generator introduces normal late-hour, short-gap, higher-amount,
category, merchant, and channel variation. Scenario generation uses partial
and probabilistic signals. The candidate matrix contains 32 features,
including prior-only merchant novelty, channel novelty, user-relative amount
deviation, and user-relative time deviation. The feature dictionary records
definitions and leakage status.

Validation-only v2 shortcut rates are: rapid-repeat <=600 seconds `0.233871`,
unusual-time fixed global-hour window `0.333333`, combined-pattern global-hour
window `0.166667`, combined fixed late-hour + <=600-second + >=3x amount rule
`0.0`, normal late-hour overlap `0.246646`, normal <=600-second
overlap `0.034056`, and behavior-deviation candidate-signal coverage
`0.976744`. No v2 shortcut review is near-perfect; checksums, reproducibility,
temporal integrity, and leakage review pass.

The v2 Gaussian baseline test metrics are accuracy `0.703673`, macro F1
`0.262793`, and weighted F1 `0.651407`, lower than v1 because the revised
dataset is harder. Final decision:
`REVISED_DATASET_READY_FOR_NEXT_ML_PHASE`. The exact next step is controlled
research-only anomaly-detection and explainability evaluation. No production
ML, fraud claim, backend, database, payment, or mobile implementation was
added.

## Controlled Research-Only Anomaly Detection and Explainability - 2026-09-12

The v2 feature artifact now has a separate anomaly-research artifact under
`data/synthetic/anomaly_detection/v2/`. The established backend virtual
environment did not contain scikit-learn, so the phase uses the explicitly
allowed dependency-free `robust_mad_distance` model rather than adding a new
dependency. It fits 12 numeric/prior-only fields on train only. The score is a
training min-max-normalized mean capped robust distance; higher means more
anomalous within this fixed configuration, not a probability or decision.

Training score percentiles are the only thresholds: p90 `0.518579`, p95
`0.740225`, p99 `0.787968`. Validation/test synthetic-only ROC-AUC/AP are
`0.562733/0.417902` and `0.553095/0.367124`. The results show weak ranking
signal and substantial normal/scenario overlap; they are not real-world
metrics. A separate fixed weighted signal baseline and deterministic
feature-grounded explanations were added. The bounded 20-row explanation
sample passed safety and determinism validation.

Added `ml/anomaly_detection.py`, `ml/explainability.py`, their focused tests,
required anomaly artifacts, and notebooks 11/12. No FastAPI route, model
serving, MongoDB/Cassandra write, payment behavior, production inference,
investigator decision, or frontend change was made. The exact decision is
`ANOMALY_EVALUATION_READY_FOR_BACKEND_RESEARCH_INTEGRATION`, with the next
step limited to a read-only backend research integration with safeguards.

## Research-Only Anomaly Backend Integration - 2026-09-12

The backend now contains `app/services/research_anomaly_service.py`, explicit
research response schemas, and `GET /api/v1/research/anomaly-score/{id}`,
`GET /api/v1/research/anomaly-scores`, and the explanation subroute. Routes
are bearer-authenticated and owner-scoped. The service loads only validated
JSON artifacts from the configured v2 directory and never trains, regenerates,
writes databases, publishes events, or invokes payment execution.

`anomaly_model_parameters.json` was added to the existing v2 research artifact
to serialize the already-fit medians, robust scales, and raw-score bounds.
This is artifact serialization, not backend training. The model remains the
dependency-free `robust_mad_distance` research model with 12 features, higher
score meaning more anomalous, and train-only percentile thresholds that are
not decisions or probabilities.

`PaymentRepository` now also exposes a bounded prior-only completed-history
window for future feature parity. Current payment transactions contain no
approved `transaction_channel` field, so the live service refuses to invent
that required context. Single-score/explanation requests return a controlled
feature-contract unavailable error; bounded lists mark rows unavailable. This
is the honest current state, not a production anomaly service.

Validation executed: backend tests **62 passed, 26 skipped, 0 failed** with 3
existing dependency warnings; ML tests **28 passed**; anomaly artifact
validation is valid with 12 features and serialized parameters. Cassandra was
not changed by this phase.

## Infrastructure and Live Anomaly Scoring - 2026-09-13

**Implemented and live-validated.** The supported local MongoDB and Cassandra
services were restored without deleting data. MongoDB 8.3 responds as writable
primary `rs0` at `127.0.0.1:27018`; Cassandra 4.0.21 reports one `UN` node at
`127.0.0.1:9042`. The existing `spendshield_events` keyspace and five event
tables are reachable.

`transaction_channel` is now required for new payment requests and is carried
through `PaymentCommand`, the current `Transaction`, MongoDB transaction
documents, payment responses, canonical transaction event payloads, and the
idempotency fingerprint. The approved values are `QR_SIMULATED`,
`CARD_SIMULATED`, `WALLET_SIMULATED`, and `BANK_SIMULATED`. Legacy documents
without the field load as `None`; no unsafe migration or invented value was
performed.

Live research feature construction now reads channels from persisted completed
operational transaction history. It enforces strict prior-only selection,
timestamp-plus-transaction-ID ordering, target exclusion, and explicit
unavailability for missing legacy channel data. Synthetic data is not mixed
with operational history. The score, listing, and explanation routes remain
authenticated, owner-scoped, read-only, non-blocking research APIs.

Validation in this phase included the focused channel/research tests, the real
MongoDB/Cassandra payment API path, and a live three-payment anomaly scoring
flow. The ML artifact directory was not regenerated or modified.

## React Native and Expo Mobile Foundation - 2026-09-14

Created `mobile/` as an Expo SDK 57 TypeScript app using React Native 0.86.3,
React 19.2.3, typed native-stack navigation, `react-native-safe-area-context`,
and Expo SecureStore. The app is configured as SpendShield with Android package
`com.spendshield.mobile` and version `0.1.0`. It contains Splash, Welcome,
Login, Registration, and an authenticated Dashboard placeholder. No payment,
QR, transaction-history, subscription, notification, analytics, anomaly, or APK
feature was added.

The mobile API foundation uses the existing `/api/v1/auth/register`,
`/api/v1/auth/login`, and `/api/v1/auth/me` contracts. The API base URL is
centralized through `EXPO_PUBLIC_API_BASE_URL` with an Android-emulator
development default; no secret is stored in the app. Login/registration are
real backend calls when the configured backend is reachable, and session data
is persisted in SecureStore. The dashboard deliberately displays no fabricated
financial state.

Validation for this phase: TypeScript **passed**; Expo dependency check
**passed**; Expo Doctor **21/21 passed**; Expo config resolution **passed**;
Android Metro bundle **passed** (HTTP 200, 873 modules, no module-resolution or
transform errors); backend regression suite **65 passed, 27 skipped, 0 failed**.
The skipped backend tests are dependency-gated. MongoDB at `127.0.0.1:27018`
and Cassandra at `127.0.0.1:9042` were not listening in this session, and no
Expo Go or physical Android device was available, so live mobile authentication
and device rendering are not claimed as validated. ML artifacts and backend
business logic were unchanged.

## Demo banking modules and UI repair - 2026-09-16

The repository now supports explicit multiple fictional BJP Bank accounts,
server-authoritative demo deposit/withdrawal, owner-scoped self-transfer,
phone and bill/recharge simulation contracts, and MongoDB current-state CRUD
for contacts, beneficiaries, billers, cards, and local notifications. The
existing MongoDB/Cassandra boundary remains unchanged: MongoDB owns current
state and Cassandra owns historical events.

The mobile app includes Ionicons, actionable bottom navigation, contact and
phone payment flows, bills/recharges, account operations, account selection,
and local QR image decoding. Full profile/MPIN/admin surfaces, automatic
notification generation, complete resource management UI, device verification,
and mobile test/lint configuration remain follow-up work.

Earlier live verification passed for MongoDB `rs0`, Cassandra, backend health,
and the demo API smoke flow while the manually started services were running.
The final backend regression rerun produced `74 passed, 27 skipped, 0 failed`;
the skips were dependency-gated because the services were no longer listening.
Mobile TypeScript passed; Expo Doctor `21/21`; Android export passed with 944
modules. A final read-only connectivity check found only the untouched
MongoDB `27017` listener, so current live verification requires manual service
restart using `Start.txt`.

## Persisted demo merchant QR and module completion - 2026-09-16

The current implementation adds MongoDB current-state `demo_merchants` and
`demo_security` collections. The seeded classroom merchants are
`MODI-CHAI-001` and `MELONI-CHOCO-002`. Version-1 QR payloads are generated
from registry state and are resolved server-side during validation and payment.
Registered QR payments require a hashed six-digit demo MPIN, preserve the
existing payment idempotency/event boundary, and return backend balance
before/after values. No real payment network is involved.

Profile editing, card controls, notification center/actions, and the mobile QR
display/payment flow are now wired to backend contracts. Automatic notifications
are owner-scoped MongoDB current state and are not SMS, email, or push alerts.
Card payments are fictional and check active status, ownership, limit, funds,
and idempotency.

Latest offline verification: full backend `76 passed, 27 skipped, 0 failed`;
focused QR/security/demo coverage `22 passed`; TypeScript passed; Expo Doctor
`21/21`; Android export passed with 1,262 modules. Final port inspection found
only untouched MongoDB `27017`; SpendShield MongoDB `27018`, Cassandra `9042`,
and backend `8000` were not listening. Live merchant/QR/MPIN integration and
device scanning therefore still require manual service/device verification.

## Prompt 2 demo banking modules and navigation repair - 2026-09-17

Implemented fictional server-backed recharge and subscription foundations,
without real banking/provider integrations or database redesign.

- Backend catalogs and APIs: `/recharge/operators`, `/recharge`,
  `/subscriptions/platforms`, `/subscriptions`, and subscription status.
- Catalogs: Airtel, Jio, Vi, BSNL; BJPPrime and BJP Entertainments; all plans explicitly
  demo-only.
- Recharge/subscription creation is authenticated, owner-scoped, MPIN-protected,
  idempotent, and uses the existing payment service for balance, transaction,
  audit, notification, and historical event behavior.
- Subscription current-state values are stored in Mongo-compatible formats and
  subscription idempotency has a sparse unique index. A payment and the
  subscription document are still separate application commits; reconciliation
  remains a known limitation after a process failure.
- All sensitive demo payment routes now require the existing six-digit hashed
  demo MPIN, including generic, QR, phone, bill, transfer, and account
  operations. QR validation is read-only and does not require a charge PIN.
- Sensitive virtual-card mutations (freeze/unfreeze/block, card PIN, and
  spending limit) now use the same owner-scoped MPIN boundary.
- Authenticated `POST /api/v1/demo-security/mpin/reset` re-authenticates with
  the account password, clears only the demo MPIN hash/lock state, and permits
  creation of a replacement MPIN.
- Mobile Pay Merchant uses the persisted demo merchant QR registry. QR amount
  entry is gated on merchant identification. Existing phone, bill, transfer,
  and account-operation screens now collect MPIN.
- Mobile added Recharge and Subscriptions routes/screens, protected account
  reference/unlock usage, organized More sections, and a three-slide working
  dashboard carousel.

Verification in this phase: Python compilation passed; focused lifestyle live
test passed; focused regression repair tests passed; TypeScript passed; Expo
Doctor `21/21`; Android Metro export passed; full backend regression was
`76 passed, 0 failed, 28 skipped` with three existing dependency deprecation
warnings. The skipped tests are dependency-gated cases.
No mobile automated test runner is configured. Manual Expo Go/device checks
remain required.

The requested existing-account balance of `10000000000` was not directly
written. Such a mutation would bypass SpendShield's financial rules and audit
boundary, and exceeds the existing `1000000.00` demo operation cap. An explicit
audited demo-funding decision is still required.

Final read-only service check after this phase found only the unrelated
MongoDB `27017` listener. SpendShield MongoDB `27018`, Cassandra `9042`, and
backend `8000` were stopped/unreachable, so current health and device/live
verification are blocked until the commands in `mobile/Start.txt` are run.
No service was started or stopped by Codex.

The MPIN reset service test passed. Live reset remains pending until MongoDB
`27018` and backend `8000` are manually started.

## Mobile presentation terminology cleanup - 2026-09-18

User-facing mobile copy no longer uses the word "Demo" in labels, actions,
payment/QR instructions, security and card messages, shared error alerts, or
fallback payment errors. The copy uses fictional and simulation-only wording so the no-real-money
boundary remains explicit.

Internal route, API, type, payload, and safety identifiers containing demo
remain unchanged for compatibility. No backend code, authentication or payment
logic, database configuration/data, or ML artifact was changed for this
presentation-only cleanup.

Mobile verification passed: TypeScript, Expo Doctor 21/21, and Android Metro
export. No mobile automated test runner is configured. A read-only check later
found all expected ports reachable and backend health/dependency endpoints
returned HTTP 200; services were started externally, not by this session.
Live device verification remains dependent on the manual startup sequence in
Start.txt.

## Mobile backend reachability and development host repair - 2026-09-18

Expo Go was reaching FastAPI but receiving HTTP 400 because the backend
environment still allowlisted the previous LAN address 10.185.191.245 while
mobile/.env.local used the current address 10.165.59.245. The rejection came
from TrustedHostMiddleware and was surfaced by the mobile client as a
development-host error.

SPENDSHIELD_ALLOWED_HOSTS is now the canonical host-list setting, with legacy
SPENDSHIELD_TRUSTED_HOSTS compatibility. The development list contains
localhost, 127.0.0.1, 0.0.0.0, and 10.165.59.245. Non-development environments
still require explicit non-wildcard host configuration.

Login and registration now show a safe development connection diagnostic with
the credential-free API base URL and status-aware network/HTTP guidance.
Mobile API status messages cover 401, 403, 404, 422, 500, and 503 without
exposing credentials.

Validation passed: backend compile, health tests 14 passed, full backend
regression 107 passed/0 failed, LAN health/dependency/docs checks, LAN
registration 201, LAN login 200, mobile TypeScript, Expo Doctor 21/21, and
Android export with 1,266 modules. One uniquely named diagnostic user was
created by the live registration check; no data was deleted or reset.

## Demo QR payment contract repair - 2026-09-18

The live `fictional_payment_details_invalid` QR failure was caused by an
incomplete transaction category snapshot, not by QR decoding or MPIN
verification. Versioned QR payment construction supplied `category_name` but
not the required `category_id`, `subcategory_id`, and `subcategory_name`, so
`PaymentCommand` rejected the request. The route then returned a generic
`invalid_demo_payment_request` response.

QR payments now derive a complete stable demo-local category snapshot from the
registered merchant. The versioned QR validator requires the canonical QR type
and `simulation_only` marker. Invalid QR inputs receive safe specific error
codes/messages, and validation logging excludes QR payloads and all secrets.
Mobile QR manual review now uses the current parsed merchant rather than a
stale state value, and the direct merchant payment success view displays the
backend transaction status and timestamp.

Verification: backend compile passed; focused QR/payment/MPIN tests passed
9/9; full backend regression passed 109/109 with three existing dependency
warnings; live Modi and Meloni QR payments completed; idempotent replay
returned the same transaction without a second deduction; wrong MPIN returned
401; mobile TypeScript passed; Expo Doctor passed 21/21; Android export passed
with 1,266 modules. Device camera/gallery and full Expo Go flow remain manual
verification items. No services were started or stopped, and no database data
was deleted or reset.

## Final consolidated repair continuation - 2026-09-18

Home shortcut routing was audited and repaired. Transaction history remains a
live owner-scoped API screen. Check bank balance now opens the existing
backend-MPIN-protected account details flow instead of a disabled placeholder.
Refresh account calls the authenticated account endpoint again and presents
progress and server-refresh feedback. The three-slide dashboard carousel has
real slide content, swipe/snap behavior, working dots, and distinct actions.

The fictional subscription catalog now exposes `BJPPrime` and `BJP
Entertainments`, matching the current product contract. No real OTT service or
recurring billing was introduced.

The payment service now emits deterministic owner-scoped `PAYMENT_FAILED`
notifications for service-level financial failures. Notifications are safe and
retryable: they contain only the stable failure category and do not persist raw
MPINs, credentials, tokens, amounts, or idempotency keys. MPIN and request
validation failures that occur before the payment service have no financial
transaction and continue to be returned as API errors rather than fabricated
payment records.

Continuation verification: targeted backend payment/API tests passed `16/16`;
backend compilation passed; full backend regression passed `110/110` with
three existing dependency warnings and no skips while services were reachable;
mobile TypeScript passed; Expo Doctor passed `21/21`; Android export passed
with 1,266 modules. Read-only live checks confirmed MongoDB `27018` as a
writable `rs0` primary, Cassandra `UN` at `127.0.0.1`, backend health,
dependency health, and docs HTTP 200, including a request using
`Host: 10.165.59.245:8000`. No services were started or stopped and no
database data was reset or deleted.
