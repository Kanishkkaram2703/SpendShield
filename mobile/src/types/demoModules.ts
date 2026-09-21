export interface DemoContact {
  contact_id: string;
  name: string;
  phone: string;
  email: string | null;
  favorite: boolean;
  contact_type: 'PERSON' | 'BUSINESS';
  created_at: string;
  updated_at: string;
}

export interface DemoBeneficiary {
  beneficiary_id: string;
  name: string;
  account_number: string;
  bank_name: string;
  bank_code: string;
  note: string | null;
  favorite: boolean;
  created_at: string;
  updated_at: string;
}

export interface DemoBiller {
  biller_id: string;
  category: string;
  provider: string;
  identifier: string;
  nickname: string | null;
  created_at: string;
  updated_at: string;
}

export interface DemoCard {
  card_id: string;
  holder_name: string;
  masked_card_number: string;
  expiry: string;
  masked_cvv: string;
  status: 'ACTIVE' | 'FROZEN' | 'BLOCKED';
  spending_limit: string;
  currency: string;
  created_at: string;
  updated_at: string;
}

export interface DemoNotification {
  notification_id: string;
  category: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
}
