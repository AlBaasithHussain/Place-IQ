import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import {
  getMe,
  login as apiLogin,
  logout as apiLogout,
  register as apiRegister,
  TOKEN_KEY,
  type AuthResponse,
  type LoginInput,
  type RegisterInput,
  type User,
} from "../lib/api";

interface AuthContextValue {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (input: LoginInput) => Promise<void>;
  register: (input: RegisterInput) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(() => Boolean(localStorage.getItem(TOKEN_KEY)));

  // On first load (or when the token changes) try to resolve the current user.
  useEffect(() => {
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }

    let active = true;
    setLoading(true);
    getMe()
      .then((current) => {
        if (active) setUser(current);
      })
      .catch(() => {
        if (!active) return;
        localStorage.removeItem(TOKEN_KEY);
        setToken(null);
        setUser(null);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [token]);

  function applyAuth(response: AuthResponse) {
    localStorage.setItem(TOKEN_KEY, response.access_token);
    setToken(response.access_token);
    setUser(response.user);
  }

  async function login(input: LoginInput) {
    applyAuth(await apiLogin(input));
  }

  async function register(input: RegisterInput) {
    applyAuth(await apiRegister(input));
  }

  async function logout() {
    try {
      if (token) await apiLogout();
    } catch {
      // Even if the server call fails, clear the local session.
    }
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  }

  const value: AuthContextValue = { user, token, loading, login, register, logout };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
