# Product Requirements Document (PRD)

## Project
**SpendShield — Intelligent Payment, Financial Awareness & Digital Forensics Platform**

## Document Status
**Version:** 1.0  
**Purpose:** Master product requirements for development  
**Audience:** Developers, ML engineers, database engineers, UI/UX designers, testers, and project evaluators

---

# 1. Product Objective

SpendShield shall provide a controlled fictional financial ecosystem where users can perform simulated payments, understand their financial behaviour, receive machine-learning-based intelligence, and investigate suspicious financial activity through an integrated computer-forensics workflow.

The product must function as **one coherent application**, not as separate demonstrations of payment processing, machine learning, databases, and forensics.

---

# 2. Problem Statement

Users can see that money moved, but understanding the complete context of a suspicious financial event can require information from multiple systems.

SpendShield must connect:

```text
Financial Transaction
        ↓
Behavioural Analysis
        ↓
Suspicious Activity
        ↓
Digital Evidence
        ↓
Forensic Correlation
        ↓
Investigation
        ↓
Evidence-Based Finding
```

---

# 3. Product Goals

## Primary Goals

1. Provide a realistic fictional payment experience.
2. Maintain accurate transaction and balance state.
3. Detect recurring financial patterns.
4. Categorize and analyse transactions.
5. Detect unusual spending behaviour.
6. Forecast future spending where sufficient data exists.
7. Identify suspicious financial activity.
8. Convert suspicious activity into a forensic investigation.
9. Preserve evidence integrity using hashing and chain-of-custody records.
10. Correlate financial events with authorized digital artifacts.
11. Build investigation timelines.
12. Identify supporting and contradictory evidence.
13. Generate explainable findings.
14. Produce investigation reports.
15. Demonstrate MongoDB and Cassandra through justified workloads.
16. Demonstrate an ML lifecycle developed in Jupyter and served through Python.

---

# 4. Non-Goals

SpendShield shall NOT:

- process real money,
- connect to real bank accounts,
- perform real UPI settlement,
- access devices without authorization,
- automatically accuse a person of a crime,
- treat an anomaly as proof of fraud,
- expose private forensic information without authorization,
- claim that a simulated dataset represents real financial activity.

---

# 5. User Roles

## 5.1 Financial User

Can:

- register/login,
- view account,
- view balance,
- make simulated payments,
- scan supported QR codes,
- view receipts,
- view transaction history,
- manage fictional subscriptions,
- review spending intelligence,
- receive alerts.

## 5.2 Investigator

Can:

- access authorized investigation cases,
- inspect suspicious transactions,
- review evidence,
- verify evidence hashes,
- inspect event timelines,
- inspect relationships,
- review ML findings,
- add notes,
- mark findings,
- generate reports.

## 5.3 Merchant

Can:

- maintain fictional merchant information,
- provide supported QR identifiers,
- view simulated transactions associated with the merchant.

## 5.4 Administrator

Can:

- manage users,
- manage merchants,
- manage system configuration,
- review audit logs,
- manage controlled/demo datasets,
- manage investigation permissions.

Role permissions must be enforced by the backend.

---

# 6. Functional Requirements

## FR-001 Authentication

The system shall support secure registration and authentication.

Requirements:

- unique user identity,
- secure password storage,
- session/token management,
- logout,
- role-based authorization,
- account status,
- validation of authentication requests.

---

## FR-002 Account & Wallet

Each financial user shall have a fictional account/wallet.

The system shall display:

- current balance,
- account identifier,
- account status,
- recent transactions,
- upcoming commitments.

The backend shall be the source of truth for balance calculations.

---

## FR-003 Simulated Payment

Users shall be able to make fictional payments.

Required flow:

```text
Select/Scan Merchant
        ↓
Enter Amount
        ↓
Validate
        ↓
Confirm
        ↓
Payment Authentication/PIN
        ↓
Process
        ↓
Persist Transaction
        ↓
Update Balance
        ↓
Receipt
```

The system shall reject:

- invalid amounts,
- insufficient balance,
- inactive accounts,
- invalid merchants,
- malformed requests,
- unauthorized payment attempts.

---

## FR-004 QR Processing

The application shall support QR-based merchant identification for the controlled fictional ecosystem.

The QR payload should resolve to a known merchant or controlled payment identifier.

The backend shall validate the decoded payload before payment processing.

Unsupported or invalid QR payloads must produce a clear error.

---

## FR-005 Transaction Management

Each transaction shall maintain a unique transaction identifier.

Recommended fields:

```text
transaction_id
user_id
account_id
merchant_id
amount
currency
transaction_type
category
status
timestamp
payment_method
device_id
session_id
risk_score
created_at
updated_at
```

Transaction state changes must be validated and auditable.

---

## FR-006 Receipts

A successful transaction shall produce a receipt containing:

- transaction ID,
- merchant,
- amount,
- timestamp,
- payment status,
- balance before,
- balance after.

---

## FR-007 Transaction History

Users shall be able to:

- search transactions,
- filter by category,
- filter by date,
- filter by merchant,
- sort by time/amount,
- open transaction details.

---

## FR-008 Subscription Management

The system shall support fictional subscriptions.

A subscription shall include:

```text
subscription_id
user_id
service_name
amount
billing_frequency
start_date
next_payment_date
auto_renewal
status
```

The system shall generate future payment events according to the configured schedule.

---

## FR-009 Recurring Payment Detection

The analytics engine shall analyse transaction history and identify recurring patterns.

The result should include:

```text
merchant
amount
frequency
estimated_next_date
confidence
supporting_transactions
```

The system must allow insufficient-data states rather than forcing a prediction.

---

## FR-010 Transaction Categorization

Transactions shall be assigned a category through a defined classification strategy.

The implementation must document:

- training data,
- preprocessing,
- features,
- algorithm,
- evaluation metrics,
- limitations.

Rules may be used as a baseline, but a machine-learning approach should be evaluated where sufficient data exists.

---

## FR-011 Spending Analytics

The dashboard shall provide financial summaries such as:

- total spending,
- category distribution,
- daily/weekly/monthly trends,
- recurring commitments,
- largest transactions,
- spending changes.

All calculations must be traceable to stored transaction data.

---

## FR-012 Unusual Activity Detection

The system shall generate an anomaly/risk score using an evaluated analytical model.

Potential factors:

- amount deviation,
- frequency deviation,
- merchant novelty,
- unusual time,
- historical user behaviour,
- transaction velocity,
- device/session changes.

Example output:

```text
Risk Score: 0.91
Status: Requires Review
```

The score is a decision-support signal, not a legal conclusion.

---

## FR-013 Suspicious Activity Case Creation

A suspicious transaction shall be capable of becoming a forensic case.

The case should contain:

```text
case_id
trigger_event
risk_score
case_status
created_at
assigned_investigator
priority
```

---

## FR-014 Forensic Evidence Ingestion

Investigators shall be able to ingest authorized evidence files or controlled forensic datasets.

The system shall record:

- evidence ID,
- case ID,
- source,
- file name/type,
- size,
- ingestion time,
- hash,
- processing state,
- provenance information.

Demo/synthetic evidence must be clearly labelled.

---

## FR-015 Evidence Hashing

The system shall calculate SHA-256 hashes for ingested evidence.

Required behaviour:

```text
Evidence
   ↓
SHA-256
   ↓
Store Hash
   ↓
Later Verification
   ↓
MATCH / MISMATCH
```

A mismatch must be clearly surfaced to the investigator.

---

## FR-016 Chain of Custody

The system shall record meaningful evidence-handling events.

Possible events:

- evidence acquired,
- evidence uploaded,
- evidence processed,
- evidence viewed,
- evidence exported,
- evidence verified.

Each event should include:

```text
actor
action
timestamp
evidence_id
case_id
metadata
```

The implementation must not pretend that a software audit trail alone provides legal admissibility.

---

## FR-017 Artifact Extraction

The forensic engine may extract supported artifacts from authorized evidence.

Potential artifact types:

- authentication records,
- session records,
- device records,
- application logs,
- network records,
- file metadata,
- transaction-related audit records.

Unsupported formats must fail gracefully.

---

## FR-018 Event Normalization

Different sources shall be converted into a common event representation.

Minimum conceptual schema:

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

The normalized representation enables cross-source correlation.

---

## FR-019 Forensic Timeline

The system shall reconstruct chronological events around an investigation.

Investigators shall be able to:

- sort by time,
- filter by event type,
- inspect event details,
- open linked evidence,
- identify gaps,
- identify conflicting timestamps.

---

## FR-020 Event Correlation

The correlation engine shall connect related entities/events using available identifiers and contextual relationships.

Potential relationships:

```text
User → Account
User → Session
Session → Device
Session → Transaction
Transaction → Audit Event
Event → Evidence
Evidence → Artifact
```

Correlation must be explainable.

---

## FR-021 Trace Back

For a selected event, investigators shall be able to inspect relevant preceding events.

Example:

```text
Suspicious Transaction
        ↑
Payment Session
        ↑
Login
        ↑
Device Activity
```

---

## FR-022 Trace Forward

For a selected event, investigators shall be able to inspect relevant subsequent events.

Example:

```text
Suspicious Transaction
        ↓
Session End
        ↓
Network Event
        ↓
Account Activity
```

---

## FR-023 Evidence Consistency Analysis

Where multiple artifacts contain related timestamps or attributes, the system shall identify potential inconsistencies.

Example:

```text
Source A → 10:42
Source B → 10:45
Source C → 10:40

Result → Temporal inconsistency requiring review
```

The system shall report the conflict rather than silently resolve it.

---

## FR-024 Investigation Graph

The investigator shall have a relationship-oriented view of the case.

Nodes may include:

- user,
- account,
- transaction,
- device,
- session,
- event,
- evidence,
- artifact,
- merchant.

Edges must represent meaningful relationships.

---

## FR-025 ML Explainability

Every ML-generated finding shall expose enough information for an investigator to understand why the system produced it.

Possible explanation:

```text
Risk Score: 91%

Contributing signals:
+ unusually large amount
+ unfamiliar merchant
+ unusual transaction time
+ new device/session
+ high transaction velocity
```

The actual explanation mechanism must match the chosen model.

---

## FR-026 Investigator Review

Investigators shall be able to:

- accept/support a finding,
- mark it inconclusive,
- dismiss it,
- add notes,
- attach supporting evidence,
- record reasoning.

Human review remains part of the workflow.

---

## FR-027 Reports

The system shall generate a case report containing:

- case metadata,
- incident summary,
- transaction information,
- timeline,
- evidence inventory,
- hash verification,
- correlations,
- ML findings,
- contradictions,
- investigator notes,
- final status.

---

## FR-028 Audit Logging

Security-sensitive operations shall generate audit records.

Examples:

- login,
- failed login,
- payment,
- evidence ingestion,
- evidence verification,
- case creation,
- finding modification,
- report generation,
- administrative action.

---

# 7. Machine Learning Requirements

## ML-001 Data Pipeline

The project shall demonstrate:

```text
Data
 ↓
Cleaning
 ↓
EDA
 ↓
Feature Engineering
 ↓
Train/Validation/Test
 ↓
Model Training
 ↓
Evaluation
 ↓
Explainability
 ↓
Export
 ↓
Production Inference
```

## ML-002 Baselines

A simple baseline must be established before using a more complex model.

## ML-003 Evaluation

Evaluation must use metrics appropriate to the task.

Examples:

### Classification
- precision,
- recall,
- F1-score,
- confusion matrix,
- ROC-AUC where appropriate.

### Anomaly Detection
- precision/recall on labelled evaluation data where available,
- false-positive rate,
- threshold analysis,
- analyst review quality.

### Forecasting
- MAE,
- RMSE,
- MAPE where appropriate.

## ML-004 No Fake Accuracy

The project must never claim an arbitrary accuracy percentage.

Performance must come from an actual evaluation experiment.

## ML-005 Data Leakage Prevention

Features must not use information that would only become available after the prediction target event.

## ML-006 Model Versioning

Each production model should have:

```text
model_name
version
training_dataset
features
algorithm
metrics
training_date
artifact_location
```

---

# 8. Database Requirements

## MongoDB Requirements

MongoDB must support flexible application and investigation documents.

Required design documentation:

- collection purpose,
- schema,
- indexes,
- validation rules,
- relationships,
- retention considerations.

## Cassandra Requirements

Cassandra must support high-volume chronological event workloads.

Required design documentation:

- query-first access patterns,
- partition key,
- clustering columns,
- expected cardinality,
- time-based considerations,
- retention strategy.

The project must explain why each database is used.

---

# 9. API Requirements

The backend should expose logically grouped API routes.

Conceptual groups:

```text
/auth
/users
/accounts
/merchants
/qr
/payments
/transactions
/subscriptions
/analytics
/ml
/alerts
/cases
/evidence
/artifacts
/timeline
/correlation
/findings
/reports
/audit
/admin
```

APIs must:

- validate input,
- authenticate requests,
- authorize roles,
- return consistent errors,
- avoid leaking sensitive information,
- log security-relevant actions.

---

# 10. Frontend Requirements

The UI shall provide separate experiences for:

### Financial User

- Home/Command Center
- Wallet
- QR Pay
- Transactions
- Subscriptions
- Spending Analytics
- Alerts

### Investigator

- Investigation Command Center
- Cases
- Case Overview
- Evidence
- Timeline
- Event Explorer
- Correlation Graph
- Trace Back
- Trace Forward
- ML Findings
- Evidence Integrity
- Notes
- Reports

### Administrator

- Users
- Merchants
- Audit Logs
- System/Data Management

The interface should prioritize clarity and investigation flow over decorative dashboards.

---

# 11. Non-Functional Requirements

## NFR-001 Security

Implement:

- password hashing,
- secure authentication,
- RBAC,
- input validation,
- secure file upload handling,
- rate limiting where appropriate,
- secret management,
- secure headers,
- CORS configuration,
- audit logging.

## NFR-002 Reliability

Failed payment operations must not leave inconsistent balance and transaction states.

## NFR-003 Integrity

Evidence hashes and chain-of-custody records must be tamper-evident within the application's security model.

## NFR-004 Explainability

ML findings must provide interpretable reasons appropriate to the model.

## NFR-005 Usability

Important information should be understandable without requiring technical knowledge.

## NFR-006 Maintainability

Backend, frontend, ML, database, and forensic components must be modular.

## NFR-007 Testability

Core business logic and critical security/forensic functions must have automated tests.

## NFR-008 Observability

Production-like deployments should provide structured logs and meaningful error reporting.

---

# 12. Data Requirements

The project may use:

1. synthetic financial transactions,
2. controlled forensic evidence,
3. public cybersecurity datasets where licensing and usage conditions permit,
4. generated event streams for demonstrating Cassandra scale.

Every dataset must be labelled by provenance.

The system must distinguish:

```text
REAL PUBLIC DATA
SYNTHETIC DATA
SIMULATED CASE DATA
USER-PROVIDED AUTHORIZED EVIDENCE
```

---

# 13. Forensic Data Requirements

A forensic event should preserve both normalized and source information where possible.

Conceptually:

```text
Normalized Event
       +
Source Reference
       +
Raw/Original Evidence Reference
```

The normalized representation is for analysis. The original evidence remains the authoritative source for verification.

---

# 14. Security & Privacy Requirements

The system must follow least privilege.

Users should only access data appropriate to their role and case permissions.

Evidence access must be auditable.

Sensitive values should not be unnecessarily exposed in logs.

Secrets must not be committed to source control.

Production credentials must be stored through environment/secret-management mechanisms.

---

# 15. Testing Requirements

Testing should cover:

### Unit Tests
- balance calculations,
- transaction validation,
- subscription scheduling,
- risk calculations,
- hash verification,
- normalization,
- correlation logic.

### Integration Tests
- API + database,
- payment workflow,
- case creation,
- evidence processing,
- ML inference.

### Security Tests
- authentication,
- authorization,
- malformed inputs,
- upload restrictions,
- access-control boundaries.

### ML Tests
- preprocessing consistency,
- model loading,
- inference output,
- threshold behaviour,
- evaluation reproducibility.

### End-to-End Test

The following scenario must work:

```text
User Login
 ↓
QR Payment
 ↓
Transaction Stored
 ↓
Analytics Updated
 ↓
Suspicious Activity Generated
 ↓
Investigation Created
 ↓
Evidence Ingested
 ↓
Hash Verified
 ↓
Events Normalized
 ↓
Timeline Built
 ↓
Correlation Generated
 ↓
ML Finding Explained
 ↓
Investigator Review
 ↓
Report Generated
```

---

# 16. Acceptance Criteria

The MVP is acceptable only when:

- a user can complete a controlled simulated payment,
- balance and transaction state remain consistent,
- transactions are persisted,
- subscriptions can be represented,
- analytics can be calculated,
- at least one evaluated ML capability works,
- suspicious activity can trigger an investigation,
- evidence can be ingested,
- SHA-256 integrity can be verified,
- forensic events can be normalized,
- a timeline can be generated,
- related events can be correlated,
- an investigator can review findings,
- a report can be generated,
- MongoDB and Cassandra have documented and working responsibilities,
- security controls are implemented,
- tests cover critical workflows.

---

# 17. Definition of Done

A feature is **Done** only when:

```text
Requirement defined
      ↓
Implementation completed
      ↓
Database/API integration completed
      ↓
Validation added
      ↓
Error states handled
      ↓
Tests added
      ↓
Security reviewed
      ↓
UI integrated
      ↓
Documentation updated
      ↓
Memory.md updated
      ↓
Feature manually verified
```

A feature is not considered complete merely because its UI exists.

---

# 18. Product Principle

SpendShield should always answer three questions:

> **What happened?**

> **Is it unusual?**

> **What evidence can help us understand it?**

And for every forensic conclusion:

> **What supports this finding, and what could contradict it?**

---

# 19. Final Product Requirement

The final application must feel like a single product.

The evaluator should be able to follow one meaningful story:

```text
A financial event occurs.
        ↓
The platform understands it.
        ↓
Machine learning identifies unusual behaviour.
        ↓
The event becomes an investigation.
        ↓
Digital evidence is examined.
        ↓
Evidence is correlated.
        ↓
The timeline is reconstructed.
        ↓
The system explains its findings.
        ↓
A human investigator makes the final decision.
```

That end-to-end connection is the core requirement of SpendShield.
