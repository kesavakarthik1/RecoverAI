import { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, RadarChart,
  Radar, PolarGrid, PolarAngleAxis,
} from 'recharts'
import { api } from '../services/api'
import type { EvaluationRun, BatchImport } from '../types'
import { PageHeader } from '../components/ui/PageHeader'
import { LoadingPage, LoadingSpinner } from '../components/ui/LoadingSpinner'
import { ErrorAlert } from '../components/ui/ErrorAlert'
import { EmptyState } from '../components/ui/EmptyState'

const INR = (v: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(v)
const PCT = (v?: number | null) => (v != null ? `${(v * 100).toFixed(1)}%` : '—')
const FMT = (v?: number | null, dec = 2) => (v != null ? v.toFixed(dec) : '—')

const STRATEGY_COLORS: Record<string, string> = {
  baseline: '#9ca3af',
  fixed_rule: '#6470f3',
  ai_assisted: '#10b981',
}

export default function Evaluation() {
  const [runs, setRuns] = useState<EvaluationRun[]>([])
  const [comparison, setComparison] = useState<{ strategies: Record<string, EvaluationRun>; comparison_table: Record<string, unknown>[] } | null>(null)
  const [batches, setBatches] = useState<BatchImport[]>([])
  const [selectedBatch, setSelectedBatch] = useState('')
  const [seed, setSeed] = useState(42)
  const [running, setRunning] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'compare' | 'runs'>('compare')

  const loadData = async () => {
    setLoading(true); setError(null)
    try {
      const [r, c, b] = await Promise.all([
        api.getEvaluationRuns(),
        api.compareStrategies(selectedBatch || undefined),
        api.getBatches(),
      ])
      setRuns(r); setComparison(c as typeof comparison); setBatches(b)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadData() }, [])

  const handleRunEvaluation = async () => {
    setRunning(true); setError(null)
    try {
      await api.runEvaluation(selectedBatch || undefined, seed)
      await loadData()
      setActiveTab('compare')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Evaluation failed')
    } finally {
      setRunning(false)
    }
  }

  const strategyRuns = comparison?.strategies ?? {}
  const strategies = Object.keys(strategyRuns)

  // Build chart data
  const recoveryRateChart = strategies.map(s => ({
    strategy: s,
    'Rate by Count (%)': ((strategyRuns[s]?.recovery_rate_by_count ?? 0) * 100),
    'Rate by Value (%)': ((strategyRuns[s]?.recovery_rate_by_value ?? 0) * 100),
  }))

  const valueChart = strategies.map(s => ({
    strategy: s,
    'Recovered (sim.)': strategyRuns[s]?.simulated_recovered_value ?? 0,
    'At Risk': strategyRuns[s]?.total_revenue_at_risk ?? 0,
    'Intervention Cost': strategyRuns[s]?.estimated_intervention_cost ?? 0,
  }))

  const radarData = [
    { metric: 'Recovery Rate', ...Object.fromEntries(strategies.map(s => [s, ((strategyRuns[s]?.recovery_rate_by_count ?? 0) * 100)])) },
    { metric: 'Precision', ...Object.fromEntries(strategies.map(s => [s, ((strategyRuns[s]?.precision ?? 0) * 100)])) },
    { metric: 'Recall', ...Object.fromEntries(strategies.map(s => [s, ((strategyRuns[s]?.recall ?? 0) * 100)])) },
    { metric: 'Low Blocks', ...Object.fromEntries(strategies.map(s => [s, Math.max(0, 100 - (strategyRuns[s]?.blocked_action_count ?? 0) * 5)])) },
    { metric: 'Low FP', ...Object.fromEntries(strategies.map(s => [s, Math.max(0, 100 - (strategyRuns[s]?.false_positive_intervention_count ?? 0) * 5)])) },
  ]

  if (loading) return <LoadingPage />

  return (
    <div className="space-y-6">
      <PageHeader
        title="Evaluation & Strategy Comparison"
        subtitle="Compare baseline, fixed-rule, and AI-assisted recovery strategies on the same dataset"
        actions={<button onClick={loadData} className="btn-secondary text-xs">↺ Refresh</button>}
      />

      {/* Simulation disclaimer */}
      <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
        <strong>Evaluation disclaimer:</strong> All recovered values are simulated outcomes. Precision/recall are calculated
        against synthetic ground-truth labels. These metrics do not represent real merchant revenue.
      </div>

      {error && <ErrorAlert message={error} onRetry={loadData} />}

      {/* Run evaluation */}
      <div className="card p-5">
        <h3 className="font-semibold text-gray-800 mb-3">Run New Evaluation</h3>
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="text-xs font-medium text-gray-600 mb-1 block">Batch (optional)</label>
            <select className="input w-64" value={selectedBatch} onChange={e => setSelectedBatch(e.target.value)}>
              <option value="">All transactions</option>
              {batches.map(b => (
                <option key={b.id} value={b.id}>{b.filename} ({b.imported_rows})</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-gray-600 mb-1 block">Seed</label>
            <input type="number" value={seed} onChange={e => setSeed(Number(e.target.value))} className="input w-24" />
          </div>
          <button onClick={handleRunEvaluation} disabled={running} className="btn-primary">
            {running ? <><LoadingSpinner size="sm" /> Running 3 strategies…</> : '▶ Run Evaluation'}
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-2">
          Runs baseline, fixed_rule, and ai_assisted strategies on the same dataset for fair comparison.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        {(['compare', 'runs'] as const).map(t => (
          <button
            key={t}
            onClick={() => setActiveTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === t ? 'border-brand-600 text-brand-600' : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t === 'compare' ? 'Strategy Comparison' : 'All Runs'}
          </button>
        ))}
      </div>

      {activeTab === 'compare' && (
        strategies.length === 0 ? (
          <EmptyState
            title="No evaluation runs yet"
            description="Run an evaluation above to compare strategies."
          />
        ) : (
          <div className="space-y-6">
            {/* Summary metric cards */}
            <div className="grid grid-cols-3 gap-4">
              {strategies.map(s => {
                const run = strategyRuns[s]
                return (
                  <div key={s} className="card p-4 border-l-4" style={{ borderLeftColor: STRATEGY_COLORS[s] }}>
                    <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">{s.replace(/_/g, ' ')}</p>
                    <p className="text-2xl font-bold text-gray-900 mt-1">{PCT(run?.recovery_rate_by_count)}</p>
                    <p className="text-xs text-gray-500">Recovery rate by count</p>
                    <div className="mt-3 space-y-1 text-xs text-gray-600">
                      <div className="flex justify-between"><span>Recovered (sim.)</span><span className="font-semibold text-green-700">{INR(run?.simulated_recovered_value ?? 0)}</span></div>
                      <div className="flex justify-between"><span>At Risk</span><span>{INR(run?.total_revenue_at_risk ?? 0)}</span></div>
                      <div className="flex justify-between"><span>Net Value</span><span className="font-semibold">{INR(run?.net_simulated_recovery_value ?? 0)}</span></div>
                      <div className="flex justify-between"><span>Blocked</span><span>{run?.blocked_action_count ?? 0}</span></div>
                      <div className="flex justify-between"><span>Human Review</span><span>{run?.human_review_count ?? 0}</span></div>
                      <div className="flex justify-between"><span>Precision</span><span>{PCT(run?.precision)}</span></div>
                      <div className="flex justify-between"><span>Recall</span><span>{PCT(run?.recall)}</span></div>
                    </div>
                    <a
                      href={`/api/v1/evaluation/runs/${run?.id}/export?format=csv`}
                      className="mt-3 inline-block text-xs text-brand-600 hover:underline"
                      target="_blank" rel="noopener noreferrer"
                    >
                      ↓ Export CSV
                    </a>
                  </div>
                )
              })}
            </div>

            {/* Charts */}
            <div className="grid lg:grid-cols-2 gap-6">
              <div className="card p-5">
                <h3 className="text-sm font-semibold text-gray-700 mb-4">Recovery Rate Comparison</h3>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={recoveryRateChart}>
                    <XAxis dataKey="strategy" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} unit="%" />
                    <Tooltip formatter={(v: number) => `${v.toFixed(1)}%`} />
                    <Legend />
                    <Bar dataKey="Rate by Count (%)" fill="#6470f3" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="Rate by Value (%)" fill="#10b981" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="card p-5">
                <h3 className="text-sm font-semibold text-gray-700 mb-4">Value Comparison (INR)</h3>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={valueChart}>
                    <XAxis dataKey="strategy" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(v: number) => INR(v)} />
                    <Legend />
                    <Bar dataKey="Recovered (sim.)" fill="#10b981" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="Intervention Cost" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Radar chart */}
            {strategies.length > 0 && (
              <div className="card p-5">
                <h3 className="text-sm font-semibold text-gray-700 mb-4">Strategy Radar Comparison</h3>
                <ResponsiveContainer width="100%" height={280}>
                  <RadarChart data={radarData}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11 }} />
                    {strategies.map(s => (
                      <Radar
                        key={s}
                        name={s}
                        dataKey={s}
                        stroke={STRATEGY_COLORS[s]}
                        fill={STRATEGY_COLORS[s]}
                        fillOpacity={0.15}
                      />
                    ))}
                    <Legend />
                    <Tooltip />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Comparison table */}
            {comparison?.comparison_table && (
              <div className="card overflow-hidden">
                <div className="px-5 py-4 border-b border-gray-100">
                  <h3 className="font-semibold text-gray-800">Detailed Metric Comparison</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="table-header">Metric</th>
                        {strategies.map(s => (
                          <th key={s} className="table-header" style={{ color: STRATEGY_COLORS[s] }}>
                            {s.replace(/_/g, ' ')}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {comparison.comparison_table.map((row: Record<string, unknown>) => (
                        <tr key={String(row.metric)} className="hover:bg-gray-50">
                          <td className="table-cell font-medium text-gray-700">{String(row.metric).replace(/_/g, ' ')}</td>
                          {strategies.map(s => {
                            const val = row[s]
                            const fmt = val == null ? '—' : typeof val === 'number' ?
                              (String(row.metric).includes('rate') ? PCT(val) :
                               String(row.metric).includes('value') || String(row.metric).includes('cost') ? INR(val) :
                               val.toFixed(0)) : String(val)
                            return <td key={s} className="table-cell text-center">{fmt}</td>
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Category breakdown */}
            {strategies[0] && strategyRuns[strategies[0]]?.results_by_category && (
              <div className="card p-5">
                <h3 className="text-sm font-semibold text-gray-700 mb-4">Results by Failure Category (AI-Assisted)</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="table-header">Category</th>
                        <th className="table-header">Count</th>
                        <th className="table-header">Recovered</th>
                        <th className="table-header">Recovery Rate</th>
                        <th className="table-header">Value Recovered</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {Object.entries(strategyRuns['ai_assisted']?.results_by_category ?? strategyRuns[strategies[0]]?.results_by_category ?? {}).map(
                        ([cat, data]) => {
                          const d = data as { count: number; recovered: number; value: number }
                          return (
                            <tr key={cat} className="hover:bg-gray-50">
                              <td className="table-cell font-medium">{cat.replace(/_/g, ' ')}</td>
                              <td className="table-cell text-center">{d.count}</td>
                              <td className="table-cell text-center text-green-700">{d.recovered}</td>
                              <td className="table-cell text-center">
                                {d.count > 0 ? PCT(d.recovered / d.count) : '—'}
                              </td>
                              <td className="table-cell text-right">{INR(d.value)}</td>
                            </tr>
                          )
                        }
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )
      )}

      {activeTab === 'runs' && (
        <div className="card overflow-hidden">
          {runs.length === 0 ? (
            <EmptyState title="No runs yet" description="Run an evaluation to see results." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    {['Name', 'Strategy', 'Status', 'Transactions', 'At Risk', 'Recovered', 'Rate', 'Created', 'Export'].map(h => (
                      <th key={h} className="table-header">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {runs.map(r => (
                    <tr key={r.id} className="hover:bg-gray-50">
                      <td className="table-cell">{r.name}</td>
                      <td className="table-cell">
                        <span className="font-medium" style={{ color: STRATEGY_COLORS[r.strategy] }}>
                          {r.strategy}
                        </span>
                      </td>
                      <td className="table-cell">
                        <span className={`badge ${r.status === 'completed' ? 'bg-green-100 text-green-800' : r.status === 'failed' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'}`}>
                          {r.status}
                        </span>
                      </td>
                      <td className="table-cell text-center">{r.total_transaction_count}</td>
                      <td className="table-cell">{INR(r.total_revenue_at_risk)}</td>
                      <td className="table-cell text-green-700">{INR(r.simulated_recovered_value)}</td>
                      <td className="table-cell">{PCT(r.recovery_rate_by_count)}</td>
                      <td className="table-cell text-xs">{new Date(r.created_at).toLocaleString()}</td>
                      <td className="table-cell">
                        <a
                          href={`/api/v1/evaluation/runs/${r.id}/export?format=csv`}
                          className="text-xs text-brand-600 hover:underline"
                          target="_blank" rel="noopener noreferrer"
                        >
                          ↓ CSV
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
