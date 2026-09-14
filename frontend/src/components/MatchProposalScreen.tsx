import React, { useEffect, useState } from "react";
import {
  fetchMatchProposal,
  respondToMatchProposal,
} from "../api/registration";
import type { MatchProposalResponse } from "../api/registration";

/**
 * MatchProposalScreen
 * Component 3 of the Sabha Gachhi matrimonial-registration site.
 * Reached from the Status Page's "View & respond" action.
 * Frontend only — responses are mocked locally; wire real API
 * calls where marked.
 */

interface MatchProposalScreenProps {
  matchId: string;
  onBackToStatus?: () => void;
}

// ---------------------------------------------------------------- Root --

export default function MatchProposalScreen({
  matchId,
  onBackToStatus,
}: MatchProposalScreenProps): React.ReactElement {
  const [proposal, setProposal] = useState<MatchProposalResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [confirmingDecline, setConfirmingDecline] = useState(false);
  const [working, setWorking] = useState(false);

  useEffect(() => {
    fetchMatchProposal(matchId)
      .then(setProposal)
      .catch((err) => console.error("Failed to load proposal:", err))
      .finally(() => setLoading(false));
  }, [matchId]);

  const handleAccept = async () => {
    setWorking(true);
    try {
      const updated = await respondToMatchProposal(matchId, "accept");
      setProposal(updated);
    } catch (err) {
      console.error("Accept failed:", err);
    } finally {
      setWorking(false);
    }
  };

  const handleDeclineConfirmed = async () => {
    setWorking(true);
    try {
      const updated = await respondToMatchProposal(matchId, "decline");
      setProposal(updated);
    } catch (err) {
      console.error("Decline failed:", err);
    } finally {
      setWorking(false);
      setConfirmingDecline(false);
    }
  };

  if (loading) {
    return (
      <div className="mh-proposal">
        <style>{STYLES}</style>
        <main className="mh-proposal-card">
          <p className="mh-help"><span className="mh-spinner" aria-hidden="true" /> Loading…</p>
        </main>
      </div>
    );
  }

  if (!proposal) {
    return (
      <div className="mh-proposal">
        <style>{STYLES}</style>
        <main className="mh-proposal-card">
          <p className="mh-kicker" data-accent="sindoor">Proposed match</p>
          <h1 className="mh-title">This proposal couldn't be found.</h1>
          <p className="mh-help mh-help-muted">
            The link may have been mistyped or is no longer active. Please
            check with your panjikar.
          </p>
        </main>
      </div>
    );
  }

  const state = proposal.state;

  return (
    <div className="mh-proposal">
      <style>{STYLES}</style>

      <header className="mh-header">
        <button
          type="button"
          className="mh-back-link"
          onClick={() => onBackToStatus?.()}
        >
          ← Back to status
        </button>
        <div className="mh-header-mark" aria-hidden="true">⟡</div>
        <div>
          <p className="mh-eyebrow">Saurath Sabha Gachhi</p>
          <p className="mh-step-trail">Proposed match</p>
        </div>
      </header>

      <main className="mh-proposal-card">
        <section className="mh-block">
          <p className="mh-kicker" data-accent="turmeric">Shared by your panjikar</p>
          <p className="mh-help mh-help-muted">
            {proposal.shared_by_panjikar} · proposed {proposal.proposed_on}
          </p>

          <ul className="mh-facts-list">
            {proposal.shared_details.map((line, idx) => (
              <li key={idx}>{line}</li>
            ))}
          </ul>
        </section>

        <section className="mh-block">
          <p className="mh-kicker" data-accent="sindoor">Where this stands</p>
          <StateBanner state={state} />
        </section>

        {state === "waiting_you" && !confirmingDecline && (
          <section className="mh-block mh-actions-block">
            <p className="mh-help">
              Take whatever time is needed. There's no urgency here — respond
              when the family is ready.
            </p>
            <div className="mh-response-actions">
              <button
                type="button"
                className="mh-btn mh-btn-outline"
                onClick={() => setConfirmingDecline(true)}
                disabled={working}
              >
                Decline
              </button>
              <button
                type="button"
                className="mh-btn mh-btn-primary"
                onClick={handleAccept}
                disabled={working}
              >
                {working ? "Recording…" : "Accept"}
              </button>
            </div>
          </section>
        )}

        {state === "waiting_you" && confirmingDecline && (
          <section className="mh-block">
            <div className="mh-decline-confirm">
              <p className="mh-help">
                This will decline the proposal. The other family will only be
                told that it did not move forward — nothing more.
              </p>
              <div className="mh-decline-actions">
                <button
                  type="button"
                  className="mh-btn mh-btn-ghost"
                  onClick={() => setConfirmingDecline(false)}
                  disabled={working}
                >
                  Go back
                </button>
                <button
                  type="button"
                  className="mh-btn mh-btn-primary"
                  onClick={handleDeclineConfirmed}
                  disabled={working}
                >
                  {working ? "Recording…" : "Yes, decline"}
                </button>
              </div>
            </div>
          </section>
        )}

        {state === "both_accepted" && (
          <ContactPanel
            contact={{
              guardianName: proposal.contact_guardian_name,
              phone: proposal.contact_phone,
              email: proposal.contact_email,
            }}
          />
        )}
      </main>
    </div>
  );
}

// ---------------------------------------------------------------- Bits --

function StateBanner({ state }: { state: MatchProposalResponse["state"] }) {
  const copy: Record<MatchProposalResponse["state"], { title: string; body: string; accent: string }> = {
    waiting_you: {
      title: "Waiting on your response",
      body: "The other family has been told of this proposal. Nothing moves forward until you respond.",
      accent: "turmeric",
    },
    waiting_other: {
      title: "Waiting on the other family",
      body: "You've accepted. We're waiting to hear from the other family — we'll let you know as soon as they respond.",
      accent: "turmeric",
    },
    both_accepted: {
      title: "Both families have accepted",
      body: "Contact details have been shared below, for the families to take things forward directly.",
      accent: "mango",
    },
    declined: {
      title: "This proposal did not move forward",
      body: "No contact details were ever shared. Your panjikar will keep this in mind for future proposals.",
      accent: "sindoor",
    },
  };
  const c = copy[state];
  return (
    <div className="mh-state-banner" data-accent={c.accent}>
      <p className="mh-state-title">{c.title}</p>
      <p className="mh-state-body">{c.body}</p>
    </div>
  );
}

function ContactPanel({
  contact,
}: {
  contact: { guardianName: string; phone: string; email: string };
}) {
  return (
    <section className="mh-block">
      <p className="mh-kicker" data-accent="mango">Contact details</p>
      <div className="mh-contact-panel">
        <div className="mh-contact-row">
          <span>Guardian</span>
          <strong>{contact.guardianName}</strong>
        </div>
        <div className="mh-contact-row">
          <span>Phone</span>
          <strong>{contact.phone}</strong>
        </div>
        <div className="mh-contact-row">
          <span>Email</span>
          <strong>{contact.email}</strong>
        </div>
      </div>
    </section>
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

.mh-proposal-card {
  max-width: 640px;
  margin: 0 auto;
  background: var(--paper);
  border: 1px solid var(--line);
  padding: 24px;
}

.mh-block {
  padding-bottom: 24px;
  margin-bottom: 24px;
  border-bottom: 1px solid var(--line);
}
.mh-block:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.mh-kicker {
  margin: 0 0 6px;
  font-size: 12px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.mh-kicker[data-accent="sindoor"] { color: var(--sindoor); }
.mh-kicker[data-accent="turmeric"] { color: var(--turmeric); }
.mh-kicker[data-accent="mango"] { color: var(--mango); }

.mh-help {
  font-size: 14px;
  line-height: 1.6;
  color: var(--ink);
  margin: 0 0 12px;
}
.mh-help-muted { color: var(--ink); opacity: 0.6; margin-bottom: 14px; }

.mh-photo-introduction {
  margin: 0 0 18px;
  max-width: 180px;
}
.mh-photo-introduction img {
  display: block;
  width: 140px;
  height: 176px;
  object-fit: cover;
  border-radius: 8px;
}
.mh-photo-introduction p {
  margin: 8px 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--ink);
  opacity: 0.6;
}

.mh-facts-list {
  margin: 0;
  padding-left: 18px;
  font-size: 15px;
  line-height: 1.8;
  color: var(--ink);
}

.mh-state-banner {
  border-left: 3px solid var(--line);
  background: var(--paper-alt);
  padding: 14px 16px;
}
.mh-state-banner[data-accent="turmeric"] { border-left-color: var(--turmeric); }
.mh-state-banner[data-accent="mango"] { border-left-color: var(--mango); }
.mh-state-banner[data-accent="sindoor"] { border-left-color: var(--sindoor); }

.mh-state-title {
  margin: 0 0 4px;
  font-weight: 600;
  font-size: 15px;
}
.mh-state-body {
  margin: 0;
  font-size: 13px;
  color: var(--ink);
  opacity: 0.75;
  line-height: 1.6;
}

.mh-actions-block { }
.mh-response-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.mh-decline-confirm {
  background: var(--paper-alt);
  border: 1px solid var(--line);
  padding: 14px 16px;
}
.mh-decline-actions {
  display: flex;
  gap: 10px;
  margin-top: 10px;
  justify-content: flex-end;
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
.mh-btn-outline {
  border-color: var(--sindoor);
  color: var(--sindoor);
  background: transparent;
}
.mh-btn-outline:not(:disabled):hover {
  background: var(--sindoor);
  color: var(--paper);
}
.mh-btn-outline:disabled {
  border-color: var(--line);
  color: var(--line);
  cursor: not-allowed;
}

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
@keyframes mh-spin {
  to { transform: rotate(360deg); }
}

.mh-contact-panel {
  background: var(--paper-alt);
  border: 1px solid var(--mango);
}
.mh-contact-row {
  display: flex;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--line);
  font-size: 14px;
}
.mh-contact-row:last-child { border-bottom: none; }
.mh-contact-row span { color: var(--ink); opacity: 0.6; }
.mh-contact-row strong { color: var(--ink); letter-spacing: 0.01em; }
`;