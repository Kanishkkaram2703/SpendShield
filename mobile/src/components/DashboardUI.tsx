import type { PropsWithChildren } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { cardStyles, colors, radii, spacing, typography } from '../theme';
import type { AccountStatus } from '../types/account';

export type DashboardIconName =
  | 'account' | 'bank' | 'bills' | 'chart' | 'home' | 'insights' | 'lock'
  | 'merchant' | 'more' | 'people' | 'pay' | 'plus' | 'profile' | 'recharge'
  | 'scan' | 'send' | 'search' | 'shield' | 'transactions';

const iconGlyphs: Record<DashboardIconName, keyof typeof Ionicons.glyphMap> = {
  account: 'wallet-outline', bank: 'business-outline', bills: 'receipt-outline',
  chart: 'bar-chart-outline', home: 'home-outline', insights: 'sparkles-outline',
  lock: 'lock-closed-outline', merchant: 'storefront-outline',
  more: 'ellipsis-horizontal-circle-outline', people: 'people-outline',
  pay: 'arrow-up-circle-outline', plus: 'add-circle-outline',
  profile: 'person-circle-outline', recharge: 'phone-portrait-outline',
  scan: 'scan-outline', send: 'send-outline', search: 'search-outline',
  shield: 'shield-checkmark-outline', transactions: 'receipt-outline',
};

export function IconGlyph({ color = colors.text, name, size = 22 }: {
  color?: string; name: DashboardIconName; size?: number;
}) {
  return <Ionicons accessibilityLabel={name} color={color} name={iconGlyphs[name]} size={size} />;
}

export function DashboardCard({ children, style }: PropsWithChildren<{ style?: object }>) {
  return <View style={[cardStyles.base, styles.card, style]}>{children}</View>;
}

export function SectionHeader({ action, onAction, title }: {
  action?: string; onAction?: () => void; title: string;
}) {
  return (
    <View style={styles.sectionHeader}>
      <Text style={[typography.sectionTitle, styles.sectionTitle]}>{title}</Text>
      {action ? (
        <Pressable accessibilityLabel={action} accessibilityRole="button" disabled={!onAction} onPress={onAction}>
          <Text style={[typography.caption, styles.sectionAction, !onAction && styles.disabledText]}>{action}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

export function StatusBadge({ status }: { status: AccountStatus }) {
  const statusStyle = statusStyles[status];
  return (
    <View style={[styles.statusBadge, { backgroundColor: statusStyle.backgroundColor }]}>
      <View style={[styles.statusDot, { backgroundColor: statusStyle.color }]} />
      <Text style={[typography.caption, { color: statusStyle.color, fontWeight: '800' }]}>{status}</Text>
    </View>
  );
}

export function QuickAction({ caption, disabled = false, icon, onPress, title }: {
  caption: string; disabled?: boolean; icon: DashboardIconName; onPress?: () => void; title: string;
}) {
  return (
    <Pressable accessible accessibilityLabel={`${title}. ${caption}`} accessibilityState={{ disabled }}
      accessibilityRole="button" disabled={disabled} onPress={onPress}
      style={[styles.quickAction, disabled && styles.quickActionDisabled]}>
      <View style={styles.quickActionIcon}><IconGlyph color={colors.primaryDark} name={icon} size={21} /></View>
      <Text numberOfLines={2} style={[typography.caption, styles.quickActionTitle]}>{title}</Text>
      <Text style={[typography.caption, styles.quickActionCaption]}>{caption}</Text>
    </Pressable>
  );
}

export function BottomNavigation({ onNavigate }: {
  onNavigate?: (destination: 'Pay' | 'More' | 'Bills' | 'Qr') => void;
}) {
  const items: Array<{ icon: DashboardIconName; label: string; active?: boolean }> = [
    { icon: 'home', label: 'Home', active: true }, { icon: 'pay', label: 'Pay Now' },
    { icon: 'bills', label: 'Bills & Recharges' }, { icon: 'more', label: 'More' },
  ];
  return (
    <View accessibilityLabel="Primary navigation" style={styles.bottomNavigationWrap}>
      <Pressable accessibilityLabel="Scan QR" accessibilityRole="button"
        onPress={() => onNavigate?.('Qr')} style={styles.scanFab}>
        <IconGlyph color={colors.white} name="scan" size={24} />
        <Text style={styles.scanFabLabel}>SCAN</Text>
      </Pressable>
      <View style={styles.bottomNavigation}>
        {items.map((item) => (
          <Pressable accessible accessibilityLabel={item.label} accessibilityRole="tab"
            accessibilityState={{ selected: item.active }} disabled={item.active}
            onPress={() => onNavigate?.(item.label === 'Pay Now' ? 'Pay' : item.label === 'More' ? 'More' : 'Bills')}
            key={item.label} style={styles.navItem}>
            <View style={[styles.navIcon, item.active && styles.navIconActive]}>
              <IconGlyph color={item.active ? colors.primaryDark : colors.textMuted} name={item.icon} size={20} />
            </View>
            <Text style={[typography.navLabel, item.active ? styles.navLabelActive : styles.navLabelInactive]}>{item.label}</Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

export function UtilityRow({ caption, disabled = true, icon, loading = false, onPress, title }: {
  caption?: string; disabled?: boolean; icon: DashboardIconName; loading?: boolean; onPress?: () => void; title: string;
}) {
  return (
    <Pressable accessibilityLabel={`${title}${disabled ? ', coming soon' : ''}`} accessibilityRole="button"
      accessibilityState={{ busy: loading, disabled: disabled || loading }} disabled={disabled || loading} onPress={onPress}
      style={[styles.utilityRow, (disabled || loading) && styles.utilityRowDisabled]}>
      {loading ? <ActivityIndicator color={colors.primaryDark} size="small" /> : <IconGlyph color={disabled ? colors.textMuted : colors.primaryDark} name={icon} size={22} />}
      <View style={styles.utilityCopy}><Text style={[typography.body, styles.utilityTitle]}>{title}</Text>
        {caption ? <Text style={[typography.caption, styles.utilityCaption]}>{caption}</Text> : null}</View>
      {!loading && <Ionicons color={disabled ? colors.textMuted : colors.primaryDark} name="chevron-forward" size={20} />}
    </Pressable>
  );
}

const statusStyles: Record<AccountStatus, { backgroundColor: string; color: string }> = {
  ACTIVE: { backgroundColor: colors.successBackground, color: colors.success },
  CLOSED: { backgroundColor: colors.errorBackground, color: colors.error },
  SUSPENDED: { backgroundColor: colors.warningBackground, color: colors.warning },
};

const styles = StyleSheet.create({
  card: { gap: spacing.md, padding: spacing.lg },
  sectionHeader: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  sectionTitle: { color: colors.navy }, sectionAction: { color: colors.primaryDark },
  disabledText: { color: colors.textMuted },
  statusBadge: { alignItems: 'center', borderRadius: radii.sm, flexDirection: 'row', gap: spacing.xs, paddingHorizontal: spacing.sm, paddingVertical: spacing.xs },
  statusDot: { borderRadius: 4, height: 8, width: 8 },
  quickAction: { alignItems: 'center', backgroundColor: colors.surface, borderColor: colors.border, borderRadius: radii.md, borderWidth: 1, flexBasis: '22%', flexGrow: 0, flexShrink: 0, gap: spacing.xs, minHeight: 104, padding: spacing.sm },
  quickActionDisabled: { opacity: 0.72 }, quickActionIcon: { alignItems: 'center', backgroundColor: colors.primarySoft, borderRadius: radii.sm, height: 36, justifyContent: 'center', width: 36 },
  quickActionTitle: { color: colors.navy, fontSize: 11, fontWeight: '800', lineHeight: 14, textAlign: 'center' }, quickActionCaption: { color: colors.textMuted, fontSize: 11 },
  bottomNavigationWrap: { backgroundColor: colors.surface, borderColor: colors.border, borderTopWidth: 1, paddingTop: spacing.md },
  bottomNavigation: { flexDirection: 'row', justifyContent: 'space-around', paddingBottom: spacing.sm, paddingHorizontal: spacing.xs },
  navItem: { alignItems: 'center', flex: 1, gap: spacing.xs }, navIcon: { alignItems: 'center', borderRadius: radii.sm, height: 30, justifyContent: 'center', width: 44 }, navIconActive: { backgroundColor: colors.primarySoft }, navLabelActive: { color: colors.primaryDark }, navLabelInactive: { color: colors.textMuted },
  scanFab: { alignItems: 'center', backgroundColor: colors.primary, borderColor: colors.surface, borderRadius: 32, borderWidth: 4, elevation: 6, height: 64, justifyContent: 'center', left: '50%', marginLeft: -32, position: 'absolute', top: -32, width: 64 }, scanFabLabel: { color: colors.white, fontSize: 10, fontWeight: '800', marginTop: -2 },
  utilityRow: { alignItems: 'center', borderBottomColor: colors.border, borderBottomWidth: 1, flexDirection: 'row', gap: spacing.md, minHeight: 64, paddingVertical: spacing.sm }, utilityRowDisabled: { opacity: 0.64 }, utilityCopy: { flex: 1, gap: spacing.xs }, utilityTitle: { color: colors.navy, fontWeight: '700' }, utilityCaption: { color: colors.textMuted },
});
