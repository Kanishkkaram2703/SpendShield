import { StyleSheet, Text, View } from 'react-native';

import { colors, radii, spacing, typography } from '../theme';

export function BrandMark() {
  return (
    <View style={styles.row} accessible accessibilityLabel="SpendShield">
      <View style={styles.mark}>
        <Text style={styles.markText}>S</Text>
      </View>
      <View>
        <Text style={[typography.heading, styles.brand]}>SpendShield</Text>
        <Text style={[typography.caption, styles.tagline]}>See your spending clearly.</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { alignItems: 'center', flexDirection: 'row', gap: spacing.sm },
  mark: {
    alignItems: 'center',
    backgroundColor: colors.primary,
    borderRadius: radii.md,
    height: 44,
    justifyContent: 'center',
    width: 44,
  },
  markText: { color: colors.white, fontSize: 24, fontWeight: '900' },
  brand: { color: colors.navy, fontSize: 20, lineHeight: 24 },
  tagline: { color: colors.textMuted },
});
