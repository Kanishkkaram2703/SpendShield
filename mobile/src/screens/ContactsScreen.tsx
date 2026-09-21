import { useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { ApiError } from '../api/client';
import { listContacts } from '../api/demoModulesApi';
import { DashboardCard, IconGlyph } from '../components/DashboardUI';
import { EmptyState, ErrorMessage } from '../components/Feedback';
import { PrimaryButton } from '../components/PrimaryButton';
import { Screen } from '../components/Screen';
import { TextField } from '../components/TextField';
import { useAuth } from '../services/AuthContext';
import { colors, radii, spacing, typography } from '../theme';
import type { DemoContact } from '../types/demoModules';
import type { RootStackParamList } from '../types/navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'Contacts'>;

export function ContactsScreen({ navigation }: Props) {
  const { session } = useAuth();
  const [contacts, setContacts] = useState<DemoContact[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    if (!session?.accessToken) return;
    setLoading(true); setError(null);
    try { setContacts((await listContacts(session.accessToken, search)).contacts); }
    catch (cause) { setError(cause instanceof ApiError ? cause.message : 'Contacts could not be loaded.'); }
    finally { setLoading(false); }
  };
  useEffect(() => { void load(); }, [session?.accessToken]);

  return <Screen><View style={styles.content}><View><Text style={[typography.eyebrow, styles.eyebrow]}>Contacts</Text><Text style={typography.title}>Pay a contact</Text><Text style={[typography.body, styles.muted]}>Select a fictional contact. Bank fields are intentionally not part of this flow.</Text></View><TextField label="Search contacts" onChangeText={setSearch} onSubmitEditing={() => void load()} placeholder="Name or phone" value={search} />{error && <><ErrorMessage message={error} /><PrimaryButton onPress={() => void load()}>Try again</PrimaryButton></>}{!loading && !error && contacts.length === 0 && <EmptyState title="No contacts yet" message="Create or seed a contact in the backend before using contact payments." />}{loading && <DashboardCard><Text style={[typography.body, styles.muted]}>Loading contacts…</Text></DashboardCard>}{contacts.map((contact) => <Pressable key={contact.contact_id} accessibilityLabel={`Pay ${contact.name}`} accessibilityRole="button" onPress={() => navigation.navigate('PhonePayment', { phoneNumber: contact.phone })}><DashboardCard style={styles.contactCard}><View style={styles.avatar}><Text style={styles.avatarText}>{contact.name.charAt(0).toUpperCase()}</Text></View><View style={styles.copy}><Text style={[typography.body, styles.name]}>{contact.name}</Text><Text style={[typography.caption, styles.muted]}>{contact.phone} · {contact.contact_type === 'BUSINESS' ? 'Business' : 'Contact'}</Text></View><IconGlyph color={colors.primaryDark} name="send" size={22} /></DashboardCard></Pressable>)}<PrimaryButton onPress={() => navigation.goBack()} variant="quiet">Back</PrimaryButton></View></Screen>;
}

const styles = StyleSheet.create({ content: { gap: spacing.lg }, eyebrow: { color: colors.primaryDark }, muted: { color: colors.textMuted }, contactCard: { alignItems: 'center', flexDirection: 'row', gap: spacing.md, padding: spacing.md }, avatar: { alignItems: 'center', backgroundColor: colors.primarySoft, borderRadius: 24, height: 48, justifyContent: 'center', width: 48 }, avatarText: { color: colors.primaryDark, fontSize: 20, fontWeight: '800' }, copy: { flex: 1, gap: spacing.xs }, name: { color: colors.navy, fontWeight: '800' } });
