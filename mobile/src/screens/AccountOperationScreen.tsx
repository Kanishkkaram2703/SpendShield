import { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { getMyAccount } from '../api/accountApi';
import { demoDeposit, demoWithdrawal } from '../api/paymentApi';
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

type Props = NativeStackScreenProps<RootStackParamList, 'AccountOperation'>;

export function AccountOperationScreen({ navigation, route }: Props) {
  const { session } = useAuth();
  const operation = route.params.operation;
  const label = operation === 'deposit' ? 'Deposit' : 'Withdraw';
  const [account, setAccount] = useState<Account | null>(null);
  const [amount, setAmount] = useState('');
  const [reason, setReason] = useState('');
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
    if (!showMpin) { setShowMpin(true); setError(null); return; }
    if (mpin.length !== 6) { setError('Enter your six-digit SpendShield MPIN.'); return; }
    setSubmitting(true); setError(null);
    try { const method = operation === 'deposit' ? demoDeposit : demoWithdrawal; setResult(await method(session.accessToken, createDemoIdempotencyKey(operation), { account_id: account.account_id, amount: amount.trim(), currency: account.currency, demo_mpin: mpin, ...(reason.trim() ? { reason: reason.trim() } : {}) })); } catch (cause) { setMpin(''); setError(getDemoPaymentError(cause)); } finally { setSubmitting(false); }
  };
  if (!account) return <Screen><View style={styles.content}>{error && <ErrorMessage message={error} />}<PrimaryButton onPress={() => navigation.goBack()} variant="secondary">Back</PrimaryButton></View></Screen>;
  if (result) return <Screen><View style={styles.content}><Text style={typography.title}>{label} recorded</Text><DashboardCard><Text style={[typography.body, styles.value]}>Transaction ID</Text><Text style={[typography.caption, styles.muted]}>{result.transaction.transaction_id}</Text><Text style={[typography.caption, styles.success]}>The server recorded fictional funds only.</Text></DashboardCard><PrimaryButton onPress={() => navigation.navigate('Transactions')}>View transaction history</PrimaryButton><PrimaryButton onPress={() => navigation.goBack()} variant="quiet">Done</PrimaryButton></View></Screen>;
  return <Screen><View style={styles.content}><Text style={typography.title}>{label}</Text><Text style={[typography.body, styles.muted]}>Simulation only. No real funds are deposited or withdrawn.</Text>{error && <ErrorMessage message={error} />}<DashboardCard><Text style={[typography.caption, styles.muted]}>Server balance</Text><Text style={[typography.heading, styles.value]}>{account.balance} {account.currency}</Text><StatusBadge status={account.status} /></DashboardCard><TextField keyboardType="decimal-pad" label={`Amount (${account.currency})`} onChangeText={setAmount} placeholder="0.00" value={amount} /><TextField label="Reason" onChangeText={setReason} placeholder={`${label} reason`} value={reason} />{showMpin && <DemoMpinPanel onChange={setMpin} value={mpin} />}<PrimaryButton disabled={showMpin && mpin.length !== 6} loading={submitting} onPress={() => void submit()}>{showMpin ? 'Confirm with MPIN' : 'Continue to MPIN'}</PrimaryButton><PrimaryButton disabled={submitting} onPress={() => navigation.goBack()} variant="quiet">Cancel</PrimaryButton></View></Screen>;
}

const styles = StyleSheet.create({ content: { gap: spacing.lg }, muted: { color: colors.textMuted }, value: { color: colors.navy, fontWeight: '800' }, success: { color: colors.success, fontWeight: '800' } });
