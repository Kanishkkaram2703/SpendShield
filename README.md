# SpendShield

SpendShield is a fictional, educational financial-awareness and digital-
forensics platform. The current repository contains a FastAPI backend and an
Expo mobile client.

## Current demo capabilities

- MongoDB `127.0.0.1:27018` / replica set `rs0` owns current operational state.
- Cassandra `127.0.0.1:9042` owns historical event data.
- Account, deposit, withdrawal, transfer, phone, bill, card, notification,
  profile, and demo merchant QR flows are simulation-only.
- QR payments use the persisted fictional merchants `MODI-CHAI-001` and
  `MELONI-CHOCO-002`, a versioned payload, server-side validation, and a
  hashed demo MPIN.

## Start and verify

Use the manual Windows/WSL commands in [Start.txt](Start.txt). Tooling does
not start or stop MongoDB, Cassandra, the backend, or Expo automatically.

## Verification status

Latest offline verification: backend `76 passed, 27 skipped, 0 failed`, mobile
TypeScript passed, Expo Doctor `21/21`, and Android Metro export passed with
1,262 modules. The skipped tests require the manually started MongoDB and
Cassandra services. No real payment or banking integration is present.
