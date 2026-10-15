interface PaginationProps {
  page: number
  totalPages: number
  total: number
  pageSize: number
  onPage: (p: number) => void
}

export function Pagination({ page, totalPages, total, pageSize, onPage }: PaginationProps) {
  const start = (page - 1) * pageSize + 1
  const end = Math.min(page * pageSize, total)
  return (
    <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
      <p className="text-sm text-gray-500">
        Showing {start}–{end} of {total}
      </p>
      <div className="flex gap-2">
        <button
          onClick={() => onPage(page - 1)}
          disabled={page <= 1}
          className="btn-secondary py-1 px-3 text-xs disabled:opacity-40"
        >
          ← Prev
        </button>
        <span className="flex items-center px-3 text-sm text-gray-600">
          {page} / {totalPages}
        </span>
        <button
          onClick={() => onPage(page + 1)}
          disabled={page >= totalPages}
          className="btn-secondary py-1 px-3 text-xs disabled:opacity-40"
        >
          Next →
        </button>
      </div>
    </div>
  )
}
