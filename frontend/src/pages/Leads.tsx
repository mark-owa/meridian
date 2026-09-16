import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { ChevronDown, ChevronUp, Plus, Sparkles, Target, Trash2 } from 'lucide-react'
import {
  apiErrorMessage,
  createLead,
  deleteLead,
  listLeads,
  qualifyLead,
  updateLeadStatus,
} from '../lib/api'
import type { Lead, LeadListResponse, LeadStatus } from '../lib/types'
import { Button } from '../components/ui/Button'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { PageSpinner } from '../components/ui/Spinner'

const statusTone: Record<LeadStatus, 'neutral' | 'brass' | 'teal' | 'success' | 'danger'> = {
  new: 'neutral',
  qualified: 'brass',
  contacted: 'teal',
  converted: 'success',
  lost: 'danger',
}

const emptyForm = {
  company_name: '',
  contact_name: '',
  contact_email: '',
  industry: '',
  budget_range: '',
  pain_points: '',
}

export function Leads() {
  const [data, setData] = useState<LeadListResponse | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [formError, setFormError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [qualifyingId, setQualifyingId] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const [error, setError] = useState<string | null>(null)

  async function refresh() {
    try {
      setData(await listLeads(statusFilter ? { status: statusFilter } : undefined))
      setError(null)
    } catch (err) {
      setError(apiErrorMessage(err))
    }
  }

  useEffect(() => {
    refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter])

  async function handleAdd(e: FormEvent) {
    e.preventDefault()
    setFormError(null)
    setIsSaving(true)
    try {
      await createLead(form)
      setForm(emptyForm)
      setShowForm(false)
      await refresh()
    } catch (err) {
      setFormError(apiErrorMessage(err))
    } finally {
      setIsSaving(false)
    }
  }

  async function handleQualify(id: string) {
    setError(null)
    setQualifyingId(id)
    try {
      await qualifyLead(id)
      await refresh()
      setExpandedId(id)
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setQualifyingId(null)
    }
  }

  async function handleStatusChange(id: string, status: string) {
    setError(null)
    try {
      await updateLeadStatus(id, status)
      await refresh()
    } catch (err) {
      setError(apiErrorMessage(err))
    }
  }

  async function handleDelete(id: string) {
    setError(null)
    try {
      await deleteLead(id)
      await refresh()
    } catch (err) {
      setError(apiErrorMessage(err))
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-display text-2xl font-medium text-ink-900">Leads</h1>
          <p className="mt-1 text-sm text-ink-500">Score inbound leads and draft outreach with AI.</p>
        </div>
        <Button icon={<Plus className="size-3.5" />} onClick={() => setShowForm((s) => !s)}>
          Add lead
        </Button>
      </div>

      {error && <p role="alert" className="rounded-md bg-danger-100 px-3 py-2 text-sm text-danger">{error}</p>}

      {showForm && (
        <Card>
          <CardHeader>
            <h2 className="font-medium text-ink-800">New lead</h2>
          </CardHeader>
          <CardBody>
            <form onSubmit={handleAdd} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <input
                required
                placeholder="Company name"
                value={form.company_name}
                onChange={(e) => setForm((f) => ({ ...f, company_name: e.target.value }))}
                className="rounded-md border border-ink-200 px-3 py-2 text-sm focus:border-brass-500 focus:outline-none focus:ring-1 focus:ring-brass-500"
              />
              <input
                required
                placeholder="Contact name"
                value={form.contact_name}
                onChange={(e) => setForm((f) => ({ ...f, contact_name: e.target.value }))}
                className="rounded-md border border-ink-200 px-3 py-2 text-sm focus:border-brass-500 focus:outline-none focus:ring-1 focus:ring-brass-500"
              />
              <input
                required
                type="email"
                placeholder="Contact email"
                value={form.contact_email}
                onChange={(e) => setForm((f) => ({ ...f, contact_email: e.target.value }))}
                className="rounded-md border border-ink-200 px-3 py-2 text-sm focus:border-brass-500 focus:outline-none focus:ring-1 focus:ring-brass-500"
              />
              <input
                placeholder="Industry"
                value={form.industry}
                onChange={(e) => setForm((f) => ({ ...f, industry: e.target.value }))}
                className="rounded-md border border-ink-200 px-3 py-2 text-sm focus:border-brass-500 focus:outline-none focus:ring-1 focus:ring-brass-500"
              />
              <input
                placeholder="Budget range (e.g. $10k–$50k)"
                value={form.budget_range}
                onChange={(e) => setForm((f) => ({ ...f, budget_range: e.target.value }))}
                className="rounded-md border border-ink-200 px-3 py-2 text-sm focus:border-brass-500 focus:outline-none focus:ring-1 focus:ring-brass-500"
              />
              <input
                placeholder="Pain points"
                value={form.pain_points}
                onChange={(e) => setForm((f) => ({ ...f, pain_points: e.target.value }))}
                className="rounded-md border border-ink-200 px-3 py-2 text-sm focus:border-brass-500 focus:outline-none focus:ring-1 focus:ring-brass-500 sm:col-span-2"
              />
              {formError && (
                <p className="rounded-md bg-danger-100 px-3 py-2 text-sm text-danger sm:col-span-2">
                  {formError}
                </p>
              )}
              <div className="sm:col-span-2">
                <Button type="submit" isLoading={isSaving}>
                  Save lead
                </Button>
              </div>
            </form>
          </CardBody>
        </Card>
      )}

      <Card>
        <CardHeader className="flex items-center justify-between">
          <h2 className="font-medium text-ink-800">
            All leads {data && <span className="font-normal text-ink-400">({data.total})</span>}
          </h2>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-md border border-ink-200 px-2.5 py-1.5 text-xs focus:border-brass-500 focus:outline-none focus:ring-1 focus:ring-brass-500"
          >
            <option value="">All statuses</option>
            <option value="new">New</option>
            <option value="qualified">Qualified</option>
            <option value="contacted">Contacted</option>
            <option value="converted">Converted</option>
            <option value="lost">Lost</option>
          </select>
        </CardHeader>
        <CardBody>
          {!data ? (
            error ? null : <PageSpinner />
          ) : data.leads.length === 0 ? (
            <EmptyState
              icon={<Target className="size-8" />}
              title="No leads yet"
              description="Add a lead to start scoring fit and drafting outreach."
            />
          ) : (
            <ul className="divide-y divide-ink-100">
              {data.leads.map((lead) => (
                <LeadRow
                  key={lead.id}
                  lead={lead}
                  isExpanded={expandedId === lead.id}
                  isQualifying={qualifyingId === lead.id}
                  onToggle={() => setExpandedId((id) => (id === lead.id ? null : lead.id))}
                  onQualify={() => handleQualify(lead.id)}
                  onStatusChange={(status) => handleStatusChange(lead.id, status)}
                  onDelete={() => handleDelete(lead.id)}
                />
              ))}
            </ul>
          )}
        </CardBody>
      </Card>
    </div>
  )
}

function LeadRow({
  lead,
  isExpanded,
  isQualifying,
  onToggle,
  onQualify,
  onStatusChange,
  onDelete,
}: {
  lead: Lead
  isExpanded: boolean
  isQualifying: boolean
  onToggle: () => void
  onQualify: () => void
  onStatusChange: (status: string) => void
  onDelete: () => void
}) {
  return (
    <li className="py-3">
      <div className="flex items-center justify-between gap-3">
        <button onClick={onToggle} className="flex min-w-0 flex-1 items-center gap-3 text-left">
          {isExpanded ? (
            <ChevronUp className="size-4 shrink-0 text-ink-300" />
          ) : (
            <ChevronDown className="size-4 shrink-0 text-ink-300" />
          )}
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-ink-800">{lead.company_name}</p>
            <p className="truncate text-xs text-ink-400">
              {lead.contact_name} · {lead.contact_email}
            </p>
          </div>
        </button>

        <div className="flex shrink-0 items-center gap-2">
          {lead.qualification_score != null && (
            <span className="tabular text-sm font-medium text-ink-700">
              {lead.qualification_score}
              <span className="text-ink-400">/100</span>
            </span>
          )}
          <select
            value={lead.status}
            onChange={(e) => onStatusChange(e.target.value)}
            className={`rounded-full border-0 px-2.5 py-0.5 text-xs font-medium focus:outline-none focus:ring-1 focus:ring-brass-500 ${
              { neutral: 'bg-ink-100 text-ink-700', brass: 'bg-brass-100 text-brass-700', teal: 'bg-teal-100 text-teal-700', success: 'bg-success-100 text-success', danger: 'bg-danger-100 text-danger' }[
                statusTone[lead.status]
              ]
            }`}
          >
            <option value="new">New</option>
            <option value="qualified">Qualified</option>
            <option value="contacted">Contacted</option>
            <option value="converted">Converted</option>
            <option value="lost">Lost</option>
          </select>
          {lead.status === 'new' && (
            <Button size="sm" variant="secondary" isLoading={isQualifying} onClick={onQualify} icon={<Sparkles className="size-3.5" />}>
              Qualify
            </Button>
          )}
          <button onClick={onDelete} aria-label="Delete lead" className="rounded p-1.5 text-ink-300 hover:bg-ink-50 hover:text-danger">
            <Trash2 className="size-3.5" />
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="ml-7 mt-3 space-y-3 rounded-lg border border-ink-100 bg-paper p-4 text-sm">
          {lead.qualification_reason ? (
            <>
              <p className="text-ink-700">{lead.qualification_reason}</p>
              <div className="grid grid-cols-2 gap-4">
                {lead.strengths && lead.strengths.length > 0 && (
                  <div>
                    <p className="mb-1 text-xs font-medium uppercase tracking-wide text-success">Strengths</p>
                    <ul className="list-inside list-disc space-y-0.5 text-ink-600">
                      {lead.strengths.map((s, i) => <li key={i}>{s}</li>)}
                    </ul>
                  </div>
                )}
                {lead.concerns && lead.concerns.length > 0 && (
                  <div>
                    <p className="mb-1 text-xs font-medium uppercase tracking-wide text-danger">Concerns</p>
                    <ul className="list-inside list-disc space-y-0.5 text-ink-600">
                      {lead.concerns.map((c, i) => <li key={i}>{c}</li>)}
                    </ul>
                  </div>
                )}
              </div>
              {lead.drafted_email && (
                <div className="border-t border-ink-100 pt-3">
                  <p className="mb-1 text-xs font-medium uppercase tracking-wide text-ink-400">Drafted email</p>
                  <p className="mb-1 font-medium text-ink-800">{lead.email_subject}</p>
                  <p className="whitespace-pre-line text-ink-600">{lead.drafted_email}</p>
                </div>
              )}
            </>
          ) : (
            <p className="text-ink-400">Not qualified yet. Click "Qualify" to score this lead with AI.</p>
          )}
          {(lead.industry || lead.budget_range || lead.pain_points) && (
            <div className="flex flex-wrap gap-x-6 gap-y-1 border-t border-ink-100 pt-3 text-xs text-ink-500">
              {lead.industry && <span>Industry: {lead.industry}</span>}
              {lead.budget_range && <span>Budget: {lead.budget_range}</span>}
              {lead.pain_points && <span>Pain points: {lead.pain_points}</span>}
            </div>
          )}
        </div>
      )}
    </li>
  )
}
