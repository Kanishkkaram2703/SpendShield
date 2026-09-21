import { request } from './client';
import type { DemoMerchant } from '../types/demoMerchant';

export function listDemoMerchants(token: string): Promise<{ merchants: DemoMerchant[]; request_id: string }> {
  return request('/demo-merchants', { token });
}

export function getDemoMerchant(token: string, merchantId: string): Promise<DemoMerchant> {
  return request(`/demo-merchants/${encodeURIComponent(merchantId)}`, { token });
}

