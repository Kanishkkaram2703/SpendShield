import { request } from './client';
import type {
  RechargeCatalogResponse,
  RechargeResponse,
  Subscription,
  SubscriptionCatalogResponse,
  SubscriptionListResponse,
} from '../types/demoLifestyle';

export function listRechargeCatalog(token: string, operator?: string): Promise<RechargeCatalogResponse> {
  const query = operator ? `?operator=${encodeURIComponent(operator)}` : '';
  return request<RechargeCatalogResponse>(`/recharge/operators${query}`, { token });
}

export function recharge(token: string, idempotencyKey: string, input: {
  account_id: string;
  operator: string;
  plan_id: string;
  mobile_number: string;
  currency: string;
  demo_mpin: string;
  note?: string;
}): Promise<RechargeResponse> {
  return request<RechargeResponse>('/recharge', { method: 'POST', token, body: input, headers: { 'Idempotency-Key': idempotencyKey } });
}

export function listSubscriptionCatalog(token: string): Promise<SubscriptionCatalogResponse> {
  return request<SubscriptionCatalogResponse>('/subscriptions/platforms', { token });
}

export function listSubscriptions(token: string): Promise<SubscriptionListResponse> {
  return request<SubscriptionListResponse>('/subscriptions', { token });
}

export function createSubscription(token: string, idempotencyKey: string, input: {
  account_id: string;
  platform_id: string;
  plan_id: string;
  currency: string;
  demo_mpin: string;
}): Promise<Subscription> {
  return request<Subscription>('/subscriptions', { method: 'POST', token, body: input, headers: { 'Idempotency-Key': idempotencyKey } });
}

export function updateSubscriptionStatus(token: string, subscriptionId: string, status: 'PAUSED' | 'CANCELLED'): Promise<Subscription> {
  return request<Subscription>(`/subscriptions/${encodeURIComponent(subscriptionId)}/status`, { method: 'PATCH', token, body: { status } });
}
