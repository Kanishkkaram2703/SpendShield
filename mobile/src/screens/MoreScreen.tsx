import type { ReactNode } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { DashboardCard, IconGlyph } from '../components/DashboardUI';
import { PrimaryButton } from '../components/PrimaryButton';
import { Screen } from '../components/Screen';
import { useAuth } from '../services/AuthContext';
import { colors, spacing, typography } from '../theme';
import type { DashboardIconName } from '../components/DashboardUI';
import type { RootStackParamList } from '../types/navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'More'>;

export function MoreScreen({ navigation }: Props) {
  const { signOut } = useAuth();
  return <Screen><View style={styles.content}><Text style={[typography.eyebrow, styles.eyebrow]}>SpendShield</Text><Text style={typography.title}>More</Text><Text style={[typography.body, styles.muted]}>Fictional controls. Real banking connections are not available.</Text><Section title="Profile"><Row icon="profile" title="Profile" caption="Name, email, phone, and sign out" onPress={() => navigation.navigate('Profile')} /></Section><Section title="Account"><Row icon="account" title="BJP Bank Account" caption="Protected balance and account details" onPress={() => navigation.navigate('AccountDetails')} /><Row icon="transactions" title="Transactions" caption="Review server transaction history" onPress={() => navigation.navigate('Transactions')} /></Section><Section title="Payments"><Row icon="scan" title="Merchant QR" caption="Display either fictional merchant QR" onPress={() => navigation.navigate('DemoMerchantQr')} /><Row icon="scan" title="Scan QR" caption="Scan a structured merchant payload" onPress={() => navigation.navigate('ComingSoonPayment', { flow: 'qr' })} /><Row icon="pay" title="Pay a Merchant" caption="Choose from the server merchant catalog" onPress={() => navigation.navigate('Pay')} /><Row icon="people" title="Contacts" caption="Fictional contacts" onPress={() => navigation.navigate('Contacts')} /><Row icon="send" title="Phone Payment" caption="Requires your SpendShield MPIN" onPress={() => navigation.navigate('PhonePayment')} /><Row icon="recharge" title="Mobile Recharge" caption="Airtel, Jio, Vi, and BSNL plans" onPress={() => navigation.navigate('Recharge')} /><Row icon="bills" title="Bills" caption="Fictional biller simulation" onPress={() => navigation.navigate('Bills')} /></Section><Section title="Security"><Row icon="shield" title="Security PIN" caption="Set or change your six-digit MPIN" onPress={() => navigation.navigate('DemoSecurity')} /><Row icon="pay" title="Virtual Card" caption="Fictional card management" onPress={() => navigation.navigate('DemoCard')} /><Row icon="shield" title="Notification Center" caption="Review account activity notifications" onPress={() => navigation.navigate('Notifications')} /></Section><Section title="Entertainment"><Row icon="insights" title="BJP Entertainments" caption="BJPPrime and BJP Entertainments subscriptions" onPress={() => navigation.navigate('Subscriptions')} /></Section><PrimaryButton onPress={() => void signOut()} variant="secondary">Sign out</PrimaryButton><PrimaryButton onPress={() => navigation.goBack()} variant="quiet">Back</PrimaryButton></View></Screen>;
}

function Section({ title, children }: { title: string; children: ReactNode }) { return <View style={styles.section}><Text style={[typography.sectionTitle, styles.sectionTitle]}>{title}</Text><DashboardCard style={styles.card}>{children}</DashboardCard></View>; }
function Row({ caption, icon, onPress, title }: { caption: string; icon: DashboardIconName; onPress: () => void; title: string }) { return <PrimaryButton onPress={onPress} variant="quiet"><View style={styles.row}><IconGlyph color={colors.primaryDark} name={icon} size={23} /><View style={styles.copy}><Text style={[typography.body, styles.value]}>{title}</Text><Text style={[typography.caption, styles.muted]}>{caption}</Text></View><IconGlyph color={colors.primaryDark} name="send" size={16} /></View></PrimaryButton>; }

const styles = StyleSheet.create({ content: { gap: spacing.lg }, eyebrow: { color: colors.primaryDark }, muted: { color: colors.textMuted }, section: { gap: spacing.sm }, sectionTitle: { color: colors.navy }, card: { gap: 0, padding: spacing.sm }, row: { alignItems: 'center', flexDirection: 'row', gap: spacing.md, width: '100%' }, copy: { flex: 1, gap: spacing.xs }, value: { color: colors.navy, fontWeight: '800' } });
