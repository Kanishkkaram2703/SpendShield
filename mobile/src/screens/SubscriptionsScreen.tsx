import { useEffect, useMemo, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { getMyAccount } from '../api/accountApi';
import { createSubscription, listSubscriptionCatalog, listSubscriptions, updateSubscriptionStatus } from '../api/demoLifestyleApi';
import { DashboardCard, StatusBadge } from '../components/DashboardUI';
import { DemoMpinPanel } from '../components/DemoControls';
import { ErrorMessage } from '../components/Feedback';
import { PrimaryButton } from '../components/PrimaryButton';
import { Screen } from '../components/Screen';
import { useAuth } from '../services/AuthContext';
import { colors, radii, spacing, typography } from '../theme';
import type { Account } from '../types/account';
import type { Subscription, SubscriptionPlatform } from '../types/demoLifestyle';
import type { RootStackParamList } from '../types/navigation';
import { createDemoIdempotencyKey, getDemoPaymentError } from '../validation/demoPaymentValidation';

type Props = NativeStackScreenProps<RootStackParamList, 'Subscriptions'>;
type Step = 'choose' | 'review' | 'mpin';

export function SubscriptionsScreen({ navigation }: Props) {
  const { session } = useAuth();
  const [account, setAccount] = useState<Account | null>(null);
  const [platforms, setPlatforms] = useState<SubscriptionPlatform[]>([]);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [platformId, setPlatformId] = useState('');
  const [planId, setPlanId] = useState('');
  const [mpin, setMpin] = useState('');
  const [step, setStep] = useState<Step>('choose');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const load = async () => {
    if (!session?.accessToken) { setError('Your session is unavailable. Please sign in again.'); setLoading(false); return; }
    try {
      const [current, catalog, active] = await Promise.all([getMyAccount(session.accessToken), listSubscriptionCatalog(session.accessToken), listSubscriptions(session.accessToken)]);
      setAccount(current); setPlatforms(catalog.platforms); setSubscriptions(active.subscriptions);
    } catch (cause) { setError(getDemoPaymentError(cause)); }
    finally { setLoading(false); }
  };
  useEffect(() => { void load(); }, [session?.accessToken]);

  const platform = useMemo(() => platforms.find((item) => item.platform_id === platformId) || null, [platformId, platforms]);
  const plan = useMemo(() => platform?.plans.find((item) => item.plan_id === planId) || null, [planId, platform]);

  const submit = async () => {
    if (!session?.accessToken || !account || !platform || !plan || mpin.length !== 6) return;
    setSubmitting(true); setError(null);
    try { await createSubscription(session.accessToken, createDemoIdempotencyKey('subscription'), { account_id: account.account_id, platform_id: platform.platform_id, plan_id: plan.plan_id, currency: account.currency, demo_mpin: mpin }); setStep('choose'); setMpin(''); await load(); }
    catch (cause) { setMpin(''); setError(getDemoPaymentError(cause)); }
    finally { setSubmitting(false); }
  };
  const changeStatus = async (subscriptionId: string, status: 'PAUSED' | 'CANCELLED') => {
    if (!session?.accessToken) return;
    setSubmitting(true); setError(null);
    try { await updateSubscriptionStatus(session.accessToken, subscriptionId, status); await load(); }
    catch (cause) { setError(getDemoPaymentError(cause)); }
    finally { setSubmitting(false); }
  };

  if (loading) return <Screen><View style={styles.content}><DashboardCard><Text style={[typography.body, styles.muted]}>Loading entertainment plans…</Text></DashboardCard></View></Screen>;
  if (!account) return <Screen><View style={styles.content}><ErrorMessage message={error || 'The account could not be loaded.'} /><PrimaryButton onPress={() => navigation.goBack()} variant="secondary">Back</PrimaryButton></View></Screen>;

  return <Screen><View style={styles.content}><Text style={typography.title}>BJP Entertainments</Text><Text style={[typography.body, styles.muted]}>Fictional subscriptions only. There is no real recurring billing.</Text>{error && <ErrorMessage message={error} />}<DashboardCard><Text style={[typography.caption, styles.muted]}>Server balance</Text><Text style={[typography.heading, styles.value]}>{account.balance} {account.currency}</Text><StatusBadge status={account.status} /></DashboardCard>{platforms.map((item) => <DashboardCard key={item.platform_id}><Text style={[typography.sectionTitle, styles.value]}>{item.platform_name}</Text><Text style={[typography.caption, styles.muted]}>{item.description}</Text><View style={styles.planList}>{item.plans.map((itemPlan) => <Pressable accessibilityRole="radio" accessibilityState={{ selected: itemPlan.plan_id === planId }} key={itemPlan.plan_id} onPress={() => { setPlatformId(item.platform_id); setPlanId(itemPlan.plan_id); setStep('review'); setError(null); }} style={[styles.plan, itemPlan.plan_id === planId && styles.planSelected]}><Text style={[typography.body, styles.value]}>{itemPlan.plan_name} · ₹{itemPlan.price}</Text><Text style={[typography.caption, styles.muted]}>{itemPlan.duration_days} days · FICTIONAL SUBSCRIPTION — NO REAL BILLING</Text></Pressable>)}</View></DashboardCard>)}{step === 'review' && platform && plan && <DashboardCard><Text style={[typography.eyebrow, styles.eyebrow]}>Subscription review</Text><Summary label="Platform" value={platform.platform_name} /><Summary label="Plan" value={`${plan.plan_name} · ${plan.duration_days} days`} /><Summary label="Amount" value={`${plan.price} ${account.currency}`} /><Summary label="Pay from" value="BJP Bank" /><Text style={[typography.caption, styles.muted]}>The subscription is created and charged only after backend MPIN verification.</Text><Text style={[typography.caption, styles.success]}>SIMULATION ONLY — NO REAL BILLING</Text><PrimaryButton onPress={() => setStep('mpin')}>Continue to MPIN</PrimaryButton><PrimaryButton onPress={() => setStep('choose')} variant="secondary">Choose another plan</PrimaryButton></DashboardCard>}{step === 'mpin' && <><DemoMpinPanel onChange={setMpin} value={mpin} /><PrimaryButton disabled={mpin.length !== 6} loading={submitting} onPress={() => void submit()}>Subscribe</PrimaryButton><PrimaryButton disabled={submitting} onPress={() => setStep('review')} variant="secondary">Back to review</PrimaryButton></>}{subscriptions.length > 0 && <DashboardCard><Text style={[typography.sectionTitle, styles.value]}>Your subscriptions</Text>{subscriptions.map((item) => <View key={item.subscription_id} style={styles.subscription}><Summary label={item.platform_name} value={`${item.plan_name} · ${item.price} ${item.currency} · ${item.status}`} /><Text style={[typography.caption, styles.muted]}>Next billing date: {item.next_billing_date}</Text>{item.status === 'ACTIVE' && <View style={styles.actions}><PrimaryButton disabled={submitting} onPress={() => void changeStatus(item.subscription_id, 'PAUSED')} variant="secondary">Pause</PrimaryButton><PrimaryButton disabled={submitting} onPress={() => void changeStatus(item.subscription_id, 'CANCELLED')} variant="quiet">Cancel</PrimaryButton></View>}{item.status === 'PAUSED' && <PrimaryButton disabled={submitting} onPress={() => void changeStatus(item.subscription_id, 'CANCELLED')} variant="secondary">Cancel paused subscription</PrimaryButton>}</View>)}</DashboardCard>}<PrimaryButton disabled={submitting} onPress={() => navigation.goBack()} variant="quiet">Back</PrimaryButton></View></Screen>;
}

function Summary({ label, value }: { label: string; value: string }) { return <View style={styles.summary}><Text style={[typography.caption, styles.muted]}>{label}</Text><Text style={[typography.body, styles.value]}>{value}</Text></View>; }

const styles = StyleSheet.create({ content: { gap: spacing.lg }, muted: { color: colors.textMuted }, value: { color: colors.navy, fontWeight: '800' }, success: { color: colors.success, fontWeight: '800' }, eyebrow: { color: colors.primaryDark }, planList: { gap: spacing.sm }, plan: { backgroundColor: colors.surfaceMuted, borderColor: colors.border, borderRadius: radii.md, borderWidth: 1, padding: spacing.md }, planSelected: { backgroundColor: colors.primarySoft, borderColor: colors.primary }, summary: { borderBottomColor: colors.border, borderBottomWidth: 1, gap: spacing.xs, paddingVertical: spacing.sm }, subscription: { borderTopColor: colors.border, borderTopWidth: 1, gap: spacing.sm, paddingTop: spacing.md }, actions: { flexDirection: 'row', gap: spacing.sm } });
