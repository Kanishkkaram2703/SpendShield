import { StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { BrandMark } from '../components/BrandMark';
import { PrimaryButton } from '../components/PrimaryButton';
import { Screen } from '../components/Screen';
import { colors, spacing, typography } from '../theme';
import type { RootStackParamList } from '../types/navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'Welcome'>;

export function WelcomeScreen({ navigation }: Props) {
  return (
    <Screen scroll={false}>
      <View style={styles.content}>
        <BrandMark />
        <View style={styles.hero}>
          <Text style={[typography.eyebrow, styles.eyebrow]}>Financial awareness</Text>
          <Text style={[typography.title, styles.title]}>Make every rupee easier to understand.</Text>
          <Text style={[typography.body, styles.body]}>
            SpendShield helps you view your fictional spending activity clearly and build better financial awareness.
          </Text>
        </View>
        <View style={styles.actions}>
          <PrimaryButton onPress={() => navigation.navigate('Login')}>Sign in</PrimaryButton>
          <PrimaryButton onPress={() => navigation.navigate('Register')} variant="secondary">
            Create account
          </PrimaryButton>
        </View>
        <Text style={[typography.caption, styles.note]}>Simulated financial environment for development.</Text>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { flex: 1, justifyContent: 'space-between', paddingVertical: spacing.md },
  hero: { gap: spacing.md, paddingVertical: spacing.xxl },
  eyebrow: { color: colors.tealDark },
  title: { color: colors.navy },
  body: { color: colors.textMuted },
  actions: { gap: spacing.md },
  note: { color: colors.textMuted, paddingTop: spacing.lg, textAlign: 'center' },
});
