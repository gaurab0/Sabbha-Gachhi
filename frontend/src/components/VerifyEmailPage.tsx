import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/useAuth";
import {
  changeEmail,
  fetchMe,
  resendVerification,
  verifyEmail,
} from "../api/auth";

const STYLES = `
.ve-wrap { font-family: Georgia, "Times New Roman", serif; color: var(--ink); background: var(--paper); min-height: 100vh; padding: 64px 24px 80px; }
.ve-card { max-width: 520px; margin: 0 auto; background: var(--paper); border: 1px solid var(--line); padding: 32px 28px; }
.ve-kicker { margin: 0 0 6px; font-size: 12px; letter-spacing: 0.06em; text-transform: uppercase; color: var(--mango); }
.ve-title { font-family: Georgia, "Times New Roman", serif; color: var(--sindoor); font-size: 24px; line-height: 1.25; margin: 0 0 10px; }
.ve-help { font-size: 14px; line-height: 1.6; margin: 0 0 16px; }
.ve-muted { color: var(--ink); opacity: 0.6; font-size: 13px; }
.ve-field { margin-bottom: 16px; }
.ve-field label { display: block; font-size: 13px; margin-bottom: 6px; opacity: 0.75; }
.ve-field input { width: 100%; box-sizing: border-box; border: 1px solid var(--line); background: var(--paper-alt); padding: 10px 12px; font-size: 14px; border-radius: 6px; color: var(--ink); }
.ve-btn { border: 1px solid var(--sindoor); background: var(--sindoor); color: var(--paper); padding: 10px 20px; font-size: 14px; cursor: pointer; }
.ve-btn:disabled { background: var(--line); border-color: var(--line); cursor: not-allowed; }
.ve-btn-ghost { background: transparent; color: var(--sindoor); border-color: var(--line); }
.ve-otp { display: flex; gap: 8px; margin: 12px 0 20px; }
.ve-otp input { width: 44px; height: 52px; text-align: center; font-size: 22px; border: 1px solid var(--line); border-radius: 6px; background: var(--paper-alt); color: var(--ink); }
.ve-error { color: #8f1d2c; font-size: 14px; margin: 0 0 12px; }
.ve-ok { color: #2e6b34; font-size: 14px; margin: 0 0 12px; }
.ve-row { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-top: 16px; }
`;

const RESEND_COOLDOWN = 60;

function maskEmail(email: string): string {
  const [local = "", domain = ""] = email.split("@");
  if (!domain) return "***";
  return `${local.slice(0, 1)}***@${domain}`;
}

export function VerifyEmailPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { emailVerified, setVerified } = useAuth();
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");
  const [email, setEmail] = useState("");
  const [meLoaded, setMeLoaded] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [sending, setSending] = useState(false);
  // Single-flight guard: rapid clicks must not fire parallel requests.
  // (React StrictMode double-invokes effects, not event handlers — this ref
  // covers double-clicks and keyboard+pointer duplicates instead.)
  const resendInFlight = useRef(false);
  const [otp, setOtp] = useState<string[]>(["", "", "", "", "", ""]);
  const [otpMode, setOtpMode] = useState(false);
  const [showChangeEmail, setShowChangeEmail] = useState(false);
  const [newEmail, setNewEmail] = useState("");
  const [password, setPassword] = useState("");
  const otpRefs = useRef<Array<HTMLInputElement | null>>([]);
  const token = params.get("token");

  useEffect(() => {
    fetchMe()
      .then((me) => {
        setEmail(me.email);
        // Default the UI to whatever the server actually issues, so users
        // aren't told to click a link that was never sent. An explicit
        // ?token= link always forces link mode (old emailed links keep
        // working after the flag flips). The toggle still overrides both.
        if (!token) {
          setOtpMode(me.verification_method === "otp");
        }
        setMeLoaded(true);
        // Verification order is email, then phone.
        if (me.email_verified) {
          navigate(me.phone_verified ? "/" : "/verify-phone", { replace: true });
        }
      })
      .catch(() => navigate("/login", { replace: true }));
  }, [navigate, token]);

  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  const doVerifyToken = useCallback(
    async (raw: string) => {
      setStatus("loading");
      setMessage("");
      try {
        await verifyEmail({ token: raw });
        setVerified();
        setStatus("success");
        setMessage("Email verified. Taking you to phone verification…");
        setTimeout(() => navigate("/verify-phone", { replace: true }), 1200);
      } catch (err: any) {
        setStatus("error");
        const code = err?.body?.code as string | undefined;
        setMessage(
          code === "EXPIRED_TOKEN"
            ? "That link has expired. Request a new one below."
            : code === "INVALID_TOKEN"
              ? "That link is invalid or already used. Request a new one below."
              : "Verification failed. Please try again."
        );
      }
    },
    [navigate, setVerified]
  );

  useEffect(() => {
    if (token) void doVerifyToken(token);
  }, [token, doVerifyToken]);

  const handleResend = async () => {
    if (resendInFlight.current) return; // drop duplicate clicks/keys
    resendInFlight.current = true;
    setSending(true);
    setMessage("");
    try {
      const res = await resendVerification();
      setMessage(res.detail);
      setCooldown(RESEND_COOLDOWN);
    } catch (err: any) {
      const body = err?.body as {
        code?: string;
        retry_after?: number;
        retry_after_seconds?: number;
        detail?: string;
      } | undefined;
      const wait = body?.retry_after_seconds ?? body?.retry_after;
      if (err?.status === 429 && wait) {
        if (body?.code === "resend_daily_limit") {
          setMessage(`Daily resend limit reached. Try again in ${wait}s.`);
        } else {
          setMessage(`Please wait ${wait}s before requesting another code.`);
        }
        setCooldown(Math.min(wait, RESEND_COOLDOWN));
      } else if (err?.status === 429) {
        setMessage("Too many requests. Please wait and try again.");
      } else if (err?.status === 503) {
        setMessage(body?.detail ?? "Email could not be sent. Please try again shortly.");
      } else {
        setMessage("Could not send right now. Please try again shortly.");
      }
    } finally {
      setSending(false);
      resendInFlight.current = false;
    }
  };

  const handleOtpChange = (i: number, v: string) => {
    const digit = v.replace(/\D/g, "").slice(-1);
    setOtp((prev) => {
      const next = [...prev];
      next[i] = digit;
      return next;
    });
    if (digit && i < 5) otpRefs.current[i + 1]?.focus();
  };

  const handleOtpKeyDown = (i: number, e: React.KeyboardEvent) => {
    if (e.key === "Backspace" && !otp[i] && i > 0) otpRefs.current[i - 1]?.focus();
  };

  const handleOtpPaste = (e: React.ClipboardEvent) => {
    const digits = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    if (!digits) return;
    e.preventDefault();
    setOtp(digits.padEnd(6, "").split("").slice(0, 6));
    otpRefs.current[Math.min(digits.length, 5)]?.focus();
  };

  const handleOtpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("loading");
    setMessage("");
    try {
      await verifyEmail({ code: otp.join("") });
      setVerified();
      setStatus("success");
      setMessage("Email verified. Taking you to phone verification…");
      setTimeout(() => navigate("/verify-phone", { replace: true }), 1200);
    } catch (err: any) {
      setStatus("error");
      const code = err?.body?.code as string | undefined;
      setMessage(
        code === "too_many_attempts"
          ? "Too many wrong attempts. Request a new code below."
          : code === "expired"
            ? "That code has expired. Request a new one below."
            : code === "not_found"
              ? "No active code found. Request a new one below."
              : "Invalid code. Check and try again."
      );
    }
  };

  const handleChangeEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage("");
    try {
      const res = await changeEmail(newEmail, password);
      setMessage(`${res.message} (${res.pending_email_masked})`);
      setEmail(newEmail);
      setShowChangeEmail(false);
      setCooldown(RESEND_COOLDOWN);
    } catch (err: any) {
      setMessage(err?.body?.message ?? err?.body?.new_email?.[0] ?? "Could not change email.");
    }
  };

  if (emailVerified) {
    navigate("/verify-phone", { replace: true });
    return null;
  }

  // Neutral state until /me/ answers: never assume a mode (and its copy)
  // before the server has told us which one it issues.
  if (!meLoaded) {
    return (
      <div className="ve-wrap">
        <style>{STYLES}</style>
        <main className="ve-card">
          <p className="ve-muted">Checking your verification status…</p>
        </main>
      </div>
    );
  }

  return (
    <div className="ve-wrap">
      <style>{STYLES}</style>
      <main className="ve-card">
        <p className="ve-kicker">Verify your email</p>
        <h1 className="ve-title">Check your inbox</h1>
        <p className="ve-help">
          We sent a verification {otpMode ? "code" : "link"} to{" "}
          <strong>{email ? maskEmail(email) : "your email"}</strong>.{" "}
          {otpMode ? "Enter the 6-digit code below." : "Open the link to finish signing in."}
        </p>

        {status === "loading" && <p className="ve-muted">Verifying…</p>}
        {status === "success" && <p className="ve-ok">{message}</p>}
        {status === "error" && <p className="ve-error">{message}</p>}
        {status === "idle" && message && <p className="ve-muted">{message}</p>}

        {!otpMode && !token && (
          <p className="ve-muted">No link open? Use resend below — a fresh link invalidates older ones.</p>
        )}

        <div className="ve-row">
          <button
            type="button"
            className="ve-btn"
            disabled={cooldown > 0 || sending}
            onClick={handleResend}
          >
            {sending
              ? "Sending…"
              : cooldown > 0
                ? `Resend in ${cooldown}s`
                : "Resend verification"}
          </button>
          {token && (
            <button
              type="button"
              className="ve-btn ve-btn-ghost"
              onClick={() => setOtpMode((m) => !m)}
            >
              {otpMode ? "Use email link instead" : "Enter a code instead"}
            </button>
          )}
        </div>

        {otpMode && (
          <form onSubmit={handleOtpSubmit}>
            <div className="ve-otp" onPaste={handleOtpPaste}>
              {otp.map((d, i) => (
                <input
                  key={i}
                  ref={(el) => {
                    otpRefs.current[i] = el;
                  }}
                  inputMode="numeric"
                  autoComplete={i === 0 ? "one-time-code" : "off"}
                  maxLength={1}
                  value={d}
                  onChange={(e) => handleOtpChange(i, e.target.value)}
                  onKeyDown={(e) => handleOtpKeyDown(i, e)}
                  aria-label={`Digit ${i + 1}`}
                />
              ))}
            </div>
            <button type="submit" className="ve-btn" disabled={otp.some((d) => !d)}>
              Verify code
            </button>
          </form>
        )}

        <div className="ve-row">
          <button
            type="button"
            className="ve-btn ve-btn-ghost"
            onClick={() => setShowChangeEmail((s) => !s)}
          >
            Use a different email
          </button>
          <Link to="/" className="ve-muted">
            Back home
          </Link>
        </div>

        {showChangeEmail && (
          <form onSubmit={handleChangeEmail} style={{ marginTop: 16 }}>
            <div className="ve-field">
              <label htmlFor="ve-new-email">New email</label>
              <input
                id="ve-new-email"
                type="email"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                required
              />
            </div>
            <div className="ve-field">
              <label htmlFor="ve-password">Current password (to confirm it&apos;s you)</label>
              <input
                id="ve-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </div>
            <button type="submit" className="ve-btn">
              Send verification to new address
            </button>
          </form>
        )}
      </main>
    </div>
  );
}
