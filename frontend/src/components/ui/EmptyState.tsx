import type { ReactNode } from 'react'

export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: ReactNode
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="chart-grid flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-ink-200 px-6 py-16 text-center">
      {icon && <div className="text-ink-300">{icon}</div>}
      <div>
        <p className="font-medium text-ink-800">{title}</p>
        {description && <p className="mt-1 text-sm text-ink-500 max-w-sm">{description}</p>}
      </div>
      {action}
    </div>
  )
}
