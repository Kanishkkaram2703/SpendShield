import {
  createContext,
  type PropsWithChildren,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';

import { getCurrentUser, login, register } from '../api/authApi';
import { clearSession, loadSession, saveSession } from '../storage/tokenStorage';
import type { AuthSession, User } from '../types/auth';

interface AuthContextValue {
  session: AuthSession | null;
  isLoading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<User>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: PropsWithChildren) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    void (async () => {
      try {
        const stored = await loadSession();
        if (!stored) {
          return;
        }
        const user = await getCurrentUser(stored.accessToken);
        if (mounted) {
          setSession({ ...stored, user });
        }
      } catch {
        await clearSession();
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    })();

    return () => {
      mounted = false;
    };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const response = await login(email.trim().toLowerCase(), password);
    const nextSession: AuthSession = {
      accessToken: response.access_token,
      tokenType: response.token_type,
      expiresIn: response.expires_in,
      user: response.user,
    };
    await saveSession(nextSession);
    setSession(nextSession);
  }, []);

  const signUp = useCallback(async (email: string, password: string) => {
    return register(email.trim().toLowerCase(), password);
  }, []);

  const signOut = useCallback(async () => {
    await clearSession();
    setSession(null);
  }, []);

  const value = useMemo(
    () => ({ session, isLoading, signIn, signUp, signOut }),
    [isLoading, session, signIn, signOut, signUp],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return context;
}
