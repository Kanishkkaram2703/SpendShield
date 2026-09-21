import { useEffect, useMemo, useState } from 'react';
import { CameraView, scanFromURLAsync, useCameraPermissions } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import { Linking, Pressable, StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { getMyAccount, listAccounts } from '../api/accountApi';
import { bankTransfer, payByQr, selfTransfer, sendMoney, validateQrPayload } from '../api/paymentApi';
import { DashboardCard, IconGlyph, StatusBadge } from '../components/DashboardUI';
import { ErrorMessage } from '../components/Feedback';
import { PrimaryButton } from '../components/PrimaryButton';
import { Screen } from '../components/Screen';
import { TextField } from '../components/TextField';
import { useAuth } from '../services/AuthContext';
import { colors, radii, spacing, typography } from '../theme';
import type { Account } from '../types/account';
import type { DemoPaymentResponse } from '../types/payment';
import type { RootStackParamList } from '../types/navigation';
import {
  createDemoIdempotencyKey,
  getDemoPaymentError,
  parseDemoQrPayload,
  validateAmount,
  validateNote,
  type DemoQrPayload,
} from '../validation/demoPaymentValidation';

type Props = NativeStackScreenProps<RootStackParamList, 'ComingSoonPayment'>;
type Flow = Props['route']['params']['flow'];
type Step = 'form' | 'review' | 'mpin' | 'result';
type FormMode = 'scan' | 'manual';

const FLOW_TITLES: Record<Flow, string> = {
  send: 'Send money',
  qr: 'Pay by QR',
  bank: 'Bank transfer',
  self: 'Self transfer',
};

export function ComingSoonPaymentScreen({ navigation, route }: Props) {
  const { session } = useAuth();
  const flow = route.params.flow;
  const [account, setAccount] = useState<Account | null>(null);
  const [ownedAccounts, setOwnedAccounts] = useState<Account[]>([]);
  const [step, setStep] = useState<Step>('form');
  const [error, setError] = useState<string | null>(null);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<DemoPaymentResponse | null>(null);
  const [resultAccount, setResultAccount] = useState<Account | null>(null);
  const [idempotencyKey, setIdempotencyKey] = useState<string | null>(null);

  const [receiverAccountId, setReceiverAccountId] = useState('');
  const [receiverName, setReceiverName] = useState('');
  const [destinationAccountId, setDestinationAccountId] = useState('');
  const [amount, setAmount] = useState('');
  const [note, setNote] = useState('');
  const [beneficiaryName, setBeneficiaryName] = useState('');
  const [demoBankAccountNumber, setDemoBankAccountNumber] = useState('');
  const [demoBankCode, setDemoBankCode] = useState('');
  const [remarks, setRemarks] = useState('');
  const [formMode, setFormMode] = useState<FormMode>('scan');
  const [qrPayload, setQrPayload] = useState('');
  const [qrMerchant, setQrMerchant] = useState<DemoQrPayload | null>(null);
  const [showScanner, setShowScanner] = useState(false);
  const [demoMpin, setDemoMpin] = useState('');
  const [isValidatingQr, setIsValidatingQr] = useState(false);

  useEffect(() => {
    let active = true;
    const load = async () => {
      if (!session?.accessToken) {
        setError('Your session is unavailable. Please sign in again.');
        setIsLoading(false);
        return;
      }
      try {
        const [current, accounts] = await Promise.all([
          getMyAccount(session.accessToken),
          listAccounts(session.accessToken),
        ]);
        if (active) { setAccount(current); setOwnedAccounts(accounts); }
      } catch (loadError) {
        if (active) setError(getDemoPaymentError(loadError));
      } finally {
        if (active) setIsLoading(false);
      }
    };
    void load();
    return () => {
      active = false;
    };
  }, [session?.accessToken]);

  const title = FLOW_TITLES[flow];

  const validateForm = (merchantOverride: DemoQrPayload | null = qrMerchant): boolean => {
    if (!account) {
      setFieldError('Your account is not available. Return home and try again.');
      return false;
    }
    const amountError = validateAmount(amount);
    if (amountError) {
      setFieldError(amountError);
      return false;
    }
    const noteError = validateNote(flow === 'bank' ? remarks : note);
    if (noteError) {
      setFieldError(noteError);
      return false;
    }
    if (flow === 'send' && (!receiverAccountId.trim() || !receiverName.trim())) {
      setFieldError('Enter the receiver account ID and name.');
      return false;
    }
    if (flow === 'self' && (!destinationAccountId.trim() || destinationAccountId.trim() === account.account_id)) {
      setFieldError('Enter a different destination account ID.');
      return false;
    }
    if (flow === 'bank' && (!beneficiaryName.trim() || !demoBankAccountNumber.trim() || !demoBankCode.trim())) {
      setFieldError('Enter the beneficiary and bank details.');
      return false;
    }
    if (flow === 'qr' && !merchantOverride && !parseDemoQrPayload(qrPayload)) {
      setFieldError('Scan or enter a valid merchant QR payload first.');
      return false;
    }
    setFieldError(null);
    setError(null);
    return true;
  };

  const review = async () => {
    const parsedQrMerchant = flow === 'qr' && !qrMerchant ? parseDemoQrPayload(qrPayload) : null;
    if (parsedQrMerchant) setQrMerchant(parsedQrMerchant);
    if (!validateForm(parsedQrMerchant || qrMerchant)) return;
    if (flow === 'qr') {
      if (!session?.accessToken || !qrPayload.trim()) return;
      setIsValidatingQr(true);
      try {
        const validated = await validateQrPayload(session.accessToken, qrPayload.trim());
        setQrMerchant({
          type: 'spendshield_demo_merchant',
          version: validated.version,
          merchantId: validated.merchant_id,
          merchantName: validated.merchant_name,
          category: validated.category || undefined,
          demoBank: validated.demo_bank || validated.bank,
          merchantAccountId: validated.merchant_account_id || undefined,
          bank: 'BJP Bank',
          mode: 'simulation',
          status: 'ACTIVE',
        });
      } catch (cause) {
        setError(getDemoPaymentError(cause));
        return;
      } finally {
        setIsValidatingQr(false);
      }
    }
    setStep('review');
  };

  const submit = async () => {
    if (!session?.accessToken || !account || !validateForm()) return;
    setIsSubmitting(true);
    setError(null);
    const key = idempotencyKey || createDemoIdempotencyKey(flow);
    setIdempotencyKey(key);
    try {
      let response: DemoPaymentResponse;
      if (flow === 'send') {
          response = await sendMoney(session.accessToken, key, {
          account_id: account.account_id,
          receiver_account_id: receiverAccountId.trim(),
          receiver_name: receiverName.trim(),
          amount: amount.trim(),
          currency: account.currency,
          ...(note.trim() ? { note: note.trim() } : {}),
          demo_mpin: demoMpin,
        });
      } else if (flow === 'qr' && qrMerchant) {
        response = await payByQr(session.accessToken, key, {
            account_id: account.account_id,
            amount: amount.trim(),
            currency: account.currency,
            qr_payload: qrPayload,
            ...(demoMpin ? { demo_mpin: demoMpin } : {}),
            ...(note.trim() ? { note: note.trim() } : {}),
          });
      } else if (flow === 'bank') {
        response = await bankTransfer(session.accessToken, key, {
          account_id: account.account_id,
          amount: amount.trim(),
          currency: account.currency,
          beneficiary_name: beneficiaryName.trim(),
          demo_bank_account_number: demoBankAccountNumber.trim(),
          demo_bank_code: demoBankCode.trim(),
          ...(remarks.trim() ? { remarks: remarks.trim() } : {}),
          demo_mpin: demoMpin,
        });
      } else {
        response = await selfTransfer(session.accessToken, key, {
          account_id: account.account_id,
          destination_account_id: destinationAccountId.trim(),
          amount: amount.trim(),
          currency: account.currency,
          ...(note.trim() ? { note: note.trim() } : {}),
          demo_mpin: demoMpin,
        });
      }
      setResult(response);
      setStep('result');
      try {
        setResultAccount(await getMyAccount(session.accessToken));
      } catch {
        setResultAccount(null);
      }
    } catch (submitError) {
      setError(getDemoPaymentError(submitError));
    } finally {
      setIsSubmitting(false);
    }
  };

  const reset = () => {
    setStep('form');
    setResult(null);
    setResultAccount(null);
    setIdempotencyKey(null);
    setAmount('');
    setNote('');
    setDemoMpin('');
    setRemarks('');
    setFieldError(null);
    setError(null);
  };

  if (isLoading) return <Screen><LoadingState title={title} /></Screen>;
  if (!account) {
    return <Screen><View style={styles.content}><ErrorMessage message={error || 'The account could not be loaded.'} /><PrimaryButton onPress={() => navigation.goBack()} variant="secondary">Back</PrimaryButton></View></Screen>;
  }
  if (step === 'result' && result) {
    return <ResultScreen account={resultAccount} navigation={navigation} onReset={reset} result={result} title={title} />;
  }

  return (
    <Screen>
      <View style={styles.content}>
        <View style={styles.heading}>
          <View style={styles.iconCircle}><IconGlyph color={colors.primaryDark} name={flow === 'qr' ? 'scan' : flow === 'bank' ? 'bank' : flow === 'self' ? 'account' : 'send'} size={26} /></View>
          <Text style={[typography.eyebrow, styles.eyebrow]}>Fictional payment · Simulation only</Text>
          <Text style={[typography.title, styles.title]}>{step === 'review' ? `Review ${title.toLowerCase()}` : title}</Text>
          <Text style={[typography.body, styles.subtitle]}>No real money will be transferred. The backend records only fictional activity.</Text>
        </View>
        {error && <ErrorMessage message={error} />}
        {fieldError && <ErrorMessage message={fieldError} />}
        <BalanceCard account={account} />
        {flow === 'qr' && step === 'form' && <QrInput formMode={formMode} merchant={qrMerchant} onManual={() => { setFormMode('manual'); setShowScanner(false); }} onScan={() => { setFormMode('scan'); setShowScanner(true); }} onPayloadChange={setQrPayload} payload={qrPayload} showScanner={showScanner} onScanned={async (data) => { setQrPayload(data); setShowScanner(false); const parsed = parseDemoQrPayload(data); if (!parsed) { setQrMerchant(null); setError('That QR code is not an accepted merchant payload. Use a SpendShield merchant QR.'); return; } if (!session?.accessToken) return; try { setIsValidatingQr(true); const validated = await validateQrPayload(session.accessToken, data); setQrMerchant({ type: 'spendshield_demo_merchant', version: validated.version, merchantId: validated.merchant_id, merchantName: validated.merchant_name, category: validated.category || undefined, demoBank: validated.demo_bank || validated.bank, merchantAccountId: validated.merchant_account_id || undefined, bank: validated.demo_bank === 'BJP Bank Demo' ? 'BJP Bank' : 'BJP Bank', mode: 'simulation', status: 'ACTIVE' }); setError(null); } catch (cause) { setQrMerchant(null); setError(getDemoPaymentError(cause)); } finally { setIsValidatingQr(false); } }} onCancelScan={() => setShowScanner(false)} />}
        {step === 'form' && <PaymentFields account={account} accounts={ownedAccounts} amount={amount} beneficiaryName={beneficiaryName} bankAccount={demoBankAccountNumber} bankCode={demoBankCode} destinationAccountId={destinationAccountId} flow={flow} merchant={qrMerchant} note={note} onAmount={setAmount} onBeneficiaryName={setBeneficiaryName} onBankAccount={setDemoBankAccountNumber} onBankCode={setDemoBankCode} onDestinationAccountId={setDestinationAccountId} onNote={setNote} onReceiverAccountId={setReceiverAccountId} onReceiverName={setReceiverName} onRemarks={setRemarks} receiverAccountId={receiverAccountId} receiverName={receiverName} remarks={remarks} />}
        {step === 'review' && <ReviewCard account={account} amount={amount} bankAccount={demoBankAccountNumber} bankCode={demoBankCode} destinationAccountId={destinationAccountId} flow={flow} merchant={qrMerchant} note={flow === 'bank' ? remarks : note} receiverAccountId={receiverAccountId} receiverName={receiverName} beneficiaryName={beneficiaryName} />}
        {step === 'mpin' && <MpinPanel value={demoMpin} onChange={setDemoMpin} />}
        {step === 'form' ? <PrimaryButton loading={isValidatingQr} onPress={() => void review()}>Review payment</PrimaryButton> : step === 'review' ? <><PrimaryButton onPress={() => setStep('mpin')}>Continue to security PIN</PrimaryButton><PrimaryButton disabled={isSubmitting} onPress={() => setStep('form')} variant="secondary">Edit details</PrimaryButton></> : step === 'mpin' ? <><PrimaryButton disabled={demoMpin.length !== 6} loading={isSubmitting} onPress={() => void submit()}>Confirm payment</PrimaryButton><PrimaryButton disabled={isSubmitting} onPress={() => setStep('review')} variant="secondary">Back to review</PrimaryButton></> : null}
        <PrimaryButton disabled={isSubmitting} onPress={() => navigation.goBack()} variant="quiet">Cancel</PrimaryButton>
      </View>
    </Screen>
  );
}

function LoadingState({ title }: { title: string }) {
  return <View style={styles.content}><DashboardCard><Text style={[typography.sectionTitle, styles.cardTitle]}>Loading {title.toLowerCase()}</Text><Text style={[typography.caption, styles.subtitle]}>Fetching your server-authoritative account.</Text></DashboardCard></View>;
}

function BalanceCard({ account }: { account: Account }) {
  return <DashboardCard style={styles.balanceCard}><Text style={[typography.eyebrow, styles.balanceEyebrow]}>BJP Bank · Available balance</Text><Text style={[typography.heading, styles.balance]}>{account.balance} {account.currency}</Text><View style={styles.balanceMeta}><StatusBadge status={account.status} /><Text style={[typography.caption, styles.simulated]}>Simulation only</Text></View></DashboardCard>;
}

function PaymentFields({ account, accounts, amount, beneficiaryName, bankAccount, bankCode, destinationAccountId, flow, merchant, note, onAmount, onBeneficiaryName, onBankAccount, onBankCode, onDestinationAccountId, onNote, onReceiverAccountId, onReceiverName, onRemarks, receiverAccountId, receiverName, remarks }: {
  account: Account;
  accounts: Account[];
  amount: string;
  beneficiaryName: string;
  bankAccount: string;
  bankCode: string;
  destinationAccountId: string;
  flow: Flow;
  merchant: DemoQrPayload | null;
  note: string;
  onAmount: (value: string) => void;
  onBeneficiaryName: (value: string) => void;
  onBankAccount: (value: string) => void;
  onBankCode: (value: string) => void;
  onDestinationAccountId: (value: string) => void;
  onNote: (value: string) => void;
  onReceiverAccountId: (value: string) => void;
  onReceiverName: (value: string) => void;
  onRemarks: (value: string) => void;
  receiverAccountId: string;
  receiverName: string;
  remarks: string;
}) {
  return <View style={styles.stack}>
    {flow === 'send' && <><TextField label="Receiver account ID" onChangeText={onReceiverAccountId} placeholder="Paste the receiver account ID" value={receiverAccountId} /><TextField label="Receiver name" onChangeText={onReceiverName} placeholder="Receiver name" value={receiverName} /></>}
    {flow === 'self' && <><TextField editable={false} label="Source account" value={`•••• ${account.account_id.slice(-4)}`} /><Text style={[typography.caption, styles.subtitle]}>Choose another account owned by you</Text>{accounts.filter((item) => item.account_id !== account.account_id).map((item) => <PrimaryButton key={item.account_id} onPress={() => onDestinationAccountId(item.account_id)} variant={destinationAccountId === item.account_id ? 'primary' : 'secondary'}>{item.account_type || 'Account'} · •••• {item.account_id.slice(-4)}</PrimaryButton>)}<TextField label="Destination account ID" onChangeText={onDestinationAccountId} placeholder="Another account owned by you" value={destinationAccountId} /></>}
    {flow === 'bank' && <><Text style={[typography.caption, styles.bankNotice]}>BJP Bank — Fictional service · Simulation only — No real transfer will occur.</Text><TextField label="Fictional bank account number" onChangeText={onBankAccount} placeholder="Enter a fictional account identifier" value={bankAccount} /><TextField autoCapitalize="characters" label="Fictional IFSC / bank code" onChangeText={onBankCode} placeholder="Enter a fictional bank code" value={bankCode} /></>}
    {flow !== 'qr' || merchant ? <>{flow === 'qr' && <Text style={[typography.caption, styles.amountLabel]}>Paying {merchant?.merchantName}</Text>}{flow === 'qr' ? <NumericKeypad value={amount} onChange={onAmount} /> : <TextField keyboardType="decimal-pad" label={`Amount (${account.currency})`} onChangeText={onAmount} placeholder="0.00" value={amount} />}</> : <Text style={[typography.caption, styles.subtitle]}>Identify a valid merchant before entering an amount.</Text>}
    <TextField label={flow === 'bank' ? 'Optional remarks' : 'Optional note'} maxLength={256} onChangeText={flow === 'bank' ? onRemarks : onNote} placeholder="Add context for this transaction" value={flow === 'bank' ? remarks : note} />
  </View>;
}

function QrInput({ formMode, merchant, onManual, onScan, onPayloadChange, payload, showScanner, onScanned, onCancelScan }: { formMode: FormMode; merchant: DemoQrPayload | null; onManual: () => void; onScan: () => void; onPayloadChange: (value: string) => void; payload: string; showScanner: boolean; onScanned: (data: string) => void | Promise<void>; onCancelScan: () => void }) {
  const [permission, requestPermission] = useCameraPermissions();
  const [permissionMessage, setPermissionMessage] = useState<string | null>(null);
  const shouldScan = showScanner && permission?.granted;

  const enableCamera = async () => {
    setPermissionMessage(null);
    if (permission?.granted) {
      onScan();
      return;
    }
    const response = await requestPermission();
    if (response.granted) {
      onScan();
      return;
    }
    setPermissionMessage(response.canAskAgain ? 'Camera access was denied. You can use manual payment entry or try permission again.' : 'Camera access is blocked. Open Settings to enable it, or use manual payment entry.');
  };

  const chooseImage = async () => {
    setPermissionMessage(null);
    try {
      const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], selectionLimit: 1 });
      if (result.canceled || !result.assets[0]?.uri) return;
      const matches = await scanFromURLAsync(result.assets[0].uri, ['qr']);
      if (!matches[0]?.data) {
        setPermissionMessage('No QR code was detected. Please choose a clearer merchant QR image.');
        return;
      }
      onScanned(matches[0].data);
    } catch {
      setPermissionMessage('The selected image could not be decoded locally. Try a clearer merchant QR image or enter the payload manually.');
    }
  };

  if (shouldScan) {
    return <DashboardCard><Text style={[typography.sectionTitle, styles.cardTitle]}>Scan merchant QR</Text><CameraView barcodeScannerSettings={{ barcodeTypes: ['qr'] }} onBarcodeScanned={({ data }) => { void onScanned(data); }} style={styles.camera} /><PrimaryButton onPress={() => onManual()} variant="secondary">Use manual entry</PrimaryButton><PrimaryButton onPress={onCancelScan} variant="quiet">Cancel scan</PrimaryButton></DashboardCard>;
  }

  return <DashboardCard style={styles.qrCard}>
    <Text style={[typography.sectionTitle, styles.cardTitle]}>Merchant QR</Text>
    <Text style={[typography.caption, styles.subtitle]}>Only payloads marked BJP Bank / simulation are accepted.</Text>
    {merchant && <View style={styles.merchantPreview}><Text style={[typography.body, styles.cardTitle]}>{merchant.merchantName}</Text><Text style={[typography.caption, styles.subtitle]}>{merchant.merchantId} · BJP Bank</Text></View>}
    {formMode === 'manual' && <TextField label="QR payload" multiline onChangeText={onPayloadChange} placeholder='{"type":"merchant",...}' value={payload} />}
    {permissionMessage && <ErrorMessage message={permissionMessage} />}
    <PrimaryButton onPress={() => void enableCamera()}>{permission?.granted ? 'Open scanner' : 'Enable camera to scan'}</PrimaryButton>
    <PrimaryButton onPress={() => void chooseImage()} variant="secondary">Upload QR image</PrimaryButton>
    <PrimaryButton onPress={onManual} variant="secondary">Enter payload manually</PrimaryButton>
    {!permission?.granted && !permission?.canAskAgain && <PrimaryButton onPress={() => void Linking.openSettings()} variant="quiet">Open Settings</PrimaryButton>}
  </DashboardCard>;
}

function NumericKeypad({ value, onChange, maxLength = 12, masked = false }: { value: string; onChange: (value: string) => void; maxLength?: number; masked?: boolean }) {
  const press = (key: string) => {
    if (key === 'clear') return onChange('');
    if (key === 'backspace') return onChange(value.slice(0, -1));
    if (value.length >= maxLength) return;
    if (key === '.' && value.includes('.')) return;
    if (key === '.' && !value) return onChange('0.');
    if (key !== '.' && value === '0') return onChange(key);
    onChange(value + key);
  };
  const display = masked ? '•'.repeat(value.length) : value || '0';
  return <View style={styles.keypad}><Text style={[typography.heading, styles.keypadValue]}>{display}</Text><View style={styles.keyGrid}>{['1', '2', '3', '4', '5', '6', '7', '8', '9', '.', '0', 'backspace'].map((key) => <Pressable accessibilityRole="button" accessibilityLabel={key === 'backspace' ? 'Backspace' : key} key={key} onPress={() => press(key)} style={styles.key}><Text style={[typography.body, styles.keyText]}>{key === 'backspace' ? '⌫' : key}</Text></Pressable>)}</View><Pressable accessibilityRole="button" onPress={() => press('clear')} style={styles.clearKey}><Text style={[typography.caption, styles.clearText]}>Clear</Text></Pressable></View>;
}

function MpinPanel({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return <DashboardCard><Text style={[typography.sectionTitle, styles.cardTitle]}>Enter security PIN</Text><Text style={[typography.caption, styles.subtitle]}>Use the six-digit SpendShield MPIN. This is not a real bank PIN.</Text><NumericKeypad maxLength={6} masked onChange={onChange} value={value} /></DashboardCard>;
}

function ReviewCard({ account, amount, bankAccount, bankCode, destinationAccountId, flow, merchant, note, receiverAccountId, receiverName, beneficiaryName }: { account: Account; amount: string; bankAccount: string; bankCode: string; destinationAccountId: string; flow: Flow; merchant: DemoQrPayload | null; note: string; receiverAccountId: string; receiverName: string; beneficiaryName: string }) {
  const rows = useMemo(() => {
    const common = [['Amount', `${amount.trim()} ${account.currency}`]] as [string, string][];
    if (flow === 'send') return [...common, ['Receiver', receiverName], ['Account', receiverAccountId]];
    if (flow === 'qr') return [...common, ['Merchant', merchant?.merchantName || 'Merchant'], ['Merchant ID', merchant?.merchantId || 'Not available']];
    if (flow === 'bank') return [...common, ['Beneficiary', beneficiaryName], ['Account', bankAccount], ['Bank code', bankCode]];
    return [...common, ['Destination account', destinationAccountId]];
  }, [account.currency, amount, bankAccount, bankCode, destinationAccountId, flow, merchant, receiverAccountId, receiverName, beneficiaryName]);
  return <DashboardCard><Text style={[typography.eyebrow, styles.eyebrow]}>Confirmation summary</Text>{rows.map(([label, value]) => <View key={label} style={styles.summary}><Text style={[typography.caption, styles.subtitle]}>{label}</Text><Text style={[typography.body, styles.summaryValue]}>{value}</Text></View>)}<View style={styles.summary}><Text style={[typography.caption, styles.subtitle]}>Note / remarks</Text><Text style={[typography.body, styles.summaryValue]}>{note.trim() || 'None'}</Text></View><Text style={[typography.caption, styles.simulated]}>SIMULATED · Confirming records a fictional transaction only.</Text></DashboardCard>;
}

function ResultScreen({ account, navigation, onReset, result, title }: { account: Account | null; navigation: Props['navigation']; onReset: () => void; result: DemoPaymentResponse; title: string }) {
  return <Screen><View style={styles.content}><View style={styles.resultHero}><Text style={styles.resultCheck}>✓</Text><Text style={[typography.title, styles.resultTitle]}>Payment recorded</Text><Text style={[typography.body, styles.resultSubtitle]}>{title} was recorded by the SpendShield backend. No real money moved.</Text></View><DashboardCard><View style={styles.transactionStatus}><Text style={[typography.caption, styles.transactionStatusText]}>{result.transaction.status}</Text></View><Summary label="Transaction ID" value={result.transaction.transaction_id} /><Summary label="Amount paid" value={`${result.paid_amount || result.transaction.amount} ${result.transaction.currency}`} />{result.merchant?.merchant_name && <Summary label="Merchant" value={result.merchant.merchant_name} />}{result.previous_balance && <Summary label="Previous balance" value={`${result.previous_balance} ${result.transaction.currency}`} />}{result.remaining_balance && <Summary label="Remaining balance" value={`${result.remaining_balance} ${result.transaction.currency}`} />}{account && !result.remaining_balance && <Summary label="Server balance after operation" value={`${account.balance} ${account.currency}`} />}<Text style={[typography.caption, styles.simulated]}>BJP Bank · Simulation only</Text></DashboardCard>{result.related_transaction_ids.length > 0 && <Text style={[typography.caption, styles.subtitle]}>Linked transfer record: {result.related_transaction_ids[0]}</Text>}<PrimaryButton onPress={() => navigation.navigate('TransactionDetails', { transactionId: result.transaction.transaction_id })}>View transaction details</PrimaryButton><PrimaryButton onPress={() => navigation.navigate('Transactions')} variant="secondary">Transaction history</PrimaryButton><PrimaryButton onPress={() => navigation.navigate('Dashboard')} variant="quiet">Return home</PrimaryButton><PrimaryButton onPress={onReset} variant="quiet">Make another payment</PrimaryButton></View></Screen>;
}

function Summary({ label, value }: { label: string; value: string }) {
  return <View style={styles.summary}><Text style={[typography.caption, styles.subtitle]}>{label}</Text><Text style={[typography.body, styles.summaryValue]}>{value}</Text></View>;
}

const styles = StyleSheet.create({
  content: { gap: spacing.lg },
  heading: { gap: spacing.sm, paddingVertical: spacing.md },
  iconCircle: { alignItems: 'center', backgroundColor: colors.primarySoft, borderRadius: radii.md, height: 54, justifyContent: 'center', width: 54 },
  eyebrow: { color: colors.primaryDark },
  title: { color: colors.navy },
  subtitle: { color: colors.textMuted },
  stack: { gap: spacing.md },
  amountLabel: { color: colors.navy, fontWeight: '800' },
  keypad: { gap: spacing.sm },
  keypadValue: { color: colors.navy, textAlign: 'center' },
  keyGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm, justifyContent: 'center' },
  key: { alignItems: 'center', backgroundColor: colors.surfaceMuted, borderColor: colors.border, borderRadius: radii.md, borderWidth: 1, height: 48, justifyContent: 'center', width: '30%' },
  keyText: { color: colors.navy, fontWeight: '800' },
  clearKey: { alignSelf: 'center', padding: spacing.sm },
  clearText: { color: colors.primaryDark, fontWeight: '800' },
  cardTitle: { color: colors.navy },
  balanceCard: { backgroundColor: colors.navy, borderColor: colors.navy },
  balanceEyebrow: { color: colors.primarySoft },
  balance: { color: colors.white, marginVertical: spacing.sm },
  balanceMeta: { alignItems: 'center', flexDirection: 'row', gap: spacing.sm },
  simulated: { color: colors.primaryDark, fontWeight: '800', marginTop: spacing.sm },
  bankNotice: { backgroundColor: colors.primarySoft, borderRadius: radii.sm, color: colors.primaryDark, padding: spacing.md },
  qrCard: { gap: spacing.sm },
  camera: { borderRadius: radii.md, height: 260, overflow: 'hidden', width: '100%' },
  merchantPreview: { backgroundColor: colors.surfaceMuted, borderRadius: radii.sm, gap: spacing.xs, padding: spacing.md },
  summary: { borderBottomColor: colors.border, borderBottomWidth: 1, gap: spacing.xs, paddingVertical: spacing.sm },
  summaryValue: { color: colors.navy, fontWeight: '800' },
  resultHero: { alignItems: 'center', gap: spacing.sm, paddingVertical: spacing.xl },
  resultCheck: { backgroundColor: colors.successBackground, borderRadius: 34, color: colors.success, fontSize: 38, fontWeight: '800', height: 68, lineHeight: 68, textAlign: 'center', width: 68 },
  resultTitle: { color: colors.navy, textAlign: 'center' },
  resultSubtitle: { color: colors.textMuted, textAlign: 'center' },
  transactionStatus: { alignSelf: 'flex-start', backgroundColor: colors.successBackground, borderRadius: radii.sm, paddingHorizontal: spacing.sm, paddingVertical: spacing.xs },
  transactionStatusText: { color: colors.navy, fontWeight: '800' },
});
