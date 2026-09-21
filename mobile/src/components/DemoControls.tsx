import { Pressable, StyleSheet, Text, View } from 'react-native';

import { DashboardCard } from './DashboardUI';
import { colors, radii, spacing, typography } from '../theme';

export function NumericKeypad({
  value,
  onChange,
  maxLength = 12,
  masked = false,
  decimal = true,
}: {
  value: string;
  onChange: (value: string) => void;
  maxLength?: number;
  masked?: boolean;
  decimal?: boolean;
}) {
  const press = (key: string) => {
    if (key === 'clear') return onChange('');
    if (key === 'backspace') return onChange(value.slice(0, -1));
    if (value.length >= maxLength) return;
    if (key === '.' && (!decimal || value.includes('.'))) return;
    if (key === '.' && !value) return onChange('0.');
    if (key !== '.' && value === '0') return onChange(key);
    onChange(value + key);
  };

  const keys = decimal ? ['1', '2', '3', '4', '5', '6', '7', '8', '9', '.', '0', 'backspace'] : ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'clear', '0', 'backspace'];
  const display = masked ? '•'.repeat(value.length) : value || '0';

  return (
    <View style={styles.keypad}>
      <Text accessibilityLabel={masked ? 'Masked input' : `Current value ${display}`} style={[typography.heading, styles.value]}>{display}</Text>
      <View style={styles.grid}>
        {keys.map((key) => (
          <Pressable accessibilityRole="button" accessibilityLabel={key === 'backspace' ? 'Backspace' : key === 'clear' ? 'Clear' : key} key={key} onPress={() => press(key)} style={styles.key}>
            <Text style={[typography.body, styles.keyText]}>{key === 'backspace' ? '⌫' : key === 'clear' ? 'C' : key}</Text>
          </Pressable>
        ))}
      </View>
      {decimal && <Pressable accessibilityRole="button" onPress={() => press('clear')} style={styles.clear}><Text style={[typography.caption, styles.clearText]}>Clear</Text></Pressable>}
    </View>
  );
}

export function DemoMpinPanel({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return (
    <DashboardCard>
      <Text style={[typography.sectionTitle, styles.title]}>Enter your six-digit SpendShield MPIN</Text>
      <Text style={[typography.caption, styles.muted]}>This is not a real bank PIN. It is verified by the SpendShield backend.</Text>
      <NumericKeypad decimal={false} masked maxLength={6} onChange={onChange} value={value} />
    </DashboardCard>
  );
}

const styles = StyleSheet.create({
  keypad: { gap: spacing.sm },
  value: { color: colors.navy, textAlign: 'center' },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm, justifyContent: 'center' },
  key: { alignItems: 'center', backgroundColor: colors.surfaceMuted, borderColor: colors.border, borderRadius: radii.md, borderWidth: 1, height: 48, justifyContent: 'center', width: '30%' },
  keyText: { color: colors.navy, fontWeight: '800' },
  clear: { alignSelf: 'center', padding: spacing.sm },
  clearText: { color: colors.primaryDark, fontWeight: '800' },
  title: { color: colors.navy },
  muted: { color: colors.textMuted },
});
