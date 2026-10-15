import { clsx } from 'clsx'

interface MetricCardProps {
  title: string
  value: string | number
  subtitle?: string
  trend?: { value: number; label: string }
  icon?: React.ReactNode
  variant?: 'default' | 'success' | 'warning' | 'danger'
  note?: string
  loading?: boolean
}

const variantClasses = {
  default: 'border-gray-200',
  success: 'border-green-200 bg-green-50',
  warning: 'border-yellow-200 bg-yellow-50',
  danger:  'border-red-200 bg-red-50',
}

export function MetricCard({
  title, value, subtitle, trend, icon, variant = 'default', note, loading,
}: MetricCardProps) {
  return (
    <div className={clsx('card p-5 flex flex-col gap-2', variantClasses[variant])}>
      <div className="flex items-start justify-between">
        <p className="text-sm font-medium text-gray-500">{title}</p>
        {icon && <span className="text-gray-400">{icon}</span>}
      </div>

      {loading ? (
        <div className="h-8 w-24 bg-gray-200 rounded animate-pulse" />
      ) : (
        <p className="text-2xl font-bold text-gray-900 tabular-nums">{value}</p>
      )}

      {subtitle && <p className="text-xs text-gray-500">{subtitle}</p>}

      {trend && (
        <p className={clsx('text-xs font-medium', trend.value >= 0 ? 'text-green-600' : 'text-red-600')}>
          {trend.value >= 0 ? '↑' : '↓'} {Math.abs(trend.value).toFixed(1)}% {trend.label}
        </p>
      )}

      {note && (
        <p className="text-xs text-gray-400 border-t border-gray-100 pt-2 mt-1">{note}</p>
      )}
    </div>
  )
}
