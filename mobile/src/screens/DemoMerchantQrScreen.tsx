import { useEffect, useState } from 'react';
import { Share, StyleSheet, Text, View } from 'react-native';
import QRCode from 'react-native-qrcode-svg';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { listDemoMerchants } from '../api/demoMerchantApi';
import { DashboardCard } from '../components/DashboardUI';
import { EmptyState, ErrorMessage } from '../components/Feedback';
import { PrimaryButton } from '../components/PrimaryButton';
import { Screen } from '../components/Screen';
import { useAuth } from '../services/AuthContext';
import { colors, radii, spacing, typography } from '../theme';
import type { DemoMerchant } from '../types/demoMerchant';
import type { RootStackParamList } from '../types/navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'DemoMerchantQr'>;

export function DemoMerchantQrScreen({ navigation }: Props) {
  const { session } = useAuth();
  const [merchants, setMerchants] = useState<DemoMerchant[]>([]);
  const [selected, setSelected] = useState<DemoMerchant | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    if (!session?.accessToken) return;
    setLoading(true);
    setError(null);
    try {
      const result = await listDemoMerchants(session.accessToken);
      setMerchants(result.merchants);
      setSelected((current) => result.merchants.find((item) => item.merchant_id === current?.merchant_id) || result.merchants[0] || null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Merchants could not be loaded.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, [session?.accessToken]);

  const sharePayload = async () => {
    if (!selected) return;
    await Share.share({ message: `SpendShield merchant QR\n${selected.merchant_name}\n${selected.qr_payload}` });
  };

  return (
    <Screen>
      <View style={styles.content}>
        <Text style={[typography.eyebrow, styles.eyebrow]}>Classroom simulation</Text>
        <Text style={typography.title}>Merchant QR</Text>
        <Text style={[typography.body, styles.muted]}>These codes contain structured SpendShield data only. They are not UPI, banking, or real payment QR codes.</Text>
        {error && <ErrorMessage message={error} />}
        {loading && <DashboardCard><Text style={[typography.body, styles.value]}>Loading merchants...</Text></DashboardCard>}
        {!loading && merchants.length === 0 && <EmptyState title="No merchants" message="The fictional merchant registry is empty." />}
        {!loading && merchants.length > 0 && <View style={styles.merchantList}>{merchants.map((merchant) => <PrimaryButton key={merchant.merchant_id} onPress={() => setSelected(merchant)} variant={selected?.merchant_id === merchant.merchant_id ? 'primary' : 'secondary'}>{merchant.merchant_name}</PrimaryButton>)}</View>}
        {selected && <DashboardCard style={styles.qrCard}>
          <Text style={[typography.sectionTitle, styles.value]}>{selected.merchant_name}</Text>
          <Text style={[typography.body, styles.muted]}>{selected.category}</Text>
          <Text style={[typography.caption, styles.notice]}>FICTIONAL MERCHANT · SIMULATION ONLY — NO REAL MONEY</Text>
          <Text style={[typography.caption, styles.muted]}>{selected.merchant_id} · BJP Bank · {selected.status}</Text>
          <View style={styles.qrFrame}><QRCode value={selected.qr_payload} size={220} backgroundColor="white" color={colors.navy} /></View>
          <Text style={[typography.caption, styles.notice]}>Scan this QR from another screen or use the gallery flow. Simulation only.</Text>
          <PrimaryButton onPress={() => void sharePayload()} variant="secondary">Share QR payload</PrimaryButton>
        </DashboardCard>}
        <PrimaryButton onPress={() => navigation.goBack()} variant="quiet">Back</PrimaryButton>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { gap: spacing.lg },
  eyebrow: { color: colors.primaryDark },
  muted: { color: colors.textMuted },
  value: { color: colors.navy, fontWeight: '800' },
  merchantList: { gap: spacing.sm },
  qrCard: { alignItems: 'center', gap: spacing.sm },
  qrFrame: { backgroundColor: colors.white, borderColor: colors.border, borderRadius: radii.md, borderWidth: 1, padding: spacing.md },
  notice: { color: colors.primaryDark, textAlign: 'center' },
});
