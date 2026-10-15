import { useEffect, useState } from 'react'
import { api } from '../services/api'
import type { PolicyConfig } from '../types'
import { PageHeader } from '../components/ui/PageHeader'
import { LoadingPage, LoadingSpinner } from '../components/ui/LoadingSpinner'
import { ErrorAlert } from '../components/ui/ErrorAlert'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'

export default function PolicyConfiguration() {
  const [policy, setPolicy] = useState<PolicyConfig | null>(null)
  const [draft, setDraft] = useState<Partial<PolicyConfig>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [confirmReset, setConfirmReset] = useState(false)

  const load = () => {
    setLoading(true); setError(null)
    api.getPolicy()
      .then(p => { setPolicy(p); setDraft(p) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleSave = async () => {
    setSaving(true); setError(null); setSuccess(null)
    try {
      await api.updatePolicy(draft)
      setSuccess('Policy saved successfully.')
      await load()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const handleReset = async () => {
    setSaving(true); setError(null)
    try {
      await api.resetPolicy()
      setSuccess('Policy reset to safe defaults.')
      await load()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Reset failed')
    } finally {
      setSaving(false); setConfirmReset(false)
    }
  }

  const set = (key: keyof PolicyConfig, value: unknown) =>
    setDraft(d => ({ ...d, [key]: value }))

  if (loading) return <LoadingPage />

  return (
    <div className="space-y-6">
      <PageHeader
        title="Policy Configuration"
        subtitle="Configure recovery rules, retry limits, and communication controls"
        actions={
          <div className="flex gap-2">
            <button onClick={() => setConfirmReset(true)} className="btn-secondary text-xs">
              ↺ Reset to Defaults
            </button>
            <button onClick={handleSave} disabled={saving} className="btn-primary text-xs">
              {saving ? <><LoadingSpinner size="sm" /> Saving…</> : '✓ Save Policy'}
            </button>
          </div>
        }
      />

      {error && <ErrorAlert message={error} />}
      {success && (
        <div className="rounded-lg bg-green-50 border border-green-200 px-4 py-3 text-sm text-green-800">
          ✓ {success}
        </div>
      )}

      <div className="rounded-lg bg-blue-50 border border-blue-200 px-4 py-3 text-sm text-blue-800">
        <strong>Note:</strong> Policy rules are enforced server-side by the deterministic policy engine.
        The AI recommendation engine cannot override these limits. Changes take effect immediately for new recovery cases.
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Retry limits */}
        <div className="card p-5 space-y-4">
          <h3 className="font-semibold text-gray-800 flex items-center gap-2">
            🔄 Retry Limits
          </h3>
          <Field label="Max retry attempts" hint="Maximum times to retry a single transaction">
            <input
              type="number" min={0} max={10} className="input"
              value={draft.max_retry_attempts ?? 3}
              onChange={e => set('max_retry_attempts', Number(e.target.value))}
            />
          </Field>
          <Field label="Min delay between retries (hours)" hint="Minimum hours to wait between retry attempts">
            <input
              type="number" min={1} max={168} className="input"
              value={draft.min_retry_delay_hours ?? 24}
              onChange={e => set('min_retry_delay_hours', Number(e.target.value))}
            />
          </Field>
          <Field label="Max recovery actions per transaction" hint="Total actions allowed per transaction">
            <input
              type="number" min={1} max={20} className="input"
              value={draft.max_recovery_actions_per_txn ?? 5}
              onChange={e => set('max_recovery_actions_per_txn', Number(e.target.value))}
            />
          </Field>
        </div>

        {/* Communication limits */}
        <div className="card p-5 space-y-4">
          <h3 className="font-semibold text-gray-800 flex items-center gap-2">
            📧 Communication Limits
          </h3>
          <Field label="Max reminders per customer per week" hint="Prevents over-communication">
            <input
              type="number" min={0} max={10} className="input"
              value={draft.max_reminders_per_customer_per_week ?? 2}
              onChange={e => set('max_reminders_per_customer_per_week', Number(e.target.value))}
            />
          </Field>
          <Field label="Require communication consent" hint="Block reminders if customer has not consented">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={draft.require_communication_consent ?? true}
                onChange={e => set('require_communication_consent', e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-brand-600"
              />
              <span className="text-sm text-gray-700">Enforce consent requirement</span>
            </label>
          </Field>
        </div>

        {/* Approval thresholds */}
        <div className="card p-5 space-y-4">
          <h3 className="font-semibold text-gray-800 flex items-center gap-2">
            ✅ Approval Thresholds
          </h3>
          <Field label="Approval threshold (INR)" hint="Actions above this amount require human approval">
            <input
              type="number" min={0} className="input"
              value={draft.approval_threshold_amount ?? 50000}
              onChange={e => set('approval_threshold_amount', Number(e.target.value))}
            />
          </Field>
          <Field label="Max batch actions" hint="Maximum recovery actions to execute in one batch run">
            <input
              type="number" min={1} max={2000} className="input"
              value={draft.batch_max_actions ?? 500}
              onChange={e => set('batch_max_actions', Number(e.target.value))}
            />
          </Field>
        </div>

        {/* Retry eligibility */}
        <div className="card p-5 space-y-4">
          <h3 className="font-semibold text-gray-800 flex items-center gap-2">
            🛡 Failure Category Rules
          </h3>
          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Retryable failure categories</p>
            <div className="space-y-1">
              {['temp_failure', 'auth_required', 'insufficient_funds', 'invalid_details', 'fraud', 'unknown'].map(cat => {
                const retryable = (draft.retryable_failure_categories ?? ['temp_failure']) as string[]
                return (
                  <label key={cat} className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                      type="checkbox"
                      checked={retryable.includes(cat)}
                      onChange={e => {
                        const updated = e.target.checked
                          ? [...retryable, cat]
                          : retryable.filter(c => c !== cat)
                        set('retryable_failure_categories', updated)
                      }}
                      className="h-4 w-4 rounded border-gray-300 text-brand-600"
                    />
                    <span className="text-gray-700">{cat}</span>
                  </label>
                )
              })}
            </div>
          </div>
          <p className="text-xs text-gray-500">
            <strong>Stopping rules enforced regardless of configuration:</strong> fraud, cancelled subscriptions,
            disputed invoices, opted-out customers, max retries reached, payment confirmed.
          </p>
        </div>
      </div>

      {/* Policy summary */}
      {policy && (
        <div className="card p-5">
          <h3 className="font-semibold text-gray-800 mb-3">Current Active Policy</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 text-sm">
            {[
              ['Policy ID', policy.id.slice(0, 12) + '…'],
              ['Max Retries', policy.max_retry_attempts],
              ['Min Retry Delay', `${policy.min_retry_delay_hours}h`],
              ['Max Actions', policy.max_recovery_actions_per_txn],
              ['Max Reminders/Week', policy.max_reminders_per_customer_per_week],
              ['Approval Threshold', `₹${policy.approval_threshold_amount.toLocaleString()}`],
              ['Batch Limit', policy.batch_max_actions],
              ['Last Updated', new Date(policy.updated_at).toLocaleString()],
            ].map(([k, v]) => (
              <div key={String(k)} className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500">{k}</p>
                <p className="text-sm font-semibold text-gray-800 mt-0.5">{String(v)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <ConfirmDialog
        open={confirmReset}
        title="Reset Policy to Defaults"
        message="This will reset all policy rules to safe defaults. Existing recovery cases will not be affected, but new cases will use the default limits."
        confirmLabel="Reset"
        variant="danger"
        onConfirm={handleReset}
        onCancel={() => setConfirmReset(false)}
      />
    </div>
  )
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="text-sm font-medium text-gray-700 block mb-1">{label}</label>
      {hint && <p className="text-xs text-gray-400 mb-1">{hint}</p>}
      {children}
    </div>
  )
}
