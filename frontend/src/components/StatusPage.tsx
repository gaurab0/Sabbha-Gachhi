import React, { useEffect, useState } from "react";
import {
  fetchRegistrationStatus,
  withdrawRegistration,
} from "../api/registration";
import type { RegistrationStatusResponse } from "../api/registration";

/**
 * StatusPage
 * Component 2 of the Sabha Gachhi matrimonial-registration site.
 * Private status view for a registered family — accessed via a
 * private link/login (auth handling is out of scope here).
 * Frontend only — data is mocked; wire real fetch/withdraw calls
 * where marked.
 */

interface StatusPageProps {
  reference: string;
  onOpenMatchProposal?: (matchId: number) => void;
  onReportConcern?: () => void;
}

// ---------------------------------------------------------------- Root --

export default function StatusPage({
  reference,
  onOpenMatchProposal,
  onReportConcern,
}: StatusPageProps): React.ReactElement {
  const [status, setStatus] = useState<RegistrationStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [withdrawing, setWithdrawing] = useState(false);
  const [confirmingWithdraw, setConfirmingWithdraw] = useState(false);
  const [withdrawn, setWithdrawn] = useState(false);

  useEffect(() => {
    fetchRegistrationStatus(reference)
      .then(setStatus)
      .catch((err) => console.error("Failed to load status:", err))
      .finally(() => setLoading(false));
  }, [reference]);

  const handleWithdrawConfirmed = async () => {
    setWithdrawing(true);
    try {
      await withdrawRegistration(reference);
      setWithdrawn(true);
    } catch (err) {
      console.error("Withdraw failed:", err);
    } finally {
      setWithdrawing(false);
      setConfirmingWithdraw(false);
    }
  };

  if (loading) {
    return (
      <main className="container py-16">
        <p className="text-body"><span className="spinner mr-2" aria-hidden="true" />Loading…</p>
      </main>
    );
  }

  if (!status) {
    return (
      <main className="container py-16">
        <div className="card max-w-[620px]">
          <p className="text-caption text-text/60 tracking-wider mb-3">Registration status</p>
          <h1 className="text-heading text-primary leading-tight mb-3">We couldn't find that registration.</h1>
          <p className="text-body leading-relaxed">
            The reference may have been mistyped. Please check the private
            link or reference shared with the family and try again.
          </p>
        </div>
      </main>
    );
  }

  if (withdrawn) {
    return (
      <main className="container py-16">
        <div className="card max-w-[620px]">
          <span className="badge mb-3"><span className="badge__dot" aria-hidden="true" />Withdrawn</span>
          <h1 className="text-heading text-primary leading-tight mb-3">This registration has been withdrawn.</h1>
          <p className="text-body leading-relaxed">
            No further action will be taken on it. If the family wishes to
            register again in the future, they're welcome to.
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="container py-16">
      <p className="text-caption text-text/60 tracking-wider mb-2">Saurath Sabha Gachhi</p>
      <p className="text-caption text-text/60 mb-8">Registration status</p>
      <div className="card max-w-[620px]">
        <section className="border-b border-border pb-8 mb-8">
          <p className="text-caption text-text/60 tracking-wider mb-3">Registration</p>
          <h1 className="text-heading text-primary leading-tight mb-3">{status.candidate_name}</h1>
          <p className="text-body text-text/55 leading-relaxed mb-6">
            Reference {status.reference} · Registered by {status.guardian_name}
          </p>

          <div className="flex items-center justify-between gap-4 border border-border rounded px-4 py-3">
            <span className="label mb-0">Verification status</span>
            <VerificationBadge status={status.verification_status} />
          </div>

          {status.verification_status === "pending" && (
            <p className="text-body text-text/55 leading-relaxed mt-4">
              A panjikar is reviewing the family and lineage details. This
              usually takes a few days — there's nothing further needed from
              you right now.
            </p>
          )}
        </section>

        <section className="border-b border-border pb-8 mb-8">
          <p className="text-caption text-text/60 tracking-wider mb-4">Proposed match</p>
          {status.match ? (
            <MatchPreview
              match={status.match}
              onOpen={() => onOpenMatchProposal?.(status.match!.id)}
            />
          ) : (
            <p className="text-body text-text/55 leading-relaxed">
              No match has been proposed yet. Your panjikar will reach out
              directly when they have someone in mind.
            </p>
          )}
        </section>

        <section>
          <p className="text-caption text-text/60 tracking-wider mb-4">This registration</p>

          {!confirmingWithdraw && (
            <button
              type="button"
              className="btn-outline"
              onClick={() => setConfirmingWithdraw(true)}
            >
              Withdraw registration
            </button>
          )}

          {confirmingWithdraw && (
            <div className="quote-block">
              <p className="text-body leading-relaxed mb-4">
                This will withdraw the registration. It can be done at any
                time, for any reason.
              </p>
              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  className="btn-outline"
                  onClick={() => setConfirmingWithdraw(false)}
                  disabled={withdrawing}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={handleWithdrawConfirmed}
                  disabled={withdrawing}
                >
                  {withdrawing ? "Withdrawing…" : "Yes, withdraw"}
                </button>
              </div>
            </div>
          )}
        </section>
      </div>

      <p className="max-w-[620px] mt-8">
        <button
          type="button"
          className="btn-quiet"
          onClick={() => onReportConcern?.()}
        >
          Something not right? Report a concern, privately.
        </button>
      </p>
    </main>
  );
}

// ---------------------------------------------------------------- Bits --

function VerificationBadge({ status }: { status: RegistrationStatusResponse["verification_status"] }) {
  const verified = status === "verified";
  const label = verified ? "Verified" : "Pending";
  return (
    <span className={verified ? "badge badge--success" : "badge"}>
      <span className="badge__dot" aria-hidden="true" />
      {label}
    </span>
  );
}

function MatchPreview({
  match,
  onOpen,
}: {
  match: NonNullable<RegistrationStatusResponse["match"]>;
  onOpen: () => void;
}) {
  return (
    <div>
      <p className="text-body text-text/55 leading-relaxed mb-4">Shared by {match.shared_by_panjikar}</p>

      <ul className="flex flex-col gap-2 mb-6">
        {match.shared_details.map((line) => (
          <li key={line} className="text-body relative pl-5 leading-relaxed">
            <span className="absolute left-0 top-[0.55em] w-[5px] h-[5px] rounded-full bg-accent" />
            {line}
          </li>
        ))}
      </ul>

      <div className="flex flex-wrap items-center justify-between gap-4">
        <MatchStateLabel state={match.state} />
        <button type="button" className="btn-primary" onClick={onOpen}>
          View &amp; respond
        </button>
      </div>
    </div>
  );
}

function MatchStateLabel({ state }: { state: NonNullable<RegistrationStatusResponse["match"]>["state"] }) {
  const text: Record<NonNullable<RegistrationStatusResponse["match"]>["state"], string> = {
    waiting_you: "Waiting on your response",
    waiting_other: "Waiting on the other family",
    both_accepted: "Both families have accepted",
    declined: "This proposal was declined",
  };
  return <span className="text-caption text-text/60">{text[state]}</span>;
}