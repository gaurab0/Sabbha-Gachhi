import React, { useState } from "react";

/**
 * ReportConcernForm
 * Component 4 of the Sabha Gachhi matrimonial-registration site.
 * Reached via a quiet link in the Status Page footer.
 * Frontend only — submission is mocked; wire a real API call
 * where marked.
 */

// ---------------------------------------------------------------- Types --

type ConcernTopic =
  | "detail_feels_wrong"
  | "unwanted_contact"
  | "unsure_about_match"
  | "something_else"
  | "";

interface ConcernSubmission {
  registrationId: string;
  topic: ConcernTopic;
  description: string;
  contactBack: string;
}

interface ReportConcernFormProps {
  registrationId?: string;
  onSubmit?: (submission: ConcernSubmission) => Promise<void> | void;
  onBackToStatus?: () => void;
}

// ---------------------------------------------------------------- Root --

const TOPIC_OPTIONS: { value: ConcernTopic; label: string }[] = [
  { value: "detail_feels_wrong", label: "A detail about the registration feels wrong" },
  { value: "unwanted_contact", label: "Someone contacted us in a way that felt off" },
  { value: "unsure_about_match", label: "I'm unsure about a proposed match" },
  { value: "something_else", label: "Something else" },
];

export default function ReportConcernForm({
  registrationId = "",
  onSubmit,
  onBackToStatus,
}: ReportConcernFormProps): React.ReactElement {
  const [regId, setRegId] = useState(registrationId);
  const [topic, setTopic] = useState<ConcernTopic>("");
  const [description, setDescription] = useState("");
  const [contactBack, setContactBack] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const canSubmit = description.trim().length > 0;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    const submission: ConcernSubmission = {
      registrationId: regId,
      topic,
      description,
      contactBack,
    };
    try {
      if (onSubmit) {
        await onSubmit(submission);
      } else {
        // MOCK — replace with a real API call.
        await new Promise((resolve) => setTimeout(resolve, 700));
      }
      setSubmitted(true);
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="mh-concern">
        <style>{STYLES}</style>
        <main className="mh-concern-card">
          <p className="mh-kicker" data-accent="mango">Received</p>
          <h1 className="mh-title">We have this.</h1>
          <p className="mh-help">
            A panjikar will look into it and follow up with you privately.
            Nothing about this is shared with anyone else involved in the
            registration or match.
          </p>
          <button type="button" className="mh-btn mh-btn-ghost" onClick={() => onBackToStatus?.()}>
            Back to status
          </button>
        </main>
      </div>
    );
  }

  return (
    <div className="mh-concern">
      <style>{STYLES}</style>

      <header className="mh-header">
        <button type="button" className="mh-back-link" onClick={() => onBackToStatus?.()}>
          ← Back to status
        </button>
        <div className="mh-header-mark" aria-hidden="true">⟡</div>
        <div>
          <p className="mh-eyebrow">Saurath Sabha Gachhi</p>
          <p className="mh-step-trail">Tell us privately</p>
        </div>
      </header>

      <main className="mh-concern-card">
        <p className="mh-kicker" data-accent="sindoor">Report a concern</p>
        <h1 className="mh-title">If something doesn't feel right, tell us.</h1>
        <p className="mh-help">
          This goes straight to a panjikar, privately. Write as much or as
          little as you'd like — there's no wrong way to say it.
        </p>

        <div className="mh-field">
          <label>Registration reference (if you have it)</label>
          <input
            value={regId}
            onChange={(e) => setRegId(e.target.value)}
            placeholder="e.g. SG-482913"
          />
        </div>

        <div className="mh-field">
          <label>What's this about? (optional)</label>
          <div className="mh-topic-grid">
            {TOPIC_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                className={"mh-topic-chip" + (topic === opt.value ? " is-selected" : "")}
                onClick={() => setTopic(topic === opt.value ? "" : opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <div className="mh-field">
          <label>What happened, in your own words</label>
          <textarea
            rows={5}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Tell us what's going on. Take your time."
          />
        </div>

        <div className="mh-field">
          <label>Best way to reach you back (optional)</label>
          <input
            value={contactBack}
            onChange={(e) => setContactBack(e.target.value)}
            placeholder="Phone or email — only if you'd like a follow-up"
          />
        </div>

        <div className="mh-actions">
          <span />
          <button
            type="button"
            className="mh-btn mh-btn-primary"
            disabled={!canSubmit || submitting}
            onClick={handleSubmit}
          >
            {submitting ? "Sending…" : "Send privately"}
          </button>
        </div>
      </main>
    </div>
  );
}

// ---------------------------------------------------------------- Styles --

const STYLES = `
:root {
  --sindoor: #7A1F2E;
  --turmeric: #DD9A34;
  --mango: #5B7A3A;
  --ink: #3B2A1E;
  --paper: #FDFBF8;
  --paper-alt: #FDFBF8;
  --line: #E7E1D8;
}

.mh-concern {
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
  max-width: 640px;
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

.mh-concern-card {
  max-width: 640px;
  margin: 0 auto;
  background: var(--paper);
  border: 1px solid var(--line);
  padding: 24px;
}

.mh-kicker {
  margin: 0 0 6px;
  font-size: 12px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.mh-kicker[data-accent="sindoor"] { color: var(--sindoor); }
.mh-kicker[data-accent="mango"] { color: var(--mango); }

.mh-title {
  font-family: inherit;
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

.mh-field { margin-bottom: 20px; }
.mh-field label {
  display: block;
  font-size: 13px;
  margin-bottom: 6px;
  color: var(--ink);
  opacity: 0.75;
}
.mh-field input, .mh-field textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--line);
  background: var(--paper-alt);
  padding: 10px 12px;
  font-size: 14px;
  font-family: inherit;
  color: var(--ink);
  resize: vertical;
}
.mh-field input:focus, .mh-field textarea:focus {
  outline: 2px solid var(--sindoor);
  outline-offset: 1px;
}

.mh-topic-grid {
  display: grid;
  gap: 8px;
}
.mh-topic-chip {
  text-align: left;
  border: 1px solid var(--line);
  background: var(--paper-alt);
  padding: 10px 14px;
  font-size: 13px;
  cursor: pointer;
  color: var(--ink);
  transition: border-color 0.15s ease, background-color 0.15s ease,
    color 0.15s ease;
}
.mh-topic-chip:hover:not(.is-selected) {
  border-color: var(--ink);
  background: var(--paper);
}
.mh-topic-chip.is-selected {
  border-color: var(--turmeric);
  background: var(--paper);
  color: var(--ink);
  font-weight: 600;
}

.mh-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 28px;
  padding-top: 20px;
  border-top: 1px solid var(--line);
}

.mh-btn {
  border: 1px solid var(--ink);
  background: transparent;
  padding: 10px 20px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease,
    border-color 0.15s ease, transform 0.15s ease;
}
.mh-btn:active {
  transform: translateY(1px);
}
.mh-btn-primary {
  background: var(--sindoor);
  border-color: var(--sindoor);
  color: var(--paper);
}
.mh-btn-primary:not(:disabled):hover {
  background: #63182A;
  border-color: #63182A;
}
.mh-btn-primary:disabled {
  background: var(--line);
  border-color: var(--line);
  cursor: not-allowed;
}
.mh-btn-ghost {
  border-color: var(--line);
  color: #6b5d4d;
  background: transparent;
}
.mh-btn-ghost:not(:disabled):hover {
  border-color: var(--ink);
  color: var(--ink);
}
`;