import { ApiError, request } from './client';
import type { Account, AccountReference, AccountStatus } from '../types/account';

const ACCOUNT_STATUSES: ReadonlySet<AccountStatus> = new Set([
  'ACTIVE',
  'SUSPENDED',
  'CLOSED',
]);

export function getMyAccount(token: string): Promise<Account> {
  return request<unknown>('/accounts/me', { token }).then(parseAccount);
}

/**
 * Creates the authenticated user's first account. The backend owns the
 * account owner, currency, opening balance, and status, so this request has
 * intentionally no body.
 */
export function createAccount(token: string): Promise<Account> {
  return request<unknown>('/accounts', {
    method: 'POST',
    token,
  }).then(parseAccount);
}

export function listAccounts(token: string): Promise<Account[]> {
  return request<unknown>('/accounts', { token }).then((payload) => {
    if (!isRecord(payload) || !Array.isArray(payload.accounts)) {
      throw invalidAccountResponse();
    }
    return payload.accounts.map(parseAccount);
  });
}

export function listAccountReferences(token: string): Promise<AccountReference[]> {
  return request<unknown>('/accounts/me/references', { token }).then((payload) => {
    if (!isRecord(payload) || !Array.isArray(payload.accounts)) {
      throw new ApiError('The backend returned an unexpected account reference response.', 502, 'invalid_account_response');
    }
    return payload.accounts as AccountReference[];
  });
}

export function unlockAccountDetails(token: string, accountId: string, demo_mpin: string): Promise<Account> {
  return request<unknown>(`/accounts/${encodeURIComponent(accountId)}/protected`, {
    method: 'POST',
    token,
    body: { demo_mpin },
  }).then(parseAccount);
}

export function createAdditionalAccount(token: string, accountType = 'DEMO_SAVINGS'): Promise<Account> {
  return request<unknown>('/accounts', {
    method: 'POST', token, body: { account_type: accountType },
  }).then(parseAccount);
}

function parseAccount(payload: unknown): Account {
  if (!isRecord(payload)) {
    throw invalidAccountResponse();
  }

  const status = payload.status;
  if (
    typeof payload.account_id !== 'string' ||
    typeof payload.currency !== 'string' ||
    typeof payload.balance !== 'string' ||
    typeof status !== 'string' ||
    !ACCOUNT_STATUSES.has(status as AccountStatus) ||
    typeof payload.created_at !== 'string' ||
    typeof payload.updated_at !== 'string' ||
    typeof payload.version !== 'number'
  ) {
    throw invalidAccountResponse();
  }

  return payload as unknown as Account;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function invalidAccountResponse(): ApiError {
  return new ApiError(
    'The backend returned an unexpected account response.',
    502,
    'invalid_account_response',
  );
}
