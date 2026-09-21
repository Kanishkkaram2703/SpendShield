export type AccountStatus = 'ACTIVE' | 'SUSPENDED' | 'CLOSED';

/**
 * The server-owned current account snapshot returned by the account API.
 * Monetary values stay as the backend's decimal string; the mobile client
 * does not calculate or mutate the authoritative balance.
 */
export interface Account {
  account_id: string;
  currency: string;
  balance: string;
  status: AccountStatus;
  created_at: string;
  updated_at: string;
  version: number;
  holder_name?: string | null;
  demo_account_number?: string | null;
  demo_bank_code?: string | null;
  demo_branch?: string | null;
  account_type?: string | null;
}

export interface AccountReference {
  account_id: string;
  currency: string;
  status: Account['status'];
  account_type: string | null;
  demo_account_number: string | null;
}
