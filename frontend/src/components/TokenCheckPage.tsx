import StatusPage from "./StatusPage";
import ErrorBoundary from "./ErrorBoundary";

/**
 * TokenCheckPage — the /status-check route.
 *
 * Renders StatusPage protected by an ErrorBoundary so unexpected runtime
 * exceptions in the status subtree cannot blank the entire page.
 */
export default function TokenCheckPage() {
  return (
    <ErrorBoundary>
      <StatusPage />
    </ErrorBoundary>
  );
}
