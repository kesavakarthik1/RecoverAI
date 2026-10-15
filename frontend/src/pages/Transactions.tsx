import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import type { Transaction, PaginatedResponse } from '../types'
import { PageHeader } from '../components/ui/PageHeader'
import { LoadingPage } from '../components/ui/LoadingSpinner'
import { ErrorAlert } from '../components/ui/ErrorAlert'
import { StatusBadge, CategoryBadge, PriorityBadge } from '../components/ui/Badge'
import { Pagination } from '../components/ui/Pagination'
import { EmptyState } from '../components/ui/EmptyState'

const INR = (v: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(v)

export default function Transactions() {
  const nav = useNavigate()
  const [data, setData] = useState<PaginatedResponse<Transaction> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [filters, setFilters] = useState({
    status: '', recovery_status: '', failure_category: '',
    transaction_type: '', search: '', page: 1, page_size: 20,
  })

  const load = useCallback(() => {
    setLoading(true); setError(null)
    const params = Object.fromEntries(
      Object.entries(filters).filter(([, v]) => v !== '' && v !== 0)
    ) as Record<string, string | number>
    api.getTransactions(params)
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [filters])

  useEffect(() => { load() }, [load])

  const setFilter = (key: string, value: string | number) =>
    setFilters(f => ({ ...f, [key]: value, page: 1 }))

  return (
    <div className="space-y-4">
      <PageHeader
        title="Transactions"
        subtitle={data ? `${data.total.toLocaleString()} transactions` : undefined}
        actions={
          <a
            href="/api/v1/transactions/export/csv"
            className="btn-secondary text-xs"
            target="_blank"
            rel="noopener noreferrer"
          >
            ↓ Export CSV
          </a>
        }
      />

      {/* Filters */}
      <div className="card p-4">
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <input
            className="input col-span-2"
            placeholder="Search ID, customer ref…"
            value={filters.search}
            onChange={e => setFilter('search', e.target.value)}
          />
          <select className="input" value={filters.status} onChange={e => setFilter('status', e.target.value)}>
            <option value="">All statuses</option>
            {['failed', 'abandoned', 'overdue', 'success', 'pending', 'cancelled'].map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <select className="input" value={filters.recovery_status} onChange={e => setFilter('recovery_status', e.target.value)}>
            <option value="">All recovery</option>
            {['pending', 'in_progress', 'recovered', 'failed', 'blocked', 'human_review', 'closed'].map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <select className="input" value={filters.failure_category} onChange={e => setFilter('failure_category', e.target.value)}>
            <option value="">All categories</option>
            {['temp_failure', 'insufficient_funds', 'auth_required', 'invalid_details', 'fraud', 'unknown'].map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <select className="input" value={filters.transaction_type} onChange={e => setFilter('transaction_type', e.target.value)}>
            <option value="">All types</option>
            {['payment', 'subscription', 'invoice', 'checkout'].map(t => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <LoadingPage />
      ) : error ? (
        <ErrorAlert message={error} onRetry={load} />
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          title="No transactions found"
          description="Import a CSV or generate a synthetic dataset to get started."
        />
      ) : (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {['Transaction ID', 'Customer', 'Amount', 'Type', 'Status', 'Failure Category', 'Retries', 'Risk', 'Recovery'].map(h => (
                    <th key={h} className="table-header whitespace-nowrap">{h}</th>
                  ))}
                  <th className="table-header" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.items.map(t => (
                  <tr
                    key={t.id}
                    className="hover:bg-gray-50 cursor-pointer transition-colors"
                    onClick={() => nav(`/transactions/${t.id}`)}
                  >
                    <td className="table-cell font-mono text-xs text-brand-600">{t.id.slice(0, 12)}…</td>
                    <td className="table-cell">{t.customer_ref}</td>
                    <td className="table-cell font-semibold whitespace-nowrap">{INR(t.amount)}</td>
                    <td className="table-cell capitalize">{t.transaction_type}</td>
                    <td className="table-cell"><StatusBadge status={t.status} /></td>
                    <td className="table-cell">
                      {t.failure_category ? <CategoryBadge category={t.failure_category} /> : <span className="text-gray-400">—</span>}
                    </td>
                    <td className="table-cell text-center">{t.retry_count}</td>
                    <td className="table-cell">
                      {t.risk_score != null ? (
                        <span className={
                          t.risk_score >= 80 ? 'text-red-600 font-semibold' :
                          t.risk_score >= 60 ? 'text-yellow-600 font-semibold' : 'text-gray-600'
                        }>
                          {t.risk_score}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="table-cell"><StatusBadge status={t.recovery_status} /></td>
                    <td className="table-cell">
                      <button
                        className="text-xs text-brand-600 hover:underline"
                        onClick={e => { e.stopPropagation(); nav(`/transactions/${t.id}`) }}
                      >
                        View →
                      </button>
                    </td>
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
            onPage={p => setFilters(f => ({ ...f, page: p }))}
          />
        </div>
      )}
    </div>
  )
}
