import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { BrandMark } from '../components/BrandMark';
import { colors, spacing, typography } from '../theme';

export function SplashScreen() {
  return (
    <View style={styles.screen}>
      <BrandMark />
      <ActivityIndicator color={colors.teal} size="large" />
      <Text style={[typography.caption, styles.text]}>Preparing your secure workspace…</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { alignItems: 'center', backgroundColor: colors.background, flex: 1, gap: spacing.lg, justifyContent: 'center', padding: spacing.lg },
  text: { color: colors.textMuted },
});
