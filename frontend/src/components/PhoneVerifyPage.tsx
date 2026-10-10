import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/useAuth";
import {
  changePhone,
  fetchMe,
  resendPhoneOtp,
  startPhoneVerification,
  verifyPhone,
} from "../api/auth";

const STYLES = `
.vp-wrap { font-family: Georgia, "Times New Roman", serif; color: var(--ink); background: var(--paper); min-height: 100vh; padding: 64px 24px 80px; }
.vp-card { max-width: 520px; margin: 0 auto; background: var(--paper); border: 1px solid var(--line); padding: 32px 28px; }
.vp-kicker { margin: 0 0 6px; font-size: 12px; letter-spacing: 0.06em; text-transform: uppercase; color: var(--mango); }
.vp-title { font-family: Georgia, "Times New Roman", serif; color: var(--sindoor); font-size: 24px; line-height: 1.25; margin: 0 0 10px; }
.vp-help { font-size: 14px; line-height: 1.6; margin: 0 0 16px; }
.vp-muted { color: var(--ink); opacity: 0.6; font-size: 13px; }
.vp-field { margin-bottom: 16px; }
.vp-field label { display: block; font-size: 13px; margin-bottom: 6px; opacity: 0.75; }
.vp-field input, .vp-field select { width: 100%; box-sizing: border-box; border: 1px solid var(--line); background: var(--paper-alt); padding: 10px 12px; font-size: 14px; border-radius: 6px; color: var(--ink); }
.vp-phone-row { display: flex; gap: 8px; }
.vp-phone-row select { width: 128px; flex-shrink: 0; }
.vp-btn { border: 1px solid var(--sindoor); background: var(--sindoor); color: var(--paper); padding: 10px 20px; font-size: 14px; cursor: pointer; }
.vp-btn:disabled { background: var(--line); border-color: var(--line); cursor: not-allowed; }
.vp-btn-ghost { background: transparent; color: var(--sindoor); border-color: var(--line); }
.vp-otp { display: flex; gap: 8px; margin: 12px 0 20px; }
.vp-otp input { width: 44px; height: 52px; text-align: center; font-size: 22px; border: 1px solid var(--line); border-radius: 6px; background: var(--paper-alt); color: var(--ink); }
.vp-error { color: #8f1d2c; font-size: 14px; margin: 0 0 12px; }
.vp-ok { color: #2e6b34; font-size: 14px; margin: 0 0 12px; }
.vp-row { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin-top: 16px; }
.vp-badges { display: flex; gap: 8px; margin: 0 0 16px; }
.vp-badge { font-size: 12px; padding: 3px 10px; border: 1px solid var(--line); border-radius: 999px; }
.vp-badge[data-on="true"] { border-color: var(--sindoor); color: var(--sindoor); }
.vp-badge[data-on="false"] { opacity: 0.55; }
`;

// Indicative client list only — the server allow-list (PHONE_ALLOWED_COUNTRIES)
// is authoritative; unsupported picks fail with a clear message.
const COUNTRIES = [
  { iso: "NP", name: "Nepal", dial: "+977" },
  { iso: "IN", name: "India", dial: "+91" },
  { iso: "BD", name: "Bangladesh", dial: "+880" },
  { iso: "AE", name: "UAE", dial: "+971" },
  { iso: "QA", name: "Qatar", dial: "+974" },
  { iso: "SA", name: "Saudi Arabia", dial: "+966" },
  { iso: "MY", name: "Malaysia", dial: "+60" },
  { iso: "GB", name: "UK", dial: "+44" },
  { iso: "US", name: "USA", dial: "+1" },
  { iso: "AU", name: "Australia", dial: "+61" },
];

const RESEND_COOLDOWN = 60;
const OTP_EXPIRY_SECONDS = 5 * 60;

export function PhoneVerifyPage() {
  const navigate = useNavigate();
  const { emailVerified, phoneVerified, setPhoneVerified } = useAuth();
  const [step, setStep] = useState<"number" | "code">("number");
  const [country, setCountry] = useState("NP");
  const [national, setNational] = useState("");
  const [masked, setMasked] = useState("");
  const [otp, setOtp] = useState<string[]>(["", "", "", "", "", ""]);
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");
  const [cooldown, setCooldown] = useState(0);
  const [expiresIn, setExpiresIn] = useState(0);
  const [channel, setChannel] = useState<"sms" | "whatsapp" | "voice">("sms");
  const [showChange, setShowChange] = useState(false);
  const [newCountry, setNewCountry] = useState("NP");
  const [newNational, setNewNational] = useState("");
  const [password, setPassword] = useState("");
  const otpRefs = useRef<Array<HTMLInputElement | null>>([]);

  useEffect(() => {
    fetchMe()
      .then((me) => {
        if (!me.email_verified) {
          navigate("/verify-email", { replace: true });
          return;
        }
        if (me.phone_verified) {
          navigate("/", { replace: true });
          return;
        }
        if (me.phone_masked) {
          setMasked(me.phone_masked);
          setStep("code");
        }
      })
      .catch(() => navigate("/login", { replace: true }));
  }, [navigate]);

  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  useEffect(() => {
    if (expiresIn <= 0) return;
    const t = setTimeout(() => setExpiresIn((s) => s - 1), 1000);
    return () => clearTimeout(t);
  }, [expiresIn]);

  if (phoneVerified) {
    navigate("/", { replace: true });
    return null;
  }

  const startWith = async (iso: string, nat: string, ch: typeof channel) => {
    setStatus("loading");
    setMessage("");
    try {
      await startPhoneVerification({ country_code: iso, national_number: nat, channel: ch });
      setStep("code");
      setCooldown(RESEND_COOLDOWN);
      setExpiresIn(OTP_EXPIRY_SECONDS);
      setStatus("idle");
      setMessage("Code sent. It expires in 5 minutes.");
    } catch (err: any) {
      setStatus("error");
      const code = err?.body?.code as string | undefined;
      setMessage(
        code === "COUNTRY_NOT_SUPPORTED"
          ? "Phone numbers from this country aren't supported yet."
          : code === "INVALID_NUMBER"
            ? "That doesn't look like a valid mobile number. Check and try again."
            : code === "LINE_TYPE_BLOCKED"
              ? (err.body?.message as string) ?? "This number type isn't accepted. Use a mobile number."
              : code === "RATE_LIMITED"
                ? "Too many requests. Try again later."
                : (err?.body?.message as string) ?? "Could not send the code. Try again."
      );
    }
  };

  const handleOtpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("loading");
    setMessage("");
    try {
      const res = await verifyPhone(otp.join(""));
      setPhoneVerified();
      setMasked(res.phone_masked);
      setStatus("success");
      setMessage("Phone verified. Taking you to the app…");
      setTimeout(() => navigate("/", { replace: true }), 1200);
    } catch (err: any) {
      setStatus("error");
      const code = err?.body?.code as string | undefined;
      setMessage(
        code === "OTP_LOCKED"
          ? "Too many wrong attempts. Request a new code below."
          : code === "EXPIRED_CODE"
            ? "That code has expired. Request a new one below."
            : "Wrong code. Check and try again."
      );
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

  const handleResend = async (ch: typeof channel) => {
    setChannel(ch);
    setMessage("");
    try {
      await resendPhoneOtp(ch);
      setCooldown(RESEND_COOLDOWN);
      setExpiresIn(OTP_EXPIRY_SECONDS);
      setMessage(ch === "sms" ? "Code re-sent." : `Code re-sent via ${ch === "voice" ? "call" : "WhatsApp"}.`);
    } catch (err: any) {
      const code = err?.body?.code as string | undefined;
      setMessage(
        code === "RATE_LIMITED"
          ? "Too many requests. Try again later."
          : code === "CAPTCHA_REQUIRED"
            ? "Additional verification needed — please try again shortly."
            : "Could not re-send right now. Try again shortly."
      );
    }
  };

  const handleChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage("");
    try {
      const res = await changePhone(
        { country_code: newCountry, national_number: newNational },
        password
      );
      setMessage(`${res.message} (${res.pending_phone_masked})`);
      setStep("code");
      setCooldown(RESEND_COOLDOWN);
      setExpiresIn(OTP_EXPIRY_SECONDS);
      setShowChange(false);
    } catch (err: any) {
      setMessage(err?.body?.message ?? "Could not change number.");
    }
  };

  const expText =
    expiresIn > 0
      ? `Code expires in ${Math.floor(expiresIn / 60)}:${String(expiresIn % 60).padStart(2, "0")}`
      : "Code expired — request a new one.";

  return (
    <div className="vp-wrap">
      <style>{STYLES}</style>
      <main className="vp-card">
        <p className="vp-kicker">Verify your phone</p>
        <h1 className="vp-title">Secure your account</h1>
        <div className="vp-badges" aria-label="Verification status">
          <span className="vp-badge" data-on={String(!!emailVerified)}>
            Email {emailVerified ? "✓ verified" : "… pending"}
          </span>
          <span className="vp-badge" data-on={String(!!phoneVerified)}>
            Phone {phoneVerified ? "✓ verified" : "… pending"}
          </span>
        </div>

        {step === "number" && (
          <>
            <p className="vp-help">
              Enter the mobile number you control. We&apos;ll text you a 6-digit code
              (valid 5 minutes).
            </p>
            {status === "error" && <p className="vp-error">{message}</p>}
            <div className="vp-field">
              <label htmlFor="vp-country">Country</label>
              <div className="vp-phone-row">
                <select
                  id="vp-country"
                  value={country}
                  onChange={(e) => setCountry(e.target.value)}
                >
                  {COUNTRIES.map((c) => (
                    <option key={c.iso} value={c.iso}>
                      {c.name} ({c.dial})
                    </option>
                  ))}
                </select>
                <input
                  id="vp-national"
                  inputMode="tel"
                  autoComplete="tel-national"
                  placeholder="e.g. 9812345678"
                  value={national}
                  onChange={(e) => setNational(e.target.value.replace(/[^\d+\s]/g, ""))}
                  aria-label="Phone number without country code"
                />
              </div>
            </div>
            <button
              type="button"
              className="vp-btn"
              disabled={status === "loading" || !national.trim()}
              onClick={() => void startWith(country, national.trim(), "sms")}
            >
              {status === "loading" ? "Sending…" : "Send code"}
            </button>
          </>
        )}

        {step === "code" && (
          <>
            <p className="vp-help">
              Code sent{masked ? <> to <strong>{masked}</strong></> : ""}.{" "}
              <span className="vp-muted">{expText}</span>
            </p>
            {status === "success" && <p className="vp-ok">{message}</p>}
            {status === "error" && <p className="vp-error">{message}</p>}
            {status === "idle" && message && <p className="vp-muted">{message}</p>}
            <form onSubmit={handleOtpSubmit}>
              <div className="vp-otp" onPaste={handleOtpPaste}>
                {otp.map((d, i) => (
                  <input
                    key={i}
                    ref={(el) => {
                      otpRefs.current[i] = el;
                    }}
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    maxLength={1}
                    value={d}
                    onChange={(e) => handleOtpChange(i, e.target.value)}
                    onKeyDown={(e) => handleOtpKeyDown(i, e)}
                    aria-label={`Digit ${i + 1}`}
                  />
                ))}
              </div>
              <button type="submit" className="vp-btn" disabled={otp.some((d) => !d)}>
                Verify code
              </button>
            </form>
            <div className="vp-row">
              <button
                type="button"
                className="vp-btn vp-btn-ghost"
                disabled={cooldown > 0}
                onClick={() => void handleResend("sms")}
              >
                {cooldown > 0 ? `Resend in ${cooldown}s` : "Resend code"}
              </button>
              <button
                type="button"
                className="vp-btn vp-btn-ghost"
                disabled={cooldown > 0}
                onClick={() => void handleResend("voice")}
                title="Receive the code by automated call"
              >
                Call me
              </button>
              <button
                type="button"
                className="vp-btn vp-btn-ghost"
                disabled={cooldown > 0}
                onClick={() => void handleResend("whatsapp")}
                title="Receive the code on WhatsApp"
              >
                WhatsApp
              </button>
            </div>
            <div className="vp-row">
              <button
                type="button"
                className="vp-btn vp-btn-ghost"
                onClick={() => {
                  setStep("number");
                  setShowChange(false);
                }}
              >
                Change number
              </button>
              <Link to="/" className="vp-muted">
                Back home
              </Link>
            </div>
            <div className="vp-row">
              <button
                type="button"
                className="vp-btn vp-btn-ghost"
                onClick={() => setShowChange((s) => !s)}
              >
                Move to a new number (needs password)
              </button>
            </div>
            {showChange && (
              <form onSubmit={handleChange} style={{ marginTop: 16 }}>
                <div className="vp-field">
                  <label htmlFor="vp-new-country">New number</label>
                  <div className="vp-phone-row">
                    <select
                      id="vp-new-country"
                      value={newCountry}
                      onChange={(e) => setNewCountry(e.target.value)}
                    >
                      {COUNTRIES.map((c) => (
                        <option key={c.iso} value={c.iso}>
                          {c.name} ({c.dial})
                        </option>
                      ))}
                    </select>
                    <input
                      inputMode="tel"
                      value={newNational}
                      onChange={(e) => setNewNational(e.target.value.replace(/[^\d+\s]/g, ""))}
                      required
                    />
                  </div>
                </div>
                <div className="vp-field">
                  <label htmlFor="vp-password">Current password</label>
                  <input
                    id="vp-password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="current-password"
                    required
                  />
                </div>
                <button type="submit" className="vp-btn">
                  Send code to new number
                </button>
              </form>
            )}
          </>
        )}
      </main>
    </div>
  );
}
