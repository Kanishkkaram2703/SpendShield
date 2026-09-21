import { useEffect, useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { getMyAccount } from '../api/accountApi';
import { listDemoMerchants } from '../api/demoMerchantApi';
import { payByQr } from '../api/paymentApi';
import { DashboardCard, StatusBadge } from '../components/DashboardUI';
import { DemoMpinPanel } from '../components/DemoControls';
import { EmptyState, ErrorMessage } from '../components/Feedback';
import { PrimaryButton } from '../components/PrimaryButton';
import { Screen } from '../components/Screen';
import { TextField } from '../components/TextField';
import { useAuth } from '../services/AuthContext';
import { colors, radii, spacing, typography } from '../theme';
import type { Account } from '../types/account';
import type { DemoMerchant } from '../types/demoMerchant';
import type { DemoPaymentResponse } from '../types/payment';
import type { RootStackParamList } from '../types/navigation';
import { createDemoIdempotencyKey, getDemoPaymentError, validateAmount } from '../validation/demoPaymentValidation';

type Props = NativeStackScreenProps<RootStackParamList, 'Pay'>;
type Step = 'form' | 'review' | 'mpin';

export function PayScreen({ navigation }: Props) {
  const { session } = useAuth();
  const [account, setAccount] = useState<Account | null>(null);
  const [merchants, setMerchants] = useState<DemoMerchant[]>([]);
  const [merchantId, setMerchantId] = useState('');
  const [amount, setAmount] = useState('');
  const [note, setNote] = useState('');
  const [mpin, setMpin] = useState('');
  const [step, setStep] = useState<Step>('form');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [result, setResult] = useState<DemoPaymentResponse | null>(null);

  useEffect(() => {
    let active = true;
    if (!session?.accessToken) { setError('Your session is unavailable. Please sign in again.'); setLoading(false); return; }
    Promise.all([getMyAccount(session.accessToken), listDemoMerchants(session.accessToken)])
      .then(([current, page]) => { if (active) { setAccount(current); setMerchants(page.merchants.filter((item) => item.status === 'ACTIVE')); } })
      .catch((cause) => { if (active) setError(getDemoPaymentError(cause)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [session?.accessToken]);

  const selectedMerchant = useMemo(() => merchants.find((item) => item.merchant_id === merchantId) || null, [merchantId, merchants]);
  const validate = () => {
    if (!account || !selectedMerchant) { setFieldError('Choose an active merchant to continue.'); return false; }
    const amountError = validateAmount(amount);
    if (amountError) { setFieldError(amountError); return false; }
    if (!isAtMost(amount.trim(), account.balance)) { setFieldError('The amount exceeds the available account balance.'); return false; }
    if (note.trim().length > 256) { setFieldError('The note cannot exceed 256 characters.'); return false; }
    setFieldError(null); setError(null); return true;
  };
  const submit = async () => {
    if (!session?.accessToken || !account || !selectedMerchant || mpin.length !== 6 || !validate()) return;
    setSubmitting(true); setError(null);
    try { setResult(await payByQr(session.accessToken, createDemoIdempotencyKey('merchant'), { account_id: account.account_id, amount: amount.trim(), currency: account.currency, qr_payload: selectedMerchant.qr_payload, demo_mpin: mpin, ...(note.trim() ? { note: note.trim() } : {}) })); }
    catch (cause) { setMpin(''); setError(getDemoPaymentError(cause)); }
    finally { setSubmitting(false); }
  };

  if (loading) return <Screen><View style={styles.content}><DashboardCard><Text style={[typography.body, styles.muted]}>Loading the server merchant catalog…</Text></DashboardCard></View></Screen>;
  if (result) return <Screen><View style={styles.content}><Text style={typography.title}>Payment successful</Text><Text style={[typography.body, styles.muted]}>The fictional payment was recorded by SpendShield. No real money moved.</Text><DashboardCard><StatusBadge status="ACTIVE" /><Summary label="Transaction status" value={result.transaction.status} /><Summary label="Paid to" value={result.merchant?.merchant_name || selectedMerchant?.merchant_name || 'Merchant'} /><Summary label="Amount" value={`${result.paid_amount || result.transaction.amount} ${result.transaction.currency}`} /><Summary label="Previous balance" value={`${result.previous_balance || 'Not returned'} ${result.transaction.currency}`} /><Summary label="Remaining balance" value={`${result.remaining_balance || 'Not returned'} ${result.transaction.currency}`} /><Summary label="Transaction ID" value={result.transaction.transaction_id} /><Summary label="Date and time" value={new Date(result.transaction.created_at).toLocaleString()} /><Text style={[typography.caption, styles.success]}>FICTIONAL MERCHANT · SIMULATION ONLY</Text></DashboardCard><PrimaryButton onPress={() => navigation.navigate('TransactionDetails', { transactionId: result.transaction.transaction_id })}>View transaction</PrimaryButton><PrimaryButton onPress={() => navigation.navigate('Dashboard')} variant="secondary">Return home</PrimaryButton></View></Screen>;
  if (!account) return <Screen><View style={styles.content}><ErrorMessage message={error || 'The account could not be loaded.'} /><PrimaryButton onPress={() => navigation.goBack()} variant="secondary">Back</PrimaryButton></View></Screen>;

  return <Screen><View style={styles.content}><Text style={typography.title}>{step === 'review' ? 'Review payment' : step === 'mpin' ? 'Confirm payment' : 'Pay a merchant'}</Text><Text style={[typography.body, styles.muted]}>Backend-authoritative fictional payment. No real funds move through this experience.</Text>{error && <ErrorMessage message={error} />}{fieldError && <ErrorMessage message={fieldError} />}{!merchants.length && <EmptyState title="No merchants available" message="The backend did not return an active fictional merchant catalog." />}{step === 'form' && merchants.length > 0 && <><DashboardCard><Text style={[typography.sectionTitle, styles.value]}>Choose a merchant</Text><View style={styles.merchantGrid}>{merchants.map((merchant) => <Pressable accessibilityRole="radio" accessibilityState={{ selected: merchant.merchant_id === merchantId }} key={merchant.merchant_id} onPress={() => setMerchantId(merchant.merchant_id)} style={[styles.merchant, merchant.merchant_id === merchantId && styles.selected]}><Text style={[typography.body, styles.value]}>{merchant.merchant_name}</Text><Text style={[typography.caption, styles.muted]}>{merchant.category}</Text><Text style={[typography.caption, styles.success]}>FICTIONAL MERCHANT</Text></Pressable>)}</View></DashboardCard><TextField keyboardType="decimal-pad" label={`Amount (${account.currency})`} onChangeText={setAmount} placeholder="0.00" value={amount} /><TextField label="Optional note" maxLength={256} onChangeText={setNote} placeholder="Payment note" value={note} /><PrimaryButton disabled={!selectedMerchant} onPress={() => { if (validate()) setStep('review'); }}>Review payment</PrimaryButton></>}{step === 'review' && selectedMerchant && <><DashboardCard><Text style={[typography.eyebrow, styles.eyebrow]}>Payment review</Text><Summary label="Merchant" value={selectedMerchant.merchant_name} /><Summary label="Category" value={selectedMerchant.category} /><Summary label="Amount" value={`${amount} ${account.currency}`} /><Summary label="Pay from" value="BJP Bank" /><Summary label="Available balance" value={`${account.balance} ${account.currency}`} /><Text style={[typography.caption, styles.muted]}>The final remaining balance comes from the backend after MPIN verification.</Text><Text style={[typography.caption, styles.success]}>SIMULATION ONLY — NO REAL MONEY</Text></DashboardCard><PrimaryButton onPress={() => setStep('mpin')}>Continue to MPIN</PrimaryButton><PrimaryButton onPress={() => setStep('form')} variant="secondary">Edit payment</PrimaryButton></>}{step === 'mpin' && <><DemoMpinPanel onChange={setMpin} value={mpin} /><PrimaryButton disabled={mpin.length !== 6} loading={submitting} onPress={() => void submit()}>Pay securely</PrimaryButton><PrimaryButton disabled={submitting} onPress={() => setStep('review')} variant="secondary">Back to review</PrimaryButton></>}<PrimaryButton disabled={submitting} onPress={() => navigation.goBack()} variant="quiet">Cancel</PrimaryButton></View></Screen>;
}

function Summary({ label, value }: { label: string; value: string }) { return <View style={styles.summary}><Text style={[typography.caption, styles.muted]}>{label}</Text><Text style={[typography.body, styles.value]}>{value}</Text></View>; }
function isAtMost(value: string, limit: string): boolean { const left = minor(value); const right = minor(limit); return Boolean(left && right && (left.length < right.length || (left.length === right.length && left <= right))); }
function minor(value: string): string { if (!/^\d+(\.\d{1,2})?$/.test(value.trim())) return ''; const [whole, fraction = ''] = value.trim().split('.'); return `${whole}${fraction.padEnd(2, '0')}`.replace(/^0+(?=\d)/, '') || '0'; }

const styles = StyleSheet.create({ content: { gap: spacing.lg }, muted: { color: colors.textMuted }, value: { color: colors.navy, fontWeight: '800' }, success: { color: colors.success, fontWeight: '800' }, eyebrow: { color: colors.primaryDark }, merchantGrid: { gap: spacing.sm }, merchant: { backgroundColor: colors.surfaceMuted, borderColor: colors.border, borderRadius: radii.md, borderWidth: 1, gap: spacing.xs, padding: spacing.md }, selected: { backgroundColor: colors.primarySoft, borderColor: colors.primary }, summary: { borderBottomColor: colors.border, borderBottomWidth: 1, gap: spacing.xs, paddingVertical: spacing.sm } });
