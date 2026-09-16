function humanizeKey(key: string) {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function formatValue(value: unknown): string {
  if (value == null || value === '') return '—'
  if (typeof value === 'number') return value.toLocaleString()
  return String(value)
}

/** Renders the JSON extracted from a document (invoice, contract, or
 * receipt — the field set differs per type) without needing a bespoke
 * component per document type. Arrays of objects (line items, parties)
 * become mini tables; arrays of strings (risks, obligations) become lists;
 * everything else is a label/value pair. */
export function ExtractedDataView({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data).filter(([key]) => key !== 'confidence_score')

  const scalarEntries = entries.filter(([, v]) => !Array.isArray(v))
  const arrayEntries = entries.filter(
    ([, v]) => Array.isArray(v) && v.length > 0,
  ) as [string, unknown[]][]

  return (
    <div className="space-y-5">
      <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3">
        {scalarEntries.map(([key, value]) => (
          <div key={key}>
            <dt className="text-xs text-ink-400">{humanizeKey(key)}</dt>
            <dd className="tabular text-sm font-medium text-ink-800">{formatValue(value)}</dd>
          </div>
        ))}
      </dl>

      {arrayEntries.map(([key, items]) => {
        const isObjectArray = typeof items[0] === 'object' && items[0] !== null
        return (
          <div key={key}>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-ink-400">
              {humanizeKey(key)}
            </p>
            {isObjectArray ? (
              <div className="overflow-x-auto rounded-md border border-ink-100">
                <table className="w-full text-sm">
                  <thead className="bg-ink-50 text-xs text-ink-500">
                    <tr>
                      {Object.keys(items[0] as object).map((col) => (
                        <th key={col} className="px-3 py-1.5 text-left font-medium">
                          {humanizeKey(col)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-ink-100">
                    {items.map((item, i) => (
                      <tr key={i}>
                        {Object.values(item as Record<string, unknown>).map((v, j) => (
                          <td key={j} className="tabular px-3 py-1.5 text-ink-700">
                            {formatValue(v)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <ul className="list-inside list-disc space-y-1 text-sm text-ink-700">
                {items.map((item, i) => (
                  <li key={i}>{String(item)}</li>
                ))}
              </ul>
            )}
          </div>
        )
      })}
    </div>
  )
}
