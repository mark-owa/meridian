import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { apiErrorMessage } from '../lib/api'
import { Button } from '../components/ui/Button'
import { MeridianMark } from '../components/MeridianMark'

export function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ full_name: '', email: '', company: '', password: '' })
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  function update<K extends keyof typeof form>(key: K, value: string) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)
    try {
      await register(form)
      navigate('/')
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="chart-grid flex min-h-screen items-center justify-center px-4 py-10">
      <div className="w-full max-w-sm rounded-xl border border-ink-100 bg-paper-raised p-8 shadow-sm">
        <div className="mb-8 flex flex-col items-center gap-3">
          <MeridianMark className="size-9" />
          <div className="text-center">
            <h1 className="font-display text-2xl font-medium text-ink-900">Create your workspace</h1>
            <p className="mt-1 text-sm text-ink-500">Start with knowledge, documents, and leads in one place</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="full_name" className="mb-1.5 block text-sm font-medium text-ink-700">
              Full name
            </label>
            <input
              id="full_name"
              required
              value={form.full_name}
              onChange={(e) => update('full_name', e.target.value)}
              className="w-full rounded-md border border-ink-200 px-3 py-2 text-sm focus:border-brass-500 focus:outline-none focus:ring-1 focus:ring-brass-500"
              placeholder="Jordan Rivera"
            />
          </div>

          <div>
            <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-ink-700">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={form.email}
              onChange={(e) => update('email', e.target.value)}
              className="w-full rounded-md border border-ink-200 px-3 py-2 text-sm focus:border-brass-500 focus:outline-none focus:ring-1 focus:ring-brass-500"
              placeholder="you@company.com"
            />
          </div>

          <div>
            <label htmlFor="company" className="mb-1.5 block text-sm font-medium text-ink-700">
              Company <span className="text-ink-400">(optional)</span>
            </label>
            <input
              id="company"
              value={form.company}
              onChange={(e) => update('company', e.target.value)}
              className="w-full rounded-md border border-ink-200 px-3 py-2 text-sm focus:border-brass-500 focus:outline-none focus:ring-1 focus:ring-brass-500"
              placeholder="Acme Co"
            />
          </div>

          <div>
            <label htmlFor="password" className="mb-1.5 block text-sm font-medium text-ink-700">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              autoComplete="new-password"
              value={form.password}
              onChange={(e) => update('password', e.target.value)}
              className="w-full rounded-md border border-ink-200 px-3 py-2 text-sm focus:border-brass-500 focus:outline-none focus:ring-1 focus:ring-brass-500"
              placeholder="At least 8 characters, with a letter and a number"
            />
          </div>

          {error && (
            <p className="rounded-md bg-danger-100 px-3 py-2 text-sm text-danger">{error}</p>
          )}

          <Button type="submit" isLoading={isSubmitting} className="w-full">
            Create account
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-ink-500">
          Already have an account?{' '}
          <Link to="/login" className="font-medium text-brass-600 hover:text-brass-700">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
