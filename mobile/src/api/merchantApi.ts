import { request } from './client';
import type { MerchantListResponse } from '../types/merchant';

export function listMerchants(token: string): Promise<MerchantListResponse> {
  return request<MerchantListResponse>('/merchants?limit=100', { token });
}
