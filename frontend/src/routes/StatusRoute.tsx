import StatusPage from "../components/StatusPage";
import ErrorBoundary from "../components/ErrorBoundary";

export function StatusRoute() {
  return (
    <ErrorBoundary>
      <StatusPage />
    </ErrorBoundary>
  );
}
