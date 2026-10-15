import { useEffect, useState } from 'react'
import { api } from '../services/api'
import type { AppSettings } from '../types'
import { PageHeader } from '../components/ui/PageHeader'
import { LoadingPage } from '../components/ui/LoadingSpinner'
import { ErrorAlert } from '../components/ui/ErrorAlert'

export default function Settings() {
  const [settings, setSettings] = useState<AppSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.getSettings()
      .then(setSettings)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingPage />
  if (error) return <ErrorAlert message={error} />
  if (!settings) return null

  return (
    <div className="space-y-6">
      <PageHeader
        title="Application Settings"
        subtitle="Read-only view of current RecoverAI configuration"
      />

      <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
        <strong>Security note:</strong> API keys, payment credentials, and database secrets are never exposed
        through this interface. To change configuration, update environment variables and restart the server.
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Application */}
        <div className="card p-5">
          <h3 className="font-semibold text-gray-800 mb-4">Application</h3>
          <dl className="space-y-3">
            {[
              ['App Name', settings.app_name],
              ['Version', settings.version],
              ['Environment', settings.environment],
            ].map(([k, v]) => <SettingRow key={String(k)} label={String(k)} value={String(v)} />)}
          </dl>
        </div>

        {/* AI Provider */}
        <div className="card p-5">
          <h3 className="font-semibold text-gray-800 mb-4">AI Provider</h3>
          <dl className="space-y-3">
            <SettingRow label="Provider" value={settings.ai_provider} />
            <SettingRow
              label="LLM Configured"
              value={settings.llm_configured ? '✓ API key present' : '✗ Not configured (using rule-based)'}
              valueClass={settings.llm_configured ? 'text-green-700' : 'text-yellow-700'}
            />
          </dl>
          {!settings.llm_configured && (
            <div className="mt-4 rounded-lg bg-yellow-50 border border-yellow-200 p-3 text-xs text-yellow-800">
              No LLM API key configured. RecoverAI is using the deterministic rule-based provider.
              To enable AI-assisted recommendations, set <code className="font-mono">OPENROUTER_API_KEY</code> and
              <code className="font-mono"> AI_PROVIDER=openrouter</code> in your <code className="font-mono">.env</code> file.
            </div>
          )}
        </div>

        {/* Payment Provider */}
        <div className="card p-5">
          <h3 className="font-semibold text-gray-800 mb-4">Payment Provider</h3>
          <dl className="space-y-3">
            <SettingRow label="Provider" value={settings.payment_provider} />
            <SettingRow
              label="Live Payments"
              value={settings.is_live_payment ? '⚠ LIVE MODE' : '✓ Simulation only — no real charges'}
              valueClass={settings.is_live_payment ? 'text-red-700 font-bold' : 'text-green-700'}
            />
            <SettingRow
              label="Razorpay Test"
              value={settings.razorpay_configured ? '✓ Test credentials present' : '✗ Not configured'}
              valueClass={settings.razorpay_configured ? 'text-green-700' : 'text-gray-500'}
            />
          </dl>
          {!settings.is_live_payment && (
            <div className="mt-4 rounded-lg bg-blue-50 border border-blue-200 p-3 text-xs text-blue-800">
              All payment operations are simulated. No real financial transactions are initiated.
              This is by design for the Razorpay AI Buildathon demonstration.
            </div>
          )}
        </div>

        {/* Recovery defaults */}
        <div className="card p-5">
          <h3 className="font-semibold text-gray-800 mb-4">Recovery Defaults</h3>
          <dl className="space-y-3">
            <SettingRow label="Max Retry Attempts" value={String(settings.max_retry_attempts)} />
            <SettingRow label="Approval Threshold (INR)" value={`₹${settings.approval_threshold_inr.toLocaleString()}`} />
            <SettingRow label="Default Currency" value={settings.default_currency} />
          </dl>
        </div>
      </div>

      {/* API docs link */}
      <div className="card p-5">
        <h3 className="font-semibold text-gray-800 mb-3">API Documentation</h3>
        <div className="flex flex-wrap gap-3">
          <a
            href="/api/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary text-xs"
          >
            📖 Open Swagger UI
          </a>
          <a
            href="/api/redoc"
            target="_blank"
            rel="noopener noreferrer"
            className="btn-secondary text-xs"
          >
            📄 Open ReDoc
          </a>
          <a
            href="/api/openapi.json"
            target="_blank"
            rel="noopener noreferrer"
            className="btn-secondary text-xs"
          >
            ⬇ OpenAPI JSON
          </a>
          <a
            href="/health"
            target="_blank"
            rel="noopener noreferrer"
            className="btn-secondary text-xs"
          >
            ✓ Health Check
          </a>
        </div>
      </div>
    </div>
  )
}

function SettingRow({ label, value, valueClass = 'text-gray-900' }: {
  label: string; value: string; valueClass?: string
}) {
  return (
    <div className="flex items-start gap-3">
      <dt className="w-44 text-sm text-gray-500 shrink-0">{label}</dt>
      <dd className={`text-sm font-medium ${valueClass}`}>{value}</dd>
    </div>
  )
}
