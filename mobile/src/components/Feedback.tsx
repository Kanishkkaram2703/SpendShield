import { StyleSheet, Text, View } from 'react-native';

import { colors, radii, spacing, typography } from '../theme';

export function ErrorMessage({ message }: { message: string }) {
  return (
    <View style={styles.errorBox} accessibilityRole="alert">
      <Text style={styles.errorText}>{presentErrorMessage(message)}</Text>
    </View>
  );
}

function presentErrorMessage(message: string): string {
  return message.replace(/\bdemo\b/gi, 'fictional');
}

export function EmptyState({ title, message }: { title: string; message: string }) {
  return (
    <View style={styles.empty}>
      <Text style={[typography.heading, styles.emptyTitle]}>{title}</Text>
      <Text style={[typography.body, styles.emptyMessage]}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  errorBox: { backgroundColor: colors.errorBackground, borderRadius: radii.sm, padding: spacing.md },
  errorText: { ...typography.caption, color: colors.error, fontWeight: '600' },
  empty: { alignItems: 'center', backgroundColor: colors.surface, borderRadius: radii.md, gap: spacing.sm, padding: spacing.xl },
  emptyTitle: { color: colors.navy, textAlign: 'center' },
  emptyMessage: { color: colors.textMuted, textAlign: 'center' },
});
