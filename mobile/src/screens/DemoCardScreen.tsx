import { useEffect, useState } from 'react';
import { Alert, StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { createCard, listCards, updateCardLimit, updateCardPin, updateCardStatus } from '../api/demoModulesApi';
import { DashboardCard } from '../components/DashboardUI';
import { DemoMpinPanel } from '../components/DemoControls';
import { ErrorMessage } from '../components/Feedback';
import { PrimaryButton } from '../components/PrimaryButton';
import { Screen } from '../components/Screen';
import { TextField } from '../components/TextField';
import { useAuth } from '../services/AuthContext';
import { colors, spacing, typography } from '../theme';
import type { DemoCard } from '../types/demoModules';
import type { RootStackParamList } from '../types/navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'DemoCard'>;

export function DemoCardScreen({ navigation }: Props) {
  const { session } = useAuth();
  const [card, setCard] = useState<DemoCard | null>(null);
  const [demoMpin, setDemoMpin] = useState('');
  const [pin, setPin] = useState('');
  const [confirmPin, setConfirmPin] = useState('');
  const [limit, setLimit] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    if (!session?.accessToken) return;
    setLoading(true);
    try {
      const result = await listCards(session.accessToken);
      setCard(result.cards[0] || null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Card could not be loaded.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, [session?.accessToken]);

  const validMpin = () => {
    if (!/^\d{6}$/.test(demoMpin)) {
      setError('Enter your six-digit SpendShield MPIN first.');
      return false;
    }
    return true;
  };

  const runStatus = (action: 'freeze' | 'unfreeze' | 'block') => {
    if (!session?.accessToken || !card || !validMpin()) return;
    const label = action === 'block' ? 'block' : action;
    Alert.alert(`${label} card?`, 'This changes only the fictional classroom card.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: label,
        style: action === 'block' ? 'destructive' : 'default',
        onPress: () => void updateCardStatus(session.accessToken, card.card_id, action, demoMpin)
          .then((next) => {
            setCard(next);
            setDemoMpin('');
            setMessage(`Card ${next.status.toLowerCase()}.`);
          })
          .catch((cause) => setError(cause instanceof Error ? cause.message : 'Card status could not be changed.')),
      },
    ]);
  };

  const savePin = async () => {
    if (!session?.accessToken || !card || !validMpin()) return;
    if (!/^\d{4,6}$/.test(pin) || pin !== confirmPin) {
      setError('Enter matching six-digit PIN values.');
      return;
    }
    try {
      setCard(await updateCardPin(session.accessToken, card.card_id, pin, confirmPin, demoMpin));
      setDemoMpin('');
      setPin('');
      setConfirmPin('');
      setMessage('Card PIN updated.');
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Card PIN could not be updated.');
    }
  };

  const saveLimit = async () => {
    if (!session?.accessToken || !card || !validMpin()) return;
    if (!/^\d+(\.\d{1,2})?$/.test(limit) || Number(limit) <= 0) {
      setError('Enter a valid positive spending limit.');
      return;
    }
    try {
      setCard(await updateCardLimit(session.accessToken, card.card_id, limit, demoMpin));
      setDemoMpin('');
      setLimit('');
      setMessage('Spending limit updated.');
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Spending limit could not be updated.');
    }
  };

  if (loading) return <Screen><DashboardCard><Text style={typography.body}>Loading virtual card...</Text></DashboardCard></Screen>;

  return (
    <Screen>
      <View style={styles.content}>
        <Text style={[typography.eyebrow, styles.eyebrow]}>Virtual card</Text>
        <Text style={typography.title}>Virtual card</Text>
        <Text style={[typography.caption, styles.muted]}>SIMULATION ONLY — NO REAL MONEY</Text>
        {error && <ErrorMessage message={error} />}
        {message && <Text style={[typography.body, styles.success]}>{message}</Text>}
        {!card ? (
          <>
            <DashboardCard><Text style={[typography.body, styles.muted]}>No virtual card exists yet.</Text></DashboardCard>
            <PrimaryButton onPress={() => {
              if (session?.accessToken) void createCard(session.accessToken)
                .then(setCard)
                .catch((cause) => setError(cause instanceof Error ? cause.message : 'Card could not be created.'));
            }}>Create card</PrimaryButton>
          </>
        ) : (
          <>
            <DashboardCard style={styles.card}>
              <Text style={styles.cardBrand}>BJP BANK</Text>
              <Text style={styles.cardNumber}>{card.masked_card_number}</Text>
              <Text style={styles.cardMeta}>VALID THRU {card.expiry} · {card.status}</Text>
              <Text style={styles.cardMeta}>{card.holder_name}</Text>
            </DashboardCard>
            <DashboardCard>
              <Text style={[typography.sectionTitle, styles.value]}>Card controls</Text>
              <Text style={[typography.caption, styles.muted]}>Confirm each sensitive card change with your SpendShield MPIN.</Text>
              <DemoMpinPanel onChange={setDemoMpin} value={demoMpin} />
              {card.status === 'ACTIVE' && <PrimaryButton onPress={() => runStatus('freeze')} variant="secondary">Freeze card</PrimaryButton>}
              {card.status === 'FROZEN' && <PrimaryButton onPress={() => runStatus('unfreeze')} variant="secondary">Unfreeze card</PrimaryButton>}
              {card.status !== 'BLOCKED' && <PrimaryButton onPress={() => runStatus('block')} variant="quiet">Block card</PrimaryButton>}
              <TextField keyboardType="number-pad" label="New card PIN" maxLength={6} onChangeText={setPin} secureTextEntry value={pin} />
              <TextField keyboardType="number-pad" label="Confirm card PIN" maxLength={6} onChangeText={setConfirmPin} secureTextEntry value={confirmPin} />
              <PrimaryButton onPress={() => void savePin()} variant="secondary">Change card PIN</PrimaryButton>
              <TextField keyboardType="decimal-pad" label={`Spending limit (${card.currency})`} onChangeText={setLimit} placeholder={card.spending_limit} value={limit} />
              <PrimaryButton onPress={() => void saveLimit()} variant="secondary">Update spending limit</PrimaryButton>
            </DashboardCard>
            <PrimaryButton onPress={() => navigation.navigate('Transactions')} variant="secondary">View card-compatible history</PrimaryButton>
          </>
        )}
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
  success: { color: colors.success, fontWeight: '700' },
  card: { backgroundColor: colors.navy, gap: spacing.lg, padding: spacing.xl },
  cardBrand: { color: colors.primarySoft, fontWeight: '800' },
  cardNumber: { color: colors.white, fontSize: 24, fontWeight: '800', letterSpacing: 2 },
  cardMeta: { color: colors.white, fontSize: 12, fontWeight: '700' },
});
