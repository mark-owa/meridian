import type { ReactNode } from 'react'
import { Card } from './Card'

export function StatCard({
  label,
  value,
  suffix,
  icon,
}: {
  label: string
  value: string | number
  suffix?: string
  icon?: ReactNode
}) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between">
        <p className="text-sm text-ink-500">{label}</p>
        {icon && <div className="text-brass-500">{icon}</div>}
      </div>
      <p className="tabular mt-2 font-display text-3xl font-medium text-ink-900">
        {value}
        {suffix && <span className="ml-1 text-lg text-ink-400">{suffix}</span>}
      </p>
    </Card>
  )
}
