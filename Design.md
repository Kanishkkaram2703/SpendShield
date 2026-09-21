# Design

## Project
**SpendShield — Intelligent Payment, Financial Awareness & Digital Forensics Platform**

## 1. Design Objective

SpendShield must feel like one professional product connecting financial activity, machine intelligence, and digital-forensic investigation.

The interface should guide the user from:

```text
Financial Activity
      ↓
Understanding
      ↓
Detection
      ↓
Investigation
      ↓
Evidence
      ↓
Decision
```

The design must prioritize clarity, trust, traceability, and meaningful interaction over decorative UI.

---

# 2. Design Philosophy

## 2.1 Two Primary Experiences

SpendShield has two major user experiences:

### Financial Experience

Designed for ordinary users.

Focus:

- money,
- payments,
- subscriptions,
- spending,
- predictions,
- alerts.

### Investigation Experience

Designed for investigators.

Focus:

- cases,
- evidence,
- timelines,
- relationships,
- anomalies,
- contradictions,
- findings.

These experiences may share the same application shell but must have different information priorities.

---

# 3. Visual Direction

The product should feel:

```text
Professional
Trustworthy
Technical
Modern
Calm
Evidence-oriented
```

Avoid:

- excessive gradients,
- unnecessary glassmorphism,
- decorative animations,
- overly dense dashboards,
- fake cybersecurity “hacker” aesthetics,
- excessive neon colours,
- visual elements that obscure evidence.

The UI should communicate seriousness because financial and forensic information requires trust.

---

# 4. Design System

## Typography

Use a clean modern sans-serif.

Recommended hierarchy:

```text
Display
H1
H2
H3
Body
Secondary
Caption
Monospace / technical
```

Technical values such as:

- transaction IDs,
- evidence IDs,
- hashes,
- event IDs,
- timestamps

may use a monospace font.

---

# 5. Colour Semantics

Colours must have consistent meanings.

```text
Normal       → neutral/success treatment
Information  → informational treatment
Warning      → caution treatment
High Risk    → strong warning treatment
Critical     → critical treatment
Verified     → integrity/success treatment
Conflict     → contradiction treatment
```

Do not use colour alone to communicate meaning.

Icons, labels, and text should accompany important statuses.

---

# 6. Application Shell

The main authenticated application should use:

```text
┌─────────────────────────────────────────────┐
│ Top Bar                                     │
├──────────────┬──────────────────────────────┤
│ Sidebar      │ Main Content                  │
│              │                              │
│ Navigation   │ Page                         │
│              │                              │
│              │                              │
└──────────────┴──────────────────────────────┘
```

## Top Bar

Possible elements:

- application logo,
- page title/breadcrumb,
- notifications,
- profile,
- role indicator,
- environment indicator where appropriate.

## Sidebar

Financial role:

```text
Home
Wallet
Pay
Transactions
Subscriptions
Analytics
Alerts
Profile
```

Investigator role:

```text
Command Center
Cases
Evidence
Timeline
Events
Correlation
Graph
ML Findings
Integrity
Reports
Notes
```

Admin role:

```text
Users
Merchants
Cases
Audit Logs
System/Data
```

---

# 7. Landing Page

The public landing page should explain the product in a few seconds.

## Hero

Suggested message:

> **Understand the transaction. Investigate the evidence.**

Supporting text:

> SpendShield combines financial intelligence, machine learning, and digital forensics inside a controlled payment ecosystem.

Primary actions:

```text
Explore Demo
Sign In
```

Avoid making the landing page look like a generic banking advertisement.

---

# 8. Authentication Screens

## Login

Elements:

- email/username,
- password,
- show/hide password,
- remember/session option where appropriate,
- login button,
- error message.

## Registration

Elements:

- name,
- email,
- password,
- confirmation,
- required validation,
- role selection only where permitted.

## Error States

Examples:

```text
Invalid credentials
Account disabled
Session expired
Network unavailable
Server unavailable
```

Errors should be specific enough to help the user but should not reveal security-sensitive information.

---

# 9. Financial Dashboard

The financial dashboard should answer immediately:

```text
How much do I have?
How much did I spend?
What is coming next?
Is anything unusual?
```

## Recommended Layout

```text
┌─────────────────────────────────────────────┐
│ Current Balance                             │
│ ₹24,500                                     │
└─────────────────────────────────────────────┘

┌──────────────┬──────────────┬───────────────┐
│ Spent        │ Upcoming     │ Spendable     │
│ ₹8,420       │ ₹3,366       │ ₹18,000       │
└──────────────┴──────────────┴───────────────┘

┌──────────────────────┬──────────────────────┐
│ Spending Trend       │ Category Breakdown   │
│                      │                      │
└──────────────────────┴──────────────────────┘

┌─────────────────────────────────────────────┐
│ Recent Transactions                         │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Intelligence / Alerts                      │
└─────────────────────────────────────────────┘
```

The dashboard must not overwhelm users with every metric available.

---

# 10. Wallet Page

Display:

- available balance,
- recent transactions,
- account information,
- upcoming commitments,
- balance history.

Actions:

```text
Pay
Scan QR
View Transactions
View Subscriptions
```

---

# 11. QR Payment Experience

The QR flow should feel like a focused transaction process.

## Step 1 — Scan

```text
┌───────────────────────────┐
│                           │
│       QR Scanner          │
│                           │
│    [ Scan Area ]          │
│                           │
└───────────────────────────┘
```

## Step 2 — Merchant Confirmation

Display:

```text
Merchant
Category
Verified fictional merchant
```

## Step 3 — Amount

Large amount input.

## Step 4 — Confirmation

Show:

```text
Merchant
Amount
Payment Method
Balance Before
Balance After
```

## Step 5 — Authentication

Payment PIN/authentication.

## Step 6 — Success

Show:

```text
Payment Successful
₹500
Transaction ID
Balance After
View Receipt
```

---

# 12. Transaction History

Use a searchable table/list.

Columns:

```text
Date
Merchant
Category
Amount
Status
Risk
```

Filters:

```text
Date
Merchant
Category
Amount
Status
Risk
```

Selecting a transaction opens a detailed drawer/page.

---

# 13. Transaction Detail

Display:

```text
Transaction ID
Status
Amount
Merchant
Timestamp
Category
Payment Method
Balance Before
Balance After
Risk Score
```

If suspicious:

```text
Requires Review
```

with:

```text
Why was this flagged?
Investigate
```

This is the bridge between the financial and forensic experiences.

---

# 14. Subscription Page

Use subscription cards.

Example:

```text
┌──────────────────────────────┐
│ StreamBox                    │
│ ₹299 / month                 │
│                              │
│ Next payment: 4 days         │
│ Auto-renewal: ON             │
│                              │
│ [View] [Review]              │
└──────────────────────────────┘
```

The page should distinguish:

```text
Active
Upcoming
Paused
Cancelled
```

---

# 15. Analytics Page

The analytics page should answer:

```text
Where is money going?
How is spending changing?
What repeats?
What might happen next?
```

Possible sections:

- spending trend,
- category distribution,
- merchant concentration,
- recurring payments,
- monthly comparison,
- forecast,
- upcoming commitments.

Every chart must have:

- title,
- time period,
- units,
- useful empty state.

Avoid charts without a clear analytical question.

---

# 16. Alerts Page

Alerts should be grouped by significance.

Example:

```text
Unusual Payment
₹18,500
Risk: High
[Review]
```

Other alerts:

```text
Upcoming Subscription
Recurring Pattern Detected
Forecast Change
New Device/Session
Evidence Integrity Conflict
```

The alert must explain why it exists.

---

# 17. Investigator Command Center

This is the primary forensic landing page.

It should answer:

```text
What requires attention?
Which cases are active?
What evidence needs review?
Are there unresolved conflicts?
```

Suggested layout:

```text
┌──────────────────────────────────────────────┐
│ Investigation Overview                       │
├─────────────┬──────────────┬─────────────────┤
│ Open Cases  │ High Risk    │ Evidence Issues │
│ 12          │ 3            │ 2               │
└─────────────┴──────────────┴─────────────────┘

┌──────────────────────────┬───────────────────┐
│ Priority Cases           │ Recent Findings   │
└──────────────────────────┴───────────────────┘

┌──────────────────────────────────────────────┐
│ Recent Investigation Activity                │
└──────────────────────────────────────────────┘
```

---

# 18. Case List

Columns:

```text
Case ID
Title
Priority
Risk
Status
Created
Assigned Investigator
```

Filters:

```text
Status
Priority
Risk
Date
Investigator
```

Case statuses:

```text
Open
Under Review
Supported
Inconclusive
Dismissed
Closed
```

---

# 19. Case Overview

The case page is the main investigation workspace.

Recommended structure:

```text
Case Header
    ↓
Incident Summary
    ↓
Trigger Event
    ↓
Investigation Navigation
    ↓
Evidence / Timeline / Graph / Findings
```

## Header

Display:

```text
Case ID
Case Status
Priority
Risk
Assigned Investigator
Created Date
```

Actions:

```text
Add Note
Verify Evidence
Generate Report
Change Status
```

---

# 20. Investigation Workspace

Use a tabbed or split-pane experience.

Recommended tabs:

```text
Overview
Timeline
Events
Evidence
Graph
Trace
Consistency
ML Findings
Notes
Report
```

The investigator should be able to move between these views without losing case context.

---

# 21. Investigation Timeline

The timeline is a major forensic interaction.

Concept:

```text
10:30 PM ── Login
             │
10:34 PM ── New Device
             │
10:35 PM ── Payment Session
             │
10:36 PM ── ₹18,500 Transaction
             │
10:37 PM ── Session End
```

Each event should be clickable.

Selecting an event opens details:

```text
Event ID
Timestamp
Event Type
Source
User
Device
Session
Related Transaction
Evidence
```

---

# 22. Event Explorer

The event explorer should support:

- search,
- event-type filtering,
- source filtering,
- time range,
- user,
- device,
- session,
- case.

Example event types:

```text
AUTH
SESSION
DEVICE
TRANSACTION
NETWORK
AUDIT
FILE
```

The raw/source reference should remain available.

---

# 23. Evidence Page

Evidence should be treated as a first-class object.

Display:

```text
Evidence ID
File Name
Source
Size
Type
Case
Ingested At
SHA-256
Integrity Status
Processing Status
```

Actions:

```text
Verify
View Metadata
View Artifacts
View Custody
```

---

# 24. Evidence Integrity View

This page should make verification visually obvious.

Example:

```text
Evidence EV-00042

SHA-256
a91f...83c2

Stored Hash
a91f...83c2

Current Hash
a91f...83c2

✓ MATCH
Evidence integrity verified
```

For mismatch:

```text
Stored Hash
a91f...83c2

Current Hash
b72d...19aa

✕ MISMATCH
Investigator review required
```

Never hide integrity failures behind generic error messages.

---

# 25. Chain-of-Custody View

Use a chronological activity list.

```text
10:02
Evidence acquired

10:05
Evidence hashed

10:07
Evidence ingested

10:15
Artifact processing started

10:20
Investigator viewed evidence
```

Each event displays:

```text
Actor
Action
Timestamp
Evidence ID
Case ID
```

---

# 26. Correlation View

Display connected entities.

Example:

```text
User
 │
 ├── Account
 │
 └── Session
       │
       ├── Device
       │
       └── Transaction
              │
              └── Evidence
```

Each relationship should be inspectable.

Example:

```text
Transaction T1
↓
Session S9

Reason:
session_id matched
```

---

# 27. Investigation Graph

The graph should support:

- zoom,
- pan,
- node selection,
- relationship selection,
- filtering,
- focus on selected node,
- expand neighbours.

Node types should be visually distinguishable through shape, label, and accessible metadata.

Do not use a graph merely for visual effect.

---

# 28. Trace Back

Selecting a suspicious event should reveal relevant preceding activity.

Example:

```text
               Login
                 ↑
            Device Event
                 ↑
             Session
                 ↑
         Payment Initiated
                 ↑
         Suspicious Event
```

The interface should show why an event was included.

---

# 29. Trace Forward

Example:

```text
Suspicious Event
       ↓
Transaction
       ↓
Session End
       ↓
Network Activity
       ↓
Subsequent Account Event
```

The investigator can change the time window where supported.

---

# 30. Consistency / Contradiction View

This should clearly separate:

```text
Consistent Evidence
Potential Conflict
Unknown / Missing
```

Example:

```text
TEMPORAL CONFLICT

Source A
10:42:11

Source B
10:45:03

Source C
10:40:57

Status:
Requires investigator review
```

The system must never silently select one source as truth.

---

# 31. ML Findings View

Every ML finding should display:

```text
Finding
Risk Score
Model
Model Version
Prediction Time
Confidence/Score where appropriate
```

Then:

```text
Why was this flagged?

+ Amount significantly above historical pattern
+ New merchant
+ Unusual transaction time
+ New device/session
```

The exact explanation must be generated from the actual model/features.

---

# 32. Investigator Review Panel

The investigator should have a clear decision area:

```text
System Finding:
Potentially unusual transaction

Evidence:
[Evidence 1]
[Evidence 2]
[Event 3]

System Explanation:
...

Investigator Decision:

○ Supported
○ Inconclusive
○ Dismissed

Notes:
[________________________]

[Save Finding]
```

The UI must avoid coercive language.

---

# 33. Notes

Notes should support:

- author,
- timestamp,
- case association,
- finding association,
- edit history where required.

Notes should not overwrite evidence.

---

# 34. Report Preview

The report preview should mirror the final report structure:

```text
Case Information
Incident Summary
Trigger Transaction
Timeline
Evidence
Integrity
Correlations
ML Analysis
Contradictions
Investigator Notes
Final Decision
```

Use clear section numbering and timestamps.

---

# 35. Loading States

Every asynchronous screen needs a meaningful loading state.

Examples:

```text
Loading transactions...
Processing evidence...
Building timeline...
Running analysis...
Generating report...
```

Avoid blank screens or indefinite spinners.

---

# 36. Empty States

Examples:

### No Transactions

> No transactions yet. Complete a simulated payment to start building your financial history.

### No Cases

> No investigations currently require attention.

### No Evidence

> No evidence has been associated with this case.

### Insufficient ML Data

> There is not enough historical activity to produce a reliable prediction.

Empty states should guide the user toward the next meaningful action.

---

# 37. Error States

Errors must be:

- understandable,
- actionable,
- non-technical where possible,
- security-conscious.

Example:

Instead of:

```text
500 Internal Server Error
```

prefer:

> We couldn't complete the payment. Your balance was not changed. Please try again.

Technical details should go to logs, not users.

---

# 38. Confirmation States

Important destructive/sensitive actions require confirmation.

Examples:

- changing case status,
- deleting a non-evidence object,
- cancelling a fictional subscription,
- administrative changes.

Evidence deletion should be heavily restricted and auditable.

---

# 39. Responsive Design

Desktop is the primary investigator environment.

Mobile should prioritize the financial-user experience.

Investigation views such as:

- graph,
- timeline,
- evidence comparison

must remain usable on smaller screens, but complex forensic analysis may use an optimized desktop layout.

---

# 40. Accessibility

The UI should support:

- keyboard navigation,
- readable contrast,
- semantic HTML,
- labels for controls,
- accessible form errors,
- focus states,
- screen-reader-friendly status indicators,
- non-colour status communication.

---

# 41. Animation

Animations should communicate state or navigation.

Good:

```text
Payment → Success
Case → Open
Graph → Expand
```

Avoid:

- continuous decorative motion,
- excessive page transitions,
- animations that slow investigation,
- distracting effects around critical evidence.

---

# 42. Notifications

Notifications should be grouped into:

```text
Financial
Security
Investigation
System
```

Examples:

```text
Financial:
Upcoming payment in 2 days.

Security:
New device/session detected.

Investigation:
Evidence integrity mismatch detected.

System:
Report generation completed.
```

---

# 43. Trust & Transparency

Whenever the application makes an analytical claim, the UI should allow the user to understand its origin.

Examples:

```text
Risk Score
→ Why?

Forecast
→ Based on what period?

Recurring Payment
→ Which transactions support this?

Forensic Relationship
→ Why are these events linked?

Evidence Status
→ Which hash was verified?
```

This principle is especially important for ML and forensic functionality.

---

# 44. Design Rule for AI/ML

Never display:

```text
AI says this is fraud.
```

Prefer:

```text
High-risk activity detected

Reason:
The transaction differs substantially from observed behaviour.

Evidence:
3 supporting signals

Investigator review required.
```

The UI must preserve the distinction between prediction and conclusion.

---

# 45. Design Rule for Forensics

Never visually imply certainty when the evidence is uncertain.

Use:

```text
Observed
Supported
Potential
Conflicting
Unknown
Requires Review
```

rather than absolute statements unsupported by evidence.

---

# 46. Design Rule for Financial Information

Money values must always show:

- currency,
- appropriate precision,
- transaction direction,
- status.

Example:

```text
− ₹1,250
Payment
Completed
```

rather than:

```text
1250
```

---

# 47. Core User Journey

## Normal User

```text
Login
 ↓
Dashboard
 ↓
Scan QR
 ↓
Merchant
 ↓
Amount
 ↓
Confirm
 ↓
PIN
 ↓
Success
 ↓
Receipt
 ↓
Analytics
```

## Suspicious Activity

```text
Transaction
 ↓
Risk Alert
 ↓
Review
 ↓
Why Flagged?
 ↓
Investigate
```

## Investigator

```text
Case
 ↓
Overview
 ↓
Timeline
 ↓
Evidence
 ↓
Integrity
 ↓
Correlation
 ↓
Graph
 ↓
Trace
 ↓
Consistency
 ↓
ML Findings
 ↓
Investigator Decision
 ↓
Report
```

---

# 48. UI Component Inventory

Reusable components should include:

```text
Button
Input
Select
Modal
Drawer
Toast
Badge
StatusBadge
MetricCard
TransactionCard
TransactionTable
SubscriptionCard
AlertCard
CaseCard
EvidenceCard
EvidenceTable
TimelineEvent
Timeline
EventDetailPanel
HashVerificationPanel
CustodyTimeline
RelationshipCard
GraphCanvas
FindingCard
RiskScore
ExplanationPanel
NotesPanel
ReportPreview
DataTable
FilterBar
SearchBar
Pagination
EmptyState
ErrorState
LoadingState
ConfirmationDialog
```

---

# 49. Component Design Principle

Components should be reusable but not artificially generic.

Prefer:

```text
EvidenceCard
```

over a massive component with dozens of unrelated configuration flags.

Feature-specific components should remain readable and maintainable.

---

# 50. Information Hierarchy

Every screen should follow:

```text
1. What is this page?
2. What requires attention?
3. What does the data say?
4. What can I do?
5. What details support it?
```

Important actions should be visually prominent.

Technical metadata should be available without dominating the interface.

---

# 51. Design Acceptance Criteria

The design is successful when:

- a new user understands the financial dashboard quickly,
- payment flow requires minimal unnecessary steps,
- suspicious transactions clearly explain their status,
- an investigator can reach a case from an alert,
- an investigator can move from transaction → event → evidence,
- evidence integrity is immediately understandable,
- timeline events are interactive,
- graph relationships are explainable,
- ML findings expose reasons,
- contradictions are visible,
- investigator conclusions remain separate from automated predictions,
- loading/error/empty states are implemented,
- desktop investigation workflows remain usable,
- accessibility is considered throughout.

---

# 52. Final Design Principle

> **The interface should never make the investigator hunt for the evidence behind a conclusion.**

Every important claim should have a visible path back to:

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

SpendShield's visual design should therefore communicate one central idea:

> **Don't just show the result. Show the path that led to it.**

---

# 53. Current Implementation Status - 2026-09-11

No frontend application has been created yet. The design remains the planned
experience for the future frontend. The backend currently exposes the first
account endpoints and keeps balance/ownership authoritative on the server;
frontend balance calculation, dashboard screens, payment screens, and
investigator workflows remain unimplemented.

Account status is currently an administrator-controlled backend operation. The
future wallet UI may display the status and version returned by the API, but it
must not calculate or mutate authoritative account state locally.

## Historical Event Delivery Boundary - 2026-09-11

The backend keeps the canonical event fact immutable and stores optional
Cassandra delivery metadata with the MongoDB audit record. A delivery service
replays the exact stored event by `event_id`, applies bounded retry backoff,
and records publication success/failure. This is an explicit modular-monolith
service pass, not a frontend concern and not a broker-backed workflow.

The UI must not display a Cassandra delivery failure as a failed financial
operation. A financial operation is decided by authoritative MongoDB state;
historical delivery is a separate operational status. Account events remain
Mongo-only until an appropriate existing Cassandra query model is selected.

## Transaction Persistence Foundation - 2026-09-11

The payment persistence design is implemented behind a closed application
service/repository boundary. The client does not provide a balance, status, or
owner authority. The repository verifies the owner against the MongoDB account
document, reserves a unique `(user_id, idempotency_key)` request, and applies
the debit with an account-version compare-and-set.

The transaction document remains current operational state in MongoDB. Its
stored lifecycle is `INITIATED` during reservation and becomes
`AUTHORIZED → PROCESSING → COMPLETED` after the account update. Rejected
attempts use `INITIATED → REJECTED`. The stored request fingerprint makes same
key/same request replay deterministic and conflicting reuse a conflict.

The event boundary is deliberately separate:

```text
MongoDB account + transaction state
    ↓
MongoDB audit record and pending publication metadata
    ↓
explicit EventDeliveryService retry pass
    ↓
Cassandra transaction_events_by_account_day
```

The configured development deployment uses the validated `rs0` MongoDB
profile, so account state, transaction state, and MongoDB publication metadata
commit as one multi-document transaction. Cassandra remains outside that
transaction; if historical delivery fails after commit, the same event remains
pending and retryable. The standalone deployment remains an explicit fallback
with optimistic compare-and-set recovery rather than true multi-document
atomicity. The API stays closed until the separate public API contract is
approved.

## Replica-Set Transaction Mode - 2026-09-11

The repository selects its persistence mode from the connected MongoDB
topology. Replica-set mode uses a client session and MongoDB transaction for
the complete current-state operation:

```text
account validation
    ↓
transaction document insert
    ↓
account version/balance update
    ↓
audit record with pending Cassandra target
    ↓
commit
```

The publication record is in MongoDB's transaction, but Cassandra is not. A
Cassandra outage after commit changes only delivery metadata and is recovered
by replaying the same event ID. The standalone mode remains the explicit
development fallback when the connected server does not advertise a replica
set.

## Payment API Boundary - 2026-09-11

The API boundary now follows:

```text
Bearer authentication
    ↓
server-side account ownership check
    ↓
validated PaymentCreateRequest
    ↓
PaymentService
    ↓
MongoPaymentRepository transaction
    ↓
best-effort EventDeliveryService pass
    ↓
safe PaymentResponse
```

The request accepts `account_id`, `amount`, `currency`, the existing opaque
`merchant_id` reference, and an explicit `transaction_channel` from the
simulated channel vocabulary. The idempotency key is required in the
`Idempotency-Key` header. The response excludes balances, actor IDs, event IDs,
publication metadata, database details, and internal retry state.

`GET /payments/{transaction_id}` and bounded `GET /payments` queries use
MongoDB current state and enforce the authenticated owner. A transaction ID
belonging to another user is represented as a safe 404. The merchant subsystem
is not invented here; merchant/category validation is the next domain phase.

## Merchant and Category Domain Foundation - 2026-09-11

The catalog boundary is:

```text
GET catalog data
    ↓
MerchantService
    ↓
MongoDB categories/merchants
```

The canonical taxonomy is a small system-controlled set of stable category and
subcategory IDs. It is populated only by the explicit `scripts/seed_catalog.py`
command. Normal users cannot create or modify taxonomy records.

Merchant management is administrator-only. The existing `MERCHANT` role can
read the catalog but cannot manage it because no merchant ownership relation
exists in the current identity model. Merchant status is `ACTIVE` or
`INACTIVE`, and updates require an expected version. There is no delete route;
deactivation preserves references and auditability.

Payment flow is now:

```text
Payment request
    ↓
account ownership check
    ↓
MerchantService.resolve_for_payment
    ↓
active merchant + active category pair
    ↓
existing MongoDB payment transaction
```

The request supplies only a merchant UUID. Category values are never trusted
from the client. The payment transaction stores merchant ID plus a category /
subcategory snapshot (`*_id` and display names). This is a historical snapshot
for deterministic analytics, while the merchant/category collections remain
the authoritative current state.

## Research anomaly read boundary - 2026-09-12

The research anomaly API is separate from payment execution:

```text
authenticated owner
        |
        v
research anomaly service
        |
        +--> current MongoDB transaction
        +--> prior-only completed MongoDB history window
        +--> validated v2 JSON artifact
        |
        v
score / explicit unavailable result / explanation
```

The service uses the exact ordered 12-feature contract from the v2 anomaly
artifact. It rejects missing or truncated history, unsupported transaction
status, missing category/merchant context, and missing channel context. It
never defaults an unavailable feature, uses synthetic rows for a live user, or
reads target/scenario/future/decision fields. Single-item score and
explanation routes return safe controlled errors when the contract cannot be
satisfied; the bounded list route reports per-row `unavailable` status.

The score is a normalized research anomaly score in `[0, 1]`; it is not a
probability and higher values mean more anomalous only within this model
configuration. Threshold metadata identifies fixed train-only percentiles as
non-decision thresholds. Explanation text is deterministic and limited to
observed signal summaries.

## Operational transaction channel - 2026-09-13

`transaction_channel` is required on new payment requests and is persisted in
the MongoDB transaction snapshot and transaction event payload. It is not
inferred from the route or event provenance. The channel is included in the
financial request fingerprint, preserving it on idempotent replay and
rejecting a same-key conflicting request.

The live feature builder reads channel values from the current operational
transaction records returned by the bounded prior-only repository query. It
requires completed history, excludes the target, and uses timestamp plus
transaction ID ordering. Missing channel data in a legacy row produces
`research_feature_contract_unavailable`; insufficient prior rows produce
`research_insufficient_history`. These read-only research outcomes never alter
payment approval, balances, or transaction status.
## Analytics Data Foundation - 2026-09-12
The backend exposes a read-only analytics slice for the authenticated account owner. It is data-oriented and does not infer fraud or design a dashboard.
Routes: GET /api/v1/analytics/spending/summary, /categories, /merchants, /trends, and /largest. Responses use an explicit UTC half-open period; omitted ranges default to the preceding 30 days and ranges cannot exceed 366 days.
Only COMPLETED current transaction documents for the authenticated owner and account currency count as spending. Category and merchant labels are payment-time snapshots. Current balance is read from current account state, not calculated by subtracting analytics totals. Empty periods return zero totals and empty groupings.

## Demo banking modules - 2026-09-16

The demo banking surface is intentionally simulation-only. A user may create
additional server-profiled accounts with separate current balances. The
default account endpoint remains compatible with earlier clients, while the
list endpoint supports explicit source/destination selection. Deposit and
withdrawal are transaction types, not direct client balance writes.

Contacts are separate from bank beneficiaries; phone payment accepts only a
demo phone number; billers accept only demo-prefixed provider/identifier
values; cards expose masked fictional values and never return PIN material.
All resource routes are bearer-authenticated and owner-scoped.

## Demo merchant QR interaction - 2026-09-16

The mobile QR experience is: scan or select an image, locally detect a
candidate, validate it against `/payments/qr/validate`, show the registered
merchant, enter an amount with the demo keypad, review the server account,
enter the six-digit demo MPIN, and submit `/payments/qr`. The success view
displays the backend's previous balance, paid amount, remaining balance,
merchant, and transaction ID. No balance is computed on the client.

The QR display screen uses actual encoded JSON from `/demo-merchants`; it is
not decorative. Sharing currently shares the demo payload text. Real payment
standards, bank credentials, settlement, and external alerts are not
implemented.
