import { request } from './client';
import type {
  DemoPaymentResponse,
  DemoQrValidationResponse,
  PaymentHistoryResponse,
  PaymentResponse,
  TransactionChannel,
  TransactionStatus,
} from '../types/payment';

export interface CreatePaymentInput {
  account_id: string;
  amount: string;
  currency: string;
  merchant_id: string;
  transaction_channel: TransactionChannel;
  note?: string;
  demo_mpin?: string;
}

export interface SendMoneyInput {
  account_id: string;
  receiver_account_id: string;
  receiver_name: string;
  amount: string;
  currency: string;
  note?: string;
  demo_mpin?: string;
}

export interface QrPaymentInput {
  account_id: string;
  amount: string;
  currency: string;
  qr_payload: string;
  note?: string;
  demo_mpin?: string;
}

export interface ManualPaymentInput {
  account_id: string;
  amount: string;
  currency: string;
  merchant_id: string;
  merchant_name: string;
  note?: string;
  demo_mpin?: string;
}

export interface BankTransferInput {
  account_id: string;
  amount: string;
  currency: string;
  beneficiary_name: string;
  demo_bank_account_number: string;
  demo_bank_code: string;
  remarks?: string;
  demo_mpin?: string;
}

export interface SelfTransferInput {
  account_id: string;
  destination_account_id: string;
  amount: string;
  currency: string;
  note?: string;
  demo_mpin?: string;
}

export interface DemoAccountOperationInput {
  account_id: string;
  amount: string;
  currency: string;
  reason?: string;
  demo_mpin?: string;
}

export interface PhonePaymentInput {
  account_id: string;
  phone_number: string;
  amount: string;
  currency: string;
  note?: string;
  demo_mpin?: string;
}

export interface BillPaymentInput {
  account_id: string;
  category: string;
  provider: string;
  identifier: string;
  amount: string;
  currency: string;
  note?: string;
  demo_mpin?: string;
}

function createDemoRequest<T>(token: string, path: string, key: string, input: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    token,
    body: input,
    headers: { 'Idempotency-Key': key },
  });
}

export function sendMoney(token: string, idempotencyKey: string, input: SendMoneyInput): Promise<DemoPaymentResponse> {
  return createDemoRequest<DemoPaymentResponse>(token, '/payments/send', idempotencyKey, input);
}

export function payByQr(token: string, idempotencyKey: string, input: QrPaymentInput): Promise<DemoPaymentResponse> {
  return createDemoRequest<DemoPaymentResponse>(token, '/payments/qr', idempotencyKey, input);
}

export function payManually(token: string, idempotencyKey: string, input: ManualPaymentInput): Promise<DemoPaymentResponse> {
  return createDemoRequest<DemoPaymentResponse>(token, '/payments/manual', idempotencyKey, input);
}

export function bankTransfer(token: string, idempotencyKey: string, input: BankTransferInput): Promise<DemoPaymentResponse> {
  return createDemoRequest<DemoPaymentResponse>(token, '/payments/bank-transfer', idempotencyKey, input);
}

export function selfTransfer(token: string, idempotencyKey: string, input: SelfTransferInput): Promise<DemoPaymentResponse> {
  return createDemoRequest<DemoPaymentResponse>(token, '/payments/self-transfer', idempotencyKey, input);
}

export function demoDeposit(token: string, idempotencyKey: string, input: DemoAccountOperationInput): Promise<DemoPaymentResponse> {
  return createDemoRequest<DemoPaymentResponse>(token, '/payments/deposit', idempotencyKey, input);
}

export function demoWithdrawal(token: string, idempotencyKey: string, input: DemoAccountOperationInput): Promise<DemoPaymentResponse> {
  return createDemoRequest<DemoPaymentResponse>(token, '/payments/withdraw', idempotencyKey, input);
}

export function phonePayment(token: string, idempotencyKey: string, input: PhonePaymentInput): Promise<DemoPaymentResponse> {
  return createDemoRequest<DemoPaymentResponse>(token, '/payments/phone', idempotencyKey, input);
}

export function billPayment(token: string, idempotencyKey: string, input: BillPaymentInput): Promise<DemoPaymentResponse> {
  return createDemoRequest<DemoPaymentResponse>(token, '/payments/bill', idempotencyKey, input);
}

export function validateQrPayload(token: string, qrPayload: string): Promise<DemoQrValidationResponse> {
  return request<DemoQrValidationResponse>('/payments/qr/validate', {
    method: 'POST',
    token,
    body: { qr_payload: qrPayload },
  });
}

export function createPayment(
  token: string,
  idempotencyKey: string,
  input: CreatePaymentInput,
): Promise<PaymentResponse> {
  return request<PaymentResponse>('/payments', {
    method: 'POST',
    token,
    body: input,
    headers: { 'Idempotency-Key': idempotencyKey },
  });
}

export function listPayments(
  token: string,
  options: { cursor?: string; status?: TransactionStatus } = {},
): Promise<PaymentHistoryResponse> {
  const query = new URLSearchParams({ limit: '50' });
  if (options.cursor) query.set('cursor', options.cursor);
  if (options.status) query.set('status', options.status);
  return request<PaymentHistoryResponse>(`/payments?${query.toString()}`, { token });
}

export function getPayment(token: string, transactionId: string): Promise<PaymentResponse> {
  return request<PaymentResponse>(`/payments/${encodeURIComponent(transactionId)}`, { token });
}
