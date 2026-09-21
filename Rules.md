# Rules

## Project
**SpendShield — Intelligent Payment, Financial Awareness & Digital Forensics Platform**

## Purpose

This document contains the non-negotiable rules that must be followed while designing, coding, testing, modifying, deploying, and documenting SpendShield.

These rules apply to human developers and AI coding agents such as Antigravity/Codex.

---

# 1. Core Product Rules

### Rule 1 — Build One Product

SpendShield must remain one coherent application.

Do not build:

```text
Payment App
+
Separate ML Demo
+
Separate Forensic Demo
```

Instead build:

```text
Financial Activity
      ↓
Intelligence
      ↓
Detection
      ↓
Investigation
      ↓
Evidence
      ↓
Decision
```

### Rule 2 — Every Technology Must Have a Purpose

Do not add a technology merely because it appears impressive.

Every major technology must answer:

```text
Why is it needed?
What workload does it solve?
What concept does it demonstrate?
```

### Rule 3 — Computer Forensics Is a Core Module

Forensics must not be an optional decorative page.

It must connect meaningfully to suspicious financial activity.

### Rule 4 — No Fake Complexity

Do not create unnecessary microservices, AI agents, blockchain systems, Kubernetes clusters, or distributed components simply to make the architecture look advanced.

Complexity must solve a real requirement.

---

# 2. AI Coding-Agent Rules

### Rule 5 — Read Documentation Before Coding

Before modifying the project, an AI agent must read:

```text
whole_project_idea_and_concept.md
PRD.md
Architecture.md
Phases.md
Design.md
Rules.md
Memory.md
```

Then inspect the existing source code.

### Rule 6 — Do Not Guess Existing Code

Never assume:

- a file exists,
- an API exists,
- a database collection exists,
- a function exists,
- an environment variable exists,
- a model exists.

Inspect first.

### Rule 7 — Do Not Rewrite Working Systems Without Reason

Before replacing working code:

1. identify the current implementation,
2. identify the problem,
3. determine impact,
4. make the smallest safe change.

### Rule 8 — Preserve Existing Functionality

A new feature must not silently break existing functionality.

After significant changes, run relevant tests.

### Rule 9 — No Blind Bulk Changes

Do not perform large automated rewrites without inspecting the affected files.

### Rule 10 — Update Memory.md

After every meaningful implementation milestone, update:

```text
Memory.md
```

Record:

- what changed,
- why,
- files affected,
- decisions,
- tests,
- known issues,
- next action.

---

# 3. Code Quality Rules

### Rule 11 — Separation of Concerns

Maintain:

```text
Routes
 ↓
Services
 ↓
Repositories/Engines
 ↓
Databases
```

Do not put business logic inside UI components or oversized API route handlers.

### Rule 12 — Small Responsibilities

Functions should have clear responsibilities.

Avoid functions that simultaneously:

```text
validate
calculate
write MongoDB
write Cassandra
run ML
generate PDF
send notification
```

Split these responsibilities.

### Rule 13 — Explicit Types

Use strong typing where practical.

Frontend:

```text
TypeScript
```

Backend:

```text
Pydantic models
Type hints
```

### Rule 14 — No Dead Code

Do not leave abandoned implementations, unused routes, fake services, or obsolete duplicate components.

Remove or document deprecated code.

### Rule 15 — No Magic Values

Configuration such as:

- thresholds,
- limits,
- time windows,
- risk levels,
- file size limits

should be centralized/configurable where appropriate.

---

# 4. Frontend Rules

### Rule 16 — Backend Is the Source of Truth

The frontend must never be the authoritative source for:

- balance,
- transaction status,
- risk score,
- evidence integrity,
- permissions.

### Rule 17 — No Direct Database Access

The frontend must never directly access:

```text
MongoDB
Cassandra
Object Storage credentials
```

All access goes through authorized backend APIs.

### Rule 18 — Handle All UI States

Every important asynchronous feature must support:

```text
Loading
Success
Empty
Error
```

### Rule 19 — Do Not Hide Important Information

If an ML finding exists, the user should be able to discover why.

If evidence conflicts, the conflict must be visible.

If evidence integrity fails, the failure must be obvious.

### Rule 20 — Avoid Decorative Cybersecurity UI

Do not use:

- fake terminal screens,
- random matrix effects,
- meaningless hacker animations,
- unnecessary neon interfaces.

The product should look professional.

---

# 5. Financial Rules

### Rule 21 — Backend Controls Balance

Balance calculations must happen in trusted backend logic.

### Rule 22 — Payment Must Be Consistent

A successful payment must produce a consistent state:

```text
Transaction
+
Balance Update
+
Relevant Event
```

### Rule 23 — Failed Payments Must Not Deduct Funds

If payment validation fails, the balance must remain unchanged.

### Rule 24 — Prevent Duplicate Payments

The payment flow must have an idempotency strategy.

Retries must not accidentally create multiple successful payments.

### Rule 25 — Never Use Real Money

The application is a fictional/educational payment environment.

Do not connect it to real banking or payment settlement systems.

---

# 6. QR Rules

### Rule 26 — Validate QR Data

Never trust decoded QR content.

Validate:

- format,
- merchant identifier,
- supported scheme,
- merchant status.

### Rule 27 — No Arbitrary External Payment

QR processing must remain inside the controlled fictional ecosystem.

---

# 7. Database Rules

### Rule 28 — MongoDB Has a Defined Responsibility

Use MongoDB for flexible documents such as:

```text
users
accounts
transactions
subscriptions
cases
evidence
findings
reports
```

### Rule 29 — Cassandra Has a Defined Responsibility

Use Cassandra for high-volume chronological/event workloads.

Do not treat Cassandra as a second MongoDB.

### Rule 30 — Cassandra Is Query-First

Before creating a Cassandra table, define:

```text
What query will this table serve?
What is the partition key?
What is the clustering order?
What is the expected partition size?
```

### Rule 31 — No Arbitrary Duplication

Do not duplicate every object into both databases.

Duplication is allowed only when justified by access patterns or event architecture.

### Rule 32 — Index Deliberately

Create indexes based on actual query patterns.

Do not index every field.

### Rule 33 — Database Credentials Stay Secret

Never commit:

```text
passwords
API keys
connection strings
private certificates
tokens
```

---

# 8. ML Rules

### Rule 34 — ML Must Solve a Defined Problem

Every model must have:

```text
Problem
Target
Features
Dataset
Baseline
Model
Metric
Evaluation
Limitations
```

### Rule 35 — Start With a Baseline

Do not begin with a complex model.

Establish a simple baseline first.

### Rule 36 — No Fake Accuracy

Never write:

```text
Accuracy = 99%
```

unless it was actually measured using a valid evaluation procedure.

### Rule 37 — Avoid Data Leakage

Do not use future information when predicting past/current events.

### Rule 38 — Reuse Training Preprocessing

Production preprocessing must match training preprocessing.

### Rule 39 — Version Models

Production models must be identifiable by version.

### Rule 40 — Explain ML Outputs

Where possible, show the signals/features contributing to the result.

### Rule 41 — Anomaly Is Not Fraud

Never convert:

```text
Anomaly
```

directly into:

```text
Fraud
```

The correct language is:

```text
Unusual
Potentially Suspicious
Requires Review
```

---

# 9. Jupyter Rules

### Rule 42 — Notebooks Are for Experimentation

Jupyter notebooks are the research/experimentation environment.

Production business logic must not depend on manually running a notebook.

### Rule 43 — Reproducibility

A notebook should document:

- data source,
- preprocessing,
- parameters,
- model,
- evaluation,
- output.

### Rule 44 — Export Production Models

Once validated:

```text
Notebook
 ↓
Exported Model
 ↓
Production Inference
```

---

# 10. Forensic Rules

### Rule 45 — Authorization First

Only authorized evidence may be processed.

### Rule 46 — Preserve Original Evidence

Do not modify original evidence during processing.

Conceptually:

```text
Original
 ↓
Hash
 ↓
Read/Process
 ↓
Derived Artifact
```

### Rule 47 — Hash Before/At Ingestion

Calculate a cryptographic hash for evidence as part of ingestion.

SHA-256 is the baseline.

### Rule 48 — Never Hide Hash Mismatches

If verification fails:

```text
INTEGRITY MISMATCH
```

must be clearly recorded and shown.

### Rule 49 — Preserve Provenance

Every derived artifact should retain a reference to its source evidence where possible.

### Rule 50 — Raw and Normalized Data Are Different

Do not overwrite original/source representations with normalized representations.

### Rule 51 — Do Not Invent Evidence

The system must never create a forensic fact merely because an expected relationship is missing.

### Rule 52 — Evidence Is Not Automatically Truth

Evidence can be incomplete, conflicting, corrupted, or misleading.

The system must support uncertainty.

---

# 11. Chain-of-Custody Rules

### Rule 53 — Record Evidence Handling

Meaningful evidence operations should be auditable.

Examples:

```text
Acquired
Ingested
Hashed
Processed
Viewed
Verified
Exported
```

### Rule 54 — Identify Actor and Time

Custody records should contain:

```text
Actor
Timestamp
Action
Evidence ID
Case ID
```

### Rule 55 — Do Not Claim Legal Admissibility

The application may support evidence integrity and provenance.

It must not automatically claim legal admissibility.

---

# 12. Timeline Rules

### Rule 56 — Preserve Source Time

Do not silently rewrite timestamps.

### Rule 57 — Track Timezone Context

Where source metadata provides timezone information, preserve it.

### Rule 58 — Conflicting Times Must Remain Visible

If sources disagree:

```text
Potential Temporal Conflict
```

must be surfaced.

### Rule 59 — Do Not Manufacture Missing Events

Missing data is:

```text
Unknown / Missing
```

not an invented event.

---

# 13. Correlation Rules

### Rule 60 — Every Relationship Needs a Reason

Example:

```text
Transaction → Session
Reason: matching session_id
```

### Rule 61 — Use Evidence-Based Correlation

Allowed signals include:

- identifiers,
- timestamps,
- known relationships,
- source metadata,
- documented contextual rules.

### Rule 62 — Avoid Over-Correlation

Temporal proximity alone should not automatically prove causality.

### Rule 63 — Correlation Is Not Causation

The UI must distinguish:

```text
Related
```

from:

```text
Caused
```

unless causal evidence genuinely exists.

---

# 14. Investigation Rules

### Rule 64 — Human Investigator Remains in Control

The system provides decision support.

### Rule 65 — Separate Observation From Interpretation

Use:

```text
Observed:
Transaction occurred at 22:36.

Analysis:
Transaction differs from historical behaviour.

Investigator:
Requires further review.
```

### Rule 66 — Support Contradictory Evidence

A finding should be able to contain both:

```text
Supporting Evidence
Contradictory Evidence
```

### Rule 67 — No Automatic Accusation

Never display:

```text
Person X committed fraud.
```

based solely on ML or correlation.

---

# 15. Evidence Upload Security Rules

### Rule 68 — Validate Uploads

Check:

- extension,
- MIME/content type,
- size,
- filename,
- storage path.

### Rule 69 — Prevent Path Traversal

Never construct storage paths directly from untrusted filenames.

### Rule 70 — Isolate Evidence Storage

Evidence storage should not expose arbitrary executable files to the web application.

### Rule 71 — Do Not Execute Evidence

Uploaded evidence must never be executed as code.

---

# 16. Authentication & Authorization Rules

### Rule 72 — Passwords Must Be Hashed

Never store plaintext passwords.

### Rule 73 — Enforce RBAC Server-Side

Frontend hiding is not authorization.

### Rule 74 — Least Privilege

Users should receive only the permissions they require.

### Rule 75 — Audit Security Events

Record meaningful:

```text
Login
Failed Login
Logout
Permission Failure
Administrative Changes
```

---

# 17. API Rules

### Rule 76 — Validate Every Input

Do not trust client-provided:

- amounts,
- IDs,
- roles,
- risk scores,
- case ownership,
- evidence metadata.

### Rule 77 — Consistent Errors

Use structured error responses.

### Rule 78 — Do Not Leak Internals

Do not return:

```text
stack traces
database credentials
internal paths
secret configuration
```

to users.

### Rule 79 — Authorization Before Sensitive Operations

Check permissions before accessing:

```text
evidence
cases
reports
administrative data
```

---

# 18. Testing Rules

### Rule 80 — Test Critical Logic

At minimum test:

```text
Payment
Balance
Authentication
Authorization
Evidence Hashing
Hash Verification
Normalization
Correlation
ML Inference
Report Generation
```

### Rule 81 — Test Failure Paths

Do not test only successful cases.

Test:

```text
Invalid input
Insufficient balance
Duplicate request
Unauthorized access
Corrupt evidence
Hash mismatch
Missing data
Model unavailable
Database failure
```

### Rule 82 — ML Must Be Evaluated Separately

Unit tests do not replace model evaluation.

### Rule 83 — End-to-End Test Must Exist

The complete investigation journey must be tested.

---

# 19. Documentation Rules

### Rule 84 — Documentation Must Match Reality

Never document a feature as complete if it does not work.

### Rule 85 — Update Architecture After Architectural Changes

If database responsibility, service boundaries, or deployment architecture changes, update `Architecture.md`.

### Rule 86 — Update PRD After Requirement Changes

If a requirement changes materially, update `PRD.md`.

### Rule 87 — Update Phases After Scope Changes

If implementation order changes, update `Phases.md`.

### Rule 88 — Update Design After UI Changes

Major screen/interaction changes must be reflected in `Design.md`.

### Rule 89 — Memory.md Is the Living Record

`Memory.md` must be updated continuously.

---

# 20. Git Rules

### Rule 90 — Small Meaningful Commits

Prefer commits representing one coherent change.

Examples:

```text
feat: add transaction service
feat: add evidence hashing
fix: prevent duplicate payment
test: add hash verification tests
```

### Rule 91 — Never Commit Secrets

Check before committing.

### Rule 92 — Do Not Commit Large Generated Data

Large datasets and raw forensic evidence should not be committed unless intentionally required and permitted.

---

# 21. Dependency Rules

### Rule 93 — Minimize Dependencies

Do not add a package for functionality already available in the existing stack unless there is a good reason.

### Rule 94 — Review New Dependencies

Before adding a dependency, consider:

```text
Maintenance
Security
License
Size
Compatibility
Necessity
```

---

# 22. Performance Rules

### Rule 95 — Measure Before Optimizing

Do not optimize based purely on assumptions.

### Rule 96 — Avoid Unnecessary Database Calls

Use appropriate queries and batching.

### Rule 97 — Paginate Large Results

Never load huge transaction/event/evidence lists into the frontend at once.

### Rule 98 — Time-Bound Forensic Queries

Investigation event queries should normally use a defined case/time scope.

---

# 23. Demo Data Rules

### Rule 99 — Clearly Label Synthetic Data

Synthetic/demo data must be distinguishable from real public datasets.

### Rule 100 — Deterministic Demo Cases

The primary demonstration case should be reproducible.

### Rule 101 — No Fake Research Claims

Synthetic results must not be presented as real-world forensic statistics.

---

# 24. AI Agent Workflow Rule

Every AI coding session should follow:

```text
READ
 ↓
UNDERSTAND
 ↓
INSPECT
 ↓
PLAN
 ↓
IMPLEMENT
 ↓
TEST
 ↓
REVIEW
 ↓
DOCUMENT
 ↓
UPDATE MEMORY.md
```

The agent must not jump directly from prompt to large-scale implementation.

---

# 25. Change Management Rule

Before implementing a major change, answer:

```text
What changes?
Why?
What depends on it?
What can break?
Which documents must change?
How will it be tested?
```

---

# 26. Definition of a Safe Change

A change is considered safe only when:

```text
Code Updated
+
Tests Passed
+
Existing Functionality Verified
+
Security Considered
+
Documentation Updated
+
Memory.md Updated
```

---

# 27. Final Non-Negotiable Principle

> **SpendShield must never manufacture certainty.**

Financial data can be incomplete.

Machine learning can be wrong.

Correlation can be misleading.

Evidence can conflict.

Therefore the platform must help investigators reason about evidence rather than pretending to know more than the evidence supports.

The product should always prefer:

```text
Evidence
→ Explanation
→ Uncertainty
→ Human Review
```

over:

```text
Guess
→ Confidence
→ Automatic Conclusion
```

That principle governs the entire architecture, ML system, forensic workflow, and user interface.

---

# 28. Current Enforcement Status - 2026-09-11

The current backend repair enforces the following rules in code and tests:

- MongoDB remains the authoritative current-state store; Cassandra remains the historical event store.
- Account ownership, server-owned account defaults, exact decimal money, account status, transaction transitions, and idempotency conflict semantics are explicit.
- Frontend/client input cannot set authoritative account ownership or opening balance.
- JWT issuer/audience validation, production security configuration checks, request IDs, and baseline response headers are implemented.
- Cross-owner account reads are denied without revealing whether the resource exists.

The following rules remain future implementation boundaries rather than completed features:

- Public payment settlement requires a tested MongoDB transaction path for state and publication metadata. The configured development environment now uses the validated `rs0` path; the standalone optimistic compare-and-set implementation remains only as an explicit fallback for environments that genuinely require it.
- Account creation and status changes now create canonical MongoDB audit records; Cassandra historical publication is not yet wired to account workflows.
- Account status changes are admin-only, version-checked, and restricted to explicit domain transitions.
- Rate limiting, refresh-token revocation, MFA, ML, forensic processing, correlation, reporting, frontend behavior, and deployment controls are not implemented.

## 29. Event Publication Enforcement Status - 2026-09-11

The current backend also enforces these event-boundary rules:

- A retry reuses the stored event ID and envelope; it never invokes the financial operation again.
- MongoDB publication records have unique event identity, explicit pending/failed/published metadata, and bounded error classifications.
- Cassandra publication targets must use an existing query-specific event table; no account table or unsupported partition is invented.
- Cassandra remains historical event storage and cannot become the source of current account or balance state.
- Correlation ID, causation ID, request provenance, schema version, and event ID remain in the canonical envelope delivered to Cassandra.
- Account state and its MongoDB audit/publication record are atomic in the configured `rs0` development path; the standalone fallback must still not be described as atomic.

### Rule 31 — Payment Persistence Must Be Recoverable Before API Exposure

The implemented payment repository follows these boundaries:

- MongoDB owns current account balance and transaction state.
- A unique owner/idempotency reservation is created before the account CAS.
- The account debit requires the expected account version, owner, active status,
  currency, and balance to match.
- Same-key/same-request retries replay the existing transaction; same-key
  conflicting requests are rejected.
- A financial-operation retry and a Cassandra event-delivery retry are separate
  concerns. Event delivery reuses the stored event ID and never reruns the
  debit.
- Cassandra stores the historical `TRANSACTION_*` envelope in the existing
  `transaction_events_by_account_day` table; it is not event sourcing.
- The standalone MongoDB fallback is not a multi-document transaction. It must
  be described as optimistic compare-and-set with staged recovery. The
  development `.env` must select the validated `rs0` transaction path before
  payment settlement is exposed.

### Rule 32 — MongoDB Atomicity Must Be Observed, Not Assumed

- A replica-set connection must report the configured set name and a writable
  primary before transaction mode is selected.
- Account state, transaction state, and MongoDB publication metadata must be
  written in one MongoDB transaction in replica-set mode.
- A rollback test must prove that an injected publication failure leaves no
  account debit, transaction document, or publication record.
- Cassandra publication is outside the MongoDB transaction and remains
  retryable through the stored event envelope.
- A standalone MongoDB connection must use and report the existing optimistic
  compare-and-set fallback; it must not be described as atomic.

### Rule 33 — Payment API Must Remain a Thin, Owner-Scoped Boundary

- Payment routes must require bearer authentication and use the server-side
  authenticated user as the payment owner.
- The client may provide only the payment request fields already supported by
  `PaymentCommand`; it may not provide balance, status, actor, transaction ID,
  event ID, timestamps, or publication state.
- Payment routes must delegate financial mutation, idempotency, and event
  construction to `PaymentService` and `MongoPaymentRepository`.
- Payment history must be bounded, owner-scoped, stably ordered, and served
  from MongoDB current state rather than Cassandra.
- Cassandra delivery is post-commit and retryable; its failure must not repeat
  or roll back an already-committed financial operation.
- The payment remains fictional and must not connect to a real payment gateway.

### Rule 34 — Merchant and Category State Must Be Server-Controlled

- Category pairs are canonical system data with stable IDs; normal users cannot
  create arbitrary taxonomy values.
- Merchant IDs are generated by the backend. Client input cannot set merchant
  status, version, timestamps, or category display data.
- Merchant creation and updates require the existing `ADMIN` role. The
  `MERCHANT` role is read-only for this phase because merchant ownership is not
  modeled yet.
- Merchant updates use expected-version checks and `ACTIVE`/`INACTIVE` state
  transitions. An inactive merchant cannot accept a payment.
- Payment routes must resolve merchant and category through `MerchantService`;
  they must not query MongoDB directly or accept a client category.
- Completed transactions retain an immutable category/subcategory snapshot for
  historical consistency. This snapshot is not a competing current-state
  source of truth.
- MongoDB owns current merchant/category state. Cassandra remains historical
  event storage; no unsupported merchant Cassandra table is introduced.
### Rule 36 — Analytics Must Be Read-Only, Owner-Scoped, and Traceable

Spending analytics use the authenticated server-side owner identity and never accept a client-selected user or account. Totals come from MongoDB current transaction state, not Cassandra event history, and current balance is never reconstructed from events.
Only COMPLETED transactions count as spending in this phase. Analytics ranges are bounded half-open UTC intervals with exact Decimal arithmetic and no implicit currency conversion. Category and merchant grouping preserves payment-time snapshots.
Analytics APIs are read-only and must not change balances, transactions, catalog state, audit state, or Cassandra history. An analytics summary is a derived view, not an ML prediction, fraud decision, forensic finding, or replacement for domain state.

### Rule 102 — Dataset Evidence Must Precede ML Claims

- The first ML implementation step is a read-only dataset and provenance audit.
- Operational transaction status is not a fraud or human-review label.
- Synthetic, public, simulated-case, and authorized user-provided data must be
  explicitly distinguished by provenance.
- A dataset contract must identify the unit of analysis, source, features,
  target semantics, temporal coverage, and leakage exclusions.
- If data volume or label quality is insufficient, the baseline must be
  reported as blocked or not ready. No accuracy, precision, recall, or risk
  claim may be invented.
- Notebook experimentation must not be required for production business
  logic and must not write operational MongoDB or Cassandra state.

### Rule 103 — Synthetic ML Data Must Be Isolated and Provenance-Marked

- Synthetic research records must remain outside MongoDB operational
  collections and Cassandra event tables. The generator must not connect to or
  mutate either database.
- Every generated row must carry explicit synthetic provenance, a dataset
  version, fictional identifiers, and a documented generator-rule label.
- Synthetic scenario labels are not confirmed fraud, financial-crime, or
  human-review labels. A field named `fraud` or `confirmed_fraud` must not be
  used for these scenarios.
- Candidate features must be separated from audit-only labels and metadata.
  Future-derived, target-derived, post-event, and scenario-injection fields are
  forbidden from the candidate feature set.
- Temporal splits must be timestamp-based and user-history features must use
  records available before the current transaction. Random row splitting is
  not an acceptable substitute where time order matters.
- Dataset counts, scenario distributions, file paths, limitations, and seed
  must be recorded in a manifest. A reproducibility failure blocks the next
  ML phase.

### Rule 104 — Candidate Features and Baselines Must Be Train-Fitted and Research-Only

- Candidate features must be generated from the isolated synthetic files or an
  explicitly approved dataset boundary; they must not read application state
  or historical Cassandra events to manufacture current-state features.
- Numeric imputation and categorical vocabularies must be fit on training rows
  only. Validation and test rows receive the already-fitted transformation.
- The target, scenario metadata, identifiers, split assignment, future
  aggregates, post-event outcomes, and direct target proxies are not model
  features. Audit identity may be retained outside the feature list.
- Time-based train/validation/test partitions are the primary evaluation
  boundary. The test set is held out until the fixed baseline configuration is
  evaluated.
- Majority references and simple interpretable baselines must precede complex
  models. No metric may be described as fraud detection, prevention, savings,
  or production risk reduction.

### Rule 105 - Error Analysis Must Preserve Held-Out Evaluation and Scenario Boundaries

- Reproduce the fixed baseline before inspecting or interpreting its errors.
- Keep validation available for diagnostic review; keep the test set out of
  fitting, tuning, and model selection.
- Report confusion matrices, per-class metrics, class support, and bounded
  misclassified records in the authoritative class order.
- Use validation-only feature distributions and shortcut evidence when
  reviewing generator behavior. Do not modify the dataset or generator during
  a diagnostic error-analysis pass unless a separate approved dataset revision
  is started.
- Treat a generator rule that is nearly exclusive to a label as a shortcut
  risk, not as proof of a useful real-world detector.
- An error-analysis result must distinguish synthetic scenario confusion from
  fraud, suspicious activity, human interpretation, and final decisions.
- If generator shortcuts or severe class sparsity undermine the protocol,
  choose `DATASET_OR_GENERATOR_REVIEW_REQUIRED_FIRST` before increasing model
  complexity.

### Rule 106 - Synthetic Dataset Revisions Must Be Versioned and Compared

- Never overwrite a prior synthetic dataset, feature artifact, baseline, or
  error-analysis report when changing generator behavior.
- A revised dataset must record its generator version, feature version,
  baseline version, seed, exact distributions, temporal ranges, provenance,
  limitations, and practical file checksums.
- Normal synthetic behavior must include controlled variation so that one
  exact amount, hour, interval, merchant, category, or channel rule does not
  define a class.
- Candidate user-relative and novelty features must be computed from records
  strictly earlier than the current transaction and documented in the feature
  dictionary.
- Compare overlap, shortcut rates, class support, leakage, temporal integrity,
  reproducibility, and per-class metrics together. A higher accuracy or F1 is
  not by itself evidence that a synthetic dataset is better.
- Revised scenario labels remain generator-defined synthetic labels and must
  not be called fraud, financial-crime, or production-risk outcomes.

### Rule 107 - Anomaly Ranking and Explanations Are Research-Only

- Anomaly models must fit only on approved candidate features from the
  training partition. Synthetic labels, scenario metadata, generator rules,
  identifiers, split assignment, future fields, post-event outcomes, and human
  decisions are forbidden model inputs.
- A higher anomaly score must have documented semantics, direction, scaling,
  and comparability limits. Training-only percentile thresholds are research
  thresholds, never payment, blocking, rejection, fraud, or financial-risk
  decisions.
- Synthetic scenario labels may be used only after scoring for offline ranking,
  subgroup, coverage, and overlap analysis. Metrics must be named
  synthetic-only and must not be presented as real-world accuracy or fraud
  performance.
- Research explanations must be deterministic and grounded in actual available
  feature values. They must identify the referenced features, distinguish
  signal from interpretation, warn about limited history, and reject forbidden
  fraud language, scenario labels, generator rules, and future metadata.
- If the environment cannot support a complex anomaly dependency cleanly, use a
  documented transparent statistical method instead of silently adding
  infrastructure or claiming a production model. Do not export or serve a
  production anomaly model in this phase.

### Rule 108 - Backend anomaly integration is read-only and contract-gated

- Backend research scoring may load only validated, versioned artifacts; it
  must not retrain, regenerate synthetic data, or write MongoDB/Cassandra at
  startup or request time.
- Current MongoDB state remains authoritative and Cassandra remains historical
  event storage. Historical event records must not reconstruct balances or
  replace the approved current/history feature source.
- A live feature must be computed from approved current or strictly prior
  records. Missing channel/category/history context must produce an explicit
  unavailable result, never a guessed default or synthetic-data fallback.
- Research score routes require authentication and object-level owner
  authorization. They must not call payment execution, change financial state,
  publish events, block/reject/reverse/delay payments, or notify users.
- API metadata must identify dataset, generator, feature, model, score
  semantics, and threshold source/version. Scores are not probabilities or
  human/investigator decisions.

### Rule 109 - Operational channel data must be explicit and persisted

- New payment commands must carry an explicit value from the approved
  simulated channel vocabulary: `QR_SIMULATED`, `CARD_SIMULATED`,
  `WALLET_SIMULATED`, or `BANK_SIMULATED`.
- The channel belongs to the operational transaction payload and snapshot; it
  must not be confused with event provenance or inferred from an HTTP route.
- The channel is part of the idempotency fingerprint. Same-key replays return
  the original transaction, while same-key requests with a different channel
  conflict.
- Legacy transactions without a channel remain unmodified. Research features
  that require the missing value must return controlled unavailability rather
  than inventing or bulk-migrating data.
- Live channel novelty uses only persisted completed operational transactions
  strictly before the target, ordered by timestamp and transaction ID. It
  never mixes synthetic training rows into operational history.
