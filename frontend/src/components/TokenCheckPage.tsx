import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  fetchMyRegistrationStatus,
  withdrawMyRegistration,
} from '../api/registrations'
import type { RegistrationStatusResponse } from '../api/registrations'
import { ApiError } from '../api/client'

interface StatusPageProps {
  onOpenMatchProposal?: (matchId: string) => void
  onReportConcern?: () => void
}

export default function StatusPage({ onOpenMatchProposal, onReportConcern }: StatusPageProps) {
  const [status, setStatus] = useState<RegistrationStatusResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [withdrawing, setWithdrawing] = useState(false)
  const [confirmingWithdraw, setConfirmingWithdraw] = useState(false)
  const [withdrawn, setWithdrawn] = useState(false)

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

  const handleWithdrawConfirmed = async () => {
    setWithdrawing(true)
    try {
      await withdrawMyRegistration()
      setWithdrawn(true)
    } catch (err) {
      console.error('Withdraw failed:', err)
    } finally {
      setWithdrawing(false)
      setConfirmingWithdraw(false)
    }
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
        <p className="text-body leading-relaxed">
          No further action will be taken on it. If the family wishes to register again
          in the future, they're welcome to.
        </p>
      </>
    )
  }

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
        <h2 className="text-body font-semibold mb-4">Proposed match</h2>
        {status.match ? (
          <MatchPreview
            match={status.match}
            onOpen={() => onOpenMatchProposal?.(String(status.match!.id))}
          />
        ) : (
          <p className="text-body text-text/70 leading-relaxed">
            No match has been proposed yet. We'll reach out directly when there's someone
            to share.
          </p>
        )}
      </div>

      <div className="border-t border-t-border py-8">
        {!confirmingWithdraw && (
          <button
            type="button"
            className="border border-primary text-primary px-5 py-2 text-sm"
            onClick={() => setConfirmingWithdraw(true)}
          >
            Withdraw registration
          </button>
        )}
        {confirmingWithdraw && (
          <div className="border border-border px-5 py-4">
            <p className="text-body mb-4">
              This will withdraw the registration. It can be done at any time, for any reason.
            </p>
            <div className="flex gap-3">
              <button
                type="button"
                className="border border-border text-text/70 px-5 py-2 text-sm"
                onClick={() => setConfirmingWithdraw(false)}
                disabled={withdrawing}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-primary text-sm"
                onClick={handleWithdrawConfirmed}
                disabled={withdrawing}
              >
                {withdrawing ? 'Withdrawing…' : 'Yes, withdraw'}
              </button>
            </div>
          </div>
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
  onOpen,
}: {
  match: NonNullable<RegistrationStatusResponse['match']>
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
      <div className="flex items-center justify-between">
        <span className="text-body text-text/70 text-sm">{stateText[match.state]}</span>
        <button type="button" className="btn-primary text-sm" onClick={onOpen}>
          View &amp; respond
        </button>
      </div>
    </div>
  )
}
