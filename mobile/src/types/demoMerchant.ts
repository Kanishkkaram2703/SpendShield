export interface DemoMerchant {
  merchant_id: string;
  merchant_name: string;
  category: string;
  demo_bank: string;
  merchant_account_id: string;
  status: 'ACTIVE' | 'INACTIVE';
  qr_payload: string;
  created_at: string;
  updated_at: string;
}

