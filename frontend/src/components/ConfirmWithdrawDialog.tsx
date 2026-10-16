import { useState } from 'react'
import Modal from './Modal'
import { WITHDRAW_REASONS } from '../api/registration'
import type { WithdrawReason } from '../api/registration'

interface ConfirmWithdrawDialogProps {
  matchState: string | null
  withdrawing: boolean
  error: string | null
  onCancel: () => void
  onConfirm: (reason: string) => void
}

export default function ConfirmWithdrawDialog({
  matchState,
  withdrawing,
  error,
  onCancel,
  onConfirm,
}: ConfirmWithdrawDialogProps) {
  const [reason, setReason] = useState<WithdrawReason>(WITHDRAW_REASONS[0])
  const [otherReason, setOtherReason] = useState('')

  const effectiveReason =
    reason === 'Other' ? otherReason.trim() : reason

  return (
    <Modal labelledBy="withdraw-dialog-title" onClose={onCancel}>
      <h2 id="withdraw-dialog-title" className="text-heading text-primary mb-4">
        Withdraw this registration?
      </h2>
      <div className="text-body leading-relaxed mb-4">
        <p className="mb-3">
          Withdrawing means the registration will be marked withdrawn, any
          pending proposed match will be cancelled, and the profile will no
          longer be shown to anyone.
        </p>
        {matchState === 'both_accepted' && (
          <p className="mb-3 border border-primary/40 px-4 py-3 text-sm" role="note">
            Heads up: both families have already accepted the current match.
            Withdrawing now will cancel that accepted match as well.
          </p>
        )}
      </div>

      <div className="field">
        <label className="label" htmlFor="withdraw-reason">
          Reason for withdrawing (optional)
        </label>
        <select
          id="withdraw-reason"
          className="select"
          value={reason}
          onChange={(e) => setReason(e.target.value as WithdrawReason)}
          disabled={withdrawing}
        >
          {WITHDRAW_REASONS.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </div>

      {reason === 'Other' && (
        <div className="field">
          <label className="label" htmlFor="withdraw-reason-other">
            Please say a little more (optional)
          </label>
          <textarea
            id="withdraw-reason-other"
            className="textarea"
            value={otherReason}
            onChange={(e) => setOtherReason(e.target.value)}
            disabled={withdrawing}
            rows={3}
          />
        </div>
      )}

      {error && (
        <p className="text-body text-sm mb-4" role="alert">
          {error}
        </p>
      )}

      <div className="flex gap-3 justify-end">
        <button
          type="button"
          className="border border-border text-text/70 px-5 py-2 text-sm"
          onClick={onCancel}
          disabled={withdrawing}
        >
          Keep registration
        </button>
        <button
          type="button"
          className="btn-primary text-sm"
          onClick={() => onConfirm(effectiveReason)}
          disabled={withdrawing}
        >
          {withdrawing ? 'Withdrawing…' : 'Yes, withdraw'}
        </button>
      </div>
    </Modal>
  )
}
