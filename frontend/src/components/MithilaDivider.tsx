export function MithilaDivider({ className = "" }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={`flex items-center justify-center gap-3 py-6 opacity-60 ${className}`}>
      <span className="h-px w-16 bg-gradient-to-r from-transparent to-border" />
      {/* Subtle traditional lotus petal motif */}
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-secondary/80">
        <path d="M12 3c-1.5 3-4.5 6-4.5 9a4.5 4.5 0 0 0 9 0c0-3-3-6-4.5-9z" />
        <path d="M7.5 12c-2.5.5-4.5 2-4.5 4a3 3 0 0 0 6 0c0-1.2-.5-2.8-1.5-4z" />
        <path d="M16.5 12c2.5.5 4.5 2 4.5 4a3 3 0 0 1-6 0c0-1.2.5-2.8 1.5-4z" />
      </svg>
      <span className="h-px w-16 bg-gradient-to-l from-transparent to-border" />
    </div>
  );
}
