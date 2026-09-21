import type { DemoPaymentResponse } from './payment';

export interface RechargePlan {
  plan_id: string;
  operator: string;
  plan_name: string;
  validity_days: number;
  data_allowance: string;
  calling_benefit: string;
  sms_benefit: string;
  price: string;
  demo_only: true;
}

export interface RechargeCatalogResponse {
  operators: string[];
  plans: RechargePlan[];
  request_id: string;
}

export interface RechargeResponse {
  operator: string;
  mobile_number_masked: string;
  plan: RechargePlan;
  payment: DemoPaymentResponse;
  demo_only: true;
}

export interface SubscriptionPlan {
  plan_id: string;
  platform_id: string;
  plan_name: string;
  period: string;
  duration_days: number;
  price: string;
  demo_only: true;
}

export interface SubscriptionPlatform {
  platform_id: string;
  platform_name: string;
  description: string;
  plans: SubscriptionPlan[];
  demo_only: true;
}

export interface SubscriptionCatalogResponse {
  platforms: SubscriptionPlatform[];
  request_id: string;
}

export interface Subscription {
  subscription_id: string;
  platform_id: string;
  platform_name: string;
  plan_id: string;
  plan_name: string;
  period: string;
  price: string;
  currency: string;
  status: 'ACTIVE' | 'PAUSED' | 'CANCELLED';
  next_billing_date: string;
  source_transaction_id: string | null;
  created_at: string;
  updated_at: string;
  demo_only: true;
}

export interface SubscriptionListResponse {
  subscriptions: Subscription[];
  request_id: string;
}
