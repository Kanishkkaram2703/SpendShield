import { useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { deleteNotification, listNotifications, markAllNotificationsRead, markNotificationRead } from '../api/demoModulesApi';
import { DashboardCard } from '../components/DashboardUI';
import { EmptyState, ErrorMessage } from '../components/Feedback';
import { PrimaryButton } from '../components/PrimaryButton';
import { Screen } from '../components/Screen';
import { useAuth } from '../services/AuthContext';
import { colors, spacing, typography } from '../theme';
import type { DemoNotification } from '../types/demoModules';
import type { RootStackParamList } from '../types/navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'Notifications'>;

export function NotificationsScreen({ navigation }: Props) {
  const { session } = useAuth();
  const [items, setItems] = useState<DemoNotification[]>([]);
  const [error, setError] = useState<string | null>(null);
  const load = async () => { if (!session?.accessToken) return; try { setItems((await listNotifications(session.accessToken)).notifications); } catch (cause) { setError(cause instanceof Error ? cause.message : 'Notifications could not be loaded.'); } };
  useEffect(() => { void load(); }, [session?.accessToken]);
  const readAll = async () => { if (!session?.accessToken) return; try { await markAllNotificationsRead(session.accessToken); setItems((current) => current.map((item) => ({ ...item, is_read: true }))); } catch (cause) { setError(cause instanceof Error ? cause.message : 'Notifications could not be updated.'); } };
  const read = async (item: DemoNotification) => { if (!session?.accessToken || item.is_read) return; try { await markNotificationRead(session.accessToken, item.notification_id); setItems((current) => current.map((entry) => entry.notification_id === item.notification_id ? { ...entry, is_read: true } : entry)); } catch (cause) { setError(cause instanceof Error ? cause.message : 'Notification could not be marked read.'); } };
  const remove = async (item: DemoNotification) => { if (!session?.accessToken) return; try { await deleteNotification(session.accessToken, item.notification_id); setItems((current) => current.filter((entry) => entry.notification_id !== item.notification_id)); } catch (cause) { setError(cause instanceof Error ? cause.message : 'Notification could not be deleted.'); } };
  return <Screen><View style={styles.content}><Text style={[typography.eyebrow, styles.eyebrow]}>Owner-scoped activity</Text><Text style={typography.title}>Notifications</Text>{error && <ErrorMessage message={error} />}{items.length > 0 && <PrimaryButton onPress={() => void readAll()} variant="secondary">Mark all as read</PrimaryButton>}{items.length === 0 ? <EmptyState title="No notifications" message="Successful operations will appear here." /> : items.map((item) => <Pressable accessibilityRole="button" key={item.notification_id} onPress={() => void read(item)}><DashboardCard style={[styles.item, !item.is_read && styles.unread]}><View style={styles.itemHeader}><Text style={[typography.caption, styles.category]}>{item.category}</Text><Text style={[typography.caption, styles.muted]}>{new Date(item.created_at).toLocaleString()}</Text></View><Text style={[typography.body, styles.value]}>{item.title}</Text><Text style={[typography.body, styles.muted]}>{item.message}</Text><PrimaryButton onPress={() => void remove(item)} variant="quiet">Clear</PrimaryButton></DashboardCard></Pressable>)}<PrimaryButton onPress={() => navigation.goBack()} variant="quiet">Back</PrimaryButton></View></Screen>;
}

const styles = StyleSheet.create({ content: { gap: spacing.lg }, eyebrow: { color: colors.primaryDark }, muted: { color: colors.textMuted }, value: { color: colors.navy, fontWeight: '800' }, category: { color: colors.primaryDark, fontWeight: '800' }, item: { gap: spacing.sm }, unread: { borderColor: colors.primary, borderWidth: 1 }, itemHeader: { flexDirection: 'row', justifyContent: 'space-between' } });
