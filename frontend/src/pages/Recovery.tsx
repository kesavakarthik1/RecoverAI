import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import type { RecoveryCase, BatchImport } from '../types'
import { PageHeader } from '../components/ui/PageHeader'
import { LoadingPage, LoadingSpinner } from '../components/ui/LoadingSpinner'
import { ErrorAlert } from '../components/ui/ErrorAlert'
import { EmptyState } from '../components/ui/EmptyState'
import { RecoveryStateBadge, PriorityBadge, CategoryBadge } from '../components/ui/Badge'
import { Pagination } from '../components/ui/Pagination'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'

const INR = (v: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(v)

export default function Recovery() {
  const nav = useNavigate()
  const [cases, setCases] = useState<RecoveryCase[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [batches, setBatches] = useState<BatchImport[]>([])
  const [selectedBatch, setSelectedBatch] = useState('')
  const [stateFilter, setStateFilter] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('')
  const [processing, setProcessing] = useState(false)
  const [processResult, setProcessResult] = useState<Record<string, unknown> | null>(null)
  const [confirmBatch, setConfirmBatch] = useState(false)

  const PAGE_SIZE = 20

  const loadQueue = useCallback(() => {
    setLoading(true); setError(null)
    const params: Record<string, string | number> = { page, page_size: PAGE_SIZE }
    if (stateFilter) params.state = stateFilter
    if (priorityFilter) params.priority = priorityFilter
    api.getRecoveryQueue(params)
      .then(r => { setCases(r.items); setTotal(r.total) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [page, stateFilter, priorityFilter])

  useEffect(() => { loadQueue() }, [loadQueue])
  useEffect(() => { api.getBatches().then(setBatches).catch(() => null) }, [])

  const handleProcessBatch = async () => {
    if (!selectedBatch) return
    setProcessing(true); setProcessResult(null); setError(null)
    try {
      const result = await api.processBatch(selectedBatch, true)
      setProcessResult(result as Record<string, unknown>)
      await loadQueue()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Batch processing failed')
    } finally {
      setProcessing(false); setConfirmBatch(false)
    }
  }

  const handleApprove = async (c: RecoveryCase) => {
    const rec = c.recommendations?.[0]
    if (!rec) return
    try {
      await api.approveAction(c.id, { recommendation_id: rec.id, approver_id: 'dashboard_user' })
      await loadQueue()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Approval failed')
    }
  }

  const handleReject = async (c: RecoveryCase) => {
    const rec = c.recommendations?.[0]
    if (!rec) return
    try {
      await api.rejectAction(c.id, {
        recommendation_id: rec.id,
        approver_id: 'dashboard_user',
        reason: 'Rejected via dashboard',
      })
      await loadQueue()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Rejection failed')
    }
  }

  const handleFlagReview = async (caseId: string) => {
    try {
      await api.flagForReview(caseId, 'Manually flagged from dashboard')
      await loadQueue()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Flag failed')
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Recovery Agent"
        subtitle="Manage and monitor AI-assisted revenue recovery cases"
        actions={
          <button onClick={loadQueue} className="btn-secondary text-xs">↺ Refresh</button>
        }
      />

      {/* Batch processing panel */}
      <div className="card p-5">
        <h3 className="font-semibold text-gray-800 mb-3">Run Recovery Agent on Batch</h3>
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="text-xs font-medium text-gray-600 mb-1 block">Select Batch</label>
            <select className="input w-64" value={selectedBatch} onChange={e => setSelectedBatch(e.target.value)}>
              <option value="">— Choose a batch —</option>
              {batches.map(b => (
                <option key={b.id} value={b.id}>
                  {b.filename} ({b.imported_rows} txns)
                </option>
              ))}
            </select>
          </div>
          <button
            onClick={() => selectedBatch && setConfirmBatch(true)}
            disabled={!selectedBatch || processing}
            className="btn-primary"
          >
            {processing ? <><LoadingSpinner size="sm" /> Processing…</> : '⚡ Process Batch'}
          </button>
        </div>

        {processResult && (
          <div className="mt-4 rounded-lg bg-green-50 border border-green-200 p-3 text-sm text-green-800">
            <strong>Batch complete:</strong> {String((processResult as Record<string, unknown>).processed)} transactions processed.
            <span className="ml-2 font-mono text-xs">
              {JSON.stringify((processResult as Record<string, unknown>).outcomes)}
            </span>
          </div>
        )}

        {/* State machine explanation */}
        <div className="mt-4 flex flex-wrap gap-2 text-xs text-gray-500">
          {['DETECTED', '→', 'DIAGNOSED', '→', 'RECOMMENDED', '→', 'POLICY_CHECKED', '→',
            'APPROVED | BLOCKED', '→', 'EXECUTING', '→', 'SUCCEEDED | FAILED | HUMAN_REVIEW'].map((s, i) => (
            <span key={i} className={s === '→' ? 'text-gray-400' : 'bg-gray-100 rounded px-1.5 py-0.5 text-gray-600'}>
              {s}
            </span>
          ))}
        </div>
      </div>

      {error && <ErrorAlert message={error} onRetry={loadQueue} />}

      {/* Filters */}
      <div className="card p-4">
        <div className="flex flex-wrap gap-3">
          <select className="input w-44" value={stateFilter} onChange={e => { setStateFilter(e.target.value); setPage(1) }}>
            <option value="">All states</option>
            {['DETECTED', 'DIAGNOSED', 'RECOMMENDED', 'POLICY_CHECKED', 'APPROVAL_REQUIRED',
              'EXECUTING', 'SUCCEEDED', 'FAILED', 'BLOCKED', 'HUMAN_REVIEW'].map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <select className="input w-36" value={priorityFilter} onChange={e => { setPriorityFilter(e.target.value); setPage(1) }}>
            <option value="">All priorities</option>
            {['critical', 'high', 'medium', 'low'].map(p => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
          <span className="text-sm text-gray-500 self-center">{total} cases</span>
        </div>
      </div>

      {/* Cases table */}
      {loading ? (
        <LoadingPage />
      ) : cases.length === 0 ? (
        <EmptyState
          title="No recovery cases found"
          description="Generate synthetic data and run 'Process Batch' to create recovery cases."
        />
      ) : (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {['Case ID', 'Transaction', 'Category', 'State', 'Priority', 'At Risk', 'Recovered (sim.)', 'Recommendation', 'Actions'].map(h => (
                    <th key={h} className="table-header whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {cases.map(c => (
                  <tr key={c.id} className="hover:bg-gray-50">
                    <td className="table-cell font-mono text-xs text-brand-600">{c.id.slice(0, 10)}…</td>
                    <td className="table-cell">
                      <button
                        className="text-xs text-brand-600 hover:underline font-mono"
                        onClick={() => nav(`/transactions/${c.transaction_id}`)}
                      >
                        {c.transaction_id.slice(0, 10)}…
                      </button>
                    </td>
                    <td className="table-cell">
                      <span className="text-xs bg-gray-100 rounded px-2 py-0.5 text-gray-700">
                        {c.category.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="table-cell"><RecoveryStateBadge state={c.state} /></td>
                    <td className="table-cell"><PriorityBadge priority={c.priority} /></td>
                    <td className="table-cell font-semibold">{INR(c.at_risk_amount)}</td>
                    <td className="table-cell text-green-700">
                      {c.recovered_amount > 0 ? (
                        <span>{INR(c.recovered_amount)} <span className="text-xs text-gray-400">(sim.)</span></span>
                      ) : '—'}
                    </td>
                    <td className="table-cell">
                      {c.latest_recommendation ? (
                        <span className="text-xs font-medium text-brand-700 uppercase">
                          {c.latest_recommendation}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="table-cell">
                      <div className="flex gap-1">
                        {c.state === 'APPROVAL_REQUIRED' && (
                          <>
                            <button onClick={() => handleApprove(c)} className="btn-primary text-xs py-1 px-2">Approve</button>
                            <button onClick={() => handleReject(c)} className="btn-danger text-xs py-1 px-2">Reject</button>
                          </>
                        )}
                        {!['HUMAN_REVIEW', 'SUCCEEDED', 'FAILED', 'BLOCKED', 'CLOSED'].includes(c.state) && (
                          <button
                            onClick={() => handleFlagReview(c.id)}
                            className="btn-secondary text-xs py-1 px-2"
                          >
                            Review
                          </button>
                        )}
                        <button
                          onClick={() => nav(`/transactions/${c.transaction_id}`)}
                          className="text-xs text-brand-600 hover:underline px-1"
                        >
                          →
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination
            page={page}
            totalPages={Math.max(1, Math.ceil(total / PAGE_SIZE))}
            total={total}
            pageSize={PAGE_SIZE}
            onPage={setPage}
          />
        </div>
      )}

      <ConfirmDialog
        open={confirmBatch}
        title="Process Batch"
        message={`Run the recovery agent on all eligible transactions in the selected batch? This will detect, diagnose, and execute simulated recovery actions.`}
        confirmLabel="Run Agent"
        onConfirm={handleProcessBatch}
        onCancel={() => setConfirmBatch(false)}
      />
    </div>
  )
}
