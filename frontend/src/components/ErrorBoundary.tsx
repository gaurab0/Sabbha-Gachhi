import { Component, type ErrorInfo, type ReactNode } from "react";
import { Link } from "react-router-dom";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public override state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public override componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught an unhandled error:", error, errorInfo);
  }

  public override render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <section className="px-5 pt-[5.5rem] pb-16 sm:px-8 sm:pt-24 sm:pb-20">
          <div className="container max-w-[640px]">
            <p className="text-caption text-text/60 tracking-wider mb-3">Something went wrong</p>
            <h1 className="text-heading text-primary mb-4">An unexpected error occurred</h1>
            <p className="text-body leading-relaxed mb-8">
              We encountered an issue displaying this page. Please try refreshing, or return home.
            </p>
            <div className="flex gap-4">
              <button
                type="button"
                className="btn-primary"
                onClick={() => this.setState({ hasError: false, error: null })}
              >
                Try again
              </button>
              <Link to="/" className="btn-outline">
                Back home
              </Link>
            </div>
          </div>
        </section>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
