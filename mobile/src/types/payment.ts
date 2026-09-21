export type TransactionChannel =
  | 'QR_SIMULATED'
  | 'CARD_SIMULATED'
  | 'WALLET_SIMULATED'
  | 'BANK_SIMULATED';

export type TransactionStatus =
  | 'INITIATED'
  | 'AUTHORIZED'
  | 'PROCESSING'
  | 'COMPLETED'
  | 'REJECTED'
  | 'FAILED'
  | 'REVERSED';

export type TransactionType =
  | 'MERCHANT_PAYMENT'
  | 'SEND_MONEY'
  | 'SEND_MONEY_CREDIT'
  | 'QR_PAYMENT'
  | 'MANUAL_PAYMENT'
  | 'BANK_TRANSFER_DEMO'
  | 'SELF_TRANSFER_DEBIT'
  | 'SELF_TRANSFER_CREDIT'
  | 'DEMO_DEPOSIT'
  | 'DEMO_WITHDRAWAL'
  | 'MOBILE_RECHARGE_DEMO'
  | 'ELECTRICITY_BILL_DEMO'
  | 'WATER_BILL_DEMO'
  | 'GAS_BILL_DEMO'
  | 'INTERNET_BILL_DEMO'
  | 'DTH_RECHARGE_DEMO'
  | 'POSTPAID_BILL_DEMO'
  | 'LOAN_EMI_DEMO'
  | 'SUBSCRIPTION_PAYMENT_DEMO';

export type TransactionDirection = 'DEBIT' | 'CREDIT';

export interface PaymentTransaction {
  transaction_id: string;
  account_id: string;
  amount: string;
  currency: string;
  transaction_channel: TransactionChannel | null;
  transaction_type: TransactionType;
  direction: TransactionDirection;
  note: string | null;
  merchant_id: string | null;
  merchant_name: string | null;
  category_id: string | null;
  category_name: string | null;
  subcategory_id: string | null;
  subcategory_name: string | null;
  counterparty_account_id: string | null;
  counterparty_name: string | null;
  beneficiary_name: string | null;
  demo_bank_account_number: string | null;
  demo_bank_code: string | null;
  transfer_reference: string | null;
  demo_mode: boolean;
  status: TransactionStatus;
  status_history: TransactionStatus[];
  failure_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaymentResponse {
  success: true;
  transaction: PaymentTransaction;
  request_id: string;
}

export interface PaymentHistoryResponse {
  success: true;
  transactions: PaymentTransaction[];
  next_cursor: string | null;
  request_id: string;
}

export interface DemoPaymentResponse {
  success: boolean;
  demo_mode: true;
  transaction: PaymentTransaction;
  related_transaction_ids: string[];
  transfer_reference: string | null;
  previous_balance: string | null;
  paid_amount: string | null;
  remaining_balance: string | null;
  merchant: {
    merchant_id?: string;
    merchant_name?: string;
    category?: string;
    demo_bank?: string;
    merchant_account_id?: string;
  } | null;
  request_id: string;
}

export interface DemoQrValidationResponse {
  valid: true;
  demo_mode: true;
  merchant_id: string;
  merchant_name: string;
  bank: string;
  mode: 'simulation';
  version: number;
  category: string | null;
  demo_bank: string | null;
  merchant_account_id: string | null;
  qr_payload: string | null;
  request_id: string;
}
