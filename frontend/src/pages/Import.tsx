import { useEffect, useRef, useState } from 'react'
import { api } from '../services/api'
import type { BatchImport } from '../types'
import { PageHeader } from '../components/ui/PageHeader'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import { ErrorAlert } from '../components/ui/ErrorAlert'
import { StatusBadge } from '../components/ui/Badge'

export default function Import() {
  const [batches, setBatches] = useState<BatchImport[]>([])
  const [generating, setGenerating] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [genCount, setGenCount] = useState(100)
  const [genSeed, setGenSeed] = useState(42)
  const [lastResult, setLastResult] = useState<unknown>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const loadBatches = () =>
    api.getBatches().then(setBatches).catch(() => null)

  useEffect(() => { loadBatches() }, [])

  const handleGenerate = async () => {
    setGenerating(true); setError(null); setSuccess(null)
    try {
      const result = await api.generateSynthetic(genCount, genSeed)
      const r = result as { imported_rows: number; batch_id: string }
      setLastResult(result)
      setSuccess(`Generated ${r.imported_rows} synthetic transactions. Batch ID: ${r.batch_id}`)
      await loadBatches()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Generation failed')
    } finally {
      setGenerating(false)
    }
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true); setError(null); setSuccess(null)
    try {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('merchant_id', 'merchant-demo-001')
      const result = await api.uploadCsv(fd)
      const r = result as { imported_rows: number; invalid_rows: number; duplicate_rows: number }
      setLastResult(result)
      setSuccess(`Imported ${r.imported_rows} rows. ${r.invalid_rows} invalid, ${r.duplicate_rows} duplicate.`)
      await loadBatches()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Upload failed')
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Import & Batches"
        subtitle="Upload CSV transactions or generate synthetic test data"
      />

      {error && <ErrorAlert message={error} />}
      {success && (
        <div className="rounded-lg bg-green-50 border border-green-200 px-4 py-3 text-sm text-green-800">
          ✓ {success}
        </div>
      )}

      {/* Two panels */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Generate synthetic */}
        <div className="card p-5 space-y-4">
          <div>
            <h3 className="font-semibold text-gray-800">Generate Synthetic Dataset</h3>
            <p className="text-sm text-gray-500 mt-1">
              Creates a labeled dataset with all required scenarios — retryable failures,
              fraud blocks, abandoned checkouts, overdue invoices, and more.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">Record count (10–500)</label>
              <input
                type="number" min={10} max={500} value={genCount}
                onChange={e => setGenCount(Number(e.target.value))}
                className="input"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">Random seed</label>
              <input
                type="number" value={genSeed}
                onChange={e => setGenSeed(Number(e.target.value))}
                className="input"
              />
            </div>
          </div>

          <button onClick={handleGenerate} disabled={generating} className="btn-primary w-full justify-center">
            {generating ? <><LoadingSpinner size="sm" /> Generating…</> : '🎲 Generate Dataset'}
          </button>

          <div className="text-xs text-gray-500 space-y-1">
            <p><strong>Included scenarios:</strong></p>
            <ul className="list-disc list-inside space-y-0.5 ml-2">
              <li>Retryable temp failures (recoverable)</li>
              <li>Fraud-blocked payments (non-retryable)</li>
              <li>Auth-required transactions</li>
              <li>Abandoned checkouts</li>
              <li>Failed subscriptions + cancelled subs</li>
              <li>Overdue + disputed invoices</li>
              <li>Opted-out customers</li>
              <li>Exhausted retry budgets</li>
              <li>Duplicate detection rows</li>
            </ul>
          </div>
        </div>

        {/* CSV Upload */}
        <div className="card p-5 space-y-4">
          <div>
            <h3 className="font-semibold text-gray-800">Upload CSV File</h3>
            <p className="text-sm text-gray-500 mt-1">
              Upload your own transaction CSV. Max {10}MB. Duplicate external IDs are detected and rejected.
            </p>
          </div>

          <div
            className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-brand-400 hover:bg-brand-50 transition-colors"
            onClick={() => fileRef.current?.click()}
          >
            <p className="text-3xl mb-2">📄</p>
            <p className="text-sm font-medium text-gray-700">Click to select CSV file</p>
            <p className="text-xs text-gray-400 mt-1">or drag and drop</p>
          </div>
          <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={handleUpload} />

          {uploading && (
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <LoadingSpinner size="sm" /> Uploading and validating…
            </div>
          )}

          {/* Template info */}
          <details className="text-xs text-gray-500">
            <summary className="cursor-pointer font-medium text-gray-700 hover:text-brand-600">
              Required CSV columns
            </summary>
            <div className="mt-2 space-y-1 bg-gray-50 rounded p-3 font-mono">
              <p className="text-green-700">✓ Required: external_id, customer_ref, amount, currency, transaction_type, status</p>
              <p className="text-gray-500">○ Optional: failure_reason, failure_category, retry_count, payment_method, gateway, description</p>
              <p className="mt-2 text-gray-600">transaction_type: payment | subscription | invoice | checkout</p>
              <p className="text-gray-600">status: pending | success | failed | abandoned | overdue | cancelled</p>
              <p className="text-gray-600">failure_category: temp_failure | insufficient_funds | auth_required | invalid_details | fraud | unknown</p>
            </div>
          </details>
        </div>
      </div>

      {/* Last result */}
      {lastResult && (
        <div className="card p-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Last Import Result</h4>
          <pre className="text-xs text-gray-600 bg-gray-50 rounded p-3 overflow-x-auto">
            {JSON.stringify(lastResult, null, 2)}
          </pre>
        </div>
      )}

      {/* Batch history */}
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100">
          <h3 className="font-semibold text-gray-800">Batch History</h3>
        </div>
        {batches.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-8">No batches yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  {['Batch ID', 'Filename', 'Status', 'Total', 'Valid', 'Invalid', 'Imported', 'Created'].map(h => (
                    <th key={h} className="table-header">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {batches.map(b => (
                  <tr key={b.id} className="hover:bg-gray-50">
                    <td className="table-cell font-mono text-xs">{b.id.slice(0, 12)}…</td>
                    <td className="table-cell">{b.filename}</td>
                    <td className="table-cell"><StatusBadge status={b.status} /></td>
                    <td className="table-cell text-center">{b.total_rows}</td>
                    <td className="table-cell text-center text-green-700">{b.valid_rows}</td>
                    <td className="table-cell text-center text-red-600">{b.invalid_rows}</td>
                    <td className="table-cell text-center text-blue-700">{b.imported_rows}</td>
                    <td className="table-cell">{new Date(b.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
