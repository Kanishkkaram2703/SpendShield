# SpendShield Mobile

Initial Android mobile foundation for SpendShield using Expo, React Native,
TypeScript, and the existing FastAPI backend.

## Setup

From this directory:

```powershell
npm install
Copy-Item .env.example .env.local
npx expo start --lan
```

This workspace was tested with Node `v25.0.0`, npm, Expo SDK `57.0.22`, React
Native `0.86.3`, and TypeScript `6.0.3`. Use a Node version compatible with
the installed Expo SDK when reproducing the setup.

Start the backend separately from `backend/`:

```powershell
cd D:\E_Drive\Project\backend
\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API base URL

Set `EXPO_PUBLIC_API_BASE_URL` in `.env.local`. It is public configuration, not
a place for secrets.

- Android emulator: `http://10.0.2.2:8000/api/v1`
- Physical Android device: set `.env.local` to
  `http://10.165.59.245:8000/api/v1`, replacing `10.165.59.245` with the
  developer computer's current LAN IPv4 address when it changes.
- iOS simulator or web: `http://127.0.0.1:8000/api/v1` may work when the
  backend runs on the same computer.

`localhost` inside an Android emulator or on a physical device refers to the
device itself, not the development computer.

The backend's development allowlist is configured separately in
`backend/.env` using `SPENDSHIELD_ALLOWED_HOSTS`. Keep the current LAN host
in that list as well as in `mobile/.env.local`; do not use a public IP or a
wildcard in staging/production.

## Expo Go

Run `npx expo start --lan`, then open the project in Expo Go using the QR code
or development URL. The phone and developer computer must be on the same
Wi-Fi network. After changing `.env.local`, restart Expo with
`npx expo start --lan --clear` so the public environment value is reloaded.
A custom development build and production APK are not part of this phase.

## Implemented foundation

- Splash/loading, welcome, login, registration, account-aware dashboard,
  account details, contacts, phone payments, bills/recharges, profile,
  demo MPIN security, merchant QR display/scanning/payment, card management,
  notification center, More, and demo account-operation screens.
- Typed native-stack navigation with authenticated and unauthenticated
  branches.
- Centralized `fetch` API client with timeout, typed auth calls, safe API error
  parsing, and bearer-token support.
- Login and registration are connected to the real FastAPI endpoints.
- Access-token session data is stored with Expo SecureStore.
- Shared SpendShield theme, buttons, fields, feedback, and screen container.

## Current limitations

The mobile app uses simulation-only contracts. Protected admin data actions,
MPIN recovery/reset, saved-biller editing, and card-specific transaction
filtering remain partial. QR camera/image flows and safe-area rendering still
require Expo Go or physical Android verification. No real bank, card, UPI,
biller, or telecom service is connected.

## Verification

The current workspace passes TypeScript, Expo Doctor (`21/21`), and Android
Metro export (`1,262` modules). The repository has no mobile test or lint
script configured.

## Next mobile phase

Complete device-level navigation and permission verification, then implement
the remaining profile/security/admin demo surfaces without moving financial
authority into the client.
