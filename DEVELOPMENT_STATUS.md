# SpendShield Development Status

Updated: 2026-09-18

## Demo QR payment contract repair - 2026-09-18

The reported `fictional_payment_details_invalid` response was reproduced with
the live API. The persisted versioned merchant QR was valid and MPIN
verification succeeded, but `/payments/qr` passed only `category_name` into
`PaymentCommand`. The financial domain correctly rejected that incomplete
category snapshot, and the route reduced the cause to a generic validation
error.

The QR payment boundary now derives a complete stable demo-local category
snapshot from the registry merchant before creating the transaction. The
backend-generated QR contract also validates its version, QR type, and
`simulation_only` marker. Invalid QR payloads return safe specific errors for
malformed, incomplete, or unsupported formats. Validation diagnostics log only
non-sensitive domain reasons; no QR contents, MPINs, tokens, passwords, or
secrets are logged.

The mobile scanner/manual flow now validates the current QR merchant state
without relying on a stale React state update. The payment success view shows
the backend transaction status and timestamp. Existing MPIN, balance,
idempotency, MongoDB current-state, Cassandra historical-event, and demo-only
boundaries remain unchanged.

Verification:

- Backend compile: passed.
- Focused QR/payment/MPIN tests: 9 passed.
- Full backend regression: 109 passed, 0 failed, with 3 dependency warnings.
- Live QR validation/payment: both `MODI-CHAI-001` and `MELONI-CHOCO-002`
  completed successfully.
- Live replay returned the original transaction ID and did not deduct twice.
- Live wrong-MPIN request returned HTTP 401.
- Mobile TypeScript: passed.
- Expo Doctor: 21/21 checks passed.
- Android Metro export: passed with 1,266 modules.

Manual Android verification of camera/gallery scanning and the complete device
flow remains required. No service was started or stopped by this session, and
no database data was deleted or reset.

## Mobile backend reachability and development host repair - 2026-09-18

The Expo Go error was caused by a stale backend host allowlist, not MPIN or
authentication logic. The mobile environment pointed to the current PC LAN
address 10.165.59.245, while backend/.env still allowed the previous address
10.185.191.245. TrustedHostMiddleware consequently returned HTTP 400 for a
request whose Host header was 10.165.59.245:8000. The mobile client presented
that 400 as the development-host error.

The existing environment-driven host validation was strengthened without
disabling it:

- SPENDSHIELD_ALLOWED_HOSTS is now the canonical development/staging setting.
- The legacy SPENDSHIELD_TRUSTED_HOSTS setting remains supported for
  compatibility.
- Development currently allows localhost, 127.0.0.1, 0.0.0.0, and
  10.165.59.245.
- Production and staging still require a non-empty explicit allowlist and
  reject wildcard hosts.
- MongoDB, Cassandra, authentication, payment logic, and the API contracts
  were not redesigned.

The mobile client now has a development connection diagnostic on login and
registration. It shows a credential-free API URL, distinguishes network
failure/timeout from HTTP 401, 403, 404, 422, 500, and 503, and never displays
tokens or passwords.

Verification:

- Backend configuration loaded the expected current LAN host and unchanged
  MongoDB/Cassandra settings.
- Backend compilation: passed.
- Health-focused backend tests: 14 passed.
- Full backend regression: 107 passed, 0 failed, with 3 dependency warnings.
- Current Host header checks: 127.0.0.1:8000 passed; 10.165.59.245:8000
  passed; stale 10.185.191.245:8000 was correctly rejected with HTTP 400.
- LAN health endpoint: HTTP 200.
- LAN dependency health endpoint: HTTP 200.
- LAN docs endpoint: HTTP 200.
- Live LAN registration: HTTP 201.
- Live LAN login: HTTP 200 with a bearer token returned; the token was not
  printed or logged.
- Mobile TypeScript: passed.
- Expo Doctor: 21/21 checks passed.
- Android Metro export: passed with 1,266 modules.

The live registration smoke check created one uniquely named diagnostic user;
no existing data was deleted or reset. Physical Expo Go login still requires
the user to restart Expo with the current environment value and perform the
device-level login manually.

## Mobile presentation terminology cleanup - 2026-09-18

The mobile presentation layer was cleaned up to remove the word "Demo" from
user-facing labels, buttons, headings, placeholders, QR/payment copy, card and
security messages, shared error alerts, and fallback payment errors. Safer wording such as
"fictional", "simulation only", and "no real money" remains where it is
needed to make the classroom-only boundary clear.

Internal compatibility identifiers were intentionally preserved. This includes
route names, component/type names, API paths, demo_mpin, serialized payment
types, merchant payload fields, DEMO_SAVINGS, and backend safety prefixes.
These are implementation contracts, not user-facing copy; renaming them would
break existing payment, MPIN, QR, and account behavior.

The subscription screen also received a small type-safe UI correction: selected
plan state now uses the selected plan's plan_id, rather than looking for a
plan ID on the containing platform.

Files changed in this cleanup include the mobile navigation, dashboard,
merchant QR, security, profile, account details, payment, phone payment,
recharge, subscription, card, bills, contacts, notifications, transaction,
shared control, and validation files.

Verification:

- Mobile TypeScript: passed (npm exec tsc -- --noEmit).
- Expo Doctor: passed (21/21 checks passed).
- Android Metro export: passed (npx expo export --platform android).
- Mobile automated tests: unavailable; no test script or Jest configuration
  exists.
- Backend code, MongoDB/Cassandra data and configuration, authentication,
  payment contracts, and ML artifacts were not changed in this cleanup.
- Services were not started or stopped by this session. A later read-only check
  found ports 27017, 27018, 8000, and 9042 reachable; the backend health and
  dependency endpoints returned HTTP 200, MongoDB 27018 reported writable
  primary rs0, and Cassandra was reported healthy. This indicates the services
  were started externally. Live login, MPIN reset, QR camera, and end-to-end
  payment verification still require manual device execution.

## Current registration diagnosis

The mobile registration payload is intentionally:

```json
{
  "email": "user@example.com",
  "password": "a-valid-password"
}
```

This matches `backend/app/schemas/auth.py::CredentialsRequest`. The
`confirmPassword` field is client-side only and is not sent to FastAPI.

The HTTP 400 seen from the Android phone was caused by the backend trusted-host
allowlist. The development backend previously allowed only `localhost` and
`127.0.0.1`, while Expo Go sent a `Host` header for the development computer's
LAN address `10.185.191.245`. `TrustedHostMiddleware` rejected that request
before the registration route executed.

The exact mobile payload was tested after MongoDB was restored and returned
HTTP 201. Invalid passwords and unexpected fields return the structured HTTP
422 validation response. Duplicate identities remain HTTP 409. No password,
token, database URL, or request body is logged.

## MongoDB

- Version: 8.3.4
- Executable: `C:\Program Files\MongoDB\Server\8.3\bin\mongod.exe`
- SpendShield data directory: `D:\E_Drive\Project\.mongodb-rs-validation`
- Port: `27018`
- Replica set: `rs0`
- Last recorded validation result: writable primary at `127.0.0.1:27018`
- Connection URI: `mongodb://127.0.0.1:27018/?replicaSet=rs0`
- Startup command:

```powershell
& 'C:\Program Files\MongoDB\Server\8.3\bin\mongod.exe' `
  --dbpath 'D:\E_Drive\Project\.mongodb-rs-validation' `
  --port 27018 --replSet rs0 --bind_ip 127.0.0.1 `
  --logpath 'D:\E_Drive\Project\.mongodb-rs-validation\mongod.log' --logappend
```

The separate MongoDB service on port `27017` was not modified.

## Cassandra

- Installation: `/home/kanishq/Cassandra` inside Ubuntu 22.04.5 WSL
- Windows-side installation directory also present at: `C:\Cassandra`
- Installed version: 4.0.21
- WSL distribution: `Ubuntu-22.04`
- Configured host: `127.0.0.1`
- Configured port: `9042`
- Configured keyspace: `spendshield_events`
- Last recorded validation result: running, one `UN` node
- Windows-to-WSL connectivity: `Test-NetConnection 127.0.0.1 -Port 9042`
  succeeded
- `cqlsh` connection: succeeded; `system.local.release_version` returned
  `4.0.21`
- Keyspaces found: `spendshield_events`, `ss_test`, three generated `ss_test_*`
  test keyspaces, and Cassandra system keyspaces
- Existing SpendShield tables:
  - `audit_events_by_case_day`
  - `authentication_events_by_user_day`
  - `device_events_by_device_day`
  - `session_events_by_user_day`
  - `transaction_events_by_account_day`
- Last recorded backend dependency health: MongoDB `ok`, Cassandra `ok`
- Cassandra-focused suite: `7 passed`
- Last recorded full backend suite with both databases available: `94 passed, 0 failed`

Startup from WSL:

```bash
wsl -d Ubuntu-22.04
~/Cassandra/bin/cassandra -f
```

Verification from a second WSL terminal:

```bash
wsl -d Ubuntu-22.04
ss -ltnp | grep 9042
~/Cassandra/bin/cqlsh 127.0.0.1 9042
```

The backend's existing initialization code remains responsible for creating
the configured schema when Cassandra is available. No Cassandra data, keyspace,
or table was deleted or recreated. Cassandra remains the historical-event
store; MongoDB remains current operational state.

## Backend

- Path: `D:\E_Drive\Project\backend`
- Environment: `backend/.env`
- Virtual environment:

```powershell
cd D:\E_Drive\Project\backend
.venv\Scripts\activate
```

- Startup:

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- Port: `8000`
- `GET http://127.0.0.1:8000/health`: passed
- `GET http://127.0.0.1:8000/docs`: HTTP 200
- Last recorded `GET http://127.0.0.1:8000/api/v1/health/dependencies`: MongoDB `ok`,
  Cassandra `unavailable`
- Trusted development hosts now include `10.185.191.245`
- LAN-host registration: HTTP 201
- LAN-host login: HTTP 200 with bearer token
- LAN-host `/auth/me`: HTTP 200 with matching user identity

## Mobile

- Path: `D:\E_Drive\Project\mobile`
- Install: `npm install`
- Start: `npx expo start`
- Current LAN API base URL: `http://10.185.191.245:8000/api/v1`
- The Expo Go Android app reached FastAPI over the LAN.
- Registration now presents structured backend messages and safe fallbacks for
  framework/plain-text responses.

## Mobile account summary and first-account onboarding

The authenticated dashboard now uses the existing account APIs without taking
ownership of financial state:

- `GET /api/v1/accounts/me` loads the current server-owned account snapshot.
- `POST /api/v1/accounts` creates the authenticated user's first account with
  an intentionally empty request body. The backend supplies the owner,
  currency, opening balance, and status.
- An API response with HTTP `404` and code `account_not_found` shows a
  controlled empty state with a `Create account` action.
- Successful creation is followed by another `GET /accounts/me`; the
  dashboard renders that response rather than a locally constructed account.
- Balance is retained as the backend's decimal string. The mobile code does
  not calculate, persist, or mutate authoritative balance data.
- Loading, retryable network/timeout errors, `401`, validation errors,
  dependency `503`, unexpected response shapes, and account creation errors
  have controlled UI states.

Implementation files:

- `mobile/src/api/accountApi.ts`
- `mobile/src/types/account.ts`
- `mobile/src/screens/DashboardScreen.tsx`

Verification completed for this implementation:

- TypeScript: `npx tsc --noEmit` passed.
- Expo Doctor: `21/21 checks passed`.
- Android bundle: `npx expo export --platform android` passed; Metro bundled
  843 modules.
- Targeted backend account tests: `7 passed`.
- Full backend suite in the current session: `67 passed, 27 skipped, 0 failed`.
- Mobile test runner: not available; `mobile/package.json` has no test script
  or Jest configuration.
- Static authority review: the account creation request sends no body, and
  the dashboard only displays the server-provided balance.

Live mobile account creation/reload was not manually verified in this task
because services were left stopped as requested. The previously recorded
MongoDB/Cassandra validation above remains historical; no service was started
or stopped, and no MongoDB or Cassandra data was changed.

## Files changed for this debugging task

- `backend/.env`
- `backend/app/main.py`
- `backend/tests/test_health.py`
- `mobile/src/api/client.ts`
- `DEVELOPMENT_STATUS.md`

Files changed for the mobile account task:

- `mobile/src/api/accountApi.ts`
- `mobile/src/types/account.ts`
- `mobile/src/screens/DashboardScreen.tsx`
- `DEVELOPMENT_STATUS.md`

No MongoDB reset, Cassandra reset, payment logic change, authentication schema
change, secret rotation, backend code change, database data change, or ML
artifact change was performed.

## Earlier mobile UI design system and dashboard presentation

The balance-card presentation described in this historical section was
superseded by the Phase 1 Home privacy revision below.

The authenticated dashboard now has a compact fintech-style presentation built
around the existing server-backed account flow:

- Added soft-blue primary tokens, card surfaces, spacing, typography, status
  colors, and elevation styles to the mobile theme.
- Added reusable dashboard cards, section headers, status badges, consistent
  text glyph icons, quick-action tiles, and bottom-navigation presentation.
- Replaced the large plain account-details block with a prominent account
  presentation card. This earlier visual was later removed from Home for
  privacy.
- Added clear Monthly spending and Recent transactions empty states because
  those APIs are not part of the current mobile contract.
- Added a security overview that describes the currently authenticated session;
  it does not invent security metrics.
- Kept Add transaction, Transactions, Insights, Security, and Profile as
  presentation-only unavailable destinations. No unsupported payment or
  navigation behavior was introduced.
- Preserved account loading, account creation, retry, authentication, network,
  validation, dependency, and malformed-response behavior.

Files changed for this UI task:

- `mobile/src/theme/index.ts`
- `mobile/src/components/BrandMark.tsx`
- `mobile/src/components/PrimaryButton.tsx`
- `mobile/src/components/Screen.tsx`
- `mobile/src/components/DashboardUI.tsx`
- `mobile/src/screens/DashboardScreen.tsx`
- `DEVELOPMENT_STATUS.md`

Verification completed:

- TypeScript: `npx tsc --noEmit` passed.
- Expo Doctor: `21/21 checks passed`.
- Android Metro bundle: `npx expo export --platform android` passed; Metro
  bundled 844 modules.
- Mobile tests: no test script or Jest configuration is present, so no mobile
  test suite was available to execute.
- Backend files and behavior: unchanged.
- MongoDB and Cassandra configuration/data: unchanged.
- ML artifacts: unchanged.

Remaining manual verification: open the authenticated dashboard in Expo Go or
an Android emulator against the running backend to visually confirm device
layout, account loading, first-account onboarding, and the preserved error
states. No service was started or stopped during this UI task.

## Phase 1 rich SpendShield Home experience

The Home screen was expanded into a richer Google Pay-style fintech layout
without copying Google Pay branding or introducing unsupported financial flows.

Implemented sections:

- Compact SpendShield header with greeting, authenticated email, and profile
  initials.
- Earlier balance-card and hide/show presentation were later removed from Home
  by the privacy revision; account refresh remains available.
- Quick-action grid for Pay, Send money, Scan/QR, Bank transfer, Bills,
  Recharge, Transactions, and Account details.
- People and merchant placeholders for frequent contacts and favorite
  merchants.
- Bills and recurring-payments placeholder.
- Monthly spending placeholder with no invented chart values.
- Security overview describing the authenticated session without claiming
  fraud detection or unusual-activity detection.
- Recent transactions empty state.
- SpendShield informational banner.
- Presentation-only bottom navigation for Home, Transactions, Insights,
  Security, and Profile. Only Home is active because the other routes do not
  exist yet.

Real versus placeholder behavior:

- Real: authenticated account loading, account creation, server balance,
  currency, status, account details, refresh, and all existing error states.
- Placeholder/unavailable: payment, sending, QR, bank transfer, bills,
  recharge, people, merchants, transactions, spending insights, security
  center, notifications, and non-Home navigation routes.
- No payment backend, fake transaction, fake balance, fake spending amount,
  fake recipient, or fake security result was added.

Files changed for this phase:

- `mobile/src/components/DashboardUI.tsx`
- `mobile/src/screens/DashboardScreen.tsx`
- `DEVELOPMENT_STATUS.md`

Phase 1 verification:

- TypeScript: `npx tsc --noEmit` passed.
- Expo Doctor: `21/21 checks passed`.
- Android Metro bundle: `npx expo export --platform android` passed; Metro
  bundled 844 modules.
- Mobile tests: unavailable; the project has no mobile test script or Jest
  configuration.
- Backend files: unchanged.
- MongoDB and Cassandra: unchanged.
- ML artifacts: unchanged.

This earlier visual verification note is superseded by the privacy-revision
verification note below. No service was started or stopped for this phase.

## Phase 1 Home privacy revision

The Home screen was revised against the supplied reference images with a
strict privacy boundary: no starting balance, current balance, account amount,
account ID, or currency value is rendered anywhere on Home. The account API is
still loaded so onboarding, account existence, status, refresh, and error
handling continue to work, but the returned monetary value is intentionally
not presented.

Implemented design changes:

- Compact SpendShield header with logo, greeting, authenticated email,
  profile initials, and a disabled search affordance.
- Local educational SpendShield promotional banner with no loan, cashback,
  reward, or financial claim.
- Reference-inspired two-row, four-column payment-action grid:
  Scan QR, Pay contacts, Pay phone number, Bank transfer, Pay UPI/account,
  Self transfer, Pay bills, and Mobile recharge.
- People and Businesses empty states without fake contacts, photos, merchants,
  or payment history.
- Bills & Recharges categories for DTH/Cable TV, Electricity, Postpaid mobile,
  Loan EMI, Water bill, and Gas bill, all clearly marked as coming soon.
- Offers & Rewards presentation-only cards for Rewards, Offers, and Referrals;
  no earnings, cashback, or reward amount is shown.
- Utility rows for transaction history, bank balance, Account details, and a
  real account refresh action. Unavailable rows are disabled and labeled.
- SpendShield security card showing only the server-backed account status and
  safe monitoring language; no fraud or anomaly result is claimed.
- Central disabled Scan/QR floating action; it requests no camera permission
  and performs no payment or scan operation.
- Reference-inspired four-item bottom navigation: Home, Pay Now,
  Bills & Recharges, and More. Only Home is active; unavailable destinations
  do not create unsupported routes.
- All generic payment/currency glyphs are neutral icons; no monetary symbol or
  amount is used as Home content.

Privacy and behavior verification:

- Home privacy scan: no balance value, account ID, account amount, or currency
  value found in `DashboardScreen.tsx` or `DashboardUI.tsx`.
- Account flow references remain intact: `getMyAccount`, `createAccount`,
  `account_not_found`, retry, refresh, and sign-out paths are present.
- TypeScript: `npx tsc --noEmit` passed.
- Expo Doctor: `21/21 checks passed`.
- Android Metro bundle: `npx expo export --platform android` passed; Metro
  bundled 844 modules.
- Mobile tests: unavailable; no mobile test script or Jest configuration
  exists.
- Backend code: unchanged.
- MongoDB and Cassandra: unchanged.
- ML artifacts: unchanged.

Remaining manual verification: run the backend and open the authenticated Home
screen in Expo Go or an Android emulator to check the reference-inspired
layout on the target device, confirm no amount appears, verify login/sign-out,
account onboarding/refresh, and exercise the preserved error states. No
service was started or stopped for this revision.

## Combined Phase 2/3/4 payment, transaction, and account-detail work

### Backend status

The repository already contained the Phase 2 payment foundation before this
task. It remains the authoritative implementation for simulated payments:

- `POST /api/v1/payments` is authenticated, owner-scoped, merchant-backed,
  balance-authoritative, idempotent, and connected to the existing MongoDB /
  Cassandra event boundary.
- `GET /api/v1/payments` provides bounded, newest-first owner-scoped history
  with cursor pagination.
- `GET /api/v1/payments/{transaction_id}` provides owner-scoped transaction
  detail.
- MongoDB remains current account/transaction state; Cassandra remains
  historical event storage.
- Replica-set MongoDB uses the existing atomic transaction path, while the
  standalone fallback uses the existing reservation/compare-and-set recovery
  path. No database schema redesign was performed.

The only backend addition in this task was an optional validated payment note:

- `PaymentCommand` and `Transaction` retain a normalized note up to 256
  characters.
- `PaymentCreateRequest` accepts the optional note.
- MongoDB current transaction documents, safe API responses, and historical
  transaction event payloads preserve the note.
- The request fingerprint includes the note, so reusing an idempotency key
  with a different note is rejected as a conflict.

### Mobile implementation

Added mobile API/types:

- `mobile/src/api/merchantApi.ts`
- `mobile/src/api/paymentApi.ts`
- `mobile/src/types/merchant.ts`
- `mobile/src/types/payment.ts`

Added authenticated routes and screens:

- `Pay` → `mobile/src/screens/PayScreen.tsx`
- `Transactions` → `mobile/src/screens/TransactionsScreen.tsx`
- `TransactionDetails` → `mobile/src/screens/TransactionDetailsScreen.tsx`
- `AccountDetails` → `mobile/src/screens/AccountDetailsScreen.tsx`
- `ComingSoonPayment` → `mobile/src/screens/ComingSoonPaymentScreen.tsx`

The real Pay flow now:

- Loads only server-provided account and active merchant data.
- Validates merchant selection, positive decimal amount, supported precision,
  note length, and available balance before review.
- Requires an explicit review step before confirmation.
- Sends the server-owned account ID/currency and a client idempotency key to
  the existing payment API; it never sends an owner ID or client balance.
- Disables confirmation during submission.
- Shows success only after the backend confirms the payment.
- Fetches the updated private account state for an optional hidden-by-default
  remaining-balance display.
- Provides transaction detail/history navigation and a simulated-payment
  disclaimer.

Transactions are real backend data only. The list is owner-scoped by the
backend, newest-first, paginated, and has loading, empty, retry, and detail
states. Account Details is separate from Home, masks the account reference,
and hides the balance by default with an explicit show/hide control.

Send money, QR/manual payment, bank transfer, and self-transfer now have
safe Coming Soon screens that explain the missing backend contract and show
planned fields without collecting data or submitting fake operations. Home
actions route to these screens rather than pretending that a merchant payment
is a recipient or bank transfer. Bills/recharge actions remain unavailable.

### Files changed in this combined task

Backend:

- `backend/app/domain/financial.py`
- `backend/app/schemas/payments.py`
- `backend/app/api/v1/payments.py`
- `backend/app/repositories/payments.py`
- `backend/tests/test_payments_api.py`

Mobile:

- `mobile/src/api/merchantApi.ts`
- `mobile/src/api/paymentApi.ts`
- `mobile/src/types/merchant.ts`
- `mobile/src/types/payment.ts`
- `mobile/src/types/navigation.ts`
- `mobile/src/navigation/AppNavigator.tsx`
- `mobile/src/components/DashboardUI.tsx`
- `mobile/src/screens/DashboardScreen.tsx`
- `mobile/src/screens/PayScreen.tsx`
- `mobile/src/screens/TransactionsScreen.tsx`
- `mobile/src/screens/TransactionDetailsScreen.tsx`
- `mobile/src/screens/AccountDetailsScreen.tsx`
- `mobile/src/screens/ComingSoonPaymentScreen.tsx`
- `mobile/package.json`
- `mobile/package-lock.json`
- `DEVELOPMENT_STATUS.md`

### Verification

- Targeted backend payment/persistence/domain tests: `9 passed, 17 skipped`.
- Full backend suite: `67 passed, 27 skipped, 0 failed`.
- TypeScript: `npx tsc --noEmit` passed.
- Expo Doctor: `21/21 checks passed` after aligning Expo to `57.0.23`.
- Android Metro: `npx expo export --platform android` passed; Metro bundled
  851 modules.
- Mobile test runner: unavailable; the project has no Jest configuration or
  mobile test script.
- Home privacy scan: no Home balance value, account ID, currency value, or
  monetary literal found.
- Backend authentication/account onboarding paths remain unchanged.
- MongoDB configuration/data, Cassandra configuration/data, and ML artifacts
  were not modified.

Skipped integration tests require the local MongoDB rs0/Cassandra services.
No service was started or stopped during this task. Live Expo Go verification
is still required for login, account onboarding, real merchant loading, Pay
review/confirmation, transaction history/detail, Account Details, back
 navigation, and all error states.

## Combined Prompt 1B — Demo payment contracts, QR permission, and testing

Implemented additive, simulation-only payment contracts without adding a
database or broker. The existing merchant payment endpoint remains intact.

### Backend contracts

Added authenticated routes under `/api/v1/payments`:

- `POST /send` — validates a receiver account and atomically debits the sender
  and credits the receiver on MongoDB replica sets.
- `POST /qr` — accepts only an explicit BJP Bank simulation QR payload.
- `POST /qr/validate` — validates a QR payload without creating a transaction.
- `POST /manual` — accepts only namespaced demo merchant identifiers.
- `POST /bank-transfer` — accepts only fictional BJP Bank demo account/code
  values and never contacts a bank.
- `POST /self-transfer` — supports two distinct accounts owned by the current
  user when such accounts exist.

All demo routes use the existing authentication, owner checks, MongoDB current
state, transaction history, audit/event publication, and `Idempotency-Key`
boundary. New history metadata includes transaction type, debit/credit
direction, counterparty/beneficiary details, transfer reference, and the
simulation flag. Existing merchant payment behavior remains compatible with
legacy transaction documents through defaults.

### Mobile implementation

The existing `ComingSoonPayment` route name was retained for navigation
compatibility, but its screen now provides the live demo flows:

- Send Money form, review, confirmation, server-result, and retry behavior.
- QR scanning with camera permission requested only inside the QR feature.
- Denied/blocked camera states with manual-entry fallback and Settings action.
- Demo QR payload validation before review and server-side validation again at
  submission.
- Manual QR merchant payment, fictional BJP Bank transfer, and self-transfer
  forms using the shared mobile validation helpers.
- Server-provided account balance display and post-operation account reload;
  no local balance calculation or authoritative client mutation.
- Transaction history/detail presentation for all new transaction types and
  debit/credit direction.

Added `expo-camera` (`~57.0.5`) and its explicit camera permission text in
`mobile/app.json`. No permission is requested during application launch.

### Known limitation

The current account foundation intentionally enforces one account per user via
the existing MongoDB account index. Therefore the self-transfer API is fully
validated and ready for distinct owned accounts, but a normal user currently
receives a controlled failure until the project intentionally adds multi-account
support. That account-model change is outside this phase and was not performed.

### Verification

- Demo contract tests: `4 passed, 0 failed`.
- Full backend suite: `71 passed, 27 skipped, 0 failed`.
- Mobile TypeScript: `npx tsc --noEmit` passed.
- Expo Doctor: `21/21 checks passed`.
- Android Metro export: passed; Metro bundled 859 modules.
- Mobile test runner: unavailable; no Jest configuration or mobile test script
  exists.
- MongoDB `127.0.0.1:27018`: unreachable during this verification.
- Cassandra `127.0.0.1:9042`: unreachable during this verification.
- No MongoDB/Cassandra data, authentication logic, ML artifacts, or existing
  payment database schema were deleted or reset.

Manual live verification remains required for real MongoDB rs0 transaction
execution, Cassandra historical publication, Expo camera permission/scanning,
and the mobile end-to-end flows.

## Remaining demo modules and UI repair — 2026-09-16

### Infrastructure verified

- Backend health: `200 OK` at `127.0.0.1:8000/api/v1/health`.
- Dependency health: `200 OK`.
- MongoDB: reachable at `127.0.0.1:27018`, replica set `rs0`, writable primary.
- Cassandra: reachable at `127.0.0.1:9042`.
- No service was started or stopped by the implementation run.
- No MongoDB, Cassandra, payment foundation, authentication, or ML artifact
  reset was performed.

### Implemented in this pass

- Intentional multiple demo accounts. Existing single-account users continue
  to use `/accounts/me`; an explicit `account_type` request creates another
  server-profiled fictional BJP Bank account. Balance, owner, currency,
  status, and identifiers remain server-owned.
- Safe account profile fields: demo holder, masked demo account reference,
  fictional bank code, branch, and account type.
- `GET /api/v1/accounts` owner-scoped account listing.
- `DEMO_DEPOSIT` and `DEMO_WITHDRAWAL` through the existing idempotent
  payment/transaction/event boundary.
- Simulation-only phone-number payment and bill/recharge payment contracts.
- Owner-scoped MongoDB current-state CRUD for contacts, beneficiaries,
  saved billers, virtual demo cards, and local notifications.
- Virtual demo card active/frozen/blocked transitions, demo PIN hashing, and
  server-controlled spending limit.
- Ionicons-based mobile icon mapping, actionable bottom navigation, scan
  action, chevrons, contacts selection, phone payment, bill/recharge flow,
  account selection/additional-account display, and local QR image decoding
  using `expo-camera.scanFromURLAsync`.
- `Start.txt` now records the verified Windows/WSL startup and health checks;
  `mobile/Start.txt` points to it.

### Verification

- Live API smoke test: passed for first account, second account, deposit,
  deposit replay, withdrawal, self-transfer, phone payment, bill payment,
  contact, biller, card freeze/unfreeze/block, and owner-scoped history.
- Deposit replay returned the same transaction ID; no duplicate financial
  effect was created.
- Backend compile: passed.
- Final backend regression rerun: `74 passed, 27 skipped, 0 failed` with
  three dependency deprecation warnings. The skipped tests were dependency
  gated because MongoDB/Cassandra were no longer listening during this final
  rerun.
- Mobile TypeScript: passed after the final account-operation screens.
- Expo Doctor: `21/21 checks passed`.
- Android Metro export: passed; 944 modules bundled.
- Mobile automated tests: not configured in the repository.

The live health and demo API smoke checks listed above passed earlier while
the manually started services were available. A final read-only connectivity
check after the regression rerun found only the existing MongoDB listener on
`127.0.0.1:27017`; SpendShield MongoDB `27018`, Cassandra `9042`, and backend
`8000` were not listening. No service was stopped by tooling. Manual restart
using `Start.txt` is required before claiming current live verification.

### Known limitations

- Profile editing, demo MPIN/session-management UX, protected admin/demo data
  actions, generated notification workflows, card-payment enforcement, and
  complete saved-biller/card/notification mobile management screens remain
  planned or partial.
- Live device verification is still required for camera permission states,
  QR image selection on Android, safe-area rendering, and every new mobile
  navigation path.
- The architecture remains a modular monolith: MongoDB owns current state and
  Cassandra owns historical events; no broker or new database was introduced.

## Persisted demo merchant QR and remaining module completion - 2026-09-16

Implemented a MongoDB-backed fictional merchant registry with `MODI-CHAI-001`
and `MELONI-CHOCO-002`, version-1 QR payload generation, server-side registry
matching, actual mobile QR rendering, camera/gallery validation, amount keypad,
review, six-digit demo MPIN, and backend-returned previous/paid/remaining
balance fields. Unknown, inactive, mismatched, legacy, and unsupported QR
payloads are rejected when the registry is configured.

Also implemented server-backed demo profile editing, hashed owner-scoped MPIN
state with failure lock handling, mobile card management, notification center
actions, committed-payment notifications, and fictional card-payment status /
limit enforcement. No real bank, card, UPI, biller, telecom, SMS, email, or
push integration exists.

Verification for this continuation: focused backend `22 passed, 0 failed`;
full backend `76 passed, 27 skipped, 0 failed` with three dependency warnings;
mobile TypeScript passed; Expo Doctor `21/21`; Android export passed with
1,262 modules. The 27 skips are dependency-gated MongoDB/Cassandra tests.

Earlier live smoke checks passed while services were manually available. The
final read-only port check found only untouched MongoDB `127.0.0.1:27017`;
SpendShield MongoDB `27018`, Cassandra `9042`, and backend `8000` were not
listening. No service was started or stopped by tooling, and no data reset or
deletion was performed.

Remaining: protected admin/demo panel, MPIN recovery/reset, mobile saved-biller
CRUD screens, card-specific history filtering, failed-payment notification
workflows, and physical-device QR validation.

## Authentication 503 repair — MongoDB index-name conflict - 2026-09-16

The mobile authentication `503 database_unavailable` response was traced to a
MongoDB schema initialization failure, not to an incorrect URI or unavailable
database service. The configured backend settings were verified as:

- MongoDB URI: `mongodb://127.0.0.1:27018/?replicaSet=rs0`
- Database: `spendshield`
- Replica set: `rs0`
- MongoDB timeouts: `3000ms` server selection and `3000ms` connection
- Cassandra contact point: `127.0.0.1:9042`
- Cassandra keyspace: `spendshield_events`
- Cassandra connection timeout: `5s`

The existing SpendShield database contained the non-unique legacy index
`ix_accounts_user_id`. The current schema expected the same `{user_id: 1}`
index under `uq_accounts_user_id`; MongoDB rejected the name mismatch with
`IndexOptionsConflict`. The authentication repository converted that driver
exception into the misleading generic `database_unavailable` response.

`backend/app/db/mongo_schema.py` now reconciles that specific legacy index by
dropping only the obsolete index definition and recreating the intended
non-unique index name. Documents and collections are not deleted. The live
account count remained unchanged at `3` and the final account indexes are
`_id_`, `uq_accounts_id`, and `uq_accounts_user_id`.

Live verification after the repair:

- MongoDB `27018`: reachable; `rs0` is writable primary.
- Cassandra `9042`: reachable; Cassandra `4.0.21`; all five event tables present.
- Backend localhost and LAN (`10.185.191.245:8000`) health endpoints: HTTP 200.
- Diagnostic registration: HTTP 201.
- Diagnostic login: HTTP 200 with a bearer token.
- Existing account registration replay: HTTP 409 duplicate identity.
- Full backend suite: `103 passed, 0 failed`, with three dependency warnings.

The mobile `.env.local` points to `http://10.185.191.245:8000/api/v1`. The
`10.185.191.223` address in the Uvicorn access log is the phone/source address,
not the backend host. No application configuration was changed in this repair;
the newly created diagnostic user remains as local test data. MongoDB `27017`
was not used by the live repair; the existing regression suite retains its
pre-existing isolated test namespaces there.

## Prompt 2 demo banking modules and navigation repair - 2026-09-17

Implemented the next server-backed fictional demo slice without adding a real
payment provider or changing the MongoDB/Cassandra ownership boundary.

Backend additions and repairs:

- Added immutable demo recharge catalogs for Airtel, Jio, Vi, and BSNL with
  server-owned plans and INR decimal prices.
- Added fictional BJP Entertainments catalogs for BJPPrime and BJP Entertainments with
  monthly, quarterly, and yearly plans.
- Added authenticated `/recharge/operators`, `/recharge`,
  `/subscriptions/platforms`, `/subscriptions`, and subscription status APIs.
- Recharge and subscription creation require the existing hashed six-digit
  demo MPIN, owner-scoped account access, payment idempotency, balance rules,
  MongoDB current-state persistence, audit/event delivery, and notifications.
- Added subscription idempotency indexing and Mongo-compatible string/date
  serialization; no existing database was reset or deleted.
- Enforced the same MPIN boundary across sensitive demo payment endpoints,
  including generic payment, phone, bill, transfer, QR, and account
  operations. QR validation alone remains non-financial and does not charge.
- Added the same MPIN requirement to sensitive virtual-card mutations: freeze,
  unfreeze, block, card PIN changes, and spending-limit changes.
- Added authenticated `POST /api/v1/demo-security/mpin/reset`. It requires
  the account password, clears only the owner-scoped demo MPIN hash and lock
  counters, and allows a new six-digit MPIN to be created.
- Added protected account references/unlock API. The mobile account-details
  screen no longer loads full balances before MPIN verification.
- Authentication, payment state-machine semantics, Cassandra schema, ML
  artifacts, and the unrelated MongoDB 27017 were not changed.

Mobile additions and repairs:

- Added server-backed recharge and subscription screens with operator → plan →
  mobile number → review → MPIN → backend success flow, and subscription
  selection/status management.
- Pay a Merchant now uses the persisted demo merchant registry and QR payload,
  so it no longer calls the unrelated canonical merchant catalog or shows a
  false empty state.
- QR merchant identification precedes amount entry; invalid/unsupported QR
  payloads remain rejected safely.
- Existing send, bank, self-transfer, phone, bill, and account-operation flows
  now collect and send the demo MPIN before submission.
- More is organized into Profile, Account, Payments, Security, and
  Entertainment sections without duplicate virtual-card routes.
- Dashboard quick actions route to their own screens. The dashboard now has
  three real swipeable slides with working pagination dots and slide actions.
- Both demo merchant QR records are explicitly labelled DEMO MERCHANT and
  SIMULATION ONLY.

Verification completed in this phase:

- Python compilation: passed.
- Focused live lifestyle test: `1 passed` against MongoDB rs0 and Cassandra
  event delivery.
- Focused regression repair tests: `2 passed`.
- TypeScript: passed.
- Expo Doctor: `21/21 checks passed`.
- Android Metro export: passed.
- Full backend regression: `76 passed, 0 failed, 28 skipped`, with three
  existing dependency deprecation warnings. The skipped tests are the
  repository's dependency-gated cases.
- Read-only live verification on 2026-09-17: ports `27017`, `27018`, `8000`,
  and `9042` were reachable; `/api/v1/health` and
  `/api/v1/health/dependencies` both returned HTTP 200. MongoDB `27018`
  reported writable primary `rs0`; Cassandra reported version `4.0.21` and
  keyspace `spendshield_events`.
- No mobile automated test runner is configured; manual Expo Go/device flow
  verification remains required.

Known limitations:

- Subscription creation commits the financial payment and subscription
  current-state document in separate application operations. Payment
  idempotency prevents duplicate financial debits, but a process failure after
  payment commit and before subscription-document creation still needs a
  reconciliation workflow.
- Mobile live login, MPIN, QR camera scan, recharge, and subscription flows
  require the user to keep MongoDB rs0, Cassandra, Uvicorn, and Expo running
  according to `mobile/Start.txt`.
- The request to set an existing account balance to `10000000000` was not
  executed. Direct database mutation would bypass the authoritative financial
  rules and audit/event boundary; the existing demo transaction cap is
  `1000000.00`. An exact audited demo funding decision is required before
  changing that account.

Final read-only service check after implementation: only the unrelated
MongoDB `27017` listener was reachable. SpendShield MongoDB `27018`,
Cassandra `9042`, and backend `8000` were not listening; health endpoints and
device/live verification were therefore blocked. No service was started or
stopped by this phase.

MPIN reset verification: the reset service test passed; live reset was not
executed because MongoDB `27018` and backend `8000` were stopped.

## Final consolidated repair continuation - 2026-09-18

The remaining Home shortcut defects were repaired without changing backend
contracts or the financial boundary:

- `See transaction history` continues to open the live authenticated,
  owner-scoped transaction history screen with loading, empty, retry, and
  error states.
- `Check bank balance` is now an active shortcut to the protected account
  details flow. It does not reveal balance data until the backend MPIN unlock
  succeeds.
- `Account details` remains routed to the same owner-scoped protected account
  flow, including masked references and multi-account selection.
- `Refresh account` now performs a real `GET /api/v1/accounts/me` reload,
  shows an in-row loading state, and reports successful server refresh or a
  mapped error.
- The dashboard carousel has three real slides with working swipe, snap, and
  pagination-dot behavior; each slide has its own destination.

The demo subscription catalog now uses the requested fictional platforms
`BJPPrime` and `BJP Entertainments`. The existing API, MPIN protection,
idempotency, transaction, audit/event, and notification behavior remain
server-backed.

Payment service failures now create one deterministic, owner-scoped
`PAYMENT_FAILED` notification for service-level failures such as inactive
accounts, insufficient funds, concurrency conflicts, recovery-in-progress,
idempotency conflicts, and financial rule violations. The notification stores
only a safe error category; raw MPINs, credentials, tokens, amounts, and raw
idempotency keys are not persisted. Pre-service validation or MPIN rejection
still has no financial transaction to notify and remains represented by the
API error response.

Continuation verification:

- Backend compile: passed.
- Targeted backend payment/API suite: `16 passed, 0 failed`, with three
  existing dependency deprecation warnings.
- Mobile TypeScript: passed.
- Expo Doctor: `21/21 checks passed`.
- Android Metro export: passed; 1,266 modules bundled.
- Full backend regression: `110 passed, 0 failed`, with three existing
  dependency deprecation warnings and no skipped tests while the configured
  services were reachable.
- Read-only live checks: MongoDB `27018` is a writable `rs0` primary;
  Cassandra is `UN` on `127.0.0.1` via `nodetool status`; backend health,
  dependency health, and docs returned HTTP 200; a request carrying
  `Host: 10.165.59.245:8000` also returned HTTP 200. No service was started or
  stopped by this phase.
