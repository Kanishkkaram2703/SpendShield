# Phases

## Project
**SpendShield — Intelligent Payment, Financial Awareness & Digital Forensics Platform**

## Purpose

This document defines the development sequence for SpendShield.

The project must be built incrementally. Each phase must produce a working, testable result before dependent work begins.

---

# Phase 0 — Project Foundation

## Objective

Create the development foundation before implementing business features.

## Tasks

- Create repository structure.
- Create frontend application.
- Create FastAPI backend.
- Create environment configuration.
- Create development documentation.
- Configure Git.
- Add `.gitignore`.
- Create basic health endpoint.
- Establish coding conventions.
- Create initial test structure.

## Deliverables

```text
Frontend starts
Backend starts
Health endpoint works
Environment configuration works
Repository structure exists
```

## Acceptance Criteria

```text
GET /health
        ↓
200 OK
```

No secrets are committed.

---

# Phase 1 — Authentication & Roles

## Objective

Build secure identity and authorization foundations.

## Tasks

- Registration.
- Login.
- Logout/session handling.
- Password hashing.
- Role model.
- Protected API routes.
- Frontend route protection.
- User status.

## Roles

```text
USER
INVESTIGATOR
MERCHANT
ADMIN
```

## Acceptance Criteria

- User can register.
- User can log in.
- Incorrect credentials are rejected.
- Protected routes require authentication.
- Unauthorized roles cannot access restricted resources.

---

# Phase 2 — Database Foundation

## Objective

Establish MongoDB and Cassandra correctly before building complex features.

## MongoDB

Create initial collections for:

```text
users
accounts
merchants
transactions
subscriptions
cases
evidence
findings
audit_records
```

## Cassandra

Create event-oriented tables such as:

```text
authentication_events
session_events
device_events
transaction_events
audit_events
```

## Tasks

- Connection management.
- Configuration.
- Repository layer.
- Health checks.
- Indexes.
- Cassandra partition design.
- Seed/demo data strategy.

## Acceptance Criteria

Both databases connect successfully and CRUD/query tests pass for their intended workloads.

---

# Phase 3 — Wallet & Account System

## Objective

Create the fictional financial foundation.

## Features

- Account creation.
- Dummy starting balance.
- Balance display.
- Account status.
- Account details.
- Balance history where useful.

## Rules

The backend owns balance state.

The frontend must never calculate the authoritative balance.

## Acceptance Criteria

A newly created account receives the configured demo balance and displays it correctly.

## Current Implementation Status - 2026-09-11

Partially implemented. The backend now provides authenticated account creation,
backend-controlled initial balance/currency/status, owner/admin account reads,
admin-only status transitions with optimistic version checks, MongoDB account
persistence, MongoDB audit records, exact money rules, and account-focused
tests.

Still pending for this phase: balance history and the frontend wallet
experience. Cassandra-dependent validation remains blocked until a local
Cassandra service is available; no Cassandra integration success is claimed.

---

# Phase 4 — Merchant & QR System

## Objective

Create the fictional merchant ecosystem.

## Tasks

- Merchant creation.
- Merchant status.
- Merchant categories.
- QR payload generation.
- QR scanning.
- QR validation.
- Merchant resolution.

## Flow

```text
QR
 ↓
Decode
 ↓
Validate
 ↓
Merchant Lookup
 ↓
Payment Screen
```

## Acceptance Criteria

A valid controlled QR resolves to the correct fictional merchant.

Invalid/unsupported QR values are rejected safely.

---

# Phase 5 — Payment Engine

## Objective

Implement reliable simulated payments.

## Flow

```text
Payment Request
 ↓
Authentication
 ↓
Authorization
 ↓
Merchant Validation
 ↓
Amount Validation
 ↓
Balance Validation
 ↓
Transaction Creation
 ↓
Balance Update
 ↓
Event Creation
 ↓
Receipt
```

## Tasks

- Payment API.
- Transaction state.
- Idempotency strategy.
- Balance consistency.
- Payment PIN/authentication.
- Failure handling.
- Audit event.

## Acceptance Criteria

A valid payment updates the account and creates exactly one valid transaction.

Failed payments must not incorrectly deduct money.

## Current Implementation Status - 2026-09-11

Payment settlement is intentionally not exposed yet. Persistence-neutral
transaction lifecycle, money, balance, and idempotency rules exist with
an implemented MongoDB persistence boundary. The repository uses a unique
transaction reservation, optimistic account compare-and-set, stable event
identity, and staged recovery; it was integration-tested with live MongoDB and
the existing Cassandra transaction-event table. Because the local MongoDB is
standalone, this is not a claimed multi-document transaction. The payment API
remains closed until the replica-set transaction path is implemented and
validated.

## Transaction Persistence Validation - 2026-09-11

Implemented and tested:

- current account and transaction state in MongoDB;
- exact Decimal money and existing lifecycle rules;
- owner/account/status/currency/funds checks;
- unique request idempotency and conflict detection;
- account version compare-and-set preventing concurrent overspend;
- recovery after an event/audit enqueue failure without a second debit;
- canonical transaction event creation with actor, correlation, causation,
  provenance, and stable event identity;
- retryable delivery to the existing
  `transaction_events_by_account_day` Cassandra model.

Not implemented and intentionally withheld:

- public `POST /payments` API;
- replica-set MongoDB transaction path;
- payment settlement, external processor integration, QR payments, or
  destination-account transfers.

---

# Phase 6 — Transaction History & Receipts

## Objective

Make financial activity observable.

## Features

- Transaction list.
- Search.
- Filters.
- Sorting.
- Transaction detail.
- Receipt.
- Date range.
- Merchant filter.
- Category filter.

## Acceptance Criteria

Every successful payment can be found and opened from transaction history.

---

# Phase 7 — Subscription Engine

## Objective

Create recurring financial obligations.

## Features

- Subscribe to fictional services.
- Billing frequency.
- Next payment date.
- Auto-renewal.
- Subscription status.
- Upcoming payment view.
- Subscription payment history.

## Acceptance Criteria

A subscription creates a correctly calculated upcoming payment schedule.

---

# Phase 8 — Financial Analytics

## Objective

Build the non-ML analytical foundation.

## Features

- Total spending.
- Category spending.
- Monthly trends.
- Daily/weekly trends.
- Largest payments.
- Recurring commitments.
- Current balance.
- Upcoming commitments.
- Estimated actually spendable amount.

## Acceptance Criteria

Analytics match independently calculated transaction totals.

---

# Phase 9 — Data Science Pipeline

## Objective

Prepare reproducible ML experimentation.

## Tasks

Create Jupyter notebooks:

```text
01_data_generation_or_collection.ipynb
02_data_cleaning.ipynb
03_eda.ipynb
04_feature_engineering.ipynb
05_baseline_models.ipynb
06_model_training.ipynb
07_model_evaluation.ipynb
08_anomaly_detection.ipynb
09_explainability.ipynb
10_model_export.ipynb
```

## Acceptance Criteria

The dataset can be reproduced/prepared and the feature pipeline can be run without manual hidden steps.

---

# Phase 10 — Transaction Categorization

## Objective

Automatically categorize financial transactions.

## Tasks

- Prepare labelled data.
- Establish baseline.
- Train candidate models.
- Compare metrics.
- Select model.
- Export model.
- Build inference service.

## Acceptance Criteria

A transaction can be categorized through the production inference path.

The model's evaluation metrics are documented.

---

# Phase 11 — Recurring Payment Intelligence

## Objective

Identify recurring payment behaviour.

## Tasks

- Normalize merchant names.
- Calculate intervals.
- Analyse amount consistency.
- Detect frequency.
- Estimate next occurrence.
- Calculate confidence.
- Handle insufficient data.

## Acceptance Criteria

Known synthetic recurring patterns are correctly identified in evaluation data.

---

# Phase 12 — Spending Anomaly Detection

## Objective

Identify transactions that significantly differ from expected behaviour.

## Tasks

- Define anomaly target/problem.
- Create baseline.
- Engineer behavioural features.
- Train/evaluate anomaly model.
- Tune threshold.
- Measure false positives.
- Generate risk score.
- Create explanation.

## Acceptance Criteria

The system flags designed anomalous test cases and produces measurable evaluation results.

No arbitrary accuracy claim is permitted.

---

# Phase 13 — Spending Forecast

## Objective

Estimate future spending.

## Tasks

- Build time-based dataset.
- Establish simple baseline.
- Evaluate candidate approach.
- Generate forecast.
- Measure MAE/RMSE where appropriate.
- Display uncertainty/limitations.

## Acceptance Criteria

Forecast output is generated only when sufficient historical data exists.

---

# Phase 14 — Suspicious Activity Engine

## Objective

Connect ML intelligence to investigation.

## Flow

```text
Transaction
 ↓
Behavioural Features
 ↓
Risk Model
 ↓
Risk Score
 ↓
Threshold/Policy
 ↓
Normal OR Requires Review
```

## Important

The system must distinguish:

```text
Anomalous
        ≠
Fraud
        ≠
Criminal Activity
```

## Acceptance Criteria

A suspicious synthetic transaction can produce a review alert with explainable signals.

---

# Phase 15 — Forensic Case Management

## Objective

Turn suspicious financial events into structured investigations.

## Features

- Create case.
- Case ID.
- Priority.
- Status.
- Assigned investigator.
- Trigger transaction.
- Case notes.
- Case history.

## Acceptance Criteria

An investigator can open a suspicious transaction and create a linked forensic case.

---

# Phase 16 — Evidence Ingestion

## Objective

Build the evidence-management foundation.

## Tasks

- Authorized evidence upload.
- File validation.
- Size limits.
- Type restrictions.
- Metadata extraction.
- Evidence ID generation.
- Case association.
- Processing status.

## Acceptance Criteria

An authorized investigator can ingest a supported evidence file and obtain a persistent evidence record.

---

# Phase 17 — Evidence Integrity

## Objective

Protect evidence integrity within the application.

## Tasks

- SHA-256 hashing.
- Hash storage.
- Verification endpoint.
- Hash comparison.
- Integrity status.
- Chain-of-custody events.

## Flow

```text
Evidence
 ↓
SHA-256
 ↓
Stored Hash
 ↓
Later Verification
 ↓
MATCH / MISMATCH
```

## Acceptance Criteria

Unmodified evidence verifies successfully.

A deliberately modified test file produces a mismatch.

---

# Phase 18 — Forensic Artifact Processing

## Objective

Extract useful structured information from supported evidence.

## Potential Artifacts

```text
Authentication
Session
Device
Application Audit
Network
File Metadata
Transaction Audit
```

## Tasks

- Parser framework.
- Source-specific parsers.
- Error handling.
- Artifact metadata.
- Source references.

## Acceptance Criteria

At least the planned supported evidence formats can be parsed into structured artifacts.

Unsupported formats fail safely.

---

# Phase 19 — Event Normalization

## Objective

Convert heterogeneous evidence into a common event model.

## Normalized Event

```text
event_id
event_type
timestamp
actor
user_id
device_id
session_id
source
action
object
severity
raw_reference
```

## Acceptance Criteria

Events from different supported sources can be represented consistently.

Original source references remain available.

---

# Phase 20 — Forensic Event Store

## Objective

Use Cassandra for chronological forensic/event workloads.

## Tasks

- Insert normalized events.
- Design partitions.
- Query by investigation/user/device/time.
- Implement time-window queries.
- Test larger event volumes.

## Acceptance Criteria

The forensic timeline can retrieve relevant events efficiently from Cassandra according to documented query patterns.

---

# Phase 21 — Correlation Engine

## Objective

Connect related events and entities.

## Example

```text
User
 ↓
Session
 ↓
Device
 ↓
Transaction
 ↓
Audit Event
 ↓
Evidence
```

## Tasks

- Identifier-based correlation.
- Timestamp-based correlation.
- Context-based correlation.
- Relationship creation.
- Relationship explanation.
- Relevance ranking.

## Acceptance Criteria

A controlled investigation produces expected relationships between known entities.

The system does not invent unsupported relationships.

---

# Phase 22 — Timeline Reconstruction

## Objective

Create an investigation timeline.

## Features

- chronological ordering,
- time filters,
- event-type filters,
- event details,
- evidence links,
- gaps,
- conflicting timestamps.

## Acceptance Criteria

An investigator can reconstruct a selected investigation window and inspect its events.

---

# Phase 23 — Evidence Consistency Analysis

## Objective

Identify potential contradictions.

## Checks

- conflicting timestamps,
- impossible ordering,
- mismatched identifiers,
- duplicate evidence,
- inconsistent metadata,
- hash mismatch,
- missing expected relationships.

## Acceptance Criteria

Designed contradictory test cases produce review signals.

The system does not silently resolve conflicts.

---

# Phase 24 — Investigation Graph

## Objective

Provide relationship-oriented investigation analysis.

## Nodes

```text
User
Account
Transaction
Session
Device
Event
Evidence
Artifact
Merchant
```

## Edges

Only meaningful relationships are displayed.

## Acceptance Criteria

The graph accurately represents relationships available from the case data.

---

# Phase 25 — Trace Back & Trace Forward

## Objective

Help investigators understand event context.

### Trace Back

```text
Selected Event
      ↑
Relevant Previous Events
      ↑
Possible Origin
```

### Trace Forward

```text
Selected Event
      ↓
Relevant Subsequent Events
      ↓
Possible Consequence
```

## Acceptance Criteria

Investigators can select an event and retrieve relevant surrounding activity using documented time and relationship rules.

---

# Phase 26 — ML Explainability

## Objective

Make ML findings understandable.

## Tasks

- Feature contribution/explanation.
- Risk score.
- Model version.
- Prediction timestamp.
- Supporting signals.
- Limitations.

Example:

```text
Risk Score: 0.91

Signals:
- unusually high amount
- unfamiliar merchant
- unusual time
- new device/session
```

## Acceptance Criteria

Every production ML finding contains an explanation appropriate to the selected model.

---

# Phase 27 — Investigator Findings

## Objective

Give investigators control over conclusions.

## Features

- Finding creation.
- Finding status.
- Evidence attachment.
- Notes.
- Supporting evidence.
- Contradictory evidence.
- Investigator decision.

## Status

```text
Open
Under Review
Supported
Inconclusive
Dismissed
Closed
```

## Acceptance Criteria

An investigator can review a system-generated finding and record a human decision.

---

# Phase 28 — Reporting

## Objective

Generate an evidence-backed investigation report.

## Report Structure

```text
Case Metadata
Incident Summary
Transaction
Timeline
Evidence
Integrity Verification
Correlations
ML Findings
Contradictions
Investigator Notes
Final Status
```

## Acceptance Criteria

A completed case can produce a readable report that distinguishes observations, automated analysis, and investigator conclusions.

---

# Phase 29 — Security Hardening

## Objective

Review the complete application as a security-sensitive system.

## Tasks

- Authentication review.
- Authorization review.
- Input validation.
- File-upload security.
- Rate limiting.
- Secret management.
- CORS.
- Secure headers.
- Error-message review.
- Audit-log review.
- Dependency review.

## Acceptance Criteria

Critical security tests pass and no known critical configuration issue remains unresolved.

---

# Phase 30 — Automated Testing

## Objective

Create confidence in the system.

## Test Layers

```text
Unit
 ↓
Integration
 ↓
ML
 ↓
Security
 ↓
End-to-End
```

## Critical Tests

- payment consistency,
- duplicate payment protection,
- access control,
- evidence hashing,
- evidence mismatch,
- event normalization,
- correlation,
- timeline,
- ML inference,
- report generation.

---

# Phase 31 — Performance & Scale Validation

## Objective

Demonstrate why the architecture uses MongoDB and Cassandra.

## Tests

Measure:

- transaction query performance,
- event ingestion,
- chronological event retrieval,
- forensic case retrieval,
- ML inference latency,
- evidence processing time.

Cassandra should be tested with increasing event volumes.

MongoDB should be tested with realistic document/query workloads.

The project should report measured observations rather than theoretical claims.

---

# Phase 32 — UI/UX Polish

## Objective

Transform the working system into a professional product.

## Tasks

- consistent design system,
- loading states,
- empty states,
- error states,
- confirmation states,
- responsive layouts,
- accessible forms,
- investigation visualizations,
- dashboard refinement.

The UI must prioritize meaningful information over decorative elements.

---

# Phase 33 — Demo Case Preparation

## Objective

Create a deterministic investigation story for evaluation.

Example:

```text
Normal User Activity
       ↓
Normal Payments
       ↓
New Device
       ↓
Unusual Session
       ↓
Large Payment
       ↓
ML Risk Alert
       ↓
Forensic Case
       ↓
Evidence
       ↓
Timeline
       ↓
Correlation
       ↓
Evidence Conflict
       ↓
Investigator Review
       ↓
Report
```

The demo must use clearly labelled controlled/synthetic data.

---

# Phase 34 — Deployment

## Objective

Deploy the application in a reproducible manner.

## Components

```text
Frontend
Backend
MongoDB
Cassandra
Object Storage
ML Artifacts
```

## Tasks

- production configuration,
- environment variables,
- database credentials,
- CORS,
- HTTPS,
- deployment health checks,
- logging,
- backup strategy where applicable.

---

# Phase 35 — Final Documentation

## Objective

Prepare the complete academic/project submission.

Required documentation:

```text
README.md
whole_project_idea_and_concept.md
PRD.md
Architecture.md
Phases.md
Design.md
Rules.md
Memory.md
```

Also document:

- setup,
- architecture,
- database design,
- ML methodology,
- evaluation,
- forensic methodology,
- security,
- limitations,
- test results,
- deployment.

---

# Phase 36 — Final Validation

## Final End-to-End Test

The following must work from beginning to end:

```text
Register
 ↓
Login
 ↓
View Wallet
 ↓
Scan QR
 ↓
Pay
 ↓
Receipt
 ↓
Transaction History
 ↓
Subscription
 ↓
Analytics
 ↓
ML Analysis
 ↓
Suspicious Activity
 ↓
Create Case
 ↓
Ingest Evidence
 ↓
Hash Verification
 ↓
Artifact Processing
 ↓
Event Normalization
 ↓
Cassandra Timeline
 ↓
Correlation
 ↓
Graph
 ↓
Trace Back / Forward
 ↓
Consistency Analysis
 ↓
ML Explanation
 ↓
Investigator Review
 ↓
Report
```

---

# Phase Completion Rule

A phase is complete only when:

```text
Implementation
+
Testing
+
UI Integration
+
Documentation
+
Security Review
+
Memory.md Update
```

are complete.

Do not move to the next major dependent phase simply because the current UI appears to work.

---

# Development Priority

If time becomes limited, prioritize:

```text
P0 — Must Work
Authentication
Wallet
Payment
Transactions
MongoDB
Cassandra event storage
ML anomaly detection
Forensic case
Evidence hashing
Event normalization
Timeline
Correlation
Investigator findings
Report

P1 — Strongly Recommended
QR
Subscriptions
Recurring detection
Categorization
Graph
Trace Back/Forward
Explainability
Forecasting

P2 — Polish
Advanced visualizations
Extended parsers
Advanced forecasting
Additional analytics
Performance optimizations
```

The project should always preserve the end-to-end investigation story before adding optional features.

---

# Phase 3/Database Boundary Validation - 2026-09-11

## Status

**Validated with live local services; the phase remains partial.** Cassandra
4.0.21 was reachable through WSL at `127.0.0.1:9042`, and the complete backend
suite passed. A duplicate `device_id` declaration in the existing Cassandra
schema generator was corrected without changing the five-table model.

## Durable Event Boundary

- Existing MongoDB `audit_records` documents can carry a routed publication
  record with `PENDING`, `FAILED`, or `PUBLISHED` delivery metadata.
- `EventDeliveryService` performs explicit retryable publication through the
  existing Cassandra adapter.
- Exact event ID replay is idempotent at the MongoDB ledger and Cassandra row
  boundary when the stored envelope is reused.
- No Kafka, Redis, Celery, RabbitMQ, worker, or new database was introduced.
- Account events remain Mongo-only because the current Cassandra schema has no
  account-specific query model; no unsupported route was invented.

## Validation

- Cassandra node: reachable, `UN`, version `4.0.21`.
- CQL keyspace access and five-table schema initialization: passed.
- MongoDB-to-Cassandra durable publication integration: passed.
- Retry, duplicate-event, correlation, and Cassandra-unavailable unit cases:
  passed.
- Full backend suite: **52 passed, 0 failed, 0 skipped**.

## Remaining Dependency-Ordered Work

The closed payment persistence foundation is now implemented with a unique
idempotency reservation, optimistic account compare-and-set, stable event
identity, and the deliberately selected
`transaction_events_by_account_day` publication target. A replica-set MongoDB
transaction path is implemented and validated; the controlled payment API is
documented in the following boundary section.

## MongoDB Replica-Set and Atomic Payment Validation - 2026-09-11

Implemented and validated using an isolated single-node development replica
set:

- MongoDB 8.3.4, replica set `rs0`, writable primary on `127.0.0.1:27018`;
- real multi-document commit and rollback tests;
- atomic account + transaction + MongoDB publication metadata;
- rollback after injected publication failure;
- same-key concurrent retry with one financial effect;
- concurrent ₹800/₹700 operations against ₹1,000 without overspend;
- Cassandra delivery after MongoDB commit remains separate and retryable.

The existing Windows service on `127.0.0.1:27017` remains standalone because
its shared data directory contains unrelated development databases and the
current session does not have administrator rights to modify its service
configuration safely. The application development `.env` now deliberately
points to the validated `rs0` endpoint on `127.0.0.1:27018`; the controlled
fictional payment API is implemented while external settlement remains closed.

## SpendShield Development Environment Configuration - 2026-09-11

The actual application configuration now selects:

- MongoDB `127.0.0.1:27018`, replica set `rs0`, single-node writable primary;
- database `spendshield` for the development runtime;
- Cassandra `127.0.0.1:9042` for historical event delivery.

The existing standalone Windows service on `127.0.0.1:27017` and its unrelated
data remain untouched. `/api/v1/health/dependencies` reports safe MongoDB
identity fields so the runtime endpoint and replica-set name are observable
without exposing the connection string. The development startup order is:

1. Start the isolated `rs0` process on `127.0.0.1:27018` and verify its
   writable-primary state. From PowerShell, use the validated project-local
   data directory and MongoDB binary:

   ```powershell
   & 'C:\Program Files\MongoDB\Server\8.3\bin\mongod.exe' `
     --dbpath 'D:\E_Drive\Project\.mongodb-rs-validation\data' `
     --replSet rs0 --port 27018 --bind_ip 127.0.0.1 `
     --logpath 'D:\E_Drive\Project\.mongodb-rs-validation\mongod.log' --logappend
   ```

   Verify with `mongosh
   'mongodb://127.0.0.1:27018/?replicaSet=rs0' --eval "db.hello()"`.
2. Start/verify Cassandra on `127.0.0.1:9042` when event delivery is needed.
3. Start the backend from `backend` with `python -m uvicorn app.main:app --reload`.
4. Verify `/health` and `/api/v1/health/dependencies`.

This single-node replica set provides transaction support for development; it
does not provide production high availability.

## Payment API Boundary - 2026-09-11

Implemented and integration-tested through the real FastAPI path:

- `POST /api/v1/payments` with bearer authentication and required
  `Idempotency-Key`;
- `GET /api/v1/payments/{transaction_id}` with owner-scoped current-state reads;
- bounded `GET /api/v1/payments` history with cursor, status, and merchant filters;
- Decimal amount validation, two-decimal precision enforcement, UUID validation,
  strict request fields, and safe error mapping;
- owner authorization, inactive-user protection, inactive-account handling,
  insufficient-funds handling, idempotency replay/conflict behavior, and
  concurrent overspend protection;
- live HTTP-to-MongoDB-rs0-to-Cassandra event publication with stable event,
  transaction, correlation, and causation identity.

The merchant ID is currently an opaque bounded reference because the Merchant
System does not yet exist. No real payment processor, UPI, card, bank, or
settlement integration was added. The exact next step is the Merchant System
and merchant/category domain foundation, followed by analytics.

Final backend verification after this slice: **70 passed, 0 failed, 0 skipped**;
3 dependency deprecation warnings. `pip check` and bytecode compilation also
passed.

## Merchant and Category Domain Foundation - 2026-09-11

Implemented the dependency-ordered catalog foundation without starting
analytics, ML, frontend work, or external settlement:

- canonical MongoDB `categories` taxonomy with stable category/subcategory IDs;
- explicit deterministic `python scripts/seed_catalog.py` seed command;
- MongoDB merchant repository with backend-generated UUIDs, active/inactive
  lifecycle, version-checked updates, bounded listing, filters, and indexes;
- authenticated category and merchant read APIs;
- administrator-only merchant creation and updates;
- safe catalog responses with no database or audit internals;
- payment-time merchant existence/status/category validation through
  `MerchantService`;
- immutable category/subcategory snapshots stored on transactions and payment
  historical events;
- negative and live MongoDB `rs0` integration tests for authorization,
  pagination, invalid categories, inactive merchants, reclassification, and
  payment integration.

The existing `MERCHANT` role is not granted management authority because the
identity model has no merchant ownership association. Merchant lifecycle audit
facts are stored in MongoDB; no new Cassandra table was added.

The exact next dependency-ordered step is to build the Analytics Data
Foundation and read-only spending analytics APIs on top of the stable Account,
Payment, Merchant, and Category domains. Analytics is intentionally not
implemented in this phase.

Final backend verification for this phase: **76 passed, 0 failed, 0 skipped**;
3 dependency deprecation warnings. `pip check` and bytecode compilation passed.
## Analytics Data Foundation and Read-Only Spending APIs - 2026-09-12

Implemented the first non-ML analytics slice over the existing domains: owner-scoped MongoDB aggregation, bounded UTC ranges (30-day default, 366-day maximum), exact Decimal summary, category/subcategory and merchant breakdowns, daily/weekly/monthly trends, largest-payment projection, strict response schemas, and authenticated read-only routes.

Analytics count only COMPLETED current transaction documents. MongoDB remains the source for current account/transaction state; Cassandra remains historical event storage and is not queried for totals. One justified transaction analytics index was added; no broker, cache, warehouse, new database, ML, forecast, or anomaly decision was introduced.

Validation: live MongoDB rs0 analytics/API integration 3 passed; authentication, owner isolation, completed-only semantics, grouping, trends, largest payment, rejected-payment exclusion, invalid ranges, and limits passed. Cassandra schema was unchanged.

The broader Phase 8 items for subscriptions, recurring commitments, upcoming commitments, spendable amount, and balance history remain planned. The exact next dependency-ordered step is the evidence-driven data science/ML dataset and baseline boundary.

## Evidence-Driven ML Dataset Audit and Notebook Foundation - 2026-09-12

Implemented the first Phase 9 foundation without training or deploying a
model:

- added output/jupyter-notebook/01_dataset_audit.ipynb;
- audited the live MongoDB transaction source read-only;
- documented application-operational provenance and MongoDB/Cassandra
  ownership;
- defined the completed-transaction dataset contract;
- defined candidate point-in-time features and excluded post-outcome fields;
- checked for fraud and human-review target fields;
- added a baseline-readiness gate that reports insufficient data instead of
  inventing labels or metrics;
- added ML_DATASET_AUDIT.md and notebook execution instructions.

Observed result: MongoDB was available, but the development
spendshield.transactions collection contained zero documents and zero
completed transactions. No target label was available, so the baseline is
BLOCKED_INSUFFICIENT_DATA. No database writes, synthetic records, model
artifacts, ML dependencies, or inference routes were introduced.

The exact next step is to obtain or deliberately create a provenance-labelled
dataset with a documented target and sufficient temporal coverage, then
implement deterministic feature preparation and a simple evaluated baseline.
Final backend verification after the analytics implementation: **79 passed, 0 failed, 0 skipped**, with 3 dependency deprecation warnings. `pip check` and Python bytecode compilation passed.

## Controlled Synthetic ML Dataset Generation and Validation - 2026-09-12

The operational ML audit found zero current transactions and no verified
labels. A separate controlled synthetic research dataset was therefore added
without inserting anything into MongoDB or Cassandra.

Implemented:

- reusable deterministic generator in `ml/synthetic_dataset_generator.py`;
- 10,000 bounded records, 500 fictional users/accounts, 100 merchants, 12
  categories, INR-only values, and 90 UTC days;
- normal, high-amount, rapid-repeat, unusual-time, behavior-deviation, and
  combined-pattern generator scenarios;
- explicit synthetic provenance and label dictionary;
- point-in-time feature group, audit-only group, and forbidden/leakage group;
- timestamp-based 70/15/15 train/validation/test splits;
- manifest, configuration, CSV files, and reproducibility instructions under
  `data/synthetic/`;
- generation and validation notebooks under `output/jupyter-notebook/`.

Validation completed with 10,000 rows, 28 columns, scenario counts of 7,600 /
800 / 600 / 600 / 300 / 100, and split counts of 7,061 / 1,481 / 1,458. The
labels are synthetic scenario labels, not confirmed fraud labels. No model,
anomaly detector, production inference, API, blocking, notification, or
database write was introduced.

The exact next dependency-ordered step is deterministic candidate-feature
preparation followed by a research-only baseline evaluation. It must not use
scenario metadata as features or claim real-world fraud performance.

## Deterministic Feature Matrix and First Research Baseline - 2026-09-12

Implemented the next ML foundation slice using only the isolated synthetic
CSV files:

- prior-only history feature audit with timestamp and transaction-ID tie-break;
- 28-column candidate model feature matrix;
- training-only numeric median imputation;
- training-only one-hot categorical vocabularies and unknown buckets;
- separate target and audit identity columns;
- feature manifest, feature dictionary, and reproducibility checks;
- majority-class reference and fixed Gaussian Naive Bayes multiclass baseline;
- temporal validation and final held-out test evaluation;
- research result JSON and notebooks 04 and 05.

Measured final test results:

- majority reference: accuracy `0.776406`, macro F1 `0.145688`;
- Gaussian Naive Bayes: accuracy `0.862826`, macro F1 `0.617953`, weighted F1
  `0.850388`.

These are synthetic scenario classification metrics, not fraud-detection or
production metrics. No database, backend financial logic, API, deployment,
notification, blocking, or model artifact changed.

The exact next dependency-ordered step is controlled error analysis and
evaluation-protocol review before considering another model.

## Phase 06 - Controlled Error Analysis and Protocol Review - IMPLEMENTED

Implemented the bounded research-only review of the fixed six-class synthetic
baseline. The stored baseline was reproduced exactly before error inspection.
Validation and test confusion matrices, per-class metrics, bounded
misclassified records, class distributions, validation-only feature
distributions, shortcut evidence, leakage checks, and a protocol review are
stored under `data/synthetic/error_analysis/`.

The review confirms the temporal and prior-only feature boundaries, but finds
generator shortcuts: all validation rapid-repeat rows satisfy the <=600-second
rule, and all validation unusual-time and combined-pattern rows satisfy the
configured unusual-hour window. The rare combined class is 1% of the full
dataset; the test ratio of majority to minority is approximately 59.58:1.

Decision: `DATASET_OR_GENERATOR_REVIEW_REQUIRED_FIRST`. Do not add model
complexity until scenario overlap and generator semantics are reviewed. This
phase added no production inference, fraud/risk API, payment behavior,
notification, blocking, model export, or database change.

## Phase 07 - Versioned Generator Revision and Comparison - IMPLEMENTED

The v1 generator artifact remains unchanged and reproducible. A separate v2
artifact was created with generator `1.1.0`, feature version `1.1.0`, baseline
version `1.1.0`, seed `20260913`, 10,000 rows, and SHA-256 manifest hashes.

The revised generator adds realistic normal variation and probabilistic
overlap for amount, time, repeat, category, merchant, and channel behavior.
The feature matrix adds four prior-only user-relative/novelty fields. Dataset
validation, feature validation, baseline evaluation, controlled error
analysis, version comparison, reproducibility, and leakage checks all passed.

Measured v2 test metrics are accuracy `0.703673`, macro F1 `0.262793`, and
weighted F1 `0.651407`. The lower score versus v1 is reported honestly: the
revised task is less trivially separable and the simple Gaussian baseline is
not a quality oracle.

Final decision: `REVISED_DATASET_READY_FOR_NEXT_ML_PHASE`. The exact next
dependency is controlled research-only anomaly-detection and explainability
evaluation. Production inference, fraud APIs, payment controls, database
writes, and mobile work remain out of scope.

## Phase 08 - Controlled Research-Only Anomaly Detection and Explainability - IMPLEMENTED

Implemented the first anomaly-ranking and explanation layer over v2 without
changing the backend or database foundation. The dependency-free robust-MAD
model is fit on train only with 12 numeric/prior-only features. Its normalized
score direction, training-percentile thresholds, version, seed, feature
manifest, and non-comparability boundary are explicit. The fixed transparent
weighted signal baseline is retained as a research reference and is not
label-tuned.

Validation and test artifacts include score distributions, per-scenario score
statistics, top 1/5/10% composition, normal representation, scenario
coverage, synthetic-only ROC-AUC/AP, threshold analyses, and overlap
limitations. Deterministic explanations are generated from observed feature
values only; a bounded sample passed forbidden-language, label/generator
metadata, feature-reference, missing-history, and repeatability checks.

Required artifacts are under `data/synthetic/anomaly_detection/v2/`, with
notebooks `11_anomaly_detection_evaluation.ipynb` and
`12_explainability_evaluation.ipynb`. The exact decision is
`ANOMALY_EVALUATION_READY_FOR_BACKEND_RESEARCH_INTEGRATION`. This does not
authorize production scoring, payment blocking/rejection, fraud claims,
database writes, or investigator decisions. The exact next step is one
read-only backend research integration with explicit non-production safeguards.

## Phase 09 - Research-Only Anomaly Backend Integration - PARTIALLY COMPLETED

Implemented the authenticated owner-scoped read-only research boundary. The
backend validates and loads the existing v2 anomaly artifact, including the
serialized train-fitted parameter file; it does not train or regenerate at
startup. It exposes bounded score listing, single-transaction score, and
deterministic explanation routes with explicit model metadata and safe error
semantics.

The repository gained a bounded prior-only completed-history read contract and
the service builds the exact ordered 12-feature vector without target,
scenario, identifier, future, post-event, or human-decision fields. Tests
cover artifact failure, determinism, feature parity, missing channel handling,
authentication, owner isolation, unavailable listing behavior, and payment
isolation.

The phase is intentionally partial for live scoring: current payment records
do not persist an approved `transaction_channel` source, while the anomaly
contract requires it for `channel_novelty_before`. The API therefore returns a
controlled unavailable result instead of guessing. No payment API behavior,
balance/status mutation, event publication, Cassandra responsibility, or
investigator workflow changed.

## Phase 10 - Infrastructure and Live Anomaly Scoring - IMPLEMENTED

The supported local infrastructure was restored and verified without a
destructive reset. MongoDB is the writable single-node `rs0` development
replica at `127.0.0.1:27018`; Cassandra 4.0.21 is reachable at
`127.0.0.1:9042` and the existing `spendshield_events` schema is present.

The operational payment flow now requires and persists an explicit simulated
transaction channel through the request schema, command, MongoDB document,
response, event payload, and idempotency fingerprint. Legacy documents remain
nullable and are not backfilled. Live research scoring reads the persisted
channel values from prior completed MongoDB transactions, excludes the target,
and preserves deterministic timestamp/ID ordering. Missing legacy data and
insufficient history remain distinct controlled unavailable outcomes.

The three research endpoints remain authenticated, owner-scoped, read-only,
research-only, and non-blocking. Existing payment and event-delivery behavior
was preserved. Synthetic datasets, notebooks, model parameters, thresholds,
and research metrics were not regenerated or changed.

## Phase 11 - React Native and Expo Mobile Foundation - IMPLEMENTED WITH REVIEW ITEMS

Added a new `mobile/` Expo SDK 57 TypeScript application for the initial
Android client foundation. The app is configured as SpendShield with Android
package `com.spendshield.mobile`, a centralized public development API URL,
and no production credentials or payment UI.

The foundation includes Splash, Welcome, Login, Registration, and an
authenticated Dashboard placeholder. Navigation uses a typed native stack with
loading, authenticated, and unauthenticated branches. Login and registration
call the existing FastAPI authentication endpoints; access-token session data
is stored in Expo SecureStore and the current user is revalidated on startup.
The API client has typed request/error handling, JSON headers, bearer-token
support, and request timeouts. No backend business logic was changed.

Validation completed: TypeScript compilation passed; Expo dependency check
passed; Expo Doctor passed all 21 checks; Expo resolved configuration passed;
and Metro returned an Android bundle successfully with 873 modules and no
module-resolution or transform errors. The backend regression suite passed 65
tests with 27 dependency-gated tests skipped. MongoDB `127.0.0.1:27018`,
Cassandra `127.0.0.1:9042`, Expo Go, and a physical Android device were not
available during this mobile validation session, so live mobile authentication
and on-device rendering remain review items.

Payments, QR scanning, transaction history, subscriptions, notifications,
analytics, anomaly visualization, APK generation, and mobile financial
decisions remain out of scope. The exact next dependency-ordered step is to
verify this foundation in Expo Go against the running backend, then connect a
read-only account summary.

## Phase 12 - Demo banking modules and UI repair - PARTIALLY IMPLEMENTED

Implemented multi-account current state, server-authoritative demo deposit and
withdrawal, self-transfer account selection, phone/bill payment contracts,
owner-scoped contacts/beneficiaries/billers/cards/notifications endpoints,
Ionicons dashboard controls, contact/phone/bills/account-operation screens,
local QR image decoding, and updated startup documentation. The final backend
regression rerun produced `74 passed, 27 skipped, 0 failed`; skips were
dependency-gated after the manually started services were no longer listening.
TypeScript, Expo Doctor, and Android export pass.

Remaining: profile and demo MPIN UX, protected admin/demo data actions,
automatic local notification generation, complete saved-biller/card/notification
mobile management, device-level Expo Go verification, and mobile automated
test/lint configuration.

## Phase 13 - Persisted demo merchant QR and module completion - PARTIALLY IMPLEMENTED

Added MongoDB-backed fictional merchant registry, versioned server-validated
QR payloads, actual mobile QR rendering, QR amount keypad, review and demo
MPIN flow, backend balance result fields, profile editing, demo security
management, card management, notification actions, automatic committed-payment
notifications, and fictional card-payment enforcement.

Verification: full backend `76 passed, 27 skipped, 0 failed`; focused QR,
security, and demo coverage `22 passed`; TypeScript passed; Expo Doctor `21/21`;
Android export passed with 1,262 modules. Integration skips occurred because
MongoDB `27018`, Cassandra `9042`, and backend `8000` were not listening at
the final run. Admin/demo destructive panel, MPIN recovery, saved-biller UI,
card-specific history filtering, and physical-device validation remain.
