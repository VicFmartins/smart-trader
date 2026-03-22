import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { fetchCurrentUser, loginWithPassword } from "../lib/api";
import {
  clearStoredAccessToken,
  getStoredAccessToken,
  setStoredAccessToken,
  UNAUTHORIZED_SESSION_EVENT
} from "../lib/auth";
import type { AuthenticatedUser } from "../types/auth";

type AuthContextValue = {
  user: AuthenticatedUser | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function restoreSession() {
      const token = getStoredAccessToken();
      if (!token) {
        if (isMounted) {
          setLoading(false);
        }
        return;
      }

      try {
        const restoredUser = await fetchCurrentUser();
        if (isMounted) {
          setUser(restoredUser);
        }
      } catch {
        clearStoredAccessToken();
        if (isMounted) {
          setUser(null);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    void restoreSession();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    function handleUnauthorizedSession() {
      clearStoredAccessToken();
      setUser(null);
    }

    window.addEventListener(UNAUTHORIZED_SESSION_EVENT, handleUnauthorizedSession);
    return () => window.removeEventListener(UNAUTHORIZED_SESSION_EVENT, handleUnauthorizedSession);
  }, []);

  async function login(email: string, password: string) {
    setLoading(true);
    try {
      const session = await loginWithPassword(email, password);
      setStoredAccessToken(session.accessToken);
      setUser(session.user);
    } catch (error) {
      clearStoredAccessToken();
      setUser(null);
      throw error;
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    clearStoredAccessToken();
    setUser(null);
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: Boolean(user),
        loading,
        login,
        logout
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider.");
  }
  return context;
}
