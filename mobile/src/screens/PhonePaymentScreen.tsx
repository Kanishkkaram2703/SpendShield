import { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { getMyAccount } from '../api/accountApi';
import { phonePayment } from '../api/paymentApi';
import { DashboardCard, StatusBadge } from '../components/DashboardUI';
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

type Props = NativeStackScreenProps<RootStackParamList, 'PhonePayment'>;

export function PhonePaymentScreen({ navigation, route }: Props) {
  const { session } = useAuth();
  const [account, setAccount] = useState<Account | null>(null);
  const [phone, setPhone] = useState(route.params?.phoneNumber || '');
  const [amount, setAmount] = useState('');
  const [note, setNote] = useState('');
  const [result, setResult] = useState<DemoPaymentResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [mpin, setMpin] = useState('');
  const [showMpin, setShowMpin] = useState(false);

  const loadAccount = async () => {
    if (!session?.accessToken) return;
    try { setAccount(await getMyAccount(session.accessToken)); } catch (cause) { setError(getDemoPaymentError(cause)); }
  };
  useEffect(() => { void loadAccount(); }, [session?.accessToken]);

  const submit = async () => {
    if (!account || !session?.accessToken) return;
    const cleanPhone = phone.replace(/[\s-]/g, '');
    const amountError = validateAmount(amount);
    if (!/^\+?\d{7,15}$/.test(cleanPhone)) { setError('Enter a valid phone number.'); return; }
    if (amountError) { setError(amountError); return; }
    if (!showMpin) { setShowMpin(true); setError(null); return; }
    if (mpin.length !== 6) { setError('Enter your six-digit SpendShield MPIN.'); return; }
    setSubmitting(true); setError(null);
    try { setResult(await phonePayment(session.accessToken, createDemoIdempotencyKey('phone'), { account_id: account.account_id, phone_number: cleanPhone, amount: amount.trim(), currency: account.currency, demo_mpin: mpin, ...(note.trim() ? { note: note.trim() } : {}) })); }
    catch (cause) { setError(getDemoPaymentError(cause)); }
    finally { setSubmitting(false); }
  };

  if (result) return <Screen><View style={styles.content}><Text style={typography.title}>Payment recorded</Text><DashboardCard><Text style={[typography.body, styles.muted]}>Phone number: {result.transaction.counterparty_name}</Text><Text style={[typography.body, styles.value]}>Transaction: {result.transaction.transaction_id}</Text><Text style={[typography.caption, styles.success]}>No real money moved.</Text></DashboardCard><PrimaryButton onPress={() => navigation.navigate('Transactions')}>View history</PrimaryButton><PrimaryButton onPress={() => navigation.goBack()} variant="quiet">Done</PrimaryButton></View></Screen>;
  if (!account) return <Screen><View style={styles.content}>{error && <ErrorMessage message={error} />}<PrimaryButton onPress={() => navigation.goBack()} variant="secondary">Back</PrimaryButton></View></Screen>;
  return <Screen><View style={styles.content}><Text style={typography.title}>Pay phone number</Text><Text style={[typography.body, styles.muted]}>Fictional phone payment only. No real money will be transferred.</Text><DashboardCard><View style={styles.balance}><Text style={[typography.caption, styles.muted]}>Server balance</Text><Text style={[typography.heading, styles.value]}>{account.balance} {account.currency}</Text><StatusBadge status={account.status} /></View></DashboardCard>{error && <ErrorMessage message={error} />}<TextField keyboardType="phone-pad" label="Phone number" onChangeText={setPhone} placeholder="+91 9000000000" value={phone} /><TextField keyboardType="decimal-pad" label={`Amount (${account.currency})`} onChangeText={setAmount} placeholder="0.00" value={amount} /><TextField label="Optional note" onChangeText={setNote} placeholder="Reason for this transaction" value={note} />{showMpin && <DemoMpinPanel onChange={setMpin} value={mpin} />}<PrimaryButton disabled={showMpin && mpin.length !== 6} loading={submitting} onPress={() => void submit()}>{showMpin ? 'Confirm with MPIN' : 'Continue to security PIN'}</PrimaryButton><PrimaryButton disabled={submitting} onPress={() => navigation.goBack()} variant="quiet">Cancel</PrimaryButton></View></Screen>;
}

const styles = StyleSheet.create({ content: { gap: spacing.lg }, muted: { color: colors.textMuted }, value: { color: colors.navy, fontWeight: '800' }, success: { color: colors.success, fontWeight: '800' }, balance: { gap: spacing.sm }, });
