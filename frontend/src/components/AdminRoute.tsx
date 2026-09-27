import { Navigate } from "react-router-dom";
import { useAuth } from "../context/useAuth";

export function AdminRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isStaff } = useAuth();
  if (!isAuthenticated || !isStaff) return <Navigate to="/login" replace />;
  return <>{children}</>;
}
