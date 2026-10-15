// ─── Core domain types ────────────────────────────────────────────────────────

export interface Transaction {
  id: string
  external_id?: string
  batch_id?: string
  merchant_id: string
  customer_ref: string
  amount: number
  currency: string
  transaction_type: 'payment' | 'subscription' | 'invoice' | 'checkout'
  status: 'pending' | 'success' | 'failed' | 'abandoned' | 'overdue' | 'cancelled'
  failure_reason?: string
  failure_category?: FailureCategory
  failure_timestamp?: string
  retry_count: number
  risk_score?: number
  recoverability: 'recoverable' | 'non_recoverable' | 'requires_review' | 'unknown' | 'not_applicable'
  recovery_status: 'pending' | 'in_progress' | 'recovered' | 'failed' | 'blocked' | 'human_review' | 'closed'
  payment_method?: string
  gateway?: string
  is_synthetic: boolean
  created_at: string
  updated_at: string
}

export type FailureCategory =
  | 'temp_failure'
  | 'insufficient_funds'
  | 'auth_required'
  | 'invalid_details'
  | 'fraud'
  | 'unknown'

export interface RecoveryCase {
  id: string
  transaction_id: string
  merchant_id: string
  customer_ref: string
  batch_id?: string
  category: string
  state: RecoveryCaseState
  at_risk_amount: number
  estimated_recoverable_amount: number
  recovered_amount: number
  currency: string
  priority: 'critical' | 'high' | 'medium' | 'low'
  risk_score?: number
  action_count: number
  requires_human_review: boolean
  human_review_reason?: string
  close_reason?: string
  is_simulated: boolean
  created_at: string
  latest_recommendation?: string
  recommendations?: RecoveryRecommendation[]
  actions?: RecoveryAction[]
}

export type RecoveryCaseState =
  | 'DETECTED'
  | 'DIAGNOSED'
  | 'RECOMMENDED'
  | 'POLICY_CHECKED'
  | 'APPROVAL_REQUIRED'
  | 'APPROVED'
  | 'EXECUTING'
  | 'SUCCEEDED'
  | 'FAILED'
  | 'BLOCKED'
  | 'HUMAN_REVIEW'
  | 'CLOSED'

export interface RecoveryRecommendation {
  id: string
  recommended_action: string
  reason: string
  evidence?: string
  confidence: number
  expected_recovery_value?: number
  estimated_cost?: number
  potential_customer_impact?: string
  requires_human_approval: boolean
  source: 'rule_based' | 'ai_assisted' | 'ai_fallback'
  status: 'pending' | 'approved' | 'rejected' | 'executed' | 'superseded'
  created_at: string
}

export interface RecoveryAction {
  id: string
  action_type: string
  execution_mode: string
  status: string
  policy_allowed: boolean
  policy_reason?: string
  executed_at?: string
  recovered_amount?: number
  is_duplicate_prevented: boolean
  error_details?: string
  created_at: string
}

export interface DashboardMetrics {
  total_transactions: number
  total_gross_value: number
  total_revenue_at_risk: number
  estimated_recoverable_value: number
  actual_recovered_value: number
  recovery_rate?: number
  recovery_success_rate?: number
  failed_payment_count: number
  abandoned_checkout_count: number
  failed_subscription_count: number
  overdue_receivable_count: number
  recovery_actions_executed: number
  blocked_actions: number
  human_review_count: number
  recovery_trend: TrendPoint[]
  failure_reason_distribution: PieSlice[]
  revenue_at_risk_by_category: CategoryBar[]
  recovery_funnel: FunnelStage[]
  recent_activity: ActivityItem[]
  high_priority_cases: HighPriorityCase[]
}

export interface TrendPoint { date: string; recovered: number; at_risk: number }
export interface PieSlice { name: string; value: number }
export interface CategoryBar { category: string; value: number }
export interface FunnelStage { stage: string; count: number }
export interface ActivityItem {
  id: string
  event_type: string
  transaction_id?: string
  actor: string
  timestamp: string
  outcome?: string
}
export interface HighPriorityCase {
  id: string
  transaction_id: string
  category: string
  priority: string
  at_risk_amount: number
  currency: string
  state: string
}

export interface EvaluationRun {
  id: string
  name: string
  strategy: 'baseline' | 'fixed_rule' | 'ai_assisted'
  status: 'pending' | 'running' | 'completed' | 'failed'
  random_seed: number
  total_transaction_count: number
  total_transaction_value: number
  eligible_at_risk_count: number
  total_revenue_at_risk: number
  estimated_recoverable_value: number
  successful_recoveries: number
  simulated_recovered_value: number
  recovery_rate_by_count?: number
  recovery_rate_by_value?: number
  retry_success_rate?: number
  action_failure_rate?: number
  blocked_action_count: number
  duplicate_prevented_count: number
  human_review_count: number
  customer_contact_count: number
  estimated_intervention_cost: number
  net_simulated_recovery_value: number
  false_positive_intervention_count: number
  precision?: number
  recall?: number
  false_positive_rate?: number
  results_by_category?: Record<string, { count: number; recovered: number; value: number }>
  started_at?: string
  completed_at?: string
  created_at: string
}

export interface AuditEvent {
  id: string
  created_at: string
  batch_id?: string
  transaction_id?: string
  recovery_case_id?: string
  agent_run_id?: string
  previous_state?: string
  new_state?: string
  event_type: string
  actor: string
  detected_risk?: string
  evidence_used?: unknown
  recommendation?: string
  policy_rules_evaluated?: unknown
  policy_decision?: string
  approval_details?: unknown
  action_attempted?: string
  execution_mode?: string
  action_result?: unknown
  error_details?: string
  final_outcome?: string
}

export interface BatchImport {
  id: string
  filename: string
  status: string
  total_rows: number
  valid_rows: number
  invalid_rows: number
  imported_rows: number
  is_synthetic: boolean
  created_at: string
  completed_at?: string
}

export interface PolicyConfig {
  id: string
  merchant_id: string
  max_retry_attempts: number
  min_retry_delay_hours: number
  max_recovery_actions_per_txn: number
  max_reminders_per_customer_per_week: number
  require_communication_consent: boolean
  approval_threshold_amount: number
  retryable_failure_categories: string[]
  non_retryable_categories: string[]
  batch_max_actions: number
  updated_at: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface AppSettings {
  app_name: string
  version: string
  environment: string
  ai_provider: string
  payment_provider: string
  is_live_payment: boolean
  default_currency: string
  max_retry_attempts: number
  approval_threshold_inr: number
  llm_configured: boolean
  razorpay_configured: boolean
}
