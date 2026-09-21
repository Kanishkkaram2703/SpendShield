import { request } from './client';
import type { DemoBeneficiary, DemoBiller, DemoCard, DemoContact, DemoNotification } from '../types/demoModules';

export function listContacts(token: string, search?: string): Promise<{ contacts: DemoContact[] }> {
  return request(`/contacts${search ? `?search=${encodeURIComponent(search)}` : ''}`, { token });
}

export function listBeneficiaries(token: string, search?: string): Promise<{ beneficiaries: DemoBeneficiary[] }> {
  return request(`/beneficiaries${search ? `?search=${encodeURIComponent(search)}` : ''}`, { token });
}

export function listBillers(token: string): Promise<{ billers: DemoBiller[] }> {
  return request('/billers', { token });
}

export function listCards(token: string): Promise<{ cards: DemoCard[] }> {
  return request('/cards', { token });
}

export function createCard(token: string): Promise<DemoCard> {
  return request('/cards', { method: 'POST', token });
}

export function updateCardStatus(token: string, cardId: string, action: 'freeze' | 'unfreeze' | 'block', demo_mpin: string): Promise<DemoCard> {
  return request(`/cards/${encodeURIComponent(cardId)}/status`, { method: 'PATCH', token, body: { action, demo_mpin } });
}

export function updateCardPin(token: string, cardId: string, pin: string, confirm_pin: string, demo_mpin: string): Promise<DemoCard> {
  return request(`/cards/${encodeURIComponent(cardId)}/pin`, { method: 'PATCH', token, body: { pin, confirm_pin, demo_mpin } });
}

export function updateCardLimit(token: string, cardId: string, spending_limit: string, demo_mpin: string): Promise<DemoCard> {
  return request(`/cards/${encodeURIComponent(cardId)}/limit`, { method: 'PATCH', token, body: { spending_limit, demo_mpin } });
}

export function listNotifications(token: string, unreadOnly = false): Promise<{ notifications: DemoNotification[] }> {
  return request(`/notifications${unreadOnly ? '?unread_only=true' : ''}`, { token });
}

export function markNotificationRead(token: string, notificationId: string): Promise<DemoNotification> {
  return request(`/notifications/${encodeURIComponent(notificationId)}/read`, { method: 'PATCH', token });
}

export function markAllNotificationsRead(token: string): Promise<void> {
  return request('/notifications/read-all', { method: 'POST', token });
}

export function deleteNotification(token: string, notificationId: string): Promise<void> {
  return request(`/notifications/${encodeURIComponent(notificationId)}`, { method: 'DELETE', token });
}
