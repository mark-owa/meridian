import { useEffect, useState } from 'react'
import { FileSearch, Sparkles } from 'lucide-react'
import { apiErrorMessage, listDocuments, runExtraction } from '../lib/api'
import type { Document, DocumentType, Extraction } from '../lib/types'
import { Button } from '../components/ui/Button'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { EmptyState } from '../components/ui/EmptyState'
import { ExtractedDataView } from '../components/ExtractedDataView'

const documentTypes: { value: DocumentType; label: string }[] = [
  { value: 'invoice', label: 'Invoice' },
  { value: 'contract', label: 'Contract' },
  { value: 'receipt', label: 'Receipt' },
]

export function DocumentIntelligence() {
  const [readyDocuments, setReadyDocuments] = useState<Document[] | null>(null)
  const [selectedDocId, setSelectedDocId] = useState('')
  const [documentType, setDocumentType] = useState<DocumentType>('invoice')
  const [isRunning, setIsRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<Extraction | null>(null)

  useEffect(() => {
    listDocuments().then((res) => {
      const ready = res.documents.filter((d) => d.status === 'ready')
      setReadyDocuments(ready)
      if (ready.length > 0) setSelectedDocId(ready[0].id)
    }).catch((err) => setError(apiErrorMessage(err)))
  }, [])

  async function handleRun() {
    if (!selectedDocId) return
    setError(null)
    setIsRunning(true)
    setResult(null)
    try {
      setResult(await runExtraction(selectedDocId, documentType))
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setIsRunning(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-medium text-ink-900">Document Intelligence</h1>
        <p className="mt-1 text-sm text-ink-500">
          Pull structured data out of invoices, contracts, and receipts.
        </p>
      </div>

      <Card>
        <CardHeader>
          <h2 className="font-medium text-ink-800">Run extraction</h2>
        </CardHeader>
        <CardBody>
          {readyDocuments === null ? null : readyDocuments.length === 0 ? (
            <EmptyState
              icon={<FileSearch className="size-8" />}
              title="No processed documents yet"
              description="Upload a document from the Knowledge Base page and wait for it to finish indexing before extracting data from it."
            />
          ) : (
            <div className="flex flex-wrap items-end gap-3">
              <div className="min-w-[220px] flex-1">
                <label className="mb-1.5 block text-sm font-medium text-ink-700">Document</label>
                <select
                  value={selectedDocId}
                  onChange={(e) => setSelectedDocId(e.target.value)}
                  className="w-full rounded-md border border-ink-200 px-3 py-2 text-sm focus:border-brass-500 focus:outline-none focus:ring-1 focus:ring-brass-500"
                >
                  {readyDocuments.map((doc) => (
                    <option key={doc.id} value={doc.id}>
                      {doc.original_name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium text-ink-700">Document type</label>
                <select
                  value={documentType}
                  onChange={(e) => setDocumentType(e.target.value as DocumentType)}
                  className="rounded-md border border-ink-200 px-3 py-2 text-sm focus:border-brass-500 focus:outline-none focus:ring-1 focus:ring-brass-500"
                >
                  {documentTypes.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>

              <Button onClick={handleRun} isLoading={isRunning} icon={<Sparkles className="size-3.5" />}>
                Extract data
              </Button>
            </div>
          )}

          {error && (
            <p className="mt-4 rounded-md bg-danger-100 px-3 py-2 text-sm text-danger">{error}</p>
          )}
        </CardBody>
      </Card>

      {result && (
        <Card>
          <CardHeader className="flex items-center justify-between">
            <h2 className="font-medium text-ink-800">Extraction result</h2>
            <div className="flex items-center gap-2">
              {result.confidence_score != null && (
                <Badge tone={result.confidence_score >= 0.8 ? 'success' : 'warning'}>
                  {(result.confidence_score * 100).toFixed(0)}% confidence
                </Badge>
              )}
              <Badge tone="brass">{result.document_type}</Badge>
            </div>
          </CardHeader>
          <CardBody>
            <ExtractedDataView data={result.extracted_data} />
          </CardBody>
        </Card>
      )}
    </div>
  )
}
