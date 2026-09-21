# SpendShield Backend
## Spending Analytics API

Authenticated users can read their own current-state spending analytics:

`GET /api/v1/analytics/spending/summary`  
`GET /api/v1/analytics/spending/categories`  
`GET /api/v1/analytics/spending/merchants`  
`GET /api/v1/analytics/spending/trends?interval=daily|weekly|monthly`  
`GET /api/v1/analytics/spending/largest`

Optional `start_at` and exclusive `end_at` timestamps define a half-open UTC
range. Naive timestamps are interpreted as UTC; omitted ranges default to the
preceding 30 days; ranges cannot exceed 366 days; list results are bounded.

Only COMPLETED transactions for the authenticated user's account currency are
counted. MongoDB current transaction documents are the analytical source and
the current balance comes from the MongoDB account document. Cassandra is not
used for totals. Category and merchant labels come from payment-time snapshots,
so mutable catalog changes do not rewrite historical meaning.

## ML dataset foundation

The first ML artifact is a read-only dataset audit notebook:

output/jupyter-notebook/01_dataset_audit.ipynb

It audits MongoDB.transactions, records provenance, checks completed
transaction volume and candidate labels, defines leakage exclusions, and
blocks baseline training when evidence is insufficient. The current
development database contains zero transactions and no verified fraud or
human-review label. A separate controlled synthetic research dataset now exists
under `../data/synthetic/`; it is never inserted into MongoDB or Cassandra and
its scenario labels are not fraud labels. Generation and validation are
implemented by `../ml/synthetic_dataset_generator.py` and notebooks
`output/jupyter-notebook/02_generate_synthetic_dataset.ipynb` and
`output/jupyter-notebook/03_validate_synthetic_dataset.ipynb`. No production
model or decision API has been added to the backend. The separate research
feature matrix and baseline artifacts are under `../data/synthetic/features/`
and `../data/synthetic/baseline/`; their metrics apply only to synthetic
scenario classification.
This directory contains the Phase 02 Python/FastAPI foundation, the Phase 03 authentication and authorization foundation, and the Phase 2 database foundation for SpendShield.

The current scope is intentionally limited to:

- a typed environment-backed configuration layer;
- a versioned FastAPI router;
- deterministic process health endpoints;
- centralized standard-library logging;
- safe structured API errors;
- common health/error schemas;
- a minimal pytest setup;
- authentication and role-based authorization foundations;
- backend-authoritative account creation, ownership checks, and admin status management;
- optimistic account version checks and MongoDB-backed audit records;
- persistence-neutral financial domain and payment boundaries;
- canonical historical event envelopes;
- MongoDB operational-document persistence boundaries;
- Cassandra chronological-event persistence boundaries;
- database dependency health reporting;
- authenticated, owner-scoped fictional payment API endpoints.

Subscriptions, notifications, and forensic functionality are not implemented
yet. ML remains research-only: the backend can load the versioned anomaly
artifact for a read-only score, but it does not train or make decisions. The
controlled fictional payment API now delegates to the
validated transaction persistence foundation, while wallet UI, real settlement,
and external payment integrations remain out of scope. The database foundation
provides connectivity, schema/index creation, and repository boundaries without
introducing a second source of financial truth.

## MongoDB transaction validation

The existing Windows MongoDB service remains on `127.0.0.1:27017` as a
standalone deployment. Its data path contains other local development
databases and was not modified. A separate single-node development replica
set named `rs0` was started for validation on `127.0.0.1:27018` with an
isolated project-local data directory. This is not production high
availability.

New payment requests must include `transaction_channel` with one of
`QR_SIMULATED`, `CARD_SIMULATED`, `WALLET_SIMULATED`, or `BANK_SIMULATED`.
The value is persisted with the current transaction and historical event. Old
documents without it are not backfilled; research scoring reports controlled
feature unavailability when it is required.

The SpendShield development `.env` selects the validated single-node `rs0`
endpoint. Set both the URI and replica-set configuration:

```text
SPENDSHIELD_MONGODB_URI=mongodb://127.0.0.1:27018/?replicaSet=rs0
SPENDSHIELD_MONGODB_REPLICA_SET=rs0
```

For physical-device development, allow the PC's current LAN address in the
backend host validation list. Keep this list local and update the LAN address
when the network changes:

```text
SPENDSHIELD_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,10.165.59.245
```

The mobile app should use the matching API base URL in `mobile/.env.local`:

```text
EXPO_PUBLIC_API_BASE_URL=http://10.165.59.245:8000/api/v1
```

The payment repository uses a real MongoDB multi-document transaction when
the connected server reports the configured replica set. It commits account
state, transaction state, and MongoDB publication metadata together. Cassandra
delivery remains a separate retryable step and is never part of the MongoDB
transaction.

## Development startup order

The isolated development replica set must be running before starting the
backend. In PowerShell, use a terminal dedicated to MongoDB:

```powershell
& 'C:\Program Files\MongoDB\Server\8.3\bin\mongod.exe' `
  --dbpath 'D:\E_Drive\Project\.mongodb-rs-validation\data' `
  --replSet rs0 --port 27018 --bind_ip 127.0.0.1 `
  --logpath 'D:\E_Drive\Project\.mongodb-rs-validation\mongod.log' --logappend
```

Verify it is primary before starting the backend:

```powershell
mongosh 'mongodb://127.0.0.1:27018/?replicaSet=rs0' --eval "db.hello()"
```

Start Cassandra only when historical event delivery is required, verify it on
`127.0.0.1:9042`, then start the backend with
`python -m uvicorn app.main:app --reload` from this directory. Finally verify
`/health` and `/api/v1/health/dependencies`; the latter must report `rs0` and
`is_writable_primary: true` for MongoDB. This single-node replica set is for
development transaction support, not production high availability.

## Prerequisites

- Python 3.11 or newer

## Setup

From this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

The copied `.env` contains local-development defaults and an authentication
placeholder. Do not add real credentials to source control.

Authentication requires `SPENDSHIELD_AUTH_SECRET_KEY` to be a long random value. The application does not use the placeholder for production authentication.

## Run the backend

```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health endpoints:

```text
GET http://127.0.0.1:8000/health
GET http://127.0.0.1:8000/api/v1/health
GET http://127.0.0.1:8000/api/v1/health/dependencies
```

Account endpoints:

```text
POST /api/v1/accounts
GET  /api/v1/accounts/me
GET  /api/v1/accounts/{account_id}
PATCH /api/v1/accounts/{account_id}/status  # administrator only
```

The two process endpoints return a process-level response similar to:

```json
{
  "status": "ok",
  "service": "spendshield-backend"
}
```

The two process endpoints do not claim that MongoDB, Cassandra, or any other
future dependency is healthy.

`/api/v1/health/dependencies` is the dependency-readiness endpoint. It reports
MongoDB and Cassandra independently as `ok`, `not_configured`, or
`unavailable`, without exposing connection strings or credentials.

## Database foundation

The database manager owns driver connections and keeps them out of routes and
services. MongoDB is used for flexible operational and investigation documents,
with initial collections for `users`, `accounts`, `merchants`, `transactions`,
`subscriptions`, `cases`, `evidence`, `findings`, and `audit_records`. The
schema initializer creates the documented uniqueness and workload indexes,
including one-account-per-user ownership uniqueness.

Cassandra is reserved for chronological event workloads. The initial tables
are partitioned by an identifier and UTC event day:

```text
authentication_events_by_user_day
session_events_by_user_day
device_events_by_device_day
transaction_events_by_account_day
audit_events_by_case_day
```

When `SPENDSHIELD_MONGODB_URI` is configured, authentication uses the
MongoDB-backed user repository while preserving the Phase 03 `UserRepository`
contract. With no MongoDB URI, the application keeps the explicit unavailable
repository and reports MongoDB as `not_configured`.

The database integration tests use isolated MongoDB database names and
Cassandra event partitions. The local Cassandra test harness reuses one valid
test keyspace to avoid repeated single-node schema-agreement migrations; test
Mongo databases and event partitions remain isolated. They run when local
services are available and skip only the external integration cases when a
service is not running.

The dependency readiness response also reports safe MongoDB identity fields
(`endpoint`, `replica_set`, and `is_writable_primary`) so a local process cannot
silently be mistaken for the untouched standalone service on port 27017.

Account creation is backend-authoritative: the client cannot set the owner,
currency, starting balance, or status. Account IDs are UUIDs and account reads
enforce owner/admin authorization. The financial domain also contains exact
decimal money rules, an explicit transaction lifecycle, idempotency fingerprint
rules, admin-only status transitions, optimistic version checks, and audit
records for account creation/status changes. The MongoDB payment repository now
provides a closed persistence boundary with unique request reservations,
version-checked balance updates, recovery after partial failure, and durable
transaction-event enqueueing. The payment API delegates to this repository and
never changes balances in route code. Routed event records can be retried from
MongoDB through `EventDeliveryService` into the existing Cassandra transaction
table. This is not event sourcing or an atomic outbox; MongoDB owns current
state and Cassandra owns historical events.

## Authentication

The authentication foundation uses:

- Argon2 password hashing through `pwdlib`;
- short-lived HS256 JWT access tokens;
- server-side user lookup for every protected request;
- controlled roles: `USER`, `INVESTIGATOR`, `MERCHANT`, and `ADMIN`;
- reusable `get_current_user` and `require_role(...)` dependencies.

Endpoints:

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/auth/me
```

Public registration always creates a `USER`. Clients cannot select `ADMIN`, `INVESTIGATOR`, or `MERCHANT` through the registration payload.

When MongoDB is not configured, the default application uses an explicit unavailable repository. When it is configured, authentication uses `MongoUserRepository`. Authentication tests inject `InMemoryUserRepository`, which is a volatile test fake and is not production persistence. There is no logout endpoint yet: clients discard the stateless access token, while server-side revocation can be added with MongoDB-backed token/session state in a later phase.

## Payment API

The controlled fictional payment boundary is available under `/api/v1`:

```text
POST /api/v1/payments
GET  /api/v1/payments/{transaction_id}
GET  /api/v1/payments
```

Payment creation requires a bearer token and an `Idempotency-Key` header. The
authenticated user's server-side identity is used as the account owner; the
client cannot provide an owner, actor, balance, status, transaction ID, event
ID, or publication state. Only the account owner may create or read payments.

The payment is fictional and internal to SpendShield. It does not connect to
UPI, cards, banks, payment gateways, or real settlement systems. MongoDB
commits the current account/transaction/publication state transactionally;
Cassandra delivery is a separate retryable historical-event operation.
History is bounded to 100 records per request and uses an owner-scoped cursor.

## Run tests

```powershell
python -m pytest
```

## Structure

```text
backend/
├── app/
│   ├── api/v1/       # Versioned HTTP routes
│   ├── core/         # Configuration, logging, exceptions
│   ├── schemas/      # Shared Pydantic API schemas
│   ├── services/     # Reserved for future application services
│   ├── repositories/ # Persistence contracts and adapters
│   ├── db/           # Database managers, schemas, and event access
│   └── utils/        # Shared backend utilities
├── tests/
├── .env.example
└── requirements.txt
```

The current implementation includes the validated **Phase 5 - Payment Engine**
and the Merchant & Category domain foundation. Account status management, audit
persistence, the generic durable event delivery boundary, transactional payment
persistence, merchant validation, category resolution, the controlled payment
API, and the first read-only spending analytics slice are implemented. Balance
history, subscriptions, recurring commitments, frontend wallet experience, ML,
and external settlement remain pending. New account/payment/analytics behavior
must use the database/repository boundaries above and must not move
authoritative state into the frontend.

## Merchant and Category API

Authenticated users can read the controlled catalog:

```text
GET /api/v1/categories
GET /api/v1/merchants
GET /api/v1/merchants/{merchant_id}
```

Only `ADMIN` users can create or update merchants:

```text
POST  /api/v1/merchants
PATCH /api/v1/merchants/{merchant_id}
```

Categories are system-controlled and seeded explicitly with:

```powershell
python scripts/seed_catalog.py
```

The application does not seed data at startup. Merchant updates are
version-checked, inactive merchants cannot accept payments, and payments
derive category information from the current merchant. Completed transactions
store an immutable category/subcategory snapshot so later merchant
reclassification does not rewrite historical meaning. MongoDB owns current
merchant/category state; Cassandra remains historical event storage and no
merchant Cassandra table was introduced.

## Demo banking modules

The authenticated demo surface also exposes server-owned, fictional
operations:

```text
GET  /api/v1/accounts
POST /api/v1/payments/deposit
POST /api/v1/payments/withdraw
POST /api/v1/payments/phone
POST /api/v1/payments/bill
CRUD  /api/v1/contacts
CRUD  /api/v1/beneficiaries
CRUD  /api/v1/billers
GET/POST/PATCH /api/v1/cards
GET/PATCH/DELETE /api/v1/notifications
```

These routes are simulation-only and owner-scoped. Account balances and
transaction effects remain in MongoDB; each committed financial operation
continues through the existing idempotent transaction and historical-event
boundary. Resource modules are current MongoDB state and do not create a
second balance or event store.

## Demo merchant QR and demo security

Authenticated routes include:

```text
GET   /api/v1/demo-merchants
GET   /api/v1/demo-merchants/{merchant_id}
PATCH /api/v1/demo-merchants/{merchant_id}/status   # ADMIN only
GET   /api/v1/demo-security
PUT   /api/v1/demo-security/mpin
POST  /api/v1/payments/qr/validate
POST  /api/v1/payments/qr
POST  /api/v1/payments/card
PATCH /api/v1/auth/me
```

The classroom merchants are `MODI-CHAI-001` (Modi Chai ki Tapri) and
`MELONI-CHOCO-002` (Meloni ki Melodi Chocolate Shop). QR data is versioned
JSON projected from MongoDB merchant state and is not UPI or a real bank QR.
Registered QR payments require a six-digit hashed demo MPIN.
