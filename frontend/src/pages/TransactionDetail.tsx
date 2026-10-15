import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import type { Transaction, RecoveryCase, AuditEvent } from '../types'
import { PageHeader } from '../components/ui/PageHeader'
import { LoadingPage } from '../components/ui/LoadingSpinner'
import { ErrorAlert } from '../components/ui/ErrorAlert'
import { StatusBadge, CategoryBadge, RecoveryStateBadge, PriorityBadge } from '../components/ui/Badge'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'

const INR = (v: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(v)

export default function TransactionDetail() {
  const { id } = useParams<{ id: string }>()
  const nav = useNavigate()
  const [txn, setTxn] = useState<Transaction | null>(null)
  const [recCase, setRecCase] = useState<RecoveryCase | null>(null)
  const [audit, setAudit] = useState<AuditEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [processing, setProcessing] = useState(false)
  const [confirmProcess, setConfirmProcess] = useState(false)

  const load = async () => {
    if (!id) return
    setLoading(true); setError(null)
    try {
      const [t, a] = await Promise.all([
        api.getTransaction(id),
        api.getTransactionAudit(id),
      ])
      setTxn(t)
      setAudit(a as unknown as AuditEvent[])
      try {
        const rc = await api.getTransactionRecoveryCase(id)
        setRecCase(rc)
      } catch { setRecCase(null) }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [id])

  const handleProcess = async () => {
    if (!id) return
    setProcessing(true)
    try {
      await api.processTransaction(id)
      await load()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Processing failed')
    } finally {
      setProcessing(false); setConfirmProcess(false)
    }
  }

  if (loading) return <LoadingPage />
  if (error) return <ErrorAlert message={error} onRetry={load} />
  if (!txn) return null

  const canProcess = ['failed', 'abandoned', 'overdue'].includes(txn.status)
    && !['recovered', 'closed', 'blocked'].includes(txn.recovery_status)

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Transaction ${txn.id.slice(0, 16)}…`}
        subtitle={`${txn.transaction_type} · ${txn.customer_ref}`}
        actions={
          <div className="flex gap-2">
            <button onClick={() => nav('/transactions')} className="btn-secondary text-xs">← Back</button>
            {canProcess && (
              <button
                onClick={() => setConfirmProcess(true)}
                disabled={processing}
                className="btn-primary text-xs"
              >
                {processing ? 'Processing…' : '⚡ Run Recovery Agent'}
              </button>
            )}
          </div>
        }
      />

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Transaction details */}
        <div className="card p-5 space-y-4">
          <h3 className="font-semibold text-gray-800">Transaction Details</h3>
          <dl className="space-y-2 text-sm">
            {[
              ['ID', txn.id],
              ['External ID', txn.external_id ?? '—'],
              ['Customer Ref', txn.customer_ref],
              ['Amount', INR(txn.amount)],
              ['Currency', txn.currency],
              ['Type', txn.transaction_type],
              ['Status', <StatusBadge key="s" status={txn.status} />],
              ['Recovery Status', <StatusBadge key="rs" status={txn.recovery_status} />],
              ['Payment Method', txn.payment_method ?? '—'],
              ['Gateway', txn.gateway ?? '—'],
              ['Retry Count', txn.retry_count],
              ['Created', new Date(txn.created_at).toLocaleString()],
            ].map(([k, v]) => (
              <div key={String(k)} className="flex items-start gap-2">
                <dt className="w-36 text-gray-500 shrink-0">{k}</dt>
                <dd className="text-gray-900 font-mono text-xs break-all">{v as React.ReactNode}</dd>
              </div>
            ))}
          </dl>
        </div>

        {/* Failure & risk */}
        <div className="card p-5 space-y-4">
          <h3 className="font-semibold text-gray-800">Failure & Risk Analysis</h3>
          {txn.failure_category ? (
            <dl className="space-y-2 text-sm">
              {[
                ['Failure Category', <CategoryBadge key="fc" category={txn.failure_category} />],
                ['Failure Reason', txn.failure_reason ?? '—'],
                ['Failure Time', txn.failure_timestamp ? new Date(txn.failure_timestamp).toLocaleString() : '—'],
                ['Risk Score', txn.risk_score != null ? (
                  <span key="rs" className={txn.risk_score >= 80 ? 'text-red-600 font-bold' : txn.risk_score >= 60 ? 'text-yellow-600 font-semibold' : 'text-gray-700'}>
                    {txn.risk_score} / 100
                  </span>
                ) : '—'],
                ['Recoverability', txn.recoverability.replace(/_/g, ' ')],
              ].map(([k, v]) => (
                <div key={String(k)} className="flex items-start gap-2">
                  <dt className="w-36 text-gray-500 shrink-0">{k}</dt>
                  <dd className="text-gray-900">{v as React.ReactNode}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="text-sm text-gray-400">No failure data recorded.</p>
          )}

          {/* Recovery case summary */}
          {recCase && (
            <>
              <h3 className="font-semibold text-gray-800 mt-4">Recovery Case</h3>
              <dl className="space-y-2 text-sm">
                {[
                  ['State', <RecoveryStateBadge key="state" state={recCase.state} />],
                  ['Priority', <PriorityBadge key="prio" priority={recCase.priority} />],
                  ['At Risk', INR(recCase.at_risk_amount)],
                  ['Est. Recoverable', INR(recCase.estimated_recoverable_amount)],
                  ['Recovered (sim.)', INR(recCase.recovered_amount)],
                  ['Actions Taken', recCase.action_count],
                  ['Requires Review', recCase.requires_human_review ? 'Yes' : 'No'],
                ].map(([k, v]) => (
                  <div key={String(k)} className="flex items-start gap-2">
                    <dt className="w-36 text-gray-500 shrink-0">{k}</dt>
                    <dd className="text-gray-900">{v as React.ReactNode}</dd>
                  </div>
                ))}
              </dl>

              {/* Recommendations */}
              {recCase.recommendations && recCase.recommendations.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">Recovery Recommendations</h4>
                  {recCase.recommendations.map(r => (
                    <div key={r.id} className="rounded-lg bg-gray-50 border border-gray-200 p-3 mb-2 text-xs space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-brand-700 uppercase">{r.recommended_action}</span>
                        <span className="text-gray-500">Confidence: {(r.confidence * 100).toFixed(0)}%</span>
                      </div>
                      <p className="text-gray-700">{r.reason}</p>
                      {r.evidence && <p className="text-gray-500 italic">Evidence: {r.evidence}</p>}
                      <div className="flex items-center gap-3 text-gray-500">
                        <span>Source: {r.source}</span>
                        <span>Status: {r.status}</span>
                        {r.expected_recovery_value != null && (
                          <span>Est. Recovery: {INR(r.expected_recovery_value)}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Audit timeline */}
      <div className="card p-5">
        <h3 className="font-semibold text-gray-800 mb-4">Audit Trail ({audit.length} events)</h3>
        {audit.length === 0 ? (
          <p className="text-sm text-gray-400">No audit events yet. Run the recovery agent to generate events.</p>
        ) : (
          <div className="relative">
            <div className="absolute left-4 top-0 bottom-0 w-px bg-gray-200" />
            <div className="space-y-4 pl-10">
              {audit.map((e, i) => (
                <div key={e.id} className="relative">
                  <div className="absolute -left-6 flex h-5 w-5 items-center justify-center rounded-full bg-brand-600 text-white text-xs font-bold">
                    {i + 1}
                  </div>
                  <div className="rounded-lg bg-gray-50 border border-gray-100 p-3 text-xs">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-gray-800 uppercase tracking-wide">{e.event_type}</span>
                      <span className="text-gray-400">{new Date(e.created_at).toLocaleString()}</span>
                    </div>
                    {(e.previous_state || e.new_state) && (
                      <p className="text-gray-600">
                        {e.previous_state} → <strong>{e.new_state}</strong>
                      </p>
                    )}
                    {e.recommendation && (
                      <p className="text-gray-600 mt-1">{e.recommendation}</p>
                    )}
                    {e.policy_decision && (
                      <p className={`mt-1 font-medium ${e.policy_decision === 'blocked' ? 'text-red-600' : 'text-green-600'}`}>
                        Policy: {e.policy_decision}
                      </p>
                    )}
                    {e.error_details && (
                      <p className="text-red-600 mt-1">{e.error_details}</p>
                    )}
                    <p className="text-gray-400 mt-1">Actor: {e.actor}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <ConfirmDialog
        open={confirmProcess}
        title="Run Recovery Agent"
        message={`Process transaction ${txn.id.slice(0, 16)}… through the recovery agent? This will detect, diagnose, and attempt a simulated recovery action.`}
        confirmLabel="Run Agent"
        onConfirm={handleProcess}
        onCancel={() => setConfirmProcess(false)}
      />
    </div>
  )
}
