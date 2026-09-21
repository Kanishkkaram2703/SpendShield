export type UserRole = 'USER' | 'INVESTIGATOR' | 'MERCHANT' | 'ADMIN';

export interface User {
  user_id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  display_name?: string | null;
  phone_number?: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: 'bearer';
  expires_in: number;
  user: User;
}

export interface AuthSession {
  accessToken: string;
  tokenType: 'bearer';
  expiresIn: number;
  user: User;
}
