export interface Merchant {
  merchant_id: string;
  merchant_name: string;
  status: 'ACTIVE' | 'INACTIVE' | 'SUSPENDED';
  category: {
    category_id: string;
    category_name: string;
    subcategory_id: string;
    subcategory_name: string;
    is_active: boolean;
  };
  version: number;
  created_at: string;
  updated_at: string;
}

export interface MerchantListResponse {
  success: true;
  merchants: Merchant[];
  next_cursor: string | null;
  request_id: string;
}
