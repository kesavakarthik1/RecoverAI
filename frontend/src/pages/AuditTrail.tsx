import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import type { AuditEvent, PaginatedResponse } from '../types'
import { PageHeader } from '../components/ui/PageHeader'
import { LoadingPage } from '../components/ui/LoadingSpinner'
import { ErrorAlert } from '../components/ui/ErrorAlert'
import { EmptyState } from '../components/ui/EmptyState'
import { Pagination } from '../components/ui/Pagination'

const EVENT_COLORS: Record<string, string> = {
  DETECTED: 'bg-blue-100 text-blue-800',
  DIAGNOSED: 'bg-blue-100 text-blue-800',
  RECOMMENDED: 'bg-yellow-100 text-yellow-800',
  POLICY_CHECKED: 'bg-yellow-100 text-yellow-800',
  APPROVED: 'bg-green-100 text-green-800',
  REJECTED: 'bg-red-100 text-red-800',
  EXECUTING: 'bg-purple-100 text-purple-800',
  SUCCEEDED: 'bg-green-100 text-green-800',
  FAILED: 'bg-red-100 text-red-800',
  BLOCKED: 'bg-red-100 text-red-800',
  HUMAN_REVIEW: 'bg-purple-100 text-purple-800',
  CLOSED: 'bg-gray-100 text-gray-700',
  IMPORT: 'bg-gray-100 text-gray-700',
  EVALUATION: 'bg-indigo-100 text-indigo-800',
}

export default function AuditTrail() {
  const nav = useNavigate()
  const [data, setData] = useState<PaginatedResponse<AuditEvent> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [txnFilter, setTxnFilter] = useState('')
  const [eventTypeFilter, setEventTypeFilter] = useState('')
  const [page, setPage] = useState(1)

  const load = useCallback(() => {
    setLoading(true); setError(null)
    const params: Record<string, string | number> = { page, page_size: 25 }
    if (txnFilter) params.transaction_id = txnFilter
    if (eventTypeFilter) params.event_type = eventTypeFilter
    api.getAuditEvents(params)
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [page, txnFilter, eventTypeFilter])

  useEffect(() => { load() }, [load])

  return (
    <div className="space-y-4">
      <PageHeader
        title="Audit Trail"
        subtitle="Append-only log of every recovery decision, action, and outcome"
        actions={<button onClick={load} className="btn-secondary text-xs">↺ Refresh</button>}
      />

      <div className="rounded-lg bg-gray-50 border border-gray-200 px-4 py-3 text-xs text-gray-600">
        The audit trail is <strong>append-only</strong> — records are never modified or deleted after creation.
        Every recovery action is traceable to its originating transaction and the policy decision that authorized it.
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex flex-wrap gap-3">
          <input
            className="input w-64"
            placeholder="Filter by Transaction ID…"
            value={txnFilter}
            onChange={e => { setTxnFilter(e.target.value); setPage(1) }}
          />
          <select
            className="input w-48"
            value={eventTypeFilter}
            onChange={e => { setEventTypeFilter(e.target.value); setPage(1) }}
          >
            <option value="">All event types</option>
            {['DETECTED', 'DIAGNOSED', 'RECOMMENDED', 'POLICY_CHECKED', 'APPROVED',
              'REJECTED', 'EXECUTING', 'SUCCEEDED', 'FAILED', 'BLOCKED', 'HUMAN_REVIEW', 'CLOSED'].map(t => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
          {data && <span className="text-sm text-gray-500 self-center">{data.total} events</span>}
        </div>
      </div>

      {loading ? (
        <LoadingPage />
      ) : error ? (
        <ErrorAlert message={error} onRetry={load} />
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          title="No audit events"
          description="Audit events are created when the recovery agent processes transactions."
        />
      ) : (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {['Timestamp', 'Event Type', 'Transaction', 'State Change', 'Policy', 'Action', 'Outcome', 'Actor'].map(h => (
                    <th key={h} className="table-header whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.items.map(e => (
                  <tr key={e.id} className="hover:bg-gray-50">
                    <td className="table-cell text-xs text-gray-500 whitespace-nowrap">
                      {new Date(e.created_at).toLocaleString()}
                    </td>
                    <td className="table-cell">
                      <span className={`badge text-xs ${EVENT_COLORS[e.event_type] ?? 'bg-gray-100 text-gray-700'}`}>
                        {e.event_type}
                      </span>
                    </td>
                    <td className="table-cell">
                      {e.transaction_id ? (
                        <button
                          className="font-mono text-xs text-brand-600 hover:underline"
                          onClick={() => nav(`/transactions/${e.transaction_id}`)}
                        >
                          {e.transaction_id.slice(0, 12)}…
                        </button>
                      ) : '—'}
                    </td>
                    <td className="table-cell text-xs">
                      {(e.previous_state || e.new_state) ? (
                        <span>
                          {e.previous_state && <span className="text-gray-500">{e.previous_state}</span>}
                          {e.previous_state && e.new_state && ' → '}
                          {e.new_state && <strong>{e.new_state}</strong>}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="table-cell">
                      {e.policy_decision ? (
                        <span className={`text-xs font-medium ${e.policy_decision === 'blocked' ? 'text-red-600' : 'text-green-600'}`}>
                          {e.policy_decision}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="table-cell text-xs">
                      {e.action_attempted ?? '—'}
                    </td>
                    <td className="table-cell text-xs">
                      {e.final_outcome ? (
                        <span className={`font-medium ${e.final_outcome === 'SUCCEEDED' ? 'text-green-600' : e.final_outcome === 'BLOCKED' || e.final_outcome === 'FAILED' ? 'text-red-600' : 'text-gray-600'}`}>
                          {e.final_outcome}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="table-cell text-xs text-gray-500">{e.actor}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination
            page={data.page}
            totalPages={data.total_pages}
            total={data.total}
            pageSize={data.page_size}
            onPage={setPage}
          />
        </div>
      )}
    </div>
  )
}
