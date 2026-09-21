import type { ApiError } from '../api/client';

export const MAX_DEMO_TRANSACTION_AMOUNT = 1000000;

export interface DemoQrPayload {
  type: 'demo_merchant' | 'spendshield_demo_merchant';
  version?: number;
  qr_type?: 'SPENDSHIELD_DEMO_MERCHANT';
  simulation_only?: true;
  merchantId: string;
  merchantName: string;
  category?: string;
  demoBank?: string;
  merchantAccountId?: string;
  bank: 'BJP Bank';
  mode: 'simulation';
  status?: 'ACTIVE' | 'INACTIVE';
}

export function validateAmount(value: string): string | null {
  const normalized = value.trim();
  if (!/^\d+(\.\d{1,2})?$/.test(normalized)) {
    return 'Enter a positive amount with no more than two decimal places.';
  }
  const amount = Number(normalized);
  if (!Number.isFinite(amount) || amount <= 0) return 'Enter an amount greater than zero.';
  if (amount > MAX_DEMO_TRANSACTION_AMOUNT) return 'The limit for one transaction is ₹10,00,000.';
  return null;
}

export function validateNote(value: string): string | null {
  return value.trim().length > 256 ? 'The note cannot exceed 256 characters.' : null;
}

export function parseDemoQrPayload(value: string): DemoQrPayload | null {
  try {
    const parsed = JSON.parse(value) as Partial<DemoQrPayload> & Record<string, unknown>;
    if (parsed.type === 'spendshield_demo_merchant') {
      if (parsed.version !== 1 || parsed.qr_type !== 'SPENDSHIELD_DEMO_MERCHANT' || parsed.simulation_only !== true || !parsed.merchant_id || !parsed.merchant_name || !parsed.category || !parsed.demo_bank || !parsed.merchant_account_id || parsed.status !== 'ACTIVE') return null;
      return {
        type: 'spendshield_demo_merchant',
        version: 1,
        qr_type: 'SPENDSHIELD_DEMO_MERCHANT',
        simulation_only: true,
        merchantId: String(parsed.merchant_id),
        merchantName: String(parsed.merchant_name),
        category: String(parsed.category),
        demoBank: String(parsed.demo_bank),
        merchantAccountId: String(parsed.merchant_account_id),
        bank: 'BJP Bank',
        mode: 'simulation',
        status: 'ACTIVE',
      };
    }
    if (parsed.type !== 'demo_merchant' || !parsed.merchantId || !parsed.merchantName || parsed.bank !== 'BJP Bank' || parsed.mode !== 'simulation') return null;
    return parsed as DemoQrPayload;
  } catch {
    return null;
  }
}

export function getDemoPaymentError(error: unknown): string {
  const apiError = error as Partial<ApiError>;
  if (typeof apiError?.message === 'string' && apiError.message) {
    return apiError.message.replace(/\bdemo\b/gi, 'fictional');
  }
  return 'The payment could not be completed. Please try again.';
}

export function createDemoIdempotencyKey(flow: string): string {
  return `mobile-${flow}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}
