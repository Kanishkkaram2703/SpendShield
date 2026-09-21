import { DefaultTheme, type Theme } from '@react-navigation/native';
import { StyleSheet } from 'react-native';

export const colors = {
  navy: '#0B1F33',
  navySoft: '#163A59',
  primary: '#5B8DEF',
  primaryDark: '#3F6DCC',
  primarySoft: '#EAF2FF',
  teal: '#1A9A8A',
  tealDark: '#127467',
  mint: '#DDF5EF',
  background: '#F5F7FB',
  surface: '#FFFFFF',
  surfaceMuted: '#F8FAFD',
  text: '#102A43',
  textMuted: '#627D98',
  border: '#D9E2EC',
  error: '#B42318',
  errorBackground: '#FEE4E2',
  success: '#16794C',
  successBackground: '#E7F6EC',
  warning: '#A15C00',
  warningBackground: '#FFF4D8',
  whiteMuted: '#DDE8FF',
  white: '#FFFFFF',
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
};

export const radii = {
  sm: 8,
  md: 14,
  lg: 22,
};

export const typography = StyleSheet.create({
  eyebrow: { fontSize: 12, fontWeight: '700', letterSpacing: 1.1, textTransform: 'uppercase' },
  title: { fontSize: 30, fontWeight: '800', lineHeight: 36 },
  heading: { fontSize: 22, fontWeight: '800', lineHeight: 28 },
  sectionTitle: { fontSize: 18, fontWeight: '800', lineHeight: 24 },
  metric: { fontSize: 36, fontWeight: '800', lineHeight: 42 },
  body: { fontSize: 16, lineHeight: 24 },
  caption: { fontSize: 13, lineHeight: 19 },
  navLabel: { fontSize: 11, fontWeight: '700', lineHeight: 14 },
});

export const cardStyles = StyleSheet.create({
  base: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radii.lg,
    borderWidth: 1,
    shadowColor: colors.navy,
    shadowOffset: { height: 8, width: 0 },
    shadowOpacity: 0.06,
    shadowRadius: 18,
    elevation: 2,
  },
});

export const navigationTheme: Theme = {
  ...DefaultTheme,
  dark: false,
  colors: {
    primary: colors.primary,
    background: colors.background,
    card: colors.surface,
    text: colors.text,
    border: colors.border,
    notification: colors.error,
  },
};
