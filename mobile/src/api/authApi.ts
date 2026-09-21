import { request } from './client';
import type { AuthResponse, User } from '../types/auth';

export function login(email: string, password: string): Promise<AuthResponse> {
  return request<AuthResponse>('/auth/login', {
    method: 'POST',
    body: { email, password },
  });
}

export function register(email: string, password: string): Promise<User> {
  return request<User>('/auth/register', {
    method: 'POST',
    body: { email, password },
  });
}

export function getCurrentUser(token: string): Promise<User> {
  return request<User>('/auth/me', {
    method: 'GET',
    token,
  });
}

export function updateCurrentUser(token: string, input: { email?: string; display_name?: string; phone_number?: string }): Promise<User> {
  return request<User>('/auth/me', { method: 'PATCH', token, body: input });
}
