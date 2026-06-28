import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, getAuthToken, setAuthToken } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [status, setStatus] = useState(null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const s = await api.authStatus();
      setStatus(s);
      if (s.auth_enabled && getAuthToken()) {
        const me = await api.me();
        setUser(me);
      } else {
        setUser(null);
      }
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = useCallback(async (email, password) => {
    const result = await api.login(email, password);
    setAuthToken(result.access_token);
    setUser(result.user);
    const s = await api.authStatus();
    setStatus(s);
    return result.user;
  }, []);

  const logout = useCallback(() => {
    setAuthToken(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      status,
      user,
      loading,
      authRequired: Boolean(status?.auth_enabled),
      login,
      logout,
      refresh,
    }),
    [status, user, loading, login, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
