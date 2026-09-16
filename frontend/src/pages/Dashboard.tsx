import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { FileText, MessageSquareText, Sparkles, Target } from 'lucide-react'
import { apiErrorMessage, getDashboardStats } from '../lib/api'
import type { DashboardStats } from '../lib/types'
import { StatCard } from '../components/ui/StatCard'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { PageSpinner } from '../components/ui/Spinner'

export function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)

  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getDashboardStats().then(setStats).catch((err) => setError(apiErrorMessage(err)))
  }, [])

  if (error) return <p role="alert" className="rounded-md bg-danger-100 p-4 text-sm text-danger">{error}</p>
  if (!stats) return <PageSpinner />

  const pipelineData = [
    { name: 'Documents', total: stats.total_documents, complete: stats.documents_ready },
    { name: 'Leads', total: stats.total_leads, complete: stats.qualified_leads },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-medium text-ink-900">Overview</h1>
        <p className="mt-1 text-sm text-ink-500">
          Your knowledge base, document processing, and lead pipeline at a glance.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Documents ready"
          value={`${stats.documents_ready}/${stats.total_documents}`}
          icon={<FileText className="size-4" />}
        />
        <StatCard
          label="Knowledge queries"
          value={stats.total_queries}
          icon={<MessageSquareText className="size-4" />}
        />
        <StatCard
          label="Qualified leads"
          value={`${stats.qualified_leads}/${stats.total_leads}`}
          icon={<Target className="size-4" />}
        />
        <StatCard
          label="Extractions run"
          value={stats.total_extractions}
          icon={<Sparkles className="size-4" />}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <h2 className="font-medium text-ink-800">Pipeline completion</h2>
          </CardHeader>
          <CardBody className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={pipelineData} barGap={6}>
                <CartesianGrid strokeDasharray="3 3" stroke="#ebedf1" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#5f6a82' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 12, fill: '#5f6a82' }} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ fontSize: 13, borderRadius: 8, border: '1px solid #ebedf1' }}
                  cursor={{ fill: '#f5f6f8' }}
                />
                <Bar dataKey="total" name="Total" fill="#d8dbe2" radius={[4, 4, 0, 0]} />
                <Bar dataKey="complete" name="Complete" fill="#b8873a" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <h2 className="font-medium text-ink-800">Response quality</h2>
          </CardHeader>
          <CardBody className="space-y-4">
            <div>
              <p className="text-xs text-ink-500">Avg. knowledge query response time</p>
              <p className="tabular font-display text-2xl text-ink-900">
                {stats.avg_response_time_ms != null ? `${Math.round(stats.avg_response_time_ms)}ms` : '—'}
              </p>
            </div>
            <div>
              <p className="text-xs text-ink-500">Avg. lead qualification score</p>
              <p className="tabular font-display text-2xl text-ink-900">
                {stats.avg_lead_score ?? '—'}
                {stats.avg_lead_score != null && <span className="text-base text-ink-400">/100</span>}
              </p>
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  )
}
