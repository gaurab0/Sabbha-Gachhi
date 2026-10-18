import { Navigate } from "react-router-dom";
import { useAuth } from "../context/useAuth";

/** Logged-in gate (unchanged behavior). */
export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

/** Verified-email gate for app pages. Unverified users only reach /verify-email. */
export function VerifiedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, emailVerified } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (emailVerified === null) {
    return <p style={{ padding: 32 }}>Checking verification…</p>;
  }
  if (!emailVerified) return <Navigate to="/verify-email" replace />;
  return <>{children}</>;
}

/** Email-then-phone gate (same order as the backend). Email gaps go to
 * /verify-email. The phone step is skipped entirely unless the server reports
 * phone_verification_required (phase-2 feature toggle). */
export function FullyVerifiedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, emailVerified, phoneVerified, phoneVerificationRequired } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (emailVerified === null || phoneVerified === null || phoneVerificationRequired === null) {
    return <p style={{ padding: 32 }}>Checking verification…</p>;
  }
  if (!emailVerified) return <Navigate to="/verify-email" replace />;
  if (phoneVerificationRequired && !phoneVerified) return <Navigate to="/verify-phone" replace />;
  return <>{children}</>;
}
