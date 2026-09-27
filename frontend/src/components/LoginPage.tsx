import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/useAuth";

const STYLES = `
.mh-proposal {
  font-family: Georgia, "Times New Roman", serif;
  color: var(--ink);
  background: var(--paper);
  min-height: 100vh;
  padding: 64px 24px 80px;
}

.mh-header {
  display: flex;
  align-items: center;
  gap: 12px;
  max-width: 520px;
  margin: 0 auto 32px;
  position: relative;
}

.mh-back-link {
  position: absolute;
  top: -22px;
  left: 0;
  background: none;
  border: none;
  color: var(--ink);
  opacity: 0.6;
  font-size: 13px;
  cursor: pointer;
  padding: 0;
  transition: opacity 0.15s ease, color 0.15s ease;
  text-decoration: none;
}
.mh-back-link:hover {
  opacity: 1;
  color: var(--sindoor);
}

.mh-header-mark {
  width: 36px;
  height: 36px;
  border: 1px solid var(--line);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--sindoor);
  font-size: 18px;
  flex-shrink: 0;
}

.mh-eyebrow {
  margin: 0;
  font-size: 12px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--sindoor);
}

.mh-step-trail {
  margin: 2px 0 0;
  font-size: 13px;
  color: #6b5d4d;
}

.mh-proposal-card {
  max-width: 520px;
  margin: 0 auto;
  background: var(--paper);
  border: 1px solid var(--line);
  padding: 32px 28px;
}

.mh-kicker {
  margin: 0 0 6px;
  font-size: 12px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.mh-kicker[data-accent="sindoor"] { color: var(--sindoor); }
.mh-kicker[data-accent="mango"] { color: var(--mango); }
.mh-kicker[data-accent="turmeric"] { color: var(--turmeric); }

.mh-title {
  font-family: Georgia, "Times New Roman", serif;
  color: var(--sindoor);
  font-size: 24px;
  line-height: 1.25;
  margin: 0 0 10px;
}

.mh-help {
  font-size: 14px;
  line-height: 1.6;
  color: var(--ink);
  margin: 0 0 24px;
}
.mh-help-muted {
  color: var(--ink);
  opacity: 0.6;
  margin-bottom: 14px;
}

.mh-field {
  margin-bottom: 20px;
}
.mh-field label {
  display: block;
  font-size: 13px;
  margin-bottom: 6px;
  color: var(--ink);
  opacity: 0.75;
}
.mh-field input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--line);
  background: var(--paper-alt);
  padding: 10px 12px;
  font-size: 14px;
  font-family: inherit;
  color: var(--ink);
  border-radius: 6px;
}
.mh-field input:focus {
  outline: 2px solid var(--sindoor);
  outline-offset: 1px;
}
.mh-field input:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.mh-btn {
  border: 1px solid var(--ink);
  background: transparent;
  padding: 10px 20px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
}
.mh-btn:active { transform: translateY(1px); }
.mh-btn-primary { background: var(--sindoor); border-color: var(--sindoor); color: var(--paper); }
.mh-btn-primary:not(:disabled):hover { background: #63182A; border-color: #63182A; }
.mh-btn-primary:disabled { background: var(--line); border-color: var(--line); cursor: not-allowed; }
.mh-btn-ghost { border-color: var(--line); color: #6b5d4d; background: transparent; }
.mh-btn-ghost:not(:disabled):hover { border-color: var(--ink); color: var(--ink); }
.mh-btn-outline { border-color: var(--sindoor); color: var(--sindoor); background: transparent; }
.mh-btn-outline:not(:disabled):hover { background: var(--sindoor); color: var(--paper); }
.mh-btn-outline:disabled { border-color: var(--line); color: var(--line); cursor: not-allowed; }

.mh-spinner {
  display: inline-block;
  width: 1em;
  height: 1em;
  vertical-align: -0.125em;
  border: 2px solid color-mix(in srgb, var(--sindoor) 25%, var(--line));
  border-top-color: var(--sindoor);
  border-radius: 50%;
  animation: mh-spin 0.8s linear infinite;
}
@keyframes mh-spin { to { transform: rotate(360deg); } }
`;

export function LoginPage() {
  const navigate = useNavigate();
  const { isAuthenticated, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (isAuthenticated) {
    navigate("/", { replace: true });
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/", { replace: true });
    } catch (err: any) {
      const body = err?.body as Record<string, string[]> | undefined;
      if (body?.email?.length) {
        setError(body.email[0]);
      } else if (body?.password?.length) {
        setError(body.password[0]);
      } else {
        setError("Invalid email or password. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mh-proposal">
      <style>{STYLES}</style>

      <header className="mh-header">
        <a href="/" className="mh-back-link">← Home</a>
        <div className="mh-header-mark" aria-hidden="true">⟡</div>
        <div>
          <p className="mh-eyebrow">Saurath Sabha Gachhi</p>
          <p className="mh-step-trail">Log in</p>
        </div>
      </header>

      <main className="mh-proposal-card">
        <p className="mh-kicker" data-accent="sindoor">Welcome back</p>
        <h1 className="mh-title">Log in to your account</h1>
        <p className="mh-help">Enter the credentials you signed up with to access your registration status.</p>
        {error && <p className="mh-help-muted">{error}</p>}
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="mh-field">
            <label htmlFor="login-email">Email</label>
            <input
              id="login-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoComplete="username"
              required
            />
          </div>
          <div className="mh-field">
            <label htmlFor="login-password">Password</label>
            <input
              id="login-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Your password"
              autoComplete="current-password"
              required
            />
          </div>
          <button type="submit" className="mh-btn mh-btn-primary" disabled={loading}>
            {loading ? <><span className="mh-spinner" aria-hidden="true" /> Signing in…</> : "Sign in"}
          </button>
        </form>
        <p className="mh-help-muted" style={{ marginTop: "20px", textAlign: "center" }}>
          Don&rsquo;t have an account?{" "}
          <Link to="/signup" style={{ color: "var(--sindoor)", textDecoration: "underline" }}>Sign up</Link>
        </p>
      </main>
    </div>
  );
}
