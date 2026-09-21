import { useEffect, useState } from 'react';
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

type Props = NativeStackScreenProps<RootStackParamList, 'Login'>;

const messageForError = (error: unknown): string => {
  if (error instanceof ApiError) return error.message;
  return 'Sign in could not be completed. Please try again.';
};

export function LoginScreen({ navigation, route }: Props) {
  const { signIn } = useAuth();
  const [email, setEmail] = useState(route.params?.email || '');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [failure, setFailure] = useState<unknown>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (route.params?.email) setEmail(route.params.email);
  }, [route.params?.email]);

  const submit = async () => {
    setError('');
    setFailure(null);
    if (!email.trim() || !password) {
      setError('Enter your email and password to continue.');
      return;
    }
    setIsSubmitting(true);
    try {
      await signIn(email, password);
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
          <Text style={[typography.title, styles.title]}>Welcome back</Text>
          {route.params?.registered ? (
            <Text style={[typography.body, styles.success]}>Account created. Sign in to continue.</Text>
          ) : (
            <Text style={[typography.body, styles.subtitle]}>Sign in to your SpendShield workspace.</Text>
          )}
        </View>
        {error ? <ErrorMessage message={error} /> : null}
        {failure ? <BackendDiagnostic error={failure} /> : null}
        <View style={styles.form}>
          <TextField autoCapitalize="none" autoComplete="email" keyboardType="email-address" label="Email" onChangeText={setEmail} value={email} />
          <TextField autoCapitalize="none" autoComplete="password" label="Password" onChangeText={setPassword} secureTextEntry value={password} />
          <PrimaryButton loading={isSubmitting} onPress={() => void submit()}>
            Sign in
          </PrimaryButton>
        </View>
        <PrimaryButton onPress={() => navigation.navigate('Register')} variant="quiet">
          Create a new account
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
  success: { color: colors.success },
  form: { gap: spacing.md },
});
