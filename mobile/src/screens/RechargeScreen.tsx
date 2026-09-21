import { useEffect, useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { getMyAccount } from '../api/accountApi';
import { listRechargeCatalog, recharge } from '../api/demoLifestyleApi';
import { DashboardCard, StatusBadge } from '../components/DashboardUI';
import { DemoMpinPanel } from '../components/DemoControls';
import { ErrorMessage } from '../components/Feedback';
import { PrimaryButton } from '../components/PrimaryButton';
import { Screen } from '../components/Screen';
import { TextField } from '../components/TextField';
import { useAuth } from '../services/AuthContext';
import { colors, radii, spacing, typography } from '../theme';
import type { Account } from '../types/account';
import type { RechargePlan, RechargeResponse } from '../types/demoLifestyle';
import type { RootStackParamList } from '../types/navigation';
import { createDemoIdempotencyKey, getDemoPaymentError } from '../validation/demoPaymentValidation';

type Props = NativeStackScreenProps<RootStackParamList, 'Recharge'>;
type Step = 'operator' | 'plan' | 'number' | 'review' | 'mpin' | 'success';

export function RechargeScreen({ navigation }: Props) {
  const { session } = useAuth();
  const [account, setAccount] = useState<Account | null>(null);
  const [operators, setOperators] = useState<string[]>([]);
  const [plans, setPlans] = useState<RechargePlan[]>([]);
  const [operator, setOperator] = useState('');
  const [planId, setPlanId] = useState('');
  const [phone, setPhone] = useState('');
  const [confirmPhone, setConfirmPhone] = useState('');
  const [mpin, setMpin] = useState('');
  const [step, setStep] = useState<Step>('operator');
  const [result, setResult] = useState<RechargeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let active = true;
    if (!session?.accessToken) { setError('Your session is unavailable. Please sign in again.'); setLoading(false); return; }
    Promise.all([getMyAccount(session.accessToken), listRechargeCatalog(session.accessToken)])
      .then(([current, catalog]) => { if (active) { setAccount(current); setOperators(catalog.operators); setPlans(catalog.plans); } })
      .catch((cause) => { if (active) setError(getDemoPaymentError(cause)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [session?.accessToken]);

  const selectedPlan = useMemo(() => plans.find((item) => item.plan_id === planId) || null, [planId, plans]);
  const operatorPlans = plans.filter((item) => item.operator === operator);
  const chooseOperator = (value: string) => { setOperator(value); setPlanId(''); setStep('plan'); setError(null); };
  const choosePlan = (value: string) => { setPlanId(value); setStep('number'); setError(null); };
  const review = () => {
    const clean = phone.replace(/\s/g, '');
    if (!selectedPlan) return setError('Choose a recharge plan first.');
    if (!/^[6-9]\d{9}$/.test(clean)) return setError('Enter a valid ten-digit Indian mobile number.');
    if (clean !== confirmPhone.replace(/\s/g, '')) return setError('The mobile number confirmation does not match.');
    setPhone(clean); setConfirmPhone(clean); setError(null); setStep('review');
  };
  const submit = async () => {
    if (!session?.accessToken || !account || !selectedPlan || mpin.length !== 6) return;
    setSubmitting(true); setError(null);
    try { setResult(await recharge(session.accessToken, createDemoIdempotencyKey('recharge'), { account_id: account.account_id, operator: selectedPlan.operator, plan_id: selectedPlan.plan_id, mobile_number: phone, currency: account.currency, demo_mpin: mpin })); setStep('success'); }
    catch (cause) { setMpin(''); setError(getDemoPaymentError(cause)); }
    finally { setSubmitting(false); }
  };

  if (loading) return <Screen><View style={styles.content}><DashboardCard><Text style={[typography.body, styles.muted]}>Loading operators and plans…</Text></DashboardCard></View></Screen>;
  if (result) return <Screen><View style={styles.content}><Text style={typography.title}>Recharge successful</Text><Text style={[typography.body, styles.muted]}>Fictional recharge only. No telecom provider was contacted.</Text><DashboardCard><Summary label="Operator" value={result.operator} /><Summary label="Mobile number" value={result.mobile_number_masked} /><Summary label="Plan" value={result.plan.plan_name} /><Summary label="Amount deducted" value={`${result.payment.paid_amount || result.plan.price} ${result.payment.transaction.currency}`} /><Summary label="Previous balance" value={`${result.payment.previous_balance || 'Not returned'} ${result.payment.transaction.currency}`} /><Summary label="Remaining balance" value={`${result.payment.remaining_balance || 'Not returned'} ${result.payment.transaction.currency}`} /><Summary label="Transaction" value={result.payment.transaction.transaction_id} /><Text style={[typography.caption, styles.success]}>FICTIONAL RECHARGE — SIMULATION ONLY</Text></DashboardCard><PrimaryButton onPress={() => navigation.navigate('Transactions')}>View transaction history</PrimaryButton><PrimaryButton onPress={() => navigation.navigate('Dashboard')} variant="secondary">Return home</PrimaryButton></View></Screen>;
  if (!account) return <Screen><View style={styles.content}><ErrorMessage message={error || 'The account could not be loaded.'} /><PrimaryButton onPress={() => navigation.goBack()} variant="secondary">Back</PrimaryButton></View></Screen>;

  return <Screen><View style={styles.content}><Text style={typography.title}>Mobile recharge</Text><Text style={[typography.body, styles.muted]}>Fictional operators and plans. No real recharge service is connected.</Text>{error && <ErrorMessage message={error} />}<DashboardCard><Text style={[typography.caption, styles.muted]}>Server balance</Text><Text style={[typography.heading, styles.value]}>{account.balance} {account.currency}</Text><StatusBadge status={account.status} /></DashboardCard>{step === 'operator' && <ChoiceCard title="Choose an operator" items={operators} selected={operator} onSelect={chooseOperator} />}{step === 'plan' && <><ChoiceCard title={`Choose a ${operator} plan`} items={operatorPlans.map((item) => `${item.plan_name} · ₹${item.price} · ${item.validity_days} days`)} selected={selectedPlan ? `${selectedPlan.plan_name} · ₹${selectedPlan.price} · ${selectedPlan.validity_days} days` : ''} onSelect={(label) => { const match = operatorPlans.find((item) => `${item.plan_name} · ₹${item.price} · ${item.validity_days} days` === label); if (match) choosePlan(match.plan_id); }} /><PrimaryButton onPress={() => setStep('operator')} variant="quiet">Change operator</PrimaryButton></>}{step === 'number' && <><DashboardCard><Text style={[typography.sectionTitle, styles.value]}>Enter mobile number</Text><Text style={[typography.caption, styles.muted]}>Selected: {selectedPlan?.plan_name} · ₹{selectedPlan?.price}</Text></DashboardCard><TextField keyboardType="phone-pad" label="Ten-digit mobile number" maxLength={10} onChangeText={setPhone} placeholder="9000000000" value={phone} /><TextField keyboardType="phone-pad" label="Confirm mobile number" maxLength={10} onChangeText={setConfirmPhone} placeholder="9000000000" value={confirmPhone} /><PrimaryButton onPress={review}>Review recharge</PrimaryButton></>}{step === 'review' && selectedPlan && <><DashboardCard><Text style={[typography.eyebrow, styles.eyebrow]}>Recharge review</Text><Summary label="Operator" value={selectedPlan.operator} /><Summary label="Mobile number" value={`••••••${phone.slice(-4)}`} /><Summary label="Plan" value={selectedPlan.plan_name} /><Summary label="Validity" value={`${selectedPlan.validity_days} days · ${selectedPlan.data_allowance}`} /><Summary label="Amount" value={`${selectedPlan.price} ${account.currency}`} /><Summary label="Pay from" value="BJP Bank" /><Text style={[typography.caption, styles.muted]}>The server will return the final balance after MPIN verification. No balance is deducted on this screen.</Text><Text style={[typography.caption, styles.success]}>SIMULATION ONLY — NO REAL MONEY</Text></DashboardCard><PrimaryButton onPress={() => setStep('mpin')}>Continue to MPIN</PrimaryButton><PrimaryButton onPress={() => setStep('number')} variant="secondary">Edit details</PrimaryButton></>}{step === 'mpin' && <><DemoMpinPanel onChange={setMpin} value={mpin} /><PrimaryButton disabled={mpin.length !== 6} loading={submitting} onPress={() => void submit()}>Confirm recharge</PrimaryButton><PrimaryButton disabled={submitting} onPress={() => setStep('review')} variant="secondary">Back to review</PrimaryButton></>}{(step === 'operator' || step === 'plan' || step === 'number' || step === 'review' || step === 'mpin') && <PrimaryButton disabled={submitting} onPress={() => navigation.goBack()} variant="quiet">Cancel</PrimaryButton>}</View></Screen>;
}

function ChoiceCard({ title, items, selected, onSelect }: { title: string; items: string[]; selected: string; onSelect: (item: string) => void }) { return <DashboardCard><Text style={[typography.sectionTitle, styles.value]}>{title}</Text><View style={styles.choices}>{items.map((item) => <Pressable accessibilityRole="radio" accessibilityState={{ selected: item === selected }} key={item} onPress={() => onSelect(item)} style={[styles.choice, item === selected && styles.choiceSelected]}><Text style={[typography.body, styles.choiceText]}>{item}</Text></Pressable>)}</View><Text style={[typography.caption, styles.success]}>FICTIONAL SERVICE — NO REAL BILLING</Text></DashboardCard>; }
function Summary({ label, value }: { label: string; value: string }) { return <View style={styles.summary}><Text style={[typography.caption, styles.muted]}>{label}</Text><Text style={[typography.body, styles.value]}>{value}</Text></View>; }

const styles = StyleSheet.create({ content: { gap: spacing.lg }, muted: { color: colors.textMuted }, value: { color: colors.navy, fontWeight: '800' }, success: { color: colors.success, fontWeight: '800' }, eyebrow: { color: colors.primaryDark }, choices: { gap: spacing.sm }, choice: { backgroundColor: colors.surfaceMuted, borderColor: colors.border, borderRadius: radii.md, borderWidth: 1, padding: spacing.md }, choiceSelected: { backgroundColor: colors.primarySoft, borderColor: colors.primary }, choiceText: { color: colors.navy, fontWeight: '700' }, summary: { borderBottomColor: colors.border, borderBottomWidth: 1, gap: spacing.xs, paddingVertical: spacing.sm } });
