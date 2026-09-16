import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { BookOpen, FileText, Loader2, Search, Upload, X } from 'lucide-react'
import {
  apiErrorMessage,
  deleteDocument,
  listDocuments,
  queryKnowledgeBase,
  uploadDocument,
} from '../lib/api'
import type { Document, KnowledgeQueryResponse } from '../lib/types'
import { Button } from '../components/ui/Button'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { EmptyState } from '../components/ui/EmptyState'
import { Spinner } from '../components/ui/Spinner'

const statusTone = {
  pending: 'neutral',
  processing: 'warning',
  ready: 'success',
  failed: 'danger',
} as const

export function KnowledgeBase() {
  const [documents, setDocuments] = useState<Document[] | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [question, setQuestion] = useState('')
  const [isAsking, setIsAsking] = useState(false)
  const [askError, setAskError] = useState<string | null>(null)
  const [answer, setAnswer] = useState<KnowledgeQueryResponse | null>(null)

  const refreshDocuments = useCallback(async () => {
    try {
      const res = await listDocuments()
      setDocuments(res.documents)
      setUploadError(null)
    } catch (err) {
      setUploadError(apiErrorMessage(err))
    }
  }, [])

  useEffect(() => {
    refreshDocuments()
  }, [refreshDocuments])

  // Poll while any document is still being processed in the background.
  useEffect(() => {
    const hasInFlight = documents?.some((d) => d.status === 'pending' || d.status === 'processing')
    if (!hasInFlight) return
    const id = setInterval(refreshDocuments, 2500)
    return () => clearInterval(id)
  }, [documents, refreshDocuments])

  async function handleUpload(file: File) {
    setUploadError(null)
    setIsUploading(true)
    try {
      await uploadDocument(file)
      await refreshDocuments()
    } catch (err) {
      setUploadError(apiErrorMessage(err))
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  async function handleDelete(id: string) {
    setUploadError(null)
    try {
      await deleteDocument(id)
      setDocuments((docs) => docs?.filter((d) => d.id !== id) ?? null)
    } catch (err) {
      setUploadError(apiErrorMessage(err))
    }
  }

  async function handleAsk(e: FormEvent) {
    e.preventDefault()
    if (question.trim().length < 5) return
    setAskError(null)
    setIsAsking(true)
    setAnswer(null)
    try {
      setAnswer(await queryKnowledgeBase(question))
    } catch (err) {
      setAskError(apiErrorMessage(err))
    } finally {
      setIsAsking(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-medium text-ink-900">Knowledge Base</h1>
        <p className="mt-1 text-sm text-ink-500">
          Upload documents, then ask questions answered only from what you've uploaded.
        </p>
      </div>

      <Card>
        <CardHeader className="flex items-center justify-between">
          <h2 className="font-medium text-ink-800">Documents</h2>
          <div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.txt,.docx,.md"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
            />
            <Button
              size="sm"
              variant="secondary"
              icon={<Upload className="size-3.5" />}
              isLoading={isUploading}
              onClick={() => fileInputRef.current?.click()}
            >
              Upload document
            </Button>
          </div>
        </CardHeader>
        <CardBody>
          {uploadError && (
            <p className="mb-4 rounded-md bg-danger-100 px-3 py-2 text-sm text-danger">{uploadError}</p>
          )}

          {!documents ? (
            uploadError ? null : <Spinner className="size-5" />
          ) : documents.length === 0 ? (
            <EmptyState
              icon={<BookOpen className="size-8" />}
              title="No documents yet"
              description="Upload a PDF, DOCX, or text file to start building your knowledge base."
            />
          ) : (
            <ul className="divide-y divide-ink-100">
              {documents.map((doc) => (
                <li key={doc.id} className="flex items-center justify-between py-3">
                  <div className="flex min-w-0 items-center gap-3">
                    <FileText className="size-4 shrink-0 text-ink-400" />
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-ink-800">{doc.original_name}</p>
                      <p className="text-xs text-ink-400">
                        {(doc.file_size_bytes / 1024).toFixed(0)} KB
                        {doc.status === 'ready' && ` · ${doc.chunk_count} chunks indexed`}
                        {doc.status === 'failed' && doc.error_message && ` · ${doc.error_message}`}
                      </p>
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-3">
                    {(doc.status === 'pending' || doc.status === 'processing') && (
                      <Loader2 className="size-3.5 animate-spin text-ink-400" />
                    )}
                    <Badge tone={statusTone[doc.status]}>{doc.status}</Badge>
                    <button
                      onClick={() => handleDelete(doc.id)}
                      aria-label={`Delete ${doc.original_name}`}
                      className="rounded p-1 text-ink-300 hover:bg-ink-50 hover:text-danger"
                    >
                      <X className="size-3.5" />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="font-medium text-ink-800">Ask a question</h2>
        </CardHeader>
        <CardBody className="space-y-4">
          <form onSubmit={handleAsk} className="flex gap-2">
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="What is our refund policy?"
              className="flex-1 rounded-md border border-ink-200 px-3 py-2 text-sm focus:border-brass-500 focus:outline-none focus:ring-1 focus:ring-brass-500"
            />
            <Button type="submit" isLoading={isAsking} icon={<Search className="size-3.5" />}>
              Ask
            </Button>
          </form>

          {askError && <p className="rounded-md bg-danger-100 px-3 py-2 text-sm text-danger">{askError}</p>}

          {answer && (
            <div className="space-y-3 rounded-lg border border-ink-100 bg-paper p-4">
              <p className="text-sm leading-relaxed text-ink-800">{answer.answer}</p>
              {answer.sources.length > 0 && (
                <div className="space-y-2 border-t border-ink-100 pt-3">
                  <p className="text-xs font-medium uppercase tracking-wide text-ink-400">Sources</p>
                  {answer.sources.map((s, i) => (
                    <div key={i} className="rounded-md bg-paper-raised p-2.5 text-xs">
                      <div className="mb-1 flex items-center justify-between">
                        <span className="font-medium text-ink-700">{s.document_name}</span>
                        <span className="tabular text-ink-400">
                          {(s.similarity_score * 100).toFixed(0)}% match
                        </span>
                      </div>
                      <p className="text-ink-500">{s.chunk_text}</p>
                    </div>
                  ))}
                </div>
              )}
              <p className="tabular text-xs text-ink-400">
                {answer.response_time_ms}ms · {answer.tokens_used} tokens
              </p>
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  )
}
