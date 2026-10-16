import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  fetchMyRegistrationStatus,
  withdrawMyRegistration,
} from '../api/registrations'
import type { RegistrationStatusResponse, MatchProposalResponse } from '../api/registrations'
import { ApiError } from '../api/client'
import MatchDetailsModal from './MatchDetailsModal'
import ConfirmWithdrawDialog from './ConfirmWithdrawDialog'

interface StatusPageProps {
  onReportConcern?: () => void
}

export default function StatusPage({ onReportConcern }: StatusPageProps) {
  const [status, setStatus] = useState<RegistrationStatusResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [withdrawing, setWithdrawing] = useState(false)
  const [confirmingWithdraw, setConfirmingWithdraw] = useState(false)
  const [withdrawn, setWithdrawn] = useState(false)
  const [withdrawError, setWithdrawError] = useState<string | null>(null)
  const [detailsOpen, setDetailsOpen] = useState<MatchProposalResponse | null>(null)

  useEffect(() => {
    fetchMyRegistrationStatus()
      .then((data) => {
        setStatus(data)
        // The backend now returns withdrawn registrations instead of 404ing
        // them, so a reload after withdrawing still reflects reality rather
        // than falling into the "notFound" branch below.
        if (data.withdrawn) {
          setWithdrawn(true)
        }
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 404) {
          setNotFound(true)
        } else {
          console.error('Failed to load status:', err)
        }
      })
      .finally(() => setLoading(false))
  }, [])

  const handleWithdrawConfirmed = async (reason: string) => {
    setWithdrawing(true)
    setWithdrawError(null)
    try {
      await withdrawMyRegistration(reason)
      setWithdrawn(true)
      setConfirmingWithdraw(false)
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        // Already withdrawn (e.g. retried in another tab): the backend is
        // idempotent, so reflect the withdrawn state instead of erroring.
        setWithdrawn(true)
        setConfirmingWithdraw(false)
      } else if (err instanceof ApiError && err.status === 403) {
        setWithdrawError("You don't have permission to withdraw this registration.")
      } else if (err instanceof ApiError && err.status === 401) {
        // An expired session usually redirects to login via the api client;
        // if we get here, invite re-login without losing dialog context.
        setWithdrawError('Your session seems to have expired. Please log in again and retry.')
      } else {
        // Network failure, 5xx — keep the dialog open for a retry.
        setWithdrawError(
          'Something went wrong and the registration was not withdrawn. ' +
          'Check your connection and try again.'
        )
      }
    } finally {
      setWithdrawing(false)
    }
  }

  const handleMatchResponded = (updated: MatchProposalResponse) => {
    setStatus((prev) => {
      if (!prev) return prev
      return {
        ...prev,
        matches: prev.matches.map((m) => (m.id === updated.id ? updated : m)),
      }
    })
    setDetailsOpen(null) // close modal after respond
  }

  const openMatchDetails = (match: MatchProposalResponse) => {
    setDetailsOpen(match)
  }

  const shell = (children: React.ReactNode) => (
    <section className="px-5 pt-[5.5rem] pb-16 sm:px-8 sm:pt-24 sm:pb-20">
      <div className="container max-w-[640px]">{children}</div>
    </section>
  )

  if (loading) {
    return shell(<p className="text-body">Loading your registration…</p>)
  }

  if (notFound) {
    return shell(
      <>
        <p className="text-caption text-text/60 tracking-wider mb-3">No registration yet</p>
        <h1 className="text-heading text-primary mb-4">Nothing to show here yet.</h1>
        <p className="text-body leading-relaxed mb-8">
          This account isn't tied to a registration yet. Once a family member registers,
          its status will appear here.
        </p>
        <Link to="/register" className="btn-primary">Start a registration</Link>
      </>
    )
  }

  if (!status) {
    return shell(
      <p className="text-body">Something went wrong loading your status. Please try again.</p>
    )
  }

  if (withdrawn) {
    return shell(
      <>
        <p className="text-caption text-text/60 tracking-wider mb-3">Registration withdrawn</p>
        <h1 className="text-heading text-primary mb-4">This registration has been withdrawn.</h1>
        <p className="text-body leading-relaxed mb-8">
          No further action will be taken on it. If the family wishes to register again
          in the future, they're welcome to.
        </p>
        <Link to="/register" className="btn-primary">Register again</Link>
      </>
    )
  }

  const canViewDetails = status.verification_status === 'verified'

  return shell(
    <>
      <p className="text-caption text-text/60 tracking-wider mb-3">Registration</p>
      <h1 className="text-heading text-primary mb-2">{status.candidate_name}</h1>
      <p className="text-body text-text/70 mb-8">
        Reference {status.reference} · Registered by {status.guardian_name}
      </p>

      <div className="border-t border-t-border py-8">
        <div className="flex items-center justify-between border border-border px-5 py-4 mb-4">
          <span className="text-body">Verification status</span>
          <VerificationBadge status={status.verification_status} />
        </div>
        {status.verification_status === 'pending' && (
          <p className="text-body text-text/70 leading-relaxed">
            A panjikar is reviewing the family and lineage details. This usually takes a
            few days — there's nothing further needed from you right now.
          </p>
        )}
      </div>

      <div className="border-t border-t-border py-8">
        <h2 className="text-body font-semibold mb-4">
          Proposed match{status.matches.length !== 1 ? 'es' : ''} ({status.matches.length})
        </h2>
        {status.matches.length > 0 ? (
          <div className="space-y-4">
            {status.matches.map((match) => (
              <MatchPreview
                key={match.id}
                match={match}
                disabled={!canViewDetails}
                onOpen={() => openMatchDetails(match)}
              />
            ))}
          </div>
        ) : (
          <p className="text-body text-text/70 leading-relaxed">
            No match has been proposed yet. We'll reach out directly when there's someone
            to share.
          </p>
        )}
      </div>

      {detailsOpen && (
        <MatchDetailsModal
          matchId={String(detailsOpen.id)}
          summary={detailsOpen}
          onClose={() => setDetailsOpen(null)}
          onResponded={handleMatchResponded}
        />
      )}

      <div className="border-t border-t-border py-8">
        {!confirmingWithdraw && (
          <button
            type="button"
            className="border border-primary text-primary px-5 py-2 text-sm"
            onClick={() => {
              setWithdrawError(null)
              setConfirmingWithdraw(true)
            }}
          >
            Withdraw registration
          </button>
        )}
        {confirmingWithdraw && (
          <ConfirmWithdrawDialog
            matchState={
              status.matches.some((m) => m.state === 'both_accepted')
                ? 'both_accepted'
                : status.matches.some((m) => m.state === 'waiting_you' || m.state === 'waiting_other')
                ? 'waiting_you'
                : null
            }
            withdrawing={withdrawing}
            error={withdrawError}
            onCancel={() => {
              if (!withdrawing) {
                setWithdrawError(null)
                setConfirmingWithdraw(false)
              }
            }}
            onConfirm={(reason) => void handleWithdrawConfirmed(reason)}
          />
        )}
      </div>

      <div className="pt-4 text-center">
        <button
          type="button"
          className="text-text/60 text-sm underline"
          onClick={() => onReportConcern?.()}
        >
          Something not right? Report a concern, privately.
        </button>
      </div>
    </>
  )
}

function VerificationBadge({ status }: { status: 'pending' | 'verified' }) {
  const verified = status === 'verified'
  return (
    <span
      className={
        'inline-flex items-center gap-2 text-xs px-3 py-1 border ' +
        (verified ? 'border-accent text-accent' : 'border-border text-text/60')
      }
    >
      <span className={'w-[6px] h-[6px] rounded-full ' + (verified ? 'bg-accent' : 'bg-text/40')} />
      {verified ? 'Verified' : 'Pending'}
    </span>
  )
}

function MatchPreview({
  match,
  disabled,
  onOpen,
}: {
  match: MatchProposalResponse
  disabled: boolean
  onOpen: () => void
}) {
  const stateText: Record<string, string> = {
    waiting_you: 'Waiting on your response',
    waiting_other: 'Waiting on the other family',
    both_accepted: 'Both families have accepted',
    declined: 'This proposal was declined',
  }
  return (
    <div className="border border-border px-5 py-4">
      <p className="text-caption text-text/60 mb-3">Shared by {match.shared_by_panjikar}</p>
      <ul className="text-body leading-relaxed list-disc pl-5 mb-4">
        {match.shared_details.map((line, i) => (
          <li key={i}>{line}</li>
        ))}
      </ul>
      <div className="flex items-center justify-between gap-3">
        <span className="text-body text-text/70 text-sm">{stateText[match.state]}</span>
        <button
          type="button"
          className="btn-primary text-sm shrink-0"
          onClick={onOpen}
          disabled={disabled}
          title={disabled ? 'Available after your registration is verified' : undefined}
        >
          View &amp; respond
        </button>
      </div>
      {disabled && (
        <p className="text-caption text-text/60 mt-3">
          Full details unlock once your registration is verified.
        </p>
      )}
    </div>
  )
}
