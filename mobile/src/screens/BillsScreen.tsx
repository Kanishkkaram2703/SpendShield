import { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { getMyAccount } from '../api/accountApi';
import { billPayment } from '../api/paymentApi';
import { DashboardCard } from '../components/DashboardUI';
import { DemoMpinPanel } from '../components/DemoControls';
import { ErrorMessage } from '../components/Feedback';
import { PrimaryButton } from '../components/PrimaryButton';
import { Screen } from '../components/Screen';
import { TextField } from '../components/TextField';
import { useAuth } from '../services/AuthContext';
import { colors, spacing, typography } from '../theme';
import type { Account } from '../types/account';
import type { DemoPaymentResponse } from '../types/payment';
import type { RootStackParamList } from '../types/navigation';
import { createDemoIdempotencyKey, getDemoPaymentError, validateAmount } from '../validation/demoPaymentValidation';

type Props = NativeStackScreenProps<RootStackParamList, 'Bills'>;

const categories = ['MOBILE_RECHARGE', 'ELECTRICITY', 'WATER', 'GAS', 'INTERNET', 'DTH', 'POSTPAID', 'LOAN_EMI'];

export function BillsScreen({ navigation }: Props) {
  const { session } = useAuth();
  const [account, setAccount] = useState<Account | null>(null);
  const [category, setCategory] = useState('MOBILE_RECHARGE');
  const [provider, setProvider] = useState('');
  const [identifier, setIdentifier] = useState('');
  const [amount, setAmount] = useState('');
  const [note, setNote] = useState('');
  const [result, setResult] = useState<DemoPaymentResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [mpin, setMpin] = useState('');
  const [showMpin, setShowMpin] = useState(false);

  useEffect(() => { if (session?.accessToken) void getMyAccount(session.accessToken).then(setAccount).catch((cause) => setError(getDemoPaymentError(cause))); }, [session?.accessToken]);
  const submit = async () => {
    if (!account || !session?.accessToken) return;
    const amountError = validateAmount(amount);
    if (amountError) { setError(amountError); return; }
    const providerValue = provider.trim() || 'DEMO_PROVIDER';
    const identifierValue = identifier.trim() || 'DEMO-0001';
    if (!providerValue.toUpperCase().startsWith('DEMO') || !identifierValue.toUpperCase().startsWith('DEMO')) { setError('Use a fictional provider and identifier.'); return; }
    if (!showMpin) { setShowMpin(true); setError(null); return; }
    if (mpin.length !== 6) { setError('Enter your six-digit SpendShield MPIN.'); return; }
    setSubmitting(true); setError(null);
    try { setResult(await billPayment(session.accessToken, createDemoIdempotencyKey('bill'), { account_id: account.account_id, category, provider: providerValue, identifier: identifierValue, amount: amount.trim(), currency: account.currency, demo_mpin: mpin, ...(note.trim() ? { note: note.trim() } : {}) })); } catch (cause) { setMpin(''); setError(getDemoPaymentError(cause)); } finally { setSubmitting(false); }
  };
  if (!account) return <Screen><View style={styles.content}>{error && <ErrorMessage message={error} />}<PrimaryButton onPress={() => navigation.goBack()} variant="secondary">Back</PrimaryButton></View></Screen>;
  if (result) return <Screen><View style={styles.content}><Text style={typography.title}>Bill paid</Text><DashboardCard><Text style={[typography.body, styles.value]}>{result.transaction.transaction_type}</Text><Text style={[typography.caption, styles.muted]}>Transaction ID: {result.transaction.transaction_id}</Text><Text style={[typography.caption, styles.success]}>No real provider was contacted.</Text></DashboardCard><PrimaryButton onPress={() => navigation.navigate('Transactions')}>View history</PrimaryButton><PrimaryButton onPress={() => navigation.goBack()} variant="quiet">Done</PrimaryButton></View></Screen>;
  return <Screen><View style={styles.content}><Text style={typography.title}>Bills & recharges</Text><Text style={[typography.body, styles.muted]}>Fictional provider simulation only. No real biller or telecom service is connected.</Text>{error && <ErrorMessage message={error} />}<Text style={[typography.caption, styles.label]}>Category</Text><View style={styles.categoryWrap}>{categories.map((item) => <PrimaryButton key={item} onPress={() => setCategory(item)} variant={item === category ? 'primary' : 'secondary'}>{item.replace('_', ' ')}</PrimaryButton>)}</View><TextField label="Provider" onChangeText={setProvider} placeholder="Fictional provider" value={provider} /><TextField label="Consumer / account ID" onChangeText={setIdentifier} placeholder="Fictional account ID" value={identifier} /><TextField keyboardType="decimal-pad" label={`Amount (${account.currency})`} onChangeText={setAmount} placeholder="0.00" value={amount} /><TextField label="Optional note" onChangeText={setNote} placeholder="Payment note" value={note} />{showMpin && <DemoMpinPanel onChange={setMpin} value={mpin} />}<PrimaryButton disabled={showMpin && mpin.length !== 6} loading={submitting} onPress={() => void submit()}>{showMpin ? 'Confirm with MPIN' : 'Continue to MPIN'}</PrimaryButton><PrimaryButton disabled={submitting} onPress={() => navigation.goBack()} variant="quiet">Cancel</PrimaryButton></View></Screen>;
}

const styles = StyleSheet.create({ content: { gap: spacing.lg }, muted: { color: colors.textMuted }, value: { color: colors.navy, fontWeight: '800' }, success: { color: colors.success, fontWeight: '800' }, label: { color: colors.navy, fontWeight: '800' }, categoryWrap: { gap: spacing.sm } });
