import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { ApiError } from '../api/client';
import { BackendDiagnostic } from '../components/BackendDiagnostic';
import { BrandMark } from '../components/BrandMark';
import { ErrorMessage } from '../components/Feedback';
import { PrimaryButton } from '../components/PrimaryButton';
import { Screen } from '../components/Screen';
import { TextField } from '../components/TextField';
import { useAuth } from '../services/AuthContext';
import { colors, spacing, typography } from '../theme';
import type { RootStackParamList } from '../types/navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'Register'>;

const messageForError = (error: unknown): string => {
  if (error instanceof ApiError) return error.message;
  return 'Account creation could not be completed. Please try again.';
};

export function RegisterScreen({ navigation }: Props) {
  const { signUp } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [error, setError] = useState('');
  const [failure, setFailure] = useState<unknown>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const submit = async () => {
    setError('');
    setFailure(null);
    if (!email.trim() || !password || !confirmation) {
      setError('Complete all fields to create your account.');
      return;
    }
    if (password !== confirmation) {
      setError('Passwords do not match.');
      return;
    }
    setIsSubmitting(true);
    try {
      await signUp(email, password);
      navigation.replace('Login', { email: email.trim().toLowerCase(), registered: true });
    } catch (submissionError) {
      setFailure(submissionError);
      setError(messageForError(submissionError));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Screen>
      <View style={styles.content}>
        <BrandMark />
        <View style={styles.heading}>
          <Text style={[typography.title, styles.title]}>Create your account</Text>
          <Text style={[typography.body, styles.subtitle]}>Start with a secure SpendShield identity.</Text>
        </View>
        {error ? <ErrorMessage message={error} /> : null}
        {failure ? <BackendDiagnostic error={failure} /> : null}
        <View style={styles.form}>
          <TextField autoCapitalize="none" autoComplete="email" keyboardType="email-address" label="Email" onChangeText={setEmail} value={email} />
          <TextField autoCapitalize="none" autoComplete="new-password" label="Password" onChangeText={setPassword} secureTextEntry value={password} />
          <TextField autoCapitalize="none" autoComplete="new-password" label="Confirm password" onChangeText={setConfirmation} secureTextEntry value={confirmation} />
          <Text style={[typography.caption, styles.hint]}>Use 8–128 characters. The backend validates the final request.</Text>
          <PrimaryButton loading={isSubmitting} onPress={() => void submit()}>
            Create account
          </PrimaryButton>
        </View>
        <PrimaryButton onPress={() => navigation.navigate('Login')} variant="quiet">
          I already have an account
        </PrimaryButton>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { gap: spacing.lg },
  heading: { gap: spacing.sm, paddingTop: spacing.xl },
  title: { color: colors.navy },
  subtitle: { color: colors.textMuted },
  form: { gap: spacing.md },
  hint: { color: colors.textMuted },
});
