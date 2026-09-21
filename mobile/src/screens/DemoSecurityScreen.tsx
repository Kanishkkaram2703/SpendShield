import { useEffect, useState } from 'react';
import { Alert, StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { getDemoSecurityStatus, resetDemoMpin, setDemoMpin } from '../api/demoSecurityApi';
import { DashboardCard } from '../components/DashboardUI';
import { ErrorMessage } from '../components/Feedback';
import { PrimaryButton } from '../components/PrimaryButton';
import { Screen } from '../components/Screen';
import { TextField } from '../components/TextField';
import { useAuth } from '../services/AuthContext';
import { colors, spacing, typography } from '../theme';
import type { DemoSecurityStatus } from '../types/demoSecurity';
import type { RootStackParamList } from '../types/navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'DemoSecurity'>;

export function DemoSecurityScreen({ navigation }: Props) {
  const { session } = useAuth();
  const [status, setStatus] = useState<DemoSecurityStatus | null>(null);
  const [pin, setPin] = useState('');
  const [confirmPin, setConfirmPin] = useState('');
  const [currentPin, setCurrentPin] = useState('');
  const [resetPassword, setResetPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    if (!session?.accessToken) return;
    try {
      setStatus(await getDemoSecurityStatus(session.accessToken));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Security settings could not be loaded.');
    }
  };

  useEffect(() => { void load(); }, [session?.accessToken]);

  const save = async () => {
    if (!session?.accessToken) return;
    if (!/^\d{6}$/.test(pin) || pin !== confirmPin || (status?.configured && !/^\d{6}$/.test(currentPin))) {
      setError(status?.configured ? 'Enter the current MPIN and matching six-digit replacement MPIN.' : 'Enter matching six-digit MPIN values.');
      return;
    }
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const next = await setDemoMpin(session.accessToken, { pin, confirm_pin: confirmPin, ...(status?.configured ? { current_pin: currentPin } : {}) });
      setStatus(next);
      setPin('');
      setConfirmPin('');
      setCurrentPin('');
      setMessage('MPIN saved. It will be required for protected operations.');
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'MPIN could not be saved.');
    } finally {
      setSaving(false);
    }
  };

  const reset = () => {
    if (!session?.accessToken) return;
    if (!resetPassword) {
      setError('Enter your account password to reset the MPIN.');
      return;
    }
    Alert.alert('Reset MPIN?', 'The existing MPIN will be removed. You can immediately create a new six-digit MPIN.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Reset',
        style: 'destructive',
        onPress: () => {
          setSaving(true);
          setError(null);
          void resetDemoMpin(session.accessToken, resetPassword)
            .then((next) => {
              setStatus(next);
              setResetPassword('');
              setCurrentPin('');
              setMessage('Existing MPIN removed. Create a new one below.');
            })
            .catch((cause) => setError(cause instanceof Error ? cause.message : 'MPIN could not be reset.'))
            .finally(() => setSaving(false));
        },
      },
    ]);
  };

  return (
    <Screen>
      <View style={styles.content}>
        <Text style={[typography.eyebrow, styles.eyebrow]}>Security</Text>
        <Text style={typography.title}>Security PIN</Text>
        <Text style={[typography.body, styles.muted]}>This MPIN protects fictional SpendShield operations only. It is not a bank PIN and is never displayed after entry.</Text>
        {error && <ErrorMessage message={error} />}
        {message && <DashboardCard><Text style={[typography.body, styles.success]}>{message}</Text></DashboardCard>}
        <DashboardCard>
          <Text style={[typography.sectionTitle, styles.value]}>{status?.configured ? 'Change MPIN' : 'Create MPIN'}</Text>
          {status?.locked && <Text style={[typography.body, styles.danger]}>The MPIN is locked after repeated failed attempts. Reset it with your account password.</Text>}
          {status?.configured && <TextField editable={!status.locked} keyboardType="number-pad" label="Current six-digit MPIN" maxLength={6} onChangeText={setCurrentPin} secureTextEntry value={currentPin} />}
          {!status?.configured || !status?.locked ? <><TextField keyboardType="number-pad" label="New six-digit MPIN" maxLength={6} onChangeText={setPin} secureTextEntry value={pin} /><TextField keyboardType="number-pad" label="Confirm MPIN" maxLength={6} onChangeText={setConfirmPin} secureTextEntry value={confirmPin} /><PrimaryButton loading={saving} onPress={() => void save()}>Save MPIN</PrimaryButton></> : null}
        </DashboardCard>
        {status?.configured && <DashboardCard>
          <Text style={[typography.sectionTitle, styles.value]}>Forgot or locked your MPIN?</Text>
          <Text style={[typography.caption, styles.muted]}>Re-authenticate with your SpendShield account password to remove it, then create a new MPIN.</Text>
          <TextField label="Account password" onChangeText={setResetPassword} secureTextEntry value={resetPassword} />
          <PrimaryButton loading={saving} onPress={reset} variant="secondary">Reset MPIN</PrimaryButton>
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
  success: { color: colors.success, fontWeight: '700' },
  danger: { color: colors.error, fontWeight: '700' },
});
