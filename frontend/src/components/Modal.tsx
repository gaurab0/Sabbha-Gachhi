import { useEffect, useRef } from 'react'

interface ModalProps {
  /** id of the element labelling the dialog (usually the title). */
  labelledBy: string
  onClose: () => void
  children: React.ReactNode
}

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), ' +
  'input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'

/**
 * Accessible modal shell shared by status-page dialogs: overlay + panel,
 * Esc/backdrop close, focus trap, focus restore, body scroll lock.
 * Follows the site's card/border visual language.
 */
export default function Modal({ labelledBy, onClose, children }: ModalProps) {
  const panelRef = useRef<HTMLDivElement>(null)
  const openerRef = useRef<Element | null>(null)

  useEffect(() => {
    openerRef.current = document.activeElement
    const panel = panelRef.current
    // Move focus inside on open (first control, else the panel itself).
    const first = panel?.querySelector<HTMLElement>(FOCUSABLE)
    ;(first ?? panel)?.focus()

    // Lock background scroll while open.
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        onClose()
        return
      }
      if (e.key !== 'Tab' || !panel) return
      const items = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (el) => el.offsetParent !== null
      )
      if (items.length === 0) {
        e.preventDefault()
        return
      }
      const firstItem = items[0]
      const lastItem = items[items.length - 1]
      if (e.shiftKey && document.activeElement === firstItem) {
        e.preventDefault()
        lastItem.focus()
      } else if (!e.shiftKey && document.activeElement === lastItem) {
        e.preventDefault()
        firstItem.focus()
      }
    }
    document.addEventListener('keydown', onKeyDown, true)

    return () => {
      document.removeEventListener('keydown', onKeyDown, true)
      document.body.style.overflow = prevOverflow
      // Return focus to whatever opened the dialog.
      const opener = openerRef.current as HTMLElement | null
      if (opener && typeof opener.focus === 'function') {
        opener.focus()
      }
    }
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="fixed inset-0 bg-text/40" aria-hidden="true" />
      <div className="relative min-h-full flex items-start sm:items-center justify-center p-4 sm:p-8">
        <div
          ref={panelRef}
          role="dialog"
          aria-modal="true"
          aria-labelledby={labelledBy}
          tabIndex={-1}
          className="relative w-full max-w-[560px] bg-bg border border-border px-5 py-6 sm:px-8 sm:py-8 outline-none"
          onMouseDown={(e) => e.stopPropagation()}
        >
          {children}
        </div>
      </div>
    </div>
  )
}
