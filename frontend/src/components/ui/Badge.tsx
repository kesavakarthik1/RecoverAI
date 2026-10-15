import { clsx } from 'clsx'

type Variant = 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'purple'

const variantClasses: Record<Variant, string> = {
  success: 'bg-green-100 text-green-800',
  warning: 'bg-yellow-100 text-yellow-800',
  danger:  'bg-red-100 text-red-800',
  info:    'bg-blue-100 text-blue-800',
  neutral: 'bg-gray-100 text-gray-700',
  purple:  'bg-purple-100 text-purple-800',
}

interface BadgeProps {
  children: React.ReactNode
  variant?: Variant
  className?: string
}

export function Badge({ children, variant = 'neutral', className }: BadgeProps) {
  return (
    <span className={clsx('badge', variantClasses[variant], className)}>
      {children}
    </span>
  )
}

// ── Domain-specific badges ───────────────────────────────────────────────────

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, Variant> = {
    success: 'success', recovered: 'success', completed: 'success',
    pending: 'warning', in_progress: 'info', human_review: 'purple',
    failed: 'danger', blocked: 'danger', abandoned: 'warning',
    overdue: 'danger', cancelled: 'neutral', closed: 'neutral',
  }
  return <Badge variant={map[status] ?? 'neutral'}>{status.replace(/_/g, ' ')}</Badge>
}

export function RecoveryStateBadge({ state }: { state: string }) {
  const map: Record<string, Variant> = {
    DETECTED: 'info', DIAGNOSED: 'info', RECOMMENDED: 'warning',
    POLICY_CHECKED: 'warning', APPROVAL_REQUIRED: 'warning',
    APPROVED: 'info', EXECUTING: 'purple',
    SUCCEEDED: 'success', FAILED: 'danger', BLOCKED: 'danger',
    HUMAN_REVIEW: 'purple', CLOSED: 'neutral',
  }
  return <Badge variant={map[state] ?? 'neutral'}>{state}</Badge>
}

export function PriorityBadge({ priority }: { priority: string }) {
  const map: Record<string, Variant> = {
    critical: 'danger', high: 'warning', medium: 'info', low: 'neutral',
  }
  return <Badge variant={map[priority] ?? 'neutral'}>{priority}</Badge>
}

export function CategoryBadge({ category }: { category: string }) {
  const labels: Record<string, string> = {
    temp_failure: 'Temp Failure', insufficient_funds: 'Insuff. Funds',
    auth_required: 'Auth Required', invalid_details: 'Invalid Details',
    fraud: 'Fraud/Security', unknown: 'Unknown',
  }
  const map: Record<string, Variant> = {
    temp_failure: 'warning', insufficient_funds: 'danger',
    auth_required: 'info', invalid_details: 'danger',
    fraud: 'danger', unknown: 'neutral',
  }
  return <Badge variant={map[category] ?? 'neutral'}>{labels[category] ?? category}</Badge>
}
