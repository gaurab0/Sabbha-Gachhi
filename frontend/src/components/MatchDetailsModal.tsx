import { useCallback, useEffect, useRef, useState } from 'react'
import Modal from './Modal'
import { resolveMediaUrl } from '../api/client'
import { fetchMatchContact, respondToMatchProposal } from '../api/registration'
import type { MatchContactResponse, MatchProposalResponse } from '../api/registration'

interface MatchDetailsModalProps {
  matchId: string
  /** Summary already on the status card (shared facts, state, panjikar line). */
  summary: MatchProposalResponse
  onClose: () => void
  /** Lets the status card refresh its label/state after a response. */
  onResponded: (updated: MatchProposalResponse) => void
}

const STATE_LABEL: Record<string, string> = {
  waiting_you: 'Waiting on your response',
  waiting_other: 'Waiting on the other family',
  both_accepted: 'Both families have accepted',
  declined: 'This proposal was declined',
}

async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    // Fallback for older browsers / non-secure contexts.
    try {
      const area = document.createElement('textarea')
      area.value = text
      area.style.position = 'fixed'
      area.style.opacity = '0'
      document.body.appendChild(area)
      area.select()
      const ok = document.execCommand('copy')
      document.body.removeChild(area)
      return ok
    } catch {
      return false
    }
  }
}

export default function MatchDetailsModal({
  matchId,
  summary,
  onClose,
  onResponded,
}: MatchDetailsModalProps) {
  const [proposal, setProposal] = useState<MatchProposalResponse>(summary)
  const [contact, setContact] = useState<MatchContactResponse | null>(null)
  const [contactLoading, setContactLoading] = useState(true)
  const [contactError, setContactError] = useState(false)
  const [working, setWorking] = useState(false)
  const [confirmingDecline, setConfirmingDecline] = useState(false)
  const [photoFailed, setPhotoFailed] = useState(false)
  const [imgLoaded, setImgLoaded] = useState(false)
  const [enlarged, setEnlarged] = useState(false)
  const [copiedField, setCopiedField] = useState<'email' | 'phone' | null>(null)
  const copyTimer = useRef<number | null>(null)

  // A fresh contact payload means a possibly-new photo: re-attempt loading it.
  const applyContact = useCallback((data: MatchContactResponse) => {
    setPhotoFailed(false)
    setImgLoaded(false)
    setContact(data)
  }, [])

  const loadContact = useCallback(() => {
    setContactLoading(true)
    setContactError(false)
    // Contact details live in component state only: fetched on demand,
    // never cached in localStorage, never logged.
    fetchMatchContact(matchId)
      .then(applyContact)
      .catch(() => setContactError(true))
      .finally(() => setContactLoading(false))
  }, [matchId, applyContact])

  useEffect(() => {
    // The /contact/ endpoint succeeds for any verified user — it returns the
    // candidate photo immediately, and email/phone once both families accept.
    // The `cancelled` flag handles React StrictMode's double-mount correctly:
    // the first fetch is cancelled on unmount, then the remount fires a fresh
    // one that resolves normally. Do NOT add a ref-guard here — it prevents
    // the remount fetch from running, leaving contactLoading stuck at true.
    let cancelled = false
    fetchMatchContact(matchId)
      .then((data) => {
        if (!cancelled) applyContact(data)
      })
      .catch(() => {
        if (!cancelled) setContactError(true)
      })
      .finally(() => {
        if (!cancelled) setContactLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [matchId, applyContact])

  useEffect(() => {
    const timer = copyTimer.current
    return () => {
      if (timer !== null) window.clearTimeout(timer)
    }
  }, [])

  const handleCopy = async (field: 'email' | 'phone', value: string) => {
    const ok = await copyText(value)
    if (!ok) return
    setCopiedField(field)
    if (copyTimer.current !== null) window.clearTimeout(copyTimer.current)
    copyTimer.current = window.setTimeout(() => setCopiedField(null), 1600)
  }

  const [respondError, setRespondError] = useState(false)
  const doRespond = async (action: 'accept' | 'decline') => {
    setRespondError(false)
    const before = proposal
    setWorking(true)
    try {
      const updated = await respondToMatchProposal(matchId, action)
      setProposal(updated)
      onResponded(updated)
      setConfirmingDecline(false)
      void loadContact()
    } catch {
      setProposal(before)
      setRespondError(true)
    } finally {
      setWorking(false)
    }
  }

  const showPhoto = Boolean(contact && contact.photo_url && !photoFailed)
  const photoSrc = resolveMediaUrl(contact?.photo_url)

  return (
    <Modal labelledBy="match-details-title" onClose={onClose}>
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <p className="text-caption text-text/60 tracking-wider mb-1">Proposed match</p>
          <h2 id="match-details-title" className="text-heading text-primary">
            {summary.shared_by_panjikar ? `Shared by ${summary.shared_by_panjikar}` : 'Shared by your panjikar'}
          </h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close details"
          className="border border-border text-text/70 px-3 py-1 text-sm shrink-0"
        >
          ✕
        </button>
      </div>

      {/* Photo: skeleton while loading, avatar fallback, enlarge on click. */}
      <div className="flex justify-center mb-6">
        {contactLoading ? (
          <div
            className="w-36 h-44 rounded-lg bg-border/60 animate-pulse"
            role="status"
            aria-label="Loading photo"
          />
        ) : showPhoto ? (
          <button
            type="button"
            onClick={() => setEnlarged(true)}
            className="relative p-0 border-0 bg-transparent cursor-zoom-in"
            aria-label="Enlarge candidate photo"
          >
            {!imgLoaded && (
              <span
                className="absolute inset-0 rounded-lg bg-border/60 animate-pulse"
                role="status"
                aria-label="Loading photo"
              />
            )}
            <img
              src={photoSrc}
              alt="Photo of proposed match"
              loading="lazy"
              onLoad={() => setImgLoaded(true)}
              onError={() => setPhotoFailed(true)}
              className={`w-36 h-44 object-cover rounded-lg border border-border transition-opacity duration-200 ${imgLoaded ? 'opacity-100' : 'opacity-0'}`}
            />
          </button>
        ) : (
          <div
            className="w-36 h-44 rounded-lg border border-border bg-bg flex flex-col items-center justify-center gap-2 text-text/40"
            role="img"
            aria-label="No photo provided — placeholder avatar"
          >
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
              <circle cx="12" cy="8" r="4" />
              <path d="M4 21c0-4 3.5-6.5 8-6.5s8 2.5 8 6.5" />
            </svg>
            <span className="text-caption">No photo</span>
          </div>
        )}
      </div>

      {enlarged && showPhoto && (
        <div
          className="fixed inset-0 z-[60] bg-text/60 flex items-center justify-center p-4"
          role="presentation"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setEnlarged(false)
          }}
        >
          <div className="relative bg-bg border border-border p-3 max-w-full">
            <img
              src={photoSrc}
              alt="Photo of proposed match, enlarged"
              className="max-h-[75vh] max-w-[85vw] object-contain"
            />
            <button
              type="button"
              onClick={() => setEnlarged(false)}
              aria-label="Close enlarged photo"
              className="absolute -top-3 -right-3 bg-primary text-bg rounded-full w-8 h-8 text-sm"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      <ul className="text-body leading-relaxed list-disc pl-5 mb-6">
        {proposal.shared_details.map((line, i) => (
          <li key={i}>{line}</li>
        ))}
      </ul>


      {/* Contact: photo is available immediately; email/phone unlock once both families accept. */}
      <div className="border border-border px-5 py-4 mb-4">
        <p className="text-caption text-text/60 tracking-wider mb-3">Contact details</p>
        {contactLoading ? (
          <div className="space-y-3" role="status" aria-label="Loading contact details">
            <div className="h-4 bg-border/60 rounded animate-pulse" />
            <div className="h-4 bg-border/60 rounded animate-pulse" />
          </div>
        ) : contactError && !contact ? (
          <div>
            <p className="text-body text-text/70 mb-3">
              Couldn't load contact details. Check your connection and try again.
            </p>
            <button type="button" className="btn-outline text-sm" onClick={() => void loadContact()}>
              Retry
            </button>
          </div>
        ) : (
          <>
            <ContactRow
              label="Email"
              value={contact?.email ?? ''}
              hrefPrefix="mailto:"
              copied={copiedField === 'email'}
              onCopy={() => contact?.email && void handleCopy('email', contact.email)}
            />
            <ContactRow
              label="Phone"
              value={contact?.phone ?? ''}
              hrefPrefix="tel:"
              copied={copiedField === 'phone'}
              onCopy={() => contact?.phone && void handleCopy('phone', contact.phone)}
            />
            {proposal.state !== 'both_accepted' && (
              <p className="text-caption text-text/60 mt-3">
                {proposal.state === 'waiting_you'
                  ? 'Full contact details will be shared once both families accept.'
                  : proposal.state === 'waiting_other'
                  ? 'Full contact details will be shared once the other family responds.'
                  : null}
              </p>
            )}
            {proposal.state === 'both_accepted' && (
              <p className="text-caption text-text/60 mt-3">
                Please keep these details private and use them respectfully.
              </p>
            )}
          </>
        )}
      </div>

      <div className="flex items-center justify-between mb-4">
        <span className="text-body text-text/70 text-sm">
          {STATE_LABEL[proposal.state] ?? proposal.state}
        </span>
      </div>

      {respondError && (
        <p className="text-body text-sm mb-4" role="alert">
          That didn't go through. Check your connection and try again.
        </p>
      )}

      {proposal.state === 'waiting_you' && !confirmingDecline && (
        <div className="flex gap-3 justify-end">
          <button
            type="button"
            className="btn-outline text-sm"
            onClick={() => setConfirmingDecline(true)}
            disabled={working}
          >
            Decline
          </button>
          <button
            type="button"
            className="btn-primary text-sm"
            onClick={() => void doRespond('accept')}
            disabled={working}
          >
            {working ? 'Recording…' : 'Accept'}
          </button>
        </div>
      )}

      {proposal.state === 'waiting_you' && confirmingDecline && (
        <div className="border border-border px-5 py-4">
          <p className="text-body mb-4">
            This will decline the proposal. The other family will only be told
            that it did not move forward — nothing more.
          </p>
          <div className="flex gap-3 justify-end">
            <button
              type="button"
              className="border border-border text-text/70 px-5 py-2 text-sm"
              onClick={() => setConfirmingDecline(false)}
              disabled={working}
            >
              Go back
            </button>
            <button
              type="button"
              className="btn-primary text-sm"
              onClick={() => void doRespond('decline')}
              disabled={working}
            >
              {working ? 'Recording…' : 'Yes, decline'}
            </button>
          </div>
        </div>
      )}
    </Modal>
  )
}

function ContactRow({
  label,
  value,
  hrefPrefix,
  copied,
  onCopy,
}: {
  label: string
  value: string
  hrefPrefix: 'mailto:' | 'tel:'
  copied: boolean
  onCopy: () => void
}) {
  if (!value) {
    return (
      <div className="flex items-center justify-between py-2 border-b border-border last:border-b-0">
        <span className="text-body text-text/60">{label}</span>
        <span className="text-body text-text/60 text-sm">Not provided</span>
      </div>
    )
  }
  return (
    <div className="flex items-center justify-between gap-3 py-2 border-b border-border last:border-b-0">
      <span className="text-body text-text/60 shrink-0">{label}</span>
      <span className="flex items-center gap-2 min-w-0">
        <a
          href={`${hrefPrefix}${value}`}
          className="text-body text-sm break-all"
        >
          {value}
        </a>
        <button
          type="button"
          onClick={onCopy}
          aria-label={`Copy ${label.toLowerCase()}`}
          className="border border-border text-text/70 px-2 py-1 text-xs shrink-0"
        >
          {copied ? 'Copied' : 'Copy'}
        </button>
      </span>
    </div>
  )
}
