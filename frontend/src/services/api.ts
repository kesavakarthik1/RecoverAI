// API client — all calls go through /api/v1 (proxied to backend)
import type {
  AuditEvent,
  BatchImport,
  DashboardMetrics,
  EvaluationRun,
  PaginatedResponse,
  PolicyConfig,
  RecoveryCase,
  Transaction,
  AppSettings,
} from '../types'

const BASE = '/api/v1'

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    let msg = `HTTP ${res.status}`
    try {
      const body = await res.json()
      msg = body.message || body.detail || msg
    } catch {/* ignore */}
    throw new Error(msg)
  }
  // Some endpoints return 204 with no body
  const text = await res.text()
  return text ? JSON.parse(text) : undefined
}

// ── Dashboard ─────────────────────────────────────────────────────────────────
export const api = {
  // Settings
  getSettings: () => request<AppSettings>('/settings'),

  // Dashboard
  getDashboard: () => request<DashboardMetrics>('/dashboard'),

  // Transactions
  getTransactions: (params: Record<string, string | number>) => {
    const qs = new URLSearchParams(
      Object.fromEntries(
        Object.entries(params)
          .filter(([, v]) => v !== undefined && v !== '' && v !== null)
          .map(([k, v]) => [k, String(v)])
      )
    ).toString()
    return request<PaginatedResponse<Transaction>>(`/transactions${qs ? '?' + qs : ''}`)
  },
  getTransaction: (id: string) => request<Transaction>(`/transactions/${id}`),
  getTransactionAudit: (id: string) => request<AuditEvent[]>(`/transactions/${id}/audit`),
  getTransactionRecoveryCase: (id: string) => request<RecoveryCase>(`/transactions/${id}/recovery-case`),

  // Import
  getBatches: () => request<BatchImport[]>('/imports'),
  getCsvTemplate: () => request<unknown>('/imports/template'),
  generateSynthetic: (count: number, seed = 42) =>
    request<{ batch_id: string; imported_rows: number; metadata: unknown }>(
      `/imports/generate-synthetic?count=${count}&seed=${seed}`,
      { method: 'POST' }
    ),
  uploadCsv: (formData: FormData) =>
    fetch(`${BASE}/imports/upload`, { method: 'POST', body: formData }).then(async res => {
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.message || `HTTP ${res.status}`)
      }
      return res.json()
    }),

  // Recovery
  getRecoveryQueue: (params: Record<string, string | number>) => {
    const qs = new URLSearchParams(
      Object.fromEntries(
        Object.entries(params)
          .filter(([, v]) => v !== undefined && v !== '')
          .map(([k, v]) => [k, String(v)])
      )
    ).toString()
    return request<{ items: RecoveryCase[]; total: number; page: number; page_size: number }>(
      `/recovery/queue${qs ? '?' + qs : ''}`
    )
  },
  processTransaction: (id: string, autoExecute = true) =>
    request<{ case_id: string; state: string }>(`/recovery/process/${id}?auto_execute=${autoExecute}`, {
      method: 'POST',
    }),
  processBatch: (batchId: string, autoExecute = true) =>
    request<{ processed: number; outcomes: Record<string, number> }>(
      `/recovery/process-batch?batch_id=${batchId}&auto_execute=${autoExecute}`,
      { method: 'POST' }
    ),
  approveAction: (caseId: string, body: { recommendation_id: string; approver_id?: string; note?: string }) =>
    request<{ status: string; new_state: string }>(`/recovery/${caseId}/approve`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  rejectAction: (caseId: string, body: { recommendation_id: string; approver_id?: string; reason: string }) =>
    request<{ status: string; new_state: string }>(`/recovery/${caseId}/reject`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  flagForReview: (caseId: string, reason: string) =>
    request<{ status: string }>(`/recovery/${caseId}/flag-review?reason=${encodeURIComponent(reason)}`, {
      method: 'POST',
    }),

  // Evaluation
  runEvaluation: (batchId?: string, seed = 42) => {
    const qs = new URLSearchParams()
    if (batchId) qs.set('batch_id', batchId)
    qs.set('seed', String(seed))
    return request<{ evaluation_runs: Record<string, unknown> }>(
      `/evaluation/run?${qs.toString()}`,
      { method: 'POST' }
    )
  },
  getEvaluationRuns: () => request<EvaluationRun[]>('/evaluation/runs'),
  getEvaluationRun: (id: string) => request<EvaluationRun>(`/evaluation/runs/${id}`),
  compareStrategies: (batchId?: string) => {
    const qs = batchId ? `?batch_id=${batchId}` : ''
    return request<{ strategies: Record<string, EvaluationRun>; comparison_table: unknown[] }>(
      `/evaluation/compare${qs}`
    )
  },

  // Audit
  getAuditEvents: (params: Record<string, string | number>) => {
    const qs = new URLSearchParams(
      Object.fromEntries(
        Object.entries(params)
          .filter(([, v]) => v !== undefined && v !== '')
          .map(([k, v]) => [k, String(v)])
      )
    ).toString()
    return request<PaginatedResponse<AuditEvent>>(`/audit${qs ? '?' + qs : ''}`)
  },

  // Policy
  getPolicy: () => request<PolicyConfig>('/policy'),
  updatePolicy: (data: Partial<PolicyConfig>) =>
    request<{ status: string }>('/policy', {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  resetPolicy: () => request<{ status: string }>('/policy/reset', { method: 'POST' }),
}
