import { useCallback, useEffect, useRef, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, useWindowDimensions, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { ApiError } from '../api/client';
import { createAccount, getMyAccount } from '../api/accountApi';
import { BrandMark } from '../components/BrandMark';
import {
  BottomNavigation,
  DashboardCard,
  IconGlyph,
  QuickAction,
  SectionHeader,
  StatusBadge,
  UtilityRow,
} from '../components/DashboardUI';
import { EmptyState, ErrorMessage } from '../components/Feedback';
import { PrimaryButton } from '../components/PrimaryButton';
import { Screen } from '../components/Screen';
import { useAuth } from '../services/AuthContext';
import { colors, radii, spacing, typography } from '../theme';
import type { Account } from '../types/account';
import type { RootStackParamList } from '../types/navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'Dashboard'>;
type ViewState = 'loading' | 'ready' | 'missing' | 'error';

export function DashboardScreen({ navigation }: Props) {
  const { session, signOut } = useAuth();
  const [account, setAccount] = useState<Account | null>(null);
  const [viewState, setViewState] = useState<ViewState>('loading');
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [refreshMessage, setRefreshMessage] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isCreating, setIsCreating] = useState(false);

  const loadAccount = useCallback(async () => {
    const token = session?.accessToken;
    if (!token) {
      setAccount(null);
      setLoadError('Your session is unavailable. Please sign in again.');
      setViewState('error');
      return;
    }

    setViewState('loading');
    setLoadError(null);
    setActionError(null);

    try {
      const currentAccount = await getMyAccount(token);
      setAccount(currentAccount);
      setViewState('ready');
    } catch (error) {
      setAccount(null);
      if (isAccountNotFound(error)) {
        setViewState('missing');
        return;
      }
      setLoadError(getAccountErrorMessage(error));
      setViewState('error');
    }
  }, [session?.accessToken]);

  useEffect(() => {
    void loadAccount();
  }, [loadAccount]);

  const handleCreateAccount = async () => {
    const token = session?.accessToken;
    if (!token) {
      setActionError('Your session is unavailable. Please sign in again.');
      return;
    }

    setIsCreating(true);
    setActionError(null);
    try {
      await createAccount(token);
      await loadAccount();
    } catch (error) {
      setActionError(getAccountErrorMessage(error));
    } finally {
      setIsCreating(false);
    }
  };

  const handleRefresh = async () => {
    const token = session?.accessToken;
    if (!token) {
      setActionError('Your session is unavailable. Please sign in again.');
      return;
    }
    setIsRefreshing(true);
    setActionError(null);
    setRefreshMessage(null);
    try {
      const currentAccount = await getMyAccount(token);
      setAccount(currentAccount);
      setViewState('ready');
      setRefreshMessage('Account refreshed from the SpendShield server.');
    } catch (error) {
      setActionError(getAccountErrorMessage(error));
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <Screen footer={<BottomNavigation onNavigate={(destination) => {
      if (destination === 'Pay') navigation.navigate('Pay');
      else if (destination === 'More') navigation.navigate('More');
      else if (destination === 'Qr') navigation.navigate('ComingSoonPayment', { flow: 'qr' });
      else navigation.navigate('Bills');
    }} />}>
      <View style={styles.content}>
        <HomeHeader email={session?.user.email} />

        {viewState === 'loading' && <LoadingState />}

        {viewState === 'ready' && account && (
          <>
            {actionError && <ErrorMessage message={actionError} />}
            <HomeExperience account={account} isRefreshing={isRefreshing} navigation={navigation} onRefresh={handleRefresh} refreshMessage={refreshMessage} />
          </>
        )}

        {viewState === 'missing' && (
          <View style={styles.feedback}>
            <EmptyState
              title="Set up your protected account"
              message="Create your SpendShield account to unlock your personalized finance home."
            />
            {actionError && <ErrorMessage message={actionError} />}
            <PrimaryButton onPress={() => void handleCreateAccount()} loading={isCreating}>
              Create account
            </PrimaryButton>
          </View>
        )}

        {viewState === 'error' && loadError && (
          <View style={styles.feedback}>
            <ErrorMessage message={loadError} />
            <PrimaryButton onPress={() => void loadAccount()}>Try again</PrimaryButton>
          </View>
        )}

        <View style={styles.environmentNotice}>
          <IconGlyph color={colors.primaryDark} name="shield" size={18} />
          <Text style={[typography.caption, styles.environmentText]}>
            Simulated financial environment. No real funds move through this app.
          </Text>
        </View>
        <PrimaryButton onPress={() => void signOut()} variant="secondary">
          Sign out
        </PrimaryButton>
      </View>
    </Screen>
  );
}

function HomeHeader({ email }: { email?: string }) {
  return (
    <View style={styles.header}>
      <View style={styles.headerTopRow}>
        <BrandMark />
        <View style={styles.headerActions}>
          <Pressable
            accessibilityHint="Search is coming soon"
            accessibilityLabel="Search, coming soon"
            accessibilityRole="button"
            accessibilityState={{ disabled: true }}
            disabled
            style={styles.headerAction}
          >
            <IconGlyph color={colors.navy} name="search" size={27} />
          </Pressable>
          <View accessibilityLabel="Profile" style={styles.profileAvatar}>
            <Text style={styles.profileInitial}>{getInitial(email)}</Text>
          </View>
        </View>
      </View>
      <View style={styles.greeting}>
        <Text style={[typography.eyebrow, styles.eyebrow]}>Your protected workspace</Text>
        <Text style={[typography.title, styles.title]}>{getGreeting()}</Text>
        <Text style={[typography.body, styles.subtitle]}>{email}</Text>
      </View>
    </View>
  );
}

function HomeExperience({
  account,
  isRefreshing,
  navigation,
  onRefresh,
  refreshMessage,
}: {
  account: Account;
  isRefreshing: boolean;
  navigation: Props['navigation'];
  onRefresh: () => Promise<void>;
  refreshMessage: string | null;
}) {
  return (
    <View style={styles.homeSections}>
      <PromoCarousel navigation={navigation} />

      <View style={styles.section}>
        <SectionHeader title="Pay and manage" />
        <View style={styles.quickActions}>
          <QuickAction caption="Secure payment" icon="pay" onPress={() => navigation.navigate('Pay')} title="Pay" />
          <QuickAction caption="Choose a contact" icon="people" onPress={() => navigation.navigate('Contacts')} title="Pay contacts" />
          <QuickAction caption="Use a number" icon="send" onPress={() => navigation.navigate('PhonePayment')} title="Pay phone number" />
          <QuickAction caption="Fictional transfer" icon="bank" onPress={() => navigation.navigate('ComingSoonPayment', { flow: 'bank' })} title="Bank transfer" />
          <QuickAction caption="Scan QR" icon="scan" onPress={() => navigation.navigate('ComingSoonPayment', { flow: 'qr' })} title="Scan QR" />
          <QuickAction caption="Fictional transfer" icon="account" onPress={() => navigation.navigate('ComingSoonPayment', { flow: 'self' })} title="Self transfer" />
          <QuickAction caption="Fictional payment" icon="pay" onPress={() => navigation.navigate('ComingSoonPayment', { flow: 'send' })} title="Pay account" />
          <QuickAction caption="Simulation only" icon="bills" onPress={() => navigation.navigate('Bills')} title="Pay bills" />
          <QuickAction caption="Simulation only" icon="recharge" onPress={() => navigation.navigate('Recharge')} title="Mobile recharge" />
        </View>
      </View>

      <DirectorySection
        icon="people"
        message="Your frequent contacts will appear here."
        title="People"
      />
      <DirectorySection
        icon="merchant"
        message="Your favorite merchants will appear here."
        title="Businesses"
      />

      <DashboardCard>
        <SectionHeader action="Coming soon" title="Bills & Recharges" />
        <Text style={[typography.caption, styles.sectionDescription]}>
          Stay on top of recurring essentials when payment support is available.
        </Text>
        <View style={styles.categoryGrid}>
          <CategoryItem icon="▣" title="DTH / Cable TV" />
          <CategoryItem icon="♧" title="Electricity" />
          <CategoryItem icon="▤" title="Postpaid mobile" />
          <CategoryItem icon="↗" title="Loan EMI" />
          <CategoryItem icon="◌" title="Water bill" />
          <CategoryItem icon="◇" title="Gas bill" />
        </View>
      </DashboardCard>

      <DashboardCard>
        <SectionHeader action="Presentation only" title="Offers & Rewards" />
        <View style={styles.offerGrid}>
          <OfferItem icon="shield" title="Rewards" />
          <OfferItem icon="insights" title="Offers" />
          <OfferItem icon="people" title="Referrals" />
        </View>
      </DashboardCard>

      <DashboardCard style={styles.utilityCard}>
        <SectionHeader title="Shortcuts" />
        <UtilityRow caption="Your simulated payment history" disabled={false} icon="transactions" onPress={() => navigation.navigate('Transactions')} title="See transaction history" />
        <UtilityRow caption="Protected fictional balance · MPIN required" disabled={false} icon="bank" onPress={() => navigation.navigate('AccountDetails')} title="Check bank balance" />
        <UtilityRow caption="Private, masked account view" disabled={false} icon="account" onPress={() => navigation.navigate('AccountDetails')} title="Account details" />
        <UtilityRow caption={isRefreshing ? 'Fetching current server state…' : 'Reload the current server account state'} disabled={false} icon="shield" loading={isRefreshing} onPress={() => void onRefresh()} title="Refresh account" />
        {refreshMessage && <Text style={[typography.caption, styles.refreshMessage]}>{refreshMessage}</Text>}
      </DashboardCard>

      <DashboardCard style={styles.securityCard}>
        <SectionHeader title="SpendShield security" />
        <View style={styles.securityRow}>
          <View style={styles.securityIcon}>
            <IconGlyph color={colors.success} name="lock" size={21} />
          </View>
          <View style={styles.securityCopy}>
            <Text style={[typography.body, styles.cardTitle]}>Account status</Text>
            <Text style={[typography.caption, styles.cardDescription]}>
              Security monitoring will appear here as your activity grows.
            </Text>
          </View>
          <StatusBadge status={account.status} />
        </View>
      </DashboardCard>

      <View style={styles.featureBanner}>
        <View style={styles.featureBannerIcon}>
          <IconGlyph color={colors.primaryDark} name="insights" size={23} />
        </View>
        <View style={styles.featureBannerCopy}>
          <Text style={[typography.body, styles.featureBannerTitle]}>Stay aware of every payment</Text>
          <Text style={[typography.caption, styles.featureBannerText]}>
            Spending insights and unusual-activity signals will be introduced as supported data becomes available.
          </Text>
        </View>
      </View>
    </View>
  );
}

function PromoCarousel({ navigation }: { navigation: Props['navigation'] }) {
  const { width } = useWindowDimensions();
  const [active, setActive] = useState(0);
  const scrollRef = useRef<ScrollView>(null);
  const slideWidth = Math.max(260, width - spacing.lg * 2);
  const slides = [
    { title: 'Review your pending activity', description: 'Review pending fictional activities and account actions.', action: 'Review now', onPress: () => navigation.navigate('Transactions'), icon: 'transactions' as const },
    { title: 'Track your spending', description: 'Understand your fictional spending activity.', action: 'View insights', onPress: () => navigation.navigate('More'), icon: 'insights' as const },
    { title: 'Protect your account', description: 'Review MPIN, card, and security settings.', action: 'Open security', onPress: () => navigation.navigate('DemoSecurity'), icon: 'shield' as const },
  ];
  return <View style={styles.carousel}><ScrollView ref={scrollRef} horizontal pagingEnabled showsHorizontalScrollIndicator={false} onMomentumScrollEnd={(event) => setActive(Math.round(event.nativeEvent.contentOffset.x / slideWidth))} scrollEventThrottle={16} snapToInterval={slideWidth} decelerationRate="fast">{slides.map((slide) => <View key={slide.title} style={[styles.promoBanner, { width: slideWidth }]}><View style={styles.promoCopy}><Text style={[typography.eyebrow, styles.promoEyebrow]}>SpendShield insight</Text><Text style={[typography.heading, styles.promoTitle]}>{slide.title}</Text><Text style={[typography.caption, styles.promoText]}>{slide.description}</Text><Pressable accessibilityRole="button" onPress={slide.onPress}><Text style={[typography.caption, styles.promoAction]}>{slide.action}  ›</Text></Pressable></View><View style={styles.promoArt}><IconGlyph color={colors.primaryDark} name={slide.icon} size={50} /><View style={styles.promoDot} /></View></View>)}</ScrollView><View style={styles.promoDots}>{slides.map((slide, index) => <Pressable accessibilityLabel={`Show slide ${index + 1}`} accessibilityRole="button" key={slide.title} onPress={() => { setActive(index); scrollRef.current?.scrollTo({ x: index * slideWidth, animated: true }); }} style={[styles.promoDotIndicator, index === active && styles.promoDotActive]} />)}</View></View>;
}

function PromoBanner() {
  return (
    <View style={styles.promoBanner}>
      <View style={styles.promoCopy}>
        <Text style={[typography.eyebrow, styles.promoEyebrow]}>SpendShield insight</Text>
        <Text style={[typography.heading, styles.promoTitle]}>Understand your spending.</Text>
        <Text style={[typography.caption, styles.promoText]}>
          A clearer, safer view of your financial activity is coming together.
        </Text>
        <Text style={[typography.caption, styles.promoAction]}>Coming soon  ›</Text>
      </View>
      <View style={styles.promoArt}>
        <IconGlyph color={colors.primaryDark} name="shield" size={50} />
        <View style={styles.promoDot} />
      </View>
      <View style={styles.promoDots}>
        <View style={[styles.promoDotIndicator, styles.promoDotActive]} />
        <View style={styles.promoDotIndicator} />
        <View style={styles.promoDotIndicator} />
      </View>
    </View>
  );
}

function DirectorySection({ icon, message, title }: { icon: 'merchant' | 'people'; message: string; title: string }) {
  return (
    <DashboardCard>
      <SectionHeader action="Coming soon" title={title} />
      <View style={styles.directoryEmpty}>
        <View style={styles.directoryIcon}>
          <IconGlyph color={colors.primaryDark} name={icon} size={23} />
        </View>
        <Text style={[typography.caption, styles.cardDescription]}>{message}</Text>
      </View>
    </DashboardCard>
  );
}

function CategoryItem({ icon, title }: { icon: string; title: string }) {
  return (
    <View accessible accessibilityLabel={`${title}, coming soon`} style={styles.categoryItem}>
      <View style={styles.categoryIcon}>
        <Text style={styles.categoryGlyph}>{icon}</Text>
      </View>
      <Text numberOfLines={2} style={[typography.caption, styles.categoryTitle]}>{title}</Text>
      <Text style={[typography.caption, styles.categoryCaption]}>Soon</Text>
    </View>
  );
}

function OfferItem({ icon, title }: { icon: 'insights' | 'people' | 'shield'; title: string }) {
  return (
    <View accessible accessibilityLabel={`${title}, presentation only`} style={styles.offerItem}>
      <IconGlyph color={colors.primaryDark} name={icon} size={23} />
      <Text style={[typography.caption, styles.offerTitle]}>{title}</Text>
      <Text style={[typography.caption, styles.offerCaption]}>Coming soon</Text>
    </View>
  );
}

function LoadingState() {
  return (
    <DashboardCard style={styles.loadingCard}>
      <Text style={[typography.sectionTitle, styles.cardTitle]}>Loading your protected home</Text>
      <Text style={[typography.caption, styles.cardDescription]}>Fetching your account status from SpendShield.</Text>
    </DashboardCard>
  );
}

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning.';
  if (hour < 18) return 'Good afternoon.';
  return 'Good evening.';
}

function getInitial(email?: string): string {
  return email?.trim().charAt(0).toUpperCase() || 'S';
}

function isAccountNotFound(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404 && error.code === 'account_not_found';
}

function getAccountErrorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return 'The account request could not be completed. Please try again.';
  }
  if (error.code === 'network_error' || error.status === 408) {
    return 'The backend could not be reached. Check the API URL and local network connection.';
  }
  if (error.status === 401) {
    return 'Your session is not authorized. Please sign in again.';
  }
  if (error.status === 422) {
    return 'The backend rejected the account request validation. Please try again.';
  }
  if (error.status === 503) {
    return 'The backend or database is temporarily unavailable. Please try again shortly.';
  }
  return error.message || 'The account request could not be completed. Please try again.';
}

const styles = StyleSheet.create({
  content: { gap: spacing.lg },
  header: { gap: spacing.md },
  headerTopRow: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  headerActions: { alignItems: 'center', flexDirection: 'row', gap: spacing.sm },
  headerAction: { alignItems: 'center', height: 42, justifyContent: 'center', width: 32 },
  profileAvatar: { alignItems: 'center', backgroundColor: colors.primarySoft, borderColor: colors.primary, borderRadius: 22, borderWidth: 1, height: 44, justifyContent: 'center', width: 44 },
  profileInitial: { color: colors.primaryDark, fontSize: 18, fontWeight: '800' },
  greeting: { gap: spacing.xs },
  eyebrow: { color: colors.primaryDark },
  title: { color: colors.navy },
  subtitle: { color: colors.textMuted },
  homeSections: { gap: spacing.lg },
  carousel: { minHeight: 190 },
  promoBanner: { backgroundColor: colors.primarySoft, borderColor: colors.border, borderRadius: radii.lg, borderWidth: 1, height: 170, overflow: 'hidden', padding: spacing.lg, position: 'relative' },
  promoCopy: { gap: spacing.sm, maxWidth: '72%' },
  promoEyebrow: { color: colors.primaryDark },
  promoTitle: { color: colors.navy },
  promoText: { color: colors.textMuted },
  promoAction: { color: colors.primaryDark, fontWeight: '800' },
  promoArt: { alignItems: 'center', backgroundColor: 'rgba(91,141,239,0.13)', borderRadius: 58, height: 116, justifyContent: 'center', position: 'absolute', right: -8, top: 22, width: 116 },
  promoDot: { backgroundColor: colors.primary, borderRadius: 5, height: 10, position: 'absolute', right: 22, top: 20, width: 10 },
  promoDots: { bottom: spacing.sm, flexDirection: 'row', gap: spacing.xs, position: 'absolute', right: spacing.lg },
  promoDotIndicator: { backgroundColor: colors.border, borderRadius: 4, height: 6, width: 6 },
  promoDotActive: { backgroundColor: colors.primary, width: 18 },
  section: { gap: spacing.md },
  sectionDescription: { color: colors.textMuted },
  quickActions: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  directoryEmpty: { alignItems: 'center', backgroundColor: colors.surfaceMuted, borderRadius: radii.md, flexDirection: 'row', gap: spacing.md, padding: spacing.md },
  directoryIcon: { alignItems: 'center', backgroundColor: colors.primarySoft, borderRadius: radii.md, height: 44, justifyContent: 'center', width: 44 },
  categoryGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md },
  categoryItem: { alignItems: 'center', flexBasis: '28%', flexGrow: 1, gap: spacing.xs, minWidth: 76 },
  categoryIcon: { alignItems: 'center', backgroundColor: colors.primarySoft, borderRadius: 28, height: 56, justifyContent: 'center', width: 56 },
  categoryGlyph: { color: colors.navy, fontSize: 24, fontWeight: '800' },
  categoryTitle: { color: colors.text, fontSize: 11, lineHeight: 14, textAlign: 'center' },
  categoryCaption: { color: colors.textMuted, fontSize: 10 },
  offerGrid: { flexDirection: 'row', gap: spacing.sm },
  offerItem: { alignItems: 'center', backgroundColor: colors.surfaceMuted, borderRadius: radii.md, flex: 1, gap: spacing.xs, minHeight: 92, justifyContent: 'center', padding: spacing.sm },
  offerTitle: { color: colors.navy, fontWeight: '800' },
  offerCaption: { color: colors.textMuted, fontSize: 10, textAlign: 'center' },
  utilityCard: { gap: spacing.sm },
  securityCard: { gap: spacing.md },
  securityRow: { alignItems: 'center', flexDirection: 'row', gap: spacing.md },
  securityIcon: { alignItems: 'center', backgroundColor: colors.successBackground, borderRadius: radii.md, height: 44, justifyContent: 'center', width: 44 },
  securityCopy: { flex: 1, gap: spacing.xs },
  featureBanner: { alignItems: 'center', backgroundColor: colors.primarySoft, borderColor: colors.primary, borderRadius: radii.lg, borderWidth: 1, flexDirection: 'row', gap: spacing.md, padding: spacing.lg },
  featureBannerIcon: { alignItems: 'center', backgroundColor: colors.surface, borderRadius: radii.md, height: 46, justifyContent: 'center', width: 46 },
  featureBannerCopy: { flex: 1, gap: spacing.xs },
  featureBannerTitle: { color: colors.navy, fontWeight: '800' },
  featureBannerText: { color: colors.primaryDark },
  cardTitle: { color: colors.navy, fontWeight: '800' },
  cardDescription: { color: colors.textMuted },
  loadingCard: { gap: spacing.sm, paddingVertical: spacing.xl },
  feedback: { gap: spacing.md },
  refreshMessage: { color: colors.success, paddingHorizontal: spacing.sm },
  environmentNotice: { alignItems: 'center', backgroundColor: colors.primarySoft, borderRadius: radii.md, flexDirection: 'row', gap: spacing.sm, padding: spacing.md },
  environmentText: { color: colors.primaryDark, flex: 1 },
});
