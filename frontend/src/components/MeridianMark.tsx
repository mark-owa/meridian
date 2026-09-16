export function MeridianMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="16" cy="16" r="13.5" stroke="currentColor" strokeWidth="2" className="text-brass-500" />
      <line x1="16" y1="2.5" x2="16" y2="29.5" stroke="currentColor" strokeWidth="2" className="text-brass-500" />
      <line x1="9" y1="4.2" x2="9" y2="27.8" stroke="currentColor" strokeWidth="1" opacity="0.55" className="text-brass-500" />
      <line x1="23" y1="4.2" x2="23" y2="27.8" stroke="currentColor" strokeWidth="1" opacity="0.55" className="text-brass-500" />
      <circle cx="16" cy="16" r="2.1" fill="currentColor" className="text-brass-500" />
    </svg>
  )
}
