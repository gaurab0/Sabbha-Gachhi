import { useEffect, useState } from "react";
import { AuthContext } from "./auth-context";
import {
  fetchMe,
  getAccessToken,
  clearTokens,
  signup as apiSignup,
  login as apiLogin,
} from "../api/auth";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(() => !!getAccessToken());
  const [isStaff, setIsStaff] = useState(false);
  const [emailVerified, setEmailVerified] = useState<boolean | null>(null);
  const [phoneVerified, setPhoneVerifiedState] = useState<boolean | null>(null);
  const [accessToken, setAccessToken] = useState(() => getAccessToken());

  // On load (and token change), resolve verification state for route guards.
  const refreshVerification = async () => {
    const token = getAccessToken();
    if (!token) {
      setEmailVerified(null);
      return;
    }
    try {
      const me = await fetchMe();
      setEmailVerified(me.email_verified);
      setPhoneVerifiedState(me.phone_verified);
      setIsStaff(me.is_staff);
    } catch {
      setEmailVerified(null);
      setPhoneVerifiedState(null);
    }
  };

  useEffect(() => {
    refreshVerification();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken]);

  const login = async (email: string, password: string) => {
    const { access, is_staff, email_verified, phone_verified } = await apiLogin(email, password);
    setAccessToken(access);
    setIsStaff(is_staff);
    setEmailVerified(email_verified);
    setPhoneVerifiedState(phone_verified);
    setIsAuthenticated(true);
    return email_verified;
  };

  const signup = async (email: string, password: string) => {
    const { access, is_staff, email_verified, phone_verified } = await apiSignup(email, password);
    setAccessToken(access);
    setIsStaff(is_staff);
    setEmailVerified(email_verified);
    setPhoneVerifiedState(phone_verified);
    setIsAuthenticated(true);
    return email_verified;
  };

  const setVerified = () => setEmailVerified(true);
  const setPhoneVerified = () => setPhoneVerifiedState(true);

  const logout = () => {
    clearTokens();
    setAccessToken(null);
    setIsStaff(false);
    setEmailVerified(null);
    setPhoneVerifiedState(null);
    setIsAuthenticated(false);
  };

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        isStaff,
        emailVerified,
        phoneVerified,
        accessToken,
        login,
        signup,
        refreshVerification,
        setVerified,
        setPhoneVerified,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
