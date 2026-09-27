import { useState } from "react";
import { AuthContext } from "./auth-context";
import {
  getAccessToken,
  clearTokens,
  signup as apiSignup,
  login as apiLogin,
} from "../api/auth";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(() => !!getAccessToken());
  const [isStaff, setIsStaff] = useState(false);
  const [accessToken, setAccessToken] = useState(() => getAccessToken());

  const login = async (email: string, password: string) => {
    const { access, is_staff } = await apiLogin(email, password);
    setAccessToken(access);
    setIsStaff(is_staff);
    setIsAuthenticated(true);
  };

  const signup = async (email: string, password: string) => {
    const { access, is_staff } = await apiSignup(email, password);
    setAccessToken(access);
    setIsStaff(is_staff);
    setIsAuthenticated(true);
  };

  const logout = () => {
    clearTokens();
    setAccessToken(null);
    setIsStaff(false);
    setIsAuthenticated(false);
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, isStaff, accessToken, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
