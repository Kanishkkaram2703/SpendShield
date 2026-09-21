import { useCallback, useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { ApiError } from '../api/client';
import { listPayments } from '../api/paymentApi';
import { DashboardCard, IconGlyph } from '../components/DashboardUI';
import { EmptyState, ErrorMessage } from '../components/Feedback';
import { PrimaryButton } from '../components/PrimaryButton';
import { Screen } from '../components/Screen';
import { useAuth } from '../services/AuthContext';
import { colors, radii, spacing, typography } from '../theme';
import type { PaymentTransaction } from '../types/payment';
import type { RootStackParamList } from '../types/navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'Transactions'>;

export function TransactionsScreen({ navigation }: Props) {
  const { session } = useAuth();
  const [transactions, setTransactions] = useState<PaymentTransaction[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadTransactions = useCallback(async (cursor?: string) => {
    if (!session?.accessToken) {
      setError('Your session is unavailable. Please sign in again.');
      setIsLoading(false);
      return;
    }
    if (cursor) setIsLoadingMore(true);
    else setIsLoading(true);
    setError(null);
    try {
      const page = await listPayments(session.accessToken, { cursor });
      setTransactions((current) => (cursor ? [...current, ...page.transactions] : page.transactions));
      setNextCursor(page.next_cursor);
    } catch (loadError) {
      setError(getErrorMessage(loadError));
    } finally {
      setIsLoading(false);
      setIsLoadingMore(false);
    }
  }, [session?.accessToken]);

  useEffect(() => {
    void loadTransactions();
  }, [loadTransactions]);

  return (
    <Screen>
      <View style={styles.content}>
        <View style={styles.heading}>
          <Text style={[typography.eyebrow, styles.eyebrow]}>Private activity</Text>
          <Text style={[typography.title, styles.title]}>Transactions</Text>
          <Text style={[typography.body, styles.subtitle]}>Your simulated payment history, newest first.</Text>
        </View>

        {isLoading && <DashboardCard><Text style={[typography.body, styles.subtitle]}>Loading transactions…</Text></DashboardCard>}
        {error && !isLoading && (
          <View style={styles.stack}>
            <ErrorMessage message={error} />
            <PrimaryButton onPress={() => void loadTransactions()}>Try again</PrimaryButton>
          </View>
        )}
        {!isLoading && !error && transactions.length === 0 && (
          <EmptyState title="No transactions yet" message="Your simulated payments will appear here." />
        )}
        {!isLoading && !error && transactions.length > 0 && (
          <View style={styles.list}>
            {transactions.map((transaction) => (
              <TransactionRow
                key={transaction.transaction_id}
                onPress={() => navigation.navigate('TransactionDetails', { transactionId: transaction.transaction_id })}
                transaction={transaction}
              />
            ))}
            {nextCursor && (
              <PrimaryButton loading={isLoadingMore} onPress={() => void loadTransactions(nextCursor)} variant="secondary">
                Load more
              </PrimaryButton>
            )}
          </View>
        )}
        <Text style={[typography.caption, styles.disclaimer]}>Simulated transactions only. No real funds moved.</Text>
      </View>
    </Screen>
  );
}

function TransactionRow({ onPress, transaction }: { onPress: () => void; transaction: PaymentTransaction }) {
  const isCompleted = transaction.status === 'COMPLETED';
  const counterparty = transaction.merchant_name || transaction.counterparty_name || transaction.beneficiary_name || 'Party';
  return (
    <Pressable accessibilityLabel={`Transaction with ${counterparty}, ${transaction.status}`} accessibilityRole="button" onPress={onPress} style={styles.row}>
      <View style={[styles.transactionIcon, isCompleted ? styles.completedIcon : styles.otherIcon]}>
        <IconGlyph color={isCompleted ? colors.success : colors.primaryDark} name="transactions" size={22} />
      </View>
      <View style={styles.rowCopy}>
        <Text numberOfLines={1} style={[typography.body, styles.merchant]}>{transaction.merchant_name || transaction.counterparty_name || transaction.beneficiary_name || 'Simulated payment'}</Text>
        <Text style={[typography.caption, styles.meta]}>{formatTransactionType(transaction.transaction_type)} · {formatDate(transaction.created_at)}</Text>
      </View>
      <View style={styles.amountBlock}>
        <Text style={[typography.body, transaction.direction === 'CREDIT' ? styles.creditAmount : styles.amount]}>{transaction.direction === 'CREDIT' ? '+' : '−'}{transaction.amount}</Text>
        <Text style={[typography.caption, isCompleted ? styles.success : styles.status]}>{transaction.status}</Text>
      </View>
    </Pressable>
  );
}

function formatTransactionType(value: string): string {
  return value.replace(/_DEMO$|_SIMULATED$/g, '').replace(/_/g, ' ').toLowerCase().replace(/^\w/, (letter) => letter.toUpperCase());
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Date unavailable' : date.toLocaleDateString();
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return 'Transactions could not be loaded. Please try again.';
}

const styles = StyleSheet.create({
  content: { gap: spacing.lg },
  heading: { gap: spacing.sm, paddingVertical: spacing.md },
  eyebrow: { color: colors.primaryDark },
  title: { color: colors.navy },
  subtitle: { color: colors.textMuted },
  stack: { gap: spacing.md },
  list: { backgroundColor: colors.surface, borderColor: colors.border, borderRadius: radii.lg, borderWidth: 1, overflow: 'hidden' },
  row: { alignItems: 'center', borderBottomColor: colors.border, borderBottomWidth: 1, flexDirection: 'row', gap: spacing.md, minHeight: 76, paddingHorizontal: spacing.md, paddingVertical: spacing.sm },
  transactionIcon: { alignItems: 'center', borderRadius: radii.md, height: 42, justifyContent: 'center', width: 42 },
  completedIcon: { backgroundColor: colors.successBackground },
  otherIcon: { backgroundColor: colors.primarySoft },
  rowCopy: { flex: 1, gap: spacing.xs },
  merchant: { color: colors.navy, fontWeight: '800' },
  meta: { color: colors.textMuted },
  amountBlock: { alignItems: 'flex-end', gap: spacing.xs },
  amount: { color: colors.navy, fontWeight: '800' },
  creditAmount: { color: colors.success, fontWeight: '800' },
  success: { color: colors.success, fontWeight: '800' },
  status: { color: colors.textMuted, fontWeight: '800' },
  disclaimer: { color: colors.textMuted, textAlign: 'center' },
});
