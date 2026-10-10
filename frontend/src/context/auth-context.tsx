import { createContext } from "react";

export interface AuthContextValue {
  isAuthenticated: boolean;
  isStaff: boolean;
  /** Null until /auth/me/ resolves; false blocks protected pages. */
  emailVerified: boolean | null;
  /** Null until /auth/me/ resolves; false blocks fully-verified pages. */
  phoneVerified: boolean | null;
  accessToken: string | null;
  login: (email: string, password: string) => Promise<boolean>;
  signup: (email: string, password: string) => Promise<boolean>;
  refreshVerification: () => Promise<void>;
  setVerified: () => void;
  setPhoneVerified: () => void;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
