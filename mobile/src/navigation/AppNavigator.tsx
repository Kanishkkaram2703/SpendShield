import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

import { SplashScreen } from '../screens/SplashScreen';
import { WelcomeScreen } from '../screens/WelcomeScreen';
import { LoginScreen } from '../screens/LoginScreen';
import { RegisterScreen } from '../screens/RegisterScreen';
import { DashboardScreen } from '../screens/DashboardScreen';
import { AccountDetailsScreen } from '../screens/AccountDetailsScreen';
import { ComingSoonPaymentScreen } from '../screens/ComingSoonPaymentScreen';
import { ContactsScreen } from '../screens/ContactsScreen';
import { PhonePaymentScreen } from '../screens/PhonePaymentScreen';
import { BillsScreen } from '../screens/BillsScreen';
import { RechargeScreen } from '../screens/RechargeScreen';
import { SubscriptionsScreen } from '../screens/SubscriptionsScreen';
import { MoreScreen } from '../screens/MoreScreen';
import { AccountOperationScreen } from '../screens/AccountOperationScreen';
import { DemoMerchantQrScreen } from '../screens/DemoMerchantQrScreen';
import { DemoSecurityScreen } from '../screens/DemoSecurityScreen';
import { ProfileScreen } from '../screens/ProfileScreen';
import { DemoCardScreen } from '../screens/DemoCardScreen';
import { NotificationsScreen } from '../screens/NotificationsScreen';
import { PayScreen } from '../screens/PayScreen';
import { TransactionDetailsScreen } from '../screens/TransactionDetailsScreen';
import { TransactionsScreen } from '../screens/TransactionsScreen';
import { useAuth } from '../services/AuthContext';
import { colors, navigationTheme } from '../theme';
import type { RootStackParamList } from '../types/navigation';

const Stack = createNativeStackNavigator<RootStackParamList>();

export function AppNavigator() {
  const { isLoading, session } = useAuth();

  return (
    <NavigationContainer theme={navigationTheme}>
      <Stack.Navigator
        screenOptions={{
          headerBackTitle: 'Back',
          headerTintColor: colors.navy,
          headerTitleStyle: { fontWeight: '700' },
          contentStyle: { backgroundColor: colors.background },
        }}
      >
        {isLoading ? (
          <Stack.Screen component={SplashScreen} name="Splash" options={{ headerShown: false }} />
        ) : session ? (
          <>
            <Stack.Screen component={DashboardScreen} name="Dashboard" options={{ headerShown: false }} />
            <Stack.Screen component={PayScreen} name="Pay" options={{ title: 'Simulated Pay' }} />
            <Stack.Screen component={TransactionsScreen} name="Transactions" options={{ title: 'Transactions' }} />
            <Stack.Screen component={TransactionDetailsScreen} name="TransactionDetails" options={{ title: 'Transaction details' }} />
            <Stack.Screen component={AccountDetailsScreen} name="AccountDetails" options={{ title: 'Account details' }} />
            <Stack.Screen component={ComingSoonPaymentScreen} name="ComingSoonPayment" options={{ title: 'Payment flow' }} />
            <Stack.Screen component={ContactsScreen} name="Contacts" options={{ title: 'Contacts' }} />
            <Stack.Screen component={PhonePaymentScreen} name="PhonePayment" options={{ title: 'Pay phone number' }} />
            <Stack.Screen component={BillsScreen} name="Bills" options={{ title: 'Bills & recharges' }} />
            <Stack.Screen component={RechargeScreen} name="Recharge" options={{ title: 'Mobile recharge' }} />
            <Stack.Screen component={SubscriptionsScreen} name="Subscriptions" options={{ title: 'BJP Entertainments' }} />
            <Stack.Screen component={MoreScreen} name="More" options={{ title: 'More' }} />
            <Stack.Screen component={AccountOperationScreen} name="AccountOperation" options={{ title: 'Account operation' }} />
            <Stack.Screen component={DemoMerchantQrScreen} name="DemoMerchantQr" options={{ title: 'Merchant QR' }} />
            <Stack.Screen component={DemoSecurityScreen} name="DemoSecurity" options={{ title: 'Security' }} />
            <Stack.Screen component={ProfileScreen} name="Profile" options={{ title: 'Profile' }} />
            <Stack.Screen component={DemoCardScreen} name="DemoCard" options={{ title: 'Virtual card' }} />
            <Stack.Screen component={NotificationsScreen} name="Notifications" options={{ title: 'Notifications' }} />
          </>
        ) : (
          <>
            <Stack.Screen component={WelcomeScreen} name="Welcome" options={{ headerShown: false }} />
            <Stack.Screen component={LoginScreen} name="Login" options={{ title: 'Sign in' }} />
            <Stack.Screen component={RegisterScreen} name="Register" options={{ title: 'Create account' }} />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
