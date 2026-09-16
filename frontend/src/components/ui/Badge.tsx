import type { ReactNode } from 'react'
import clsx from 'clsx'

type BadgeTone = 'neutral' | 'success' | 'warning' | 'danger' | 'brass' | 'teal'

const tones: Record<BadgeTone, string> = {
  neutral: 'bg-ink-100 text-ink-700',
  success: 'bg-success-100 text-success',
  warning: 'bg-warning-100 text-warning',
  danger: 'bg-danger-100 text-danger',
  brass: 'bg-brass-100 text-brass-700',
  teal: 'bg-teal-100 text-teal-700',
}

export function Badge({ tone = 'neutral', children }: { tone?: BadgeTone; children: ReactNode }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium',
        tones[tone],
      )}
    >
      {children}
    </span>
  )
}
