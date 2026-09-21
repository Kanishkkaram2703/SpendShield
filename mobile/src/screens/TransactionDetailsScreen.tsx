import { useCallback, useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { ApiError } from '../api/client';
import { getPayment } from '../api/paymentApi';
import { DashboardCard } from '../components/DashboardUI';
import { EmptyState, ErrorMessage } from '../components/Feedback';
import { PrimaryButton } from '../components/PrimaryButton';
import { Screen } from '../components/Screen';
import { useAuth } from '../services/AuthContext';
import { colors, spacing, typography } from '../theme';
import type { PaymentTransaction } from '../types/payment';
import type { RootStackParamList } from '../types/navigation';

type Props = NativeStackScreenProps<RootStackParamList, 'TransactionDetails'>;

export function TransactionDetailsScreen({ navigation, route }: Props) {
  const { session } = useAuth();
  const [transaction, setTransaction] = useState<PaymentTransaction | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadTransaction = useCallback(async () => {
    if (!session?.accessToken) {
      setError('Your session is unavailable. Please sign in again.');
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const response = await getPayment(session.accessToken, route.params.transactionId);
      setTransaction(response.transaction);
    } catch (loadError) {
      setError(getErrorMessage(loadError));
    } finally {
      setIsLoading(false);
    }
  }, [route.params.transactionId, session?.accessToken]);

  useEffect(() => {
    void loadTransaction();
  }, [loadTransaction]);

  return (
    <Screen>
      <View style={styles.content}>
        {isLoading && <DashboardCard><Text style={[typography.body, styles.muted]}>Loading transaction details…</Text></DashboardCard>}
        {error && !isLoading && (
          <View style={styles.stack}>
            <ErrorMessage message={error} />
            <PrimaryButton onPress={() => void loadTransaction()}>Try again</PrimaryButton>
          </View>
        )}
        {!isLoading && !error && !transaction && (
          <EmptyState title="Transaction unavailable" message="This transaction could not be found for your account." />
        )}
        {!isLoading && !error && transaction && <TransactionDetails transaction={transaction} />}
        <Text style={[typography.caption, styles.disclaimer]}>Simulated transaction only. No real funds moved.</Text>
        <PrimaryButton onPress={() => navigation.goBack()} variant="secondary">Back</PrimaryButton>
      </View>
    </Screen>
  );
}

function TransactionDetails({ transaction }: { transaction: PaymentTransaction }) {
  return (
    <View style={styles.stack}>
      <DashboardCard>
        <View style={styles.statusHeader}>
          <Text style={[typography.eyebrow, styles.eyebrow]}>Payment result</Text>
          <Text style={[typography.metric, styles.amount]}>{transaction.amount} {transaction.currency}</Text>
          <View style={[styles.transactionStatus, transaction.status === 'COMPLETED' ? styles.completed : styles.notCompleted]}>
            <Text style={[typography.caption, styles.transactionStatusText]}>{transaction.status}</Text>
          </View>
        </View>
        <Detail label="Type" value={formatTransactionType(transaction.transaction_type)} />
        <Detail label="Direction" value={transaction.direction} />
        <Detail label="Merchant / counterparty" value={transaction.merchant_name || transaction.counterparty_name || transaction.beneficiary_name || 'Not available'} />
        <Detail label="Payment method" value={transaction.transaction_channel || 'Not available'} />
        <Detail label="Reference" value={transaction.transaction_id} />
        {transaction.transfer_reference ? <Detail label="Transfer reference" value={transaction.transfer_reference} /> : null}
        <Detail label="Created" value={formatDate(transaction.created_at)} />
        {transaction.note ? <Detail label="Note" value={transaction.note} /> : null}
        {transaction.failure_reason ? <Detail label="Failure reason" value={transaction.failure_reason} /> : null}
      </DashboardCard>
    </View>
  );
}

function formatTransactionType(value: string): string {
  return value.replace(/_DEMO$|_SIMULATED$/g, '').replace(/_/g, ' ').toLowerCase().replace(/^\w/, (letter) => letter.toUpperCase());
}

function Detail({ label, value }: { label: string; value: string }) {
  return <View style={styles.detail}><Text style={[typography.caption, styles.muted]}>{label}</Text><Text style={[typography.body, styles.value]}>{value}</Text></View>;
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Date unavailable' : date.toLocaleString();
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return 'Transaction details could not be loaded. Please try again.';
}

const styles = StyleSheet.create({
  content: { gap: spacing.lg },
  stack: { gap: spacing.md },
  muted: { color: colors.textMuted },
  statusHeader: { alignItems: 'flex-start', gap: spacing.sm, paddingBottom: spacing.sm },
  eyebrow: { color: colors.primaryDark },
  amount: { color: colors.navy },
  detail: { borderBottomColor: colors.border, borderBottomWidth: 1, gap: spacing.xs, paddingVertical: spacing.sm },
  value: { color: colors.text, fontWeight: '700' },
  transactionStatus: { borderRadius: 8, paddingHorizontal: spacing.sm, paddingVertical: spacing.xs },
  completed: { backgroundColor: colors.successBackground },
  notCompleted: { backgroundColor: colors.warningBackground },
  transactionStatusText: { color: colors.navy, fontWeight: '800' },
  disclaimer: { color: colors.textMuted, textAlign: 'center' },
});
