# Architecture

## Project
**SpendShield — Intelligent Payment, Financial Awareness & Digital Forensics Platform**

## 1. Architecture Objective

SpendShield uses a modular, layered architecture that connects:

```text
Frontend
   ↓
FastAPI Backend
   ↓
Application Services
   ├── Financial Engine
   ├── ML Intelligence Engine
   ├── Forensic Engine
   ├── Correlation Engine
   └── Reporting Engine
   ↓
Data Access Layer
   ├── MongoDB
   ├── Cassandra
   └── Evidence/Object Storage
```

The architecture is designed so that every technology has a clear responsibility.

---

# 2. High-Level Architecture

```text
                         ┌──────────────────────┐
                         │      FRONTEND        │
                         │   Next.js / React    │
                         └──────────┬───────────┘
                                    │ HTTPS / JSON
                                    ▼
                         ┌──────────────────────┐
                         │     FASTAPI API      │
                         │ Authentication/RBAC  │
                         └──────────┬───────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
     ┌────────────────┐    ┌────────────────┐    ┌────────────────┐
     │ Financial      │    │ ML Intelligence│    │ Forensic       │
     │ Services       │    │ Services       │    │ Services       │
     └───────┬────────┘    └───────┬────────┘    └───────┬────────┘
             │                     │                     │
             └─────────────────────┼─────────────────────┘
                                   ▼
                         ┌──────────────────────┐
                         │ Correlation Engine   │
                         │ Timeline / Graph     │
                         └──────────┬───────────┘
                                    │
                         ┌──────────┴───────────┐
                         ▼                      ▼
                ┌────────────────┐     ┌────────────────┐
                │    MongoDB     │     │   Cassandra    │
                │ Documents      │     │ Event Streams  │
                └────────────────┘     └────────────────┘
                         │
                         ▼
                ┌────────────────┐
                │ Evidence/Object│
                │ Storage        │
                └────────────────┘
```

---

# 3. Architectural Principles

## 3.1 Separation of Responsibilities

Frontend must not contain business-critical logic.

Backend owns:

- payment validation,
- balance calculation,
- authorization,
- risk decisions,
- evidence processing,
- database operations.

## 3.2 Database Responsibility Must Be Explicit

MongoDB and Cassandra must not store arbitrary copies of the same data without a reason.

Each database should have a documented workload.

## 3.3 ML Is a Service, Not the Application

Training happens in Jupyter.

Production inference happens through a versioned model service/module.

```text
Jupyter
  ↓
Train/Evaluate
  ↓
Export Model
  ↓
Model Registry/Artifacts
  ↓
FastAPI ML Service
  ↓
Prediction
```

## 3.4 Original Evidence Is Not the Same as Processed Data

The forensic system must distinguish:

```text
Original Evidence
      ↓
Hash / Integrity
      ↓
Processing
      ↓
Normalized Artifacts
      ↓
Analytical Results
```

Processed artifacts must not silently replace original evidence.

---

# 4. Frontend Architecture

Recommended stack:

```text
Next.js
React
TypeScript
Tailwind CSS
Component Library
Charting Library
Graph Visualization
```

## Frontend Layers

```text
app/
components/
features/
hooks/
lib/
services/
types/
styles/
```

### `app/`

Routing and page composition.

### `components/`

Reusable UI components.

### `features/`

Feature-specific modules:

```text
auth
wallet
payments
transactions
subscriptions
analytics
investigations
evidence
timeline
graph
reports
admin
```

### `services/`

API communication.

The frontend must never directly access MongoDB or Cassandra.

---

# 5. Backend Architecture

Recommended:

```text
Python
FastAPI
Pydantic
PyMongo/MongoDB driver
Cassandra Python driver
JWT/session mechanism
scikit-learn
pandas
numpy
```

The exact library selection may change during implementation, but architecture boundaries should remain stable.

---

# 6. Backend Directory Structure

Recommended:

```text
backend/
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── accounts.py
│   │   ├── payments.py
│   │   ├── transactions.py
│   │   ├── subscriptions.py
│   │   ├── analytics.py
│   │   ├── ml.py
│   │   ├── alerts.py
│   │   ├── cases.py
│   │   ├── evidence.py
│   │   ├── timeline.py
│   │   ├── correlation.py
│   │   ├── findings.py
│   │   └── reports.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── logging.py
│   │   └── dependencies.py
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── transaction.py
│   │   ├── subscription.py
│   │   ├── case.py
│   │   ├── evidence.py
│   │   └── finding.py
│   │
│   ├── schemas/
│   │   └── ...
│   │
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── payment_service.py
│   │   ├── transaction_service.py
│   │   ├── subscription_service.py
│   │   ├── analytics_service.py
│   │   ├── ml_service.py
│   │   ├── forensic_service.py
│   │   ├── evidence_service.py
│   │   ├── correlation_service.py
│   │   └── report_service.py
│   │
│   ├── repositories/
│   │   ├── mongo/
│   │   └── cassandra/
│   │
│   ├── forensic/
│   │   ├── hashing.py
│   │   ├── ingestion.py
│   │   ├── parsers/
│   │   ├── normalization.py
│   │   ├── timeline.py
│   │   └── consistency.py
│   │
│   ├── ml/
│   │   ├── inference.py
│   │   ├── preprocessing.py
│   │   ├── models/
│   │   └── explainability.py
│   │
│   └── tests/
│
├── notebooks/
├── model_artifacts/
├── scripts/
└── requirements.txt
```

---

# 7. API Layer

The API layer handles:

```text
HTTP Request
    ↓
Authentication
    ↓
Authorization
    ↓
Validation
    ↓
Service Call
    ↓
Response
```

Routes must not contain large business workflows.

Bad:

```text
Route → 300 lines of database + ML + forensic logic
```

Good:

```text
Route
 ↓
Service
 ↓
Repository / Engine
```

---

# 8. Financial Engine

The financial engine handles:

- wallet/account state,
- payment validation,
- QR merchant resolution,
- transaction creation,
- balance updates,
- subscriptions,
- recurring payment generation,
- receipts.

Conceptual payment transaction:

```text
Payment Request
      ↓
Authenticate
      ↓
Authorize
      ↓
Validate Merchant
      ↓
Validate Amount
      ↓
Check Balance
      ↓
Create Transaction
      ↓
Update Account State
      ↓
Write Audit/Event
      ↓
Return Receipt
```

Critical balance operations must be designed to avoid race-condition-related inconsistencies.

---

# 9. ML Intelligence Architecture

```text
Historical Data
      ↓
Data Preparation
      ↓
Feature Engineering
      ↓
Model
      ↓
Prediction
      ↓
Risk/Category/Forecast
      ↓
Explanation
      ↓
Stored Finding
```

The ML module should support:

```text
transaction categorization
recurring pattern detection
anomaly detection
spending forecasting
risk scoring
```

Not every capability needs the same algorithm.

---

# 10. ML Training Architecture

Jupyter notebooks are the experimentation environment.

```text
Data Sources
    ↓
Cleaning
    ↓
EDA
    ↓
Feature Engineering
    ↓
Train/Test Split
    ↓
Baseline
    ↓
Model Training
    ↓
Evaluation
    ↓
Explainability
    ↓
Model Export
```

Model artifacts should contain metadata describing:

- version,
- features,
- preprocessing,
- training data,
- metrics,
- algorithm.

---

# 11. ML Production Inference

Production inference should be separated from training.

```text
Frontend
   ↓
FastAPI
   ↓
ML Service
   ↓
Preprocessing
   ↓
Loaded Versioned Model
   ↓
Prediction
   ↓
Explanation
   ↓
API Response
```

The preprocessing used in production must match the preprocessing used during training.

---

# 12. Forensic Engine

The forensic engine is a core subsystem.

Responsibilities:

```text
Evidence Ingestion
Evidence Hashing
Metadata Extraction
Artifact Parsing
Event Normalization
Timeline Reconstruction
Consistency Analysis
Evidence Linking
Case Findings
```

Architecture:

```text
Authorized Evidence
        ↓
Ingestion
        ↓
SHA-256
        ↓
Evidence Metadata
        ↓
Artifact Extraction
        ↓
Normalization
        ↓
Event Store
        ↓
Correlation
        ↓
Timeline
        ↓
Investigation Findings
```

---

# 13. Evidence Storage Architecture

Evidence should be separated from application metadata.

Conceptually:

```text
Object/File Storage
        │
        │ original evidence
        ▼
Evidence Metadata in MongoDB
        │
        ├── SHA-256
        ├── source
        ├── case
        ├── ingestion time
        └── custody history
```

MongoDB should store metadata and investigation documents rather than unnecessarily storing huge raw evidence blobs.

---

# 14. MongoDB Architecture

MongoDB is the document-oriented operational store.

Potential collections:

```text
users
accounts
merchants
subscriptions
transactions
notifications
cases
evidence
artifacts
findings
relationships
investigator_notes
reports
audit_records
model_metadata
```

MongoDB is appropriate for documents whose structure may evolve, especially investigation objects.

Indexes must be created according to actual query patterns.

Potential indexes:

```text
users.email
transactions.user_id + timestamp
transactions.merchant_id + timestamp
cases.status + created_at
evidence.case_id
findings.case_id
```

Exact indexes must be validated through workload testing.

---

# 15. Cassandra Architecture

Cassandra is the event-oriented high-volume store.

The schema must be query-first.

Potential tables:

```text
authentication_events_by_user_day
session_events_by_user_day
device_events_by_device_day
transaction_events_by_account_day
network_events_by_device_day
audit_events_by_case_day
```

Conceptual record:

```text
partition key
cluster timestamp
event id
actor
device
session
event type
source
payload/reference
```

Cassandra should be used where high-volume sequential/event access benefits from its distributed architecture.

Do not model Cassandra like MongoDB.

---

# 16. Data Flow

## Normal Financial Flow

```text
User
 ↓
Frontend
 ↓
FastAPI
 ↓
Payment Service
 ↓
MongoDB Transaction
 ↓
Cassandra Event
 ↓
Analytics/ML
 ↓
Dashboard
```

## Suspicious Activity Flow

```text
Transaction
 ↓
ML/Risk Engine
 ↓
Risk Signal
 ↓
Alert
 ↓
Investigation Case
```

## Forensic Flow

```text
Case
 ↓
Evidence
 ↓
Hash
 ↓
Artifacts
 ↓
Normalized Events
 ↓
Cassandra Event Queries
 ↓
Correlation Engine
 ↓
Timeline
 ↓
Graph
 ↓
Finding
 ↓
Report
```

---

# 17. Correlation Engine

The correlation engine is responsible for joining related observations.

Example:

```text
Transaction T1
    │
    ├── user U1
    ├── account A1
    ├── session S9
    ├── device D4
    ├── audit event E7
    └── evidence EV42
```

Correlation should use:

- stable identifiers,
- timestamps,
- contextual attributes,
- source relationships.

Every relationship should have an understandable reason.

Example:

```text
Transaction T1
   └── linked_to_session
       reason: session_id match
```

---

# 18. Timeline Engine

The timeline engine receives normalized events and produces an ordered investigation view.

```text
Raw Events
   ↓
Normalize Timestamp
   ↓
Validate Event
   ↓
Sort / Query
   ↓
Group Related Events
   ↓
Detect Gaps/Conflicts
   ↓
Investigation Timeline
```

Timestamp handling must account for timezone and source-specific timestamp semantics.

The system must not silently modify source timestamps.

---

# 19. Evidence Consistency Engine

This engine looks for contradictions or unusual inconsistencies.

Possible checks:

- timestamp conflicts,
- impossible event ordering,
- duplicate artifacts,
- mismatched identifiers,
- inconsistent source metadata,
- hash mismatch,
- missing expected event relationships.

Example:

```text
Expected:
Login → Session → Payment

Observed:
Payment → Login
```

This should produce a review signal, not an automatic conclusion.

---

# 20. Investigation Graph

The graph view represents relationships between entities and events.

Example:

```text
             Device
                │
                ▼
User ─────── Session
 │              │
 │              ▼
 └────────── Transaction
                │
                ▼
             Evidence
                │
                ▼
             Artifact
```

The graph is a visualization of known relationships.

It must not invent relationships simply to make the graph look complete.

---

# 21. Trace Back / Trace Forward Architecture

## Trace Back

Input:

```text
selected event
```

Process:

```text
Find related predecessors
        ↓
Apply time window
        ↓
Apply relationship rules
        ↓
Rank relevance
        ↓
Return investigation chain
```

## Trace Forward

Same principle, but searches subsequent activity.

The time window and correlation rules must be configurable and documented.

---

# 22. Reporting Architecture

```text
Case Data
   ↓
Timeline
   ↓
Evidence
   ↓
Findings
   ↓
ML Explanations
   ↓
Investigator Notes
   ↓
Report Generator
   ↓
PDF / Export
```

Generated reports must distinguish:

```text
Observed Evidence
System Analysis
ML Prediction
Investigator Interpretation
```

---

# 23. Security Architecture

```text
Browser
   ↓ HTTPS
API Gateway / FastAPI
   ↓
Authentication
   ↓
Authorization
   ↓
Services
   ↓
Database
```

Required security controls include:

- password hashing,
- secure sessions/tokens,
- RBAC,
- input validation,
- file upload restrictions,
- size limits,
- content-type validation,
- path traversal protection,
- rate limiting,
- secure secrets,
- audit logging,
- CORS configuration,
- secure headers.

---

# 24. Role-Based Access

Example:

| Capability | User | Investigator | Admin |
|---|---:|---:|---:|
| View own wallet | Yes | Optional | Yes |
| Make payment | Yes | Optional | Yes |
| View own transactions | Yes | Optional | Yes |
| Create investigation | No/limited | Yes | Yes |
| View evidence | No | Authorized cases | Yes |
| Verify evidence | No | Yes | Yes |
| Modify findings | No | Yes | Yes |
| View audit logs | No | Case-specific | Yes |
| Manage users | No | No | Yes |

Actual authorization rules must be enforced server-side.

---

# 25. Deployment Architecture

Development:

```text
Browser
   ↓
Next.js
   ↓
FastAPI
   ├── MongoDB
   ├── Cassandra
   └── Local/Object Storage
```

Production-style deployment:

```text
User
 ↓
HTTPS
 ↓
Frontend Hosting
 ↓
FastAPI Service
 ├── MongoDB Atlas / managed MongoDB
 ├── Managed Cassandra-compatible service
 └── Object Storage
```

ML model artifacts should be versioned and deployed with controlled configuration.

Secrets must be supplied through environment variables or a secret manager.

---

# 26. Observability

The application should produce structured logs for:

- API requests,
- authentication,
- payment processing,
- ML inference,
- evidence ingestion,
- hash verification,
- forensic processing,
- errors,
- administrative actions.

Sensitive values must not be unnecessarily logged.

Metrics may include:

```text
API latency
error rate
payment success rate
ML inference latency
evidence processing time
case processing time
database latency
```

---

# 27. Failure Handling

Every subsystem must have defined failure states.

Examples:

### Payment Failure

```text
Validation failed
Insufficient balance
Merchant unavailable
Duplicate request
Database failure
```

### Evidence Failure

```text
Unsupported format
Corrupted file
Hash failure
Parser failure
Incomplete metadata
```

### ML Failure

```text
Model unavailable
Invalid feature input
Preprocessing mismatch
Insufficient data
```

The application should fail safely and clearly.

---

# 28. Architecture Boundaries

The following boundaries must remain clear:

```text
Frontend
    ≠
Business Logic

Business Logic
    ≠
Database Queries

ML Training
    ≠
Production Inference

Original Evidence
    ≠
Derived Artifacts

Anomaly Score
    ≠
Forensic Conclusion

System Finding
    ≠
Human Investigator Decision
```

These boundaries are essential to the credibility of the project.

---

# 29. Recommended Build Order

The architecture should be implemented in dependency order:

```text
1. Repository / project structure
2. Configuration
3. Authentication
4. MongoDB foundation
5. Cassandra foundation
6. Account/wallet
7. Merchants
8. Transactions
9. QR payment
10. Subscriptions
11. Analytics
12. ML pipeline
13. Risk/anomaly detection
14. Case management
15. Evidence ingestion
16. Hash verification
17. Event normalization
18. Cassandra event queries
19. Correlation
20. Timeline
21. Consistency analysis
22. Investigation graph
23. Trace Back / Forward
24. Findings
25. Reports
26. Security hardening
27. Testing
28. Deployment
```

The detailed execution plan belongs in `Phases.md`.

---

# 30. Architecture Success Condition

The architecture is successful only when one event can travel through the entire system:

```text
Financial Transaction
        ↓
Stored Transaction
        ↓
Event
        ↓
ML Analysis
        ↓
Risk Signal
        ↓
Investigation Case
        ↓
Evidence
        ↓
Normalized Events
        ↓
Correlation
        ↓
Timeline
        ↓
Investigation Graph
        ↓
Finding
        ↓
Human Review
        ↓
Report
```

This is the architectural backbone of SpendShield.

---

# 31. Final Architectural Principle

> **Use the simplest architecture that correctly demonstrates the required concepts, but never introduce a technology without a clear workload, responsibility, or learning objective.**

MongoDB, Cassandra, FastAPI, machine learning, Jupyter, and computer forensics must all contribute to the actual product rather than appearing as disconnected technologies.

---

# 32. Current Implementation Boundary - 2026-09-11

The implemented backend currently contains the FastAPI foundation,
authentication/RBAC, MongoDB/Cassandra database adapters, an authoritative
account domain, and a canonical event envelope.

The current account flow is:

```text
Authenticated User
        ↓
Account Service
        ↓
Account Domain Rules
        ↓
Account Repository
        ↓
MongoDB current account state
```

Account IDs, owners, currency, starting balance, status, and reads are
backend-controlled. The client cannot set authoritative account state.

The transaction and payment domain rules are implemented independently of
persistence, including exact money normalization, lifecycle transitions,
balance-before/after values, and idempotency fingerprints. A public payment
route is intentionally not present until the persistence boundary can provide
atomic account/transaction effects and durable event publication.

The data ownership rule remains:

```text
MongoDB  = current operational/domain state
Cassandra = append-oriented historical event data
```

The system is not event-sourced, and no ML or forensic conclusion is created
from the current account implementation.

---

# 33. Phase 3 Account Status and Audit Decision - 2026-09-11

## Decision

Account status changes are explicit domain transitions and are exposed through
an administrator-only `PATCH /api/v1/accounts/{account_id}/status` endpoint.
The account repository applies optimistic version checks so concurrent updates
cannot silently overwrite one another.

Meaningful account state changes emit the canonical event envelope into the
existing MongoDB `audit_records` collection. This is the current operational
audit record path. Cassandra remains the historical event store; no new
Cassandra table was added before a query-specific account-event workload and a
durable publication strategy are defined.

## Context and Trade-offs

The existing MongoDB schema represented account status but had no update path,
and the existing Cassandra tables were not an account-audit query model. The
chosen approach completes this Phase 3 slice without inventing a Cassandra
partition or claiming a non-atomic outbox. Audit records use unique event IDs,
so replaying the same event is safe. The later durable publication boundary
adds retry metadata for routed events, but state persistence and audit
insertion remain separate operations and are not claimed to be atomic.

The account `user_id` index is now unique because the current Phase 3 contract
defines one account per owner. This is a focused integrity correction, not a
database technology or collection redesign.

---

# 34. Durable Historical Event Boundary - 2026-09-11

## Implemented Boundary

The existing `audit_records` MongoDB document now carries two distinct kinds
of information:

```text
Immutable event envelope
    event_id, event_type, subject, actor, timestamps,
    correlation/causation, payload, provenance

Mutable delivery metadata
    publication target, status, attempts, retry time, published time,
    bounded error classification
```

When a caller supplies a valid target for one of the existing Cassandra event
tables, the record starts as `PENDING`. `EventDeliveryService` reads due
records, publishes the exact stored envelope through the existing Cassandra
adapter, and then marks the record `PUBLISHED`. A failure becomes `FAILED`
with bounded exponential backoff. The delivery pass is explicit; no broker,
worker framework, or new infrastructure was introduced.

The flow is therefore:

```text
Domain operation
      ↓
MongoDB current state
      ↓
MongoDB audit + publication record
      ↓
Explicit delivery pass
      ↓
Cassandra historical event
      ↓
MongoDB publication acknowledgement
```

The stored `event_id` is the retry identity. Replaying that record does not
rerun the domain operation. MongoDB's unique audit ID prevents duplicate
publication records, and replaying the same envelope to Cassandra uses the
same event timestamp and event ID, which maps to the same existing Cassandra
row key.

## Deliberate Consistency Guarantee

This is a durable, retryable publication ledger, not a claimed atomic outbox
across MongoDB and Cassandra. In the configured development environment,
MongoDB account state, transaction state, and the audit/publication record are
committed in one `rs0` MongoDB transaction. If Cassandra delivery fails after
that commit, only delivery metadata changes and the same event remains
retryable; the financial operation is not repeated. The standalone fallback
still has a window in which state and publication metadata are separate, so the
limitation remains explicit.

Account lifecycle events continue to be stored as MongoDB audit records only.
The current Cassandra schema has no account-specific query table, and no
partition was invented. The generic boundary is tested against the existing
authentication, device, and transaction event models. Selecting the correct
historical route for account/payment workflows remains a dependency of the
future payment persistence slice.

MongoDB still owns current balances, account state, and transaction state.
Cassandra still owns chronological history. No current financial state is
reconstructed from Cassandra.

---

# 35. Transaction Persistence Boundary - 2026-09-11

## Implemented foundation

The production payment repository now uses the existing MongoDB `accounts` and
`transactions` collections. It does not expose a payment route. A payment
reservation stores the logical request fingerprint, expected account version,
before/after balances, lifecycle identity, and one stable event ID. MongoDB's
compare-and-set update then changes the authoritative account balance only when
the expected version, owner, status, currency, and balance still match.

The current MongoDB service is standalone (`setName` was absent during live
validation), so this is an optimistic compare-and-set boundary, not a claimed
multi-document transaction. A retry can recover a reservation that was debited
but not finalized by comparing the stored expected post-debit version and
balance. An ambiguous concurrent change is rejected rather than debited again.

## Payment-to-history flow

```text
PaymentCommand
    ↓
owner/account validation and domain rules
    ↓
unique MongoDB transaction reservation
    ↓
version-checked MongoDB account debit
    ↓
MongoDB transaction COMPLETED
    ↓
MongoDB audit record with PENDING publication metadata
    ↓
EventDeliveryService
    ↓
existing Cassandra transaction_events_by_account_day table
```

The event's identity is independent from the financial request's idempotency
key. Replaying a request reuses the stored transaction and event IDs; retrying
historical delivery reuses the immutable event envelope. Cassandra receives
historical event data only and never becomes a balance or transaction-state
source of truth. The current payment target remains the documented fictional
merchant flow; no peer-account destination contract was invented.

## Current limitation

The standalone fallback cannot atomically commit account state, transaction
state, and audit-publication metadata in one MongoDB transaction. It therefore
provides recoverable optimistic behavior and no duplicate debit under the
tested compare-and-set races, but it is not the final payment-settlement
consistency guarantee. The development configuration now deliberately selects
the validated `rs0` profile on `127.0.0.1:27018`; the public payment API remains
NOT READY while its public contract and route-level controls remain closed.

---

# 36. MongoDB Replica-Set Atomic Payment Boundary - 2026-09-11

The existing Windows MongoDB service on `127.0.0.1:27017` was inspected and
found to use the standalone configuration at
`C:\Program Files\MongoDB\Server\8.3\bin\mongod.cfg`. Its data directory
contains unrelated local development databases, so the service configuration
and data directory were not changed without administrator approval.

For safe validation, a separate single-node MongoDB 8.3.4 development
instance named `rs0` was started on `127.0.0.1:27018` with an isolated
project-local data directory. It reached `isWritablePrimary=true` and was
used by the replica-set integration tests. This is a development transaction
environment, not a high-availability deployment.

When the connected server reports replica-set transaction support,
`MongoPaymentRepository` executes account validation, transaction insertion,
account version/balance update, and MongoDB audit/publication metadata insertion
inside one MongoDB session transaction. Any exception aborts all three
MongoDB effects. Transient write conflicts are retried within a bounded number
of attempts.

After MongoDB commits, `EventDeliveryService` publishes the stored event to
the existing `transaction_events_by_account_day` table. Cassandra is not part
of the MongoDB transaction; its failure changes only delivery state and cannot
repeat the financial operation. The standalone fallback remains explicit and
uses the prior optimistic compare-and-set recovery behavior.

# 38. Merchant and Category Domain Foundation - 2026-09-11

Merchant and category state is current operational state in MongoDB:

```text
MongoDB
├── categories  → controlled category/subcategory taxonomy
├── merchants   → current merchant identity, category relationship, status
└── transactions → payment-time category snapshot plus merchant reference
```

Categories are system-controlled canonical pairs with stable lowercase IDs.
The explicit seed command creates a small deterministic taxonomy; application
startup never inserts seed data. Merchant IDs are backend-generated UUIDs.

Authenticated users may read active merchants and categories. Merchant
creation and updates are administrator-only because the existing `MERCHANT`
role has no merchant-owner relationship in the user model. Deactivation is a
version-checked status update; deletion is not exposed.

Payment processing now resolves the merchant through `MerchantService`,
rejects unknown or inactive merchants, verifies the current category pair, and
passes the resolved category snapshot into the existing payment service. The
payment route still contains no MongoDB or balance logic.

The transaction category fields are historical denormalization, not a second
current-state authority. They preserve the category/subcategory associated
with the completed payment if an administrator later reclassifies the merchant.
Merchant lifecycle audit facts remain in MongoDB audit records. No merchant
Cassandra table or unsupported event partition was introduced.

# 37. Controlled Payment API Boundary - 2026-09-11

The payment API is now a thin authenticated boundary over the existing
`PaymentService` and `MongoPaymentRepository`; it does not contain balance
calculation, transaction-state mutation, event construction, or MongoDB writes.

Implemented routes:

```text
POST /api/v1/payments
GET  /api/v1/payments/{transaction_id}
GET  /api/v1/payments
```

Creation requires a validated bearer token, an owner match between the server
identity and the requested account, a bounded Decimal amount with at most two
decimal places, supported three-letter currency syntax, and an
`Idempotency-Key` header. The service passes the request ID as correlation
metadata and preserves an optional causation header. The repository remains the
only component that applies the financial mutation.

Reads are owner-scoped against MongoDB current transaction documents. History
is bounded to 100 records, uses stable timestamp/transaction-ID ordering, and
supports an owner-scoped cursor plus status and merchant reference filters. The
query index `ix_transactions_user_time_id` exists specifically for this stable
history access pattern.

After the MongoDB transaction commits, the service makes a best-effort explicit
`EventDeliveryService` pass. Cassandra failure is recorded as retryable delivery
state and never reruns or rolls back the financial operation. The endpoint is a
controlled fictional payment simulation; no external payment gateway or real
settlement was introduced.
# 39. Analytics Data Foundation - 2026-09-12
 
The first analytics slice is read-only over MongoDB current transaction state.
Analytics routes:
GET /api/v1/analytics/spending/summary
GET /api/v1/analytics/spending/categories
GET /api/v1/analytics/spending/merchants
GET /api/v1/analytics/spending/trends
GET /api/v1/analytics/spending/largest
Analytics uses only COMPLETED transactions in a bounded half-open UTC range. Amounts remain Decimal values; no currency conversion is performed. Current balance and currency come from the authoritative MongoDB account document and are never reconstructed from payment history.
Category and merchant grouping uses payment-time snapshots. Current catalog state is not joined into historical totals, so reclassification and deactivation cannot rewrite past spending meaning. New payment records retain a payment-time merchant display-name snapshot; older records may have no merchant name.
MongoDB owns the operational transaction/account state used by these queries. Cassandra remains chronological event storage and is intentionally not an analytics aggregate source. No cache, warehouse, broker, new database, or ML decision was added.

# 40. Evidence-Driven ML Dataset Boundary - 2026-09-12

The ML foundation begins with a read-only dataset audit, not model training:

MongoDB current transactions -> provenance and schema audit -> point-in-time feature contract -> verified target check -> baseline readiness decision.

The initial notebook is output/jupyter-notebook/01_dataset_audit.ipynb. It
uses MongoDB.transactions and includes only COMPLETED current transaction
documents as the proposed unit of analysis. It does not read Cassandra to
reconstruct current state, insert synthetic data, create labels, train a
model, or claim metrics.

The current live audit found zero transaction documents and zero verified fraud
or human-review labels. The baseline boundary is therefore
BLOCKED_INSUFFICIENT_DATA. A future dataset must carry explicit provenance,
target semantics, temporal coverage, and leakage exclusions before model work
begins.

# 41. Controlled Synthetic ML Dataset Boundary - 2026-09-12

The empty operational dataset is not bypassed by inserting research data into
the application. A separate generator writes only to `data/synthetic/`:

```text
ml/synthetic_dataset_generator.py
        |
        +--> data/synthetic/*.csv and *.json
        |
        +--> validation and temporal split checks
```

The generated dataset is `synthetic_research`, uses fictional `syn-*`
identifiers, and is explicitly marked synthetic. It contains 10,000 bounded
rows, 500 users/accounts, 100 merchants, 12 categories, and a configured
90-day UTC period. MongoDB remains current operational state and Cassandra
remains historical event data; neither is read or written by the generator.

The dataset has six transparent generator-rule scenario labels. They are
audit/research labels and not fraud facts, real-world outcomes, or human
decisions. Candidate features are point-in-time fields only; scenario labels,
injection reasons, future-derived fields, post-event outcomes, and research
metadata are excluded from the candidate feature group. Splits are timestamp
based at 70/15/15, with historical user features calculated from prior
records only.

Generation and validation are documented in
`output/jupyter-notebook/02_generate_synthetic_dataset.ipynb` and
`output/jupyter-notebook/03_validate_synthetic_dataset.ipynb`. This remains a
research artifact, not a production ML service or inference boundary.

# 42. Deterministic Feature Matrix and Research Baseline - 2026-09-12

The synthetic dataset is transformed outside the application boundary:

```text
data/synthetic/*.csv
        |
        +--> prior-only history audit
        +--> train-fitted imputation and one-hot vocabulary
        +--> data/synthetic/features/*.csv
        +--> fixed research-only baseline
```

The feature artifact contains 28 model features and keeps identity, timestamp,
split, and `target_scenario_label` separate from the feature list. Scenario
metadata, identifiers, future statistics, post-event outcomes, and target
proxies are excluded from model inputs. Preprocessing is fit on training rows
only; validation and test are transformed with that fixed preprocessing.

The first evaluated baselines are a majority-class reference and a
standard-library Gaussian Naive Bayes classifier. The test result is a
synthetic scenario classification result only. No model artifact, production
inference route, fraud API, risk API, notification, blocking, or financial
decision was added.

# 43. Controlled ML Error Analysis Boundary - 2026-09-12

The baseline is now followed by a deterministic, research-only error-analysis
boundary. `ml/error_analysis.py` reproduces the stored Gaussian Naive Bayes
result, writes validation/test confusion matrices and per-class metrics,
exports bounded safe-field misclassification records, and performs
validation-only feature-distribution and generator-shortcut review.

The test set remains held out from fitting and model selection. Leakage review
passes for prior-only historical features, deterministic timestamp/ID
ordering, training-only preprocessing, target/metadata exclusion, and
temporal splits. The analysis does not convert synthetic scenario labels into
fraud facts, risk decisions, or production inference.

The current research decision is
`DATASET_OR_GENERATOR_REVIEW_REQUIRED_FIRST`. Rapid-repeat is perfectly
recalled on the current test split and is exactly separated by the generated
short-interval rule; unusual-time and combined-pattern rows are also exactly
associated with the configured late-hour window. These are generator-design
signals, not evidence that a complex model is ready. No dataset or generator
was changed in this review.

# 44. Versioned Synthetic Generator Revision - 2026-09-12

The original v1 synthetic artifact remains preserved under
`data/synthetic/`. A separate v2 artifact was generated under
`data/synthetic/v2/` with generator `1.1.0`, seed `20260913`, and a revised
behavior-overlap design. The generator never imports or writes MongoDB,
Cassandra, FastAPI, payment, or operational state.

Version 2 keeps the six synthetic scenario labels but makes normal behavior
non-clean: normal rows can include late hours, short gaps, higher amounts,
category changes, merchant reuse, and channel variation. Scenario modifiers
use mixtures and partial signal combinations rather than one exact rule.
Combined-pattern rows are not automatically late + rapid + extreme amount.

The candidate feature matrix remains outside the application boundary and now
has 32 fields. Four v2 features are point-in-time only: merchant novelty,
channel novelty, user-relative amount deviation, and user-relative time
deviation. Training-only preprocessing, temporal partitions, and target/
metadata exclusion remain mandatory.

The v1/v2 comparison shows reduced exact-rule rates and valid leakage and
reproducibility checks, although the transparent baseline metrics are lower on
the harder v2 task. The data-quality decision is
`REVISED_DATASET_READY_FOR_NEXT_ML_PHASE`, meaning controlled research-only
anomaly-detection and explainability evaluation may proceed. It is not a
production fraud or financial-risk boundary.

# 45. Research-Only Anomaly Detection and Explainability - 2026-09-12

Anomaly research remains outside the application and database boundaries:

```text
v2 candidate feature matrix
        |
        +--> train-only robust MAD distance model
        +--> fixed transparent signal baseline
        +--> validation/test synthetic-label ranking analysis
        +--> bounded research explanations
        |
        +--> data/synthetic/anomaly_detection/v2/
```

The selected primary model is `robust_mad_distance`, a deterministic
dependency-free statistical model. Each selected feature is centered on its
training median and scaled by `max(1.4826 * MAD, IQR / 1.349, 1e-9)`; capped
feature distances are averaged and normalized using training raw-score
min/max. Higher score means more anomalous within this experiment. Labels and
scenario metadata are used only after scoring for offline synthetic-label
evaluation. Thresholds are training score percentiles and are not action
thresholds.

The explanation layer is deterministic and feature-grounded. It distinguishes
observed signals from interpretation, warns when history is limited, and
rejects forbidden fraud language, scenario labels, generator rules, and future
metadata. The explanation sample is bounded for manual review. No production
inference artifact, FastAPI route, MongoDB write, Cassandra write, payment
control, or human decision was introduced.

## 46. Research-Only Anomaly Backend Boundary - 2026-09-12

The backend now has an authenticated, owner-scoped, read-only research anomaly
boundary:

```text
FastAPI research read
        |
        +--> MongoDB current transaction + prior COMPLETED history
        |
        +--> versioned JSON research artifact
                 |
                 +--> deterministic score and explanation
```

MongoDB remains authoritative for current transaction state. Cassandra remains
historical event storage and is not used to reconstruct balances or manufacture
model features. The integration does not write either database, publish
events, call the payment service, block/reject/delay/reverse payments, change
status or balances, or send notifications.

The artifact loader consumes `data/synthetic/anomaly_detection/v2/` and
validates model configuration, feature order, leakage contract, serialized
train-fitted parameters, and research-only thresholds. Backend startup does
not regenerate data or train a model. The persisted
`anomaly_model_parameters.json` file serializes the parameters of the already
evaluated robust-MAD research model.

Routes are `GET /api/v1/research/anomaly-score/{transaction_id}`,
`GET /api/v1/research/anomaly-scores`, and
`GET /api/v1/research/anomaly-score/{transaction_id}/explanation`.
They require bearer authentication and enforce owner scoping. Current payment
records do not contain an approved `transaction_channel` source, so live score
requests return a controlled feature-contract unavailable result rather than
inventing a channel or silently scoring an incompatible vector. Bounded list
responses mark such rows `unavailable`.

# 47. Operational Transaction Channel and Live Research Scoring - 2026-09-13

New fictional payment requests require the explicit `transaction_channel`
value `QR_SIMULATED`, `CARD_SIMULATED`, `WALLET_SIMULATED`, or
`BANK_SIMULATED`. The value is part of the current MongoDB transaction
document, payment response, and canonical transaction event payload. It is
also included in the request fingerprint, so replaying one idempotency key
cannot silently change the channel.

Legacy transaction documents may not contain this field. They remain readable
as current state, but research scoring returns an explicit unavailable result
when the current or required prior channel is missing. No bulk backfill or
invented channel is performed.

Live `channel_novelty_before` is built only from persisted completed MongoDB
transactions strictly earlier than the target, ordered by UTC timestamp and
transaction ID. The target is excluded. Synthetic rows are never mixed into
live history. MongoDB remains the current operational source; Cassandra
continues to store the historical event envelope and is not used to rebuild
account state.

The local development dependencies were verified on 2026-09-13: MongoDB
`rs0` is writable at `127.0.0.1:27018`, and Cassandra 4.0.21 is `UN` at
`127.0.0.1:9042` with the existing `spendshield_events` five-table schema.

## 48. Demo banking modules and multi-account state - 2026-09-16

MongoDB continues to own current account/resource state. The account owner
index is now non-unique so one user can explicitly create multiple fictional
BJP Bank accounts; `/accounts/me` remains the backwards-compatible default
account and `/accounts` returns the owner-scoped collection. Account balance,
owner, currency, status, identifiers, and demo profile values are server-owned.

Deposit, withdrawal, phone, bill/recharge, and self-transfer operations use
the existing idempotent payment repository and publish the same canonical
historical event boundary. Contacts, beneficiaries, billers, cards, and local
notifications are current MongoDB resource collections. They are not copied
to Cassandra as authoritative state and do not create a second balance store.

The mobile client exposes only fictional operations and reads authoritative
responses. It does not calculate or mutate balances locally. Profile/security
MPIN, admin data actions, complete card management, and notification
generation remain follow-up work.

## 49. Persisted demo merchant QR and demo security - 2026-09-16

`demo_merchants` is MongoDB current state for the two fictional classroom
merchants. A QR payload is a versioned projection of that state, not an
independent merchant authority. QR validation parses the payload, resolves the
merchant ID from MongoDB, compares protected fields, and rejects inactive or
mismatched records. Cassandra remains historical event storage only.

The demo MPIN is stored as a password hash in the owner-scoped
`demo_security` MongoDB collection. It is required for registered versioned QR
payments, has a bounded failure counter and lock state, and is never logged or
returned. This is a simulation control separate from bearer authentication.

Committed payment operations create owner-scoped in-app notification records
in MongoDB using the transaction ID as the idempotent source identity. A
notification failure cannot roll back a committed financial operation. The
fictional card-payment route uses `CARD_SIMULATED` and checks card ownership,
active status, spending limit, account funds, idempotency, and the existing
MongoDB/Cassandra event boundary.
