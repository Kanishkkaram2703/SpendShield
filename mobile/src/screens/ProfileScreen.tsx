import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { updateCurrentUser } from '../api/authApi';
import { DashboardCard } from '../components/DashboardUI';
import { ErrorMessage } from '../components/Feedback';
import { PrimaryButton } from '../components/PrimaryButton';
import { Screen } from '../components/Screen';
import { TextField } from '../components/TextField';
import { useAuth } from '../services/AuthContext';
import { colors, spacing, typography } from '../theme';
import type { RootStackParamList } from '../types/navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'Profile'>;

export function ProfileScreen({ navigation }: Props) {
  const { session, signOut } = useAuth();
  const user = session?.user;
  const [name, setName] = useState(user?.display_name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [phone, setPhone] = useState(user?.phone_number || '');
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    if (!session?.accessToken || !email.trim() || !email.includes('@')) { setError('Enter a valid email address.'); return; }
    if (phone.trim() && !/^[+0-9() -]{7,32}$/.test(phone.trim())) { setError('Enter a valid phone number.'); return; }
    setSaving(true); setError(null); setMessage(null);
    try {
      const updated = await updateCurrentUser(session.accessToken, { email: email.trim().toLowerCase(), ...(name.trim() ? { display_name: name.trim() } : {}), ...(phone.trim() ? { phone_number: phone.trim() } : {}) });
      session.user = updated;
      setName(updated.display_name || ''); setEmail(updated.email); setPhone(updated.phone_number || ''); setMessage('Profile saved.');
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Profile could not be saved.'); }
    finally { setSaving(false); }
  };

  return <Screen><View style={styles.content}><Text style={[typography.eyebrow, styles.eyebrow]}>Account identity</Text><Text style={typography.title}>Profile</Text><Text style={[typography.body, styles.muted]}>Fictional account information only. No banking credentials are collected.</Text>{error && <ErrorMessage message={error} />}{message && <DashboardCard><Text style={[typography.body, styles.success]}>{message}</Text></DashboardCard>}<DashboardCard><View style={styles.avatar}><Text style={styles.avatarText}>{(name || email || 'S').slice(0, 1).toUpperCase()}</Text></View><TextField label="Name" maxLength={128} onChangeText={setName} placeholder="Your name" value={name} /><TextField autoCapitalize="none" autoCorrect={false} keyboardType="email-address" label="Email" onChangeText={setEmail} value={email} /><TextField keyboardType="phone-pad" label="Phone number" maxLength={32} onChangeText={setPhone} placeholder="Optional phone" value={phone} /><PrimaryButton loading={saving} onPress={() => void save()}>Save profile</PrimaryButton></DashboardCard><PrimaryButton onPress={() => void signOut()} variant="secondary">Sign out</PrimaryButton><PrimaryButton onPress={() => navigation.goBack()} variant="quiet">Cancel</PrimaryButton></View></Screen>;
}

const styles = StyleSheet.create({ content: { gap: spacing.lg }, eyebrow: { color: colors.primaryDark }, muted: { color: colors.textMuted }, success: { color: colors.success, fontWeight: '700' }, avatar: { alignItems: 'center', alignSelf: 'center', backgroundColor: colors.primarySoft, borderRadius: 36, height: 72, justifyContent: 'center', width: 72 }, avatarText: { color: colors.primaryDark, fontSize: 30, fontWeight: '800' } });
