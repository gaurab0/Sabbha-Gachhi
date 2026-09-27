import { createContext } from "react";

export interface AuthContextValue {
  isAuthenticated: boolean;
  isStaff: boolean;
  accessToken: string | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
