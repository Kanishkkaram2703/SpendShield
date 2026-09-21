import { request } from './client';
import type { DemoSecurityStatus } from '../types/demoSecurity';

export function getDemoSecurityStatus(token: string): Promise<DemoSecurityStatus> {
  return request('/demo-security', { token });
}

export function setDemoMpin(token: string, input: { pin: string; confirm_pin: string; current_pin?: string }): Promise<DemoSecurityStatus> {
  return request('/demo-security/mpin', { method: 'PUT', token, body: input });
}

export function resetDemoMpin(token: string, password: string): Promise<DemoSecurityStatus> {
  return request('/demo-security/mpin/reset', { method: 'POST', token, body: { password } });
}
