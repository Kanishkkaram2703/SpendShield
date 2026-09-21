import { useCallback, useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { ApiError } from '../api/client';
import { createAdditionalAccount, listAccountReferences, unlockAccountDetails } from '../api/accountApi';
import { DashboardCard, IconGlyph, StatusBadge } from '../components/DashboardUI';
import { DemoMpinPanel } from '../components/DemoControls';
import { EmptyState, ErrorMessage } from '../components/Feedback';
import { PrimaryButton } from '../components/PrimaryButton';
import { Screen } from '../components/Screen';
import { useAuth } from '../services/AuthContext';
import { colors, radii, spacing, typography } from '../theme';
import type { Account, AccountReference } from '../types/account';
import type { RootStackParamList } from '../types/navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'AccountDetails'>;

export function AccountDetailsScreen({ navigation, route }: Props) {
  const { session } = useAuth();
  const [references, setReferences] = useState<AccountReference[]>([]);
  const [selectedId, setSelectedId] = useState(route.params?.accountId || '');
  const [account, setAccount] = useState<Account | null>(null);
  const [mpin, setMpin] = useState('');
  const [loading, setLoading] = useState(true);
  const [unlocking, setUnlocking] = useState(false);
  const [isBalanceVisible, setIsBalanceVisible] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadReferences = useCallback(async () => {
    if (!session?.accessToken) { setError('Your session is unavailable. Please sign in again.'); setLoading(false); return; }
    setLoading(true); setError(null);
    try {
      const result = await listAccountReferences(session.accessToken);
      setReferences(result);
      if (!selectedId && result[0]) setSelectedId(result[0].account_id);
    } catch (cause) { setError(getErrorMessage(cause)); }
    finally { setLoading(false); }
  }, [selectedId, session?.accessToken]);
  useEffect(() => { void loadReferences(); }, [loadReferences]);

  const unlock = async () => {
    if (!session?.accessToken || !selectedId || mpin.length !== 6) return;
    setUnlocking(true); setError(null);
    try { setAccount(await unlockAccountDetails(session.accessToken, selectedId, mpin)); setMpin(''); setIsBalanceVisible(true); }
    catch (cause) { setError(getErrorMessage(cause)); setAccount(null); setIsBalanceVisible(false); }
    finally { setUnlocking(false); }
  };

  const createAnother = async () => {
    if (!session?.accessToken) return;
    try { const created = await createAdditionalAccount(session.accessToken); setReferences((current) => [...current, { account_id: created.account_id, currency: created.currency, status: created.status, account_type: created.account_type || null, demo_account_number: created.demo_account_number || null }]); setSelectedId(created.account_id); setAccount(null); }
    catch (cause) { setError(getErrorMessage(cause)); }
  };

  return <Screen><View style={styles.content}><View style={styles.heading}><Text style={[typography.eyebrow, styles.eyebrow]}>Protected account view</Text><Text style={[typography.title, styles.title]}>Account details</Text><Text style={[typography.body, styles.subtitle]}>Account references are shown without balances. Enter the six-digit MPIN before sensitive account data is returned.</Text></View>{loading && <DashboardCard><Text style={[typography.body, styles.subtitle]}>Loading safe account references…</Text></DashboardCard>}{error && <ErrorMessage message={error} />}{!loading && !references.length && <EmptyState title="No accounts" message="Create a fictional account from the dashboard first." />}{references.length > 0 && <DashboardCard><Text style={[typography.sectionTitle, styles.cardTitle]}>Choose an account</Text>{references.map((item) => <Pressable accessibilityRole="radio" accessibilityState={{ selected: item.account_id === selectedId }} key={item.account_id} onPress={() => { setSelectedId(item.account_id); setAccount(null); setIsBalanceVisible(false); }} style={[styles.accountPicker, item.account_id === selectedId && styles.accountSelected]}><IconGlyph color={item.account_id === selectedId ? colors.primaryDark : colors.textMuted} name="account" size={20} /><View style={styles.pickerCopy}><Text style={[typography.body, styles.value]}>{item.account_type || 'Savings account'}</Text><Text style={[typography.caption, styles.subtitle]}>{item.currency} · {item.status} · •••• {item.account_id.slice(-4)}</Text></View></Pressable>)}</DashboardCard>}{selectedId && !account && <><DemoMpinPanel onChange={setMpin} value={mpin} /><PrimaryButton disabled={mpin.length !== 6 || unlocking} loading={unlocking} onPress={() => void unlock()}>Unlock account details</PrimaryButton></>}{account && <View style={styles.stack}><DashboardCard><View style={styles.cardHeader}><View style={styles.iconCircle}><IconGlyph color={colors.primaryDark} name="shield" size={24} /></View><StatusBadge status={account.status} /></View><Detail label="Bank profile" value={account.account_type || 'SAVINGS'} /><Detail label="Currency" value={account.currency} /><Detail label="Account holder" value={account.holder_name || 'Account holder'} /><Detail label="Masked account" value={account.demo_account_number ? `•••• ${account.demo_account_number.slice(-4)}` : 'Not available'} /><Detail label="Bank code" value={account.demo_bank_code || 'Not available'} /><Detail label="Branch" value={account.demo_branch || 'Not available'} /><Detail label="Account reference" value={`•••• ${account.account_id.slice(-4)}`} /><Detail label="Created" value={formatDate(account.created_at)} /><Detail label="Server version" value={String(account.version)} /></DashboardCard><DashboardCard><Text style={[typography.sectionTitle, styles.cardTitle]}>Available balance</Text><Text style={[typography.caption, styles.privateHint]}>Returned only after successful MPIN verification.</Text><Text style={[typography.metric, styles.balance]}>{isBalanceVisible ? `${account.balance} ${account.currency}` : '••••••••'}</Text><Pressable accessibilityRole="button" onPress={() => setIsBalanceVisible((visible) => !visible)} style={styles.toggle}><Text style={[typography.caption, styles.toggleText]}>{isBalanceVisible ? 'Hide balance' : 'Show balance'}</Text></Pressable></DashboardCard><View style={styles.operationRow}><PrimaryButton onPress={() => navigation.navigate('AccountOperation', { operation: 'deposit' })} variant="secondary">Deposit</PrimaryButton><PrimaryButton onPress={() => navigation.navigate('AccountOperation', { operation: 'withdrawal' })} variant="secondary">Withdraw</PrimaryButton></View></View>}{references.length > 0 && <PrimaryButton onPress={() => void createAnother()} variant="secondary">Create another account</PrimaryButton>}<PrimaryButton onPress={() => navigation.goBack()} variant="quiet">Back</PrimaryButton></View></Screen>;
}

function Detail({ label, value }: { label: string; value: string }) { return <View style={styles.detail}><Text style={[typography.caption, styles.label]}>{label}</Text><Text style={[typography.body, styles.value]}>{value}</Text></View>; }
function formatDate(value: string): string { const date = new Date(value); return Number.isNaN(date.getTime()) ? 'Not available' : date.toLocaleString(); }
function getErrorMessage(error: unknown): string { if (error instanceof ApiError) return error.message; return 'Account details could not be loaded. Please try again.'; }

const styles = StyleSheet.create({ content: { gap: spacing.lg }, heading: { gap: spacing.sm, paddingVertical: spacing.md }, eyebrow: { color: colors.primaryDark }, title: { color: colors.navy }, subtitle: { color: colors.textMuted }, stack: { gap: spacing.md }, cardHeader: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' }, iconCircle: { alignItems: 'center', backgroundColor: colors.primarySoft, borderRadius: radii.md, height: 48, justifyContent: 'center', width: 48 }, cardTitle: { color: colors.navy }, detail: { borderBottomColor: colors.border, borderBottomWidth: 1, gap: spacing.xs, paddingVertical: spacing.sm }, label: { color: colors.textMuted }, value: { color: colors.navy, fontWeight: '700' }, privateHint: { color: colors.textMuted }, balance: { color: colors.navy, marginVertical: spacing.md }, toggle: { alignSelf: 'flex-start', backgroundColor: colors.primarySoft, borderRadius: radii.sm, paddingHorizontal: spacing.md, paddingVertical: spacing.sm }, toggleText: { color: colors.primaryDark, fontWeight: '800' }, accountPicker: { alignItems: 'center', borderBottomColor: colors.border, borderBottomWidth: 1, flexDirection: 'row', gap: spacing.md, paddingVertical: spacing.sm }, accountSelected: { backgroundColor: colors.primarySoft }, pickerCopy: { flex: 1, gap: spacing.xs }, operationRow: { flexDirection: 'row', gap: spacing.sm } });
