import { StyleSheet, Text, View } from 'react-native';

import { ApiError } from '../api/client';
import { API_BASE_URL_FOR_DISPLAY } from '../constants/config';
import { colors, radii, spacing, typography } from '../theme';

export function BackendDiagnostic({ error }: { error: unknown }) {
  const status = error instanceof ApiError ? error.status : 0;
  const detail = status === 0
    ? 'Network failure: the phone could not connect to this address.'
    : status === 408
      ? 'Timeout: the backend did not respond within the development limit.'
      : 'HTTP ' + status + ': the backend responded, but rejected or could not complete the request.';

  return (
    <View style={styles.box}>
      <Text style={styles.title}>Development connection</Text>
      <Text style={styles.detail}>{detail}</Text>
      <Text selectable style={styles.url}>API: {API_BASE_URL_FOR_DISPLAY}</Text>
      <Text style={styles.hint}>For Expo Go, use the developer computer's current LAN IPv4 address and keep the phone on the same Wi-Fi network.</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  box: {
    backgroundColor: colors.surfaceMuted,
    borderColor: colors.border,
    borderRadius: radii.sm,
    borderWidth: 1,
    gap: spacing.xs,
    padding: spacing.md,
  },
  title: { ...typography.caption, color: colors.navy, fontWeight: '800' },
  detail: { ...typography.caption, color: colors.textMuted },
  url: { ...typography.caption, color: colors.primaryDark, fontFamily: 'monospace' },
  hint: { ...typography.caption, color: colors.textMuted },
});
