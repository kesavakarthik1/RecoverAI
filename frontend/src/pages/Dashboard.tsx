import { useEffect, useState } from 'react'
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { api } from '../services/api'
import type { DashboardMetrics } from '../types'
import { MetricCard } from '../components/ui/MetricCard'
import { PageHeader } from '../components/ui/PageHeader'
import { LoadingPage } from '../components/ui/LoadingSpinner'
import { ErrorAlert } from '../components/ui/ErrorAlert'
import { RecoveryStateBadge, PriorityBadge } from '../components/ui/Badge'

const INR = (v: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(v)
const PCT = (v?: number | null) => v != null ? `${(v * 100).toFixed(1)}%` : '—'

const COLORS = ['#6470f3', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4']

export default function Dashboard() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = () => {
    setLoading(true); setError(null)
    api.getDashboard()
      .then(setMetrics)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  if (loading) return <LoadingPage />
  if (error) return <ErrorAlert message={error} onRetry={load} />
  if (!metrics) return null

  return (
    <div className="space-y-6">
      <PageHeader
        title="Executive Dashboard"
        subtitle="Revenue recovery performance across all transactions"
        actions={
          <button onClick={load} className="btn-secondary text-xs">↺ Refresh</button>
        }
      />

      {/* Simulation notice */}
      <div className="rounded-lg bg-blue-50 border border-blue-200 px-4 py-3 text-sm text-blue-800">
        <strong>Simulation Mode:</strong> All recovery actions are simulated. Recovered values shown here are simulated outcomes — not real merchant revenue collected.
      </div>

      {/* Primary metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        <MetricCard title="Total Transactions" value={metrics.total_transactions.toLocaleString()} icon={<span>📄</span>} />
        <MetricCard title="Gross Transaction Value" value={INR(metrics.total_gross_value)} subtitle="All transactions" />
        <MetricCard title="Revenue at Risk" value={INR(metrics.total_revenue_at_risk)} variant="warning" subtitle="Failed/abandoned/overdue" />
        <MetricCard title="Est. Recoverable" value={INR(metrics.estimated_recoverable_value)} subtitle="40% base estimate" />
        <MetricCard
          title="Simulated Recovered"
          value={INR(metrics.actual_recovered_value)}
          variant="success"
          note="Simulated outcome — not real revenue"
        />
        <MetricCard title="Recovery Rate" value={PCT(metrics.recovery_rate)} subtitle="Recovered / at-risk cases" />
        <MetricCard title="Action Success Rate" value={PCT(metrics.recovery_success_rate)} subtitle="Successful / attempted actions" />
        <MetricCard title="Human Review" value={metrics.human_review_count} variant="warning" />
      </div>

      {/* Volume metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <MetricCard title="Failed Payments" value={metrics.failed_payment_count} variant="danger" />
        <MetricCard title="Abandoned Checkouts" value={metrics.abandoned_checkout_count} variant="warning" />
        <MetricCard title="Failed Subscriptions" value={metrics.failed_subscription_count} variant="warning" />
        <MetricCard title="Overdue Receivables" value={metrics.overdue_receivable_count} variant="danger" />
      </div>

      {/* Actions */}
      <div className="grid grid-cols-3 gap-4">
        <MetricCard title="Actions Executed" value={metrics.recovery_actions_executed} variant="success" />
        <MetricCard title="Blocked Actions" value={metrics.blocked_actions} variant="danger" />
        <MetricCard title="Pending Review" value={metrics.human_review_count} variant="warning" />
      </div>

      {/* Charts row 1 */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Recovery trend */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Recovery Trend (7 days)</h3>
          {metrics.recovery_trend.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={metrics.recovery_trend}>
                <defs>
                  <linearGradient id="colorRec" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorRisk" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: number) => INR(v)} />
                <Legend />
                <Area type="monotone" dataKey="at_risk" name="At Risk" stroke="#f59e0b" fill="url(#colorRisk)" />
                <Area type="monotone" dataKey="recovered" name="Recovered (simulated)" stroke="#10b981" fill="url(#colorRec)" />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-400 text-center py-8">No trend data yet. Generate or import transactions.</p>
          )}
        </div>

        {/* Failure reason distribution */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Failure Reason Distribution</h3>
          {metrics.failure_reason_distribution.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={metrics.failure_reason_distribution}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  labelLine={false}
                >
                  {metrics.failure_reason_distribution.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-400 text-center py-8">No failure data yet.</p>
          )}
        </div>
      </div>

      {/* Charts row 2 */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Revenue at risk by category */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Revenue at Risk by Category</h3>
          {metrics.revenue_at_risk_by_category.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={metrics.revenue_at_risk_by_category}>
                <XAxis dataKey="category" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: number) => INR(v)} />
                <Bar dataKey="value" name="At Risk (INR)" fill="#6470f3" radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-400 text-center py-8">No data yet.</p>
          )}
        </div>

        {/* Recovery funnel */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Recovery Funnel</h3>
          {metrics.recovery_funnel.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={metrics.recovery_funnel} layout="vertical">
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis dataKey="stage" type="category" tick={{ fontSize: 10 }} width={100} />
                <Tooltip />
                <Bar dataKey="count" name="Cases" fill="#6470f3" radius={[0,4,4,0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-gray-400 text-center py-8">No cases yet. Run the recovery agent.</p>
          )}
        </div>
      </div>

      {/* Bottom row */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* High priority cases */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">High Priority Cases</h3>
          {metrics.high_priority_cases.length > 0 ? (
            <div className="space-y-2">
              {metrics.high_priority_cases.map(c => (
                <div key={c.id} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                  <div>
                    <p className="text-xs font-mono text-gray-500">{c.transaction_id.slice(0, 12)}…</p>
                    <p className="text-sm text-gray-700">{c.category.replace(/_/g, ' ')}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <PriorityBadge priority={c.priority} />
                    <span className="text-sm font-semibold">{INR(c.at_risk_amount)}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400 text-center py-4">No high-priority cases.</p>
          )}
        </div>

        {/* Recent activity */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Recent Activity</h3>
          {metrics.recent_activity.length > 0 ? (
            <div className="space-y-2">
              {metrics.recent_activity.map(a => (
                <div key={a.id} className="flex items-start gap-3 py-2 border-b border-gray-100 last:border-0">
                  <div className="flex-1">
                    <p className="text-xs font-medium text-gray-700">{a.event_type}</p>
                    <p className="text-xs text-gray-500">{a.transaction_id?.slice(0, 12)}… · {a.actor}</p>
                  </div>
                  <div className="text-right">
                    {a.outcome && <RecoveryStateBadge state={a.outcome} />}
                    <p className="text-xs text-gray-400 mt-1">
                      {new Date(a.timestamp).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400 text-center py-4">No recent activity.</p>
          )}
        </div>
      </div>
    </div>
  )
}
